(function () {
  'use strict';
  var cfg = window.SCRLAdaptive;
  if (!cfg || !window.fetch) return;
  var key = 'sc_rl_adaptive_v580';
  function loadState() { try { return JSON.parse(localStorage.getItem(key) || '{}'); } catch (e) { return {}; } }
  function saveState(s) { try { localStorage.setItem(key, JSON.stringify(s)); } catch (e) {} }
  function today() { return new Date().toISOString().slice(0, 10); }
  function allowed(ruleId) {
    var s = loadState(), now = Date.now(), day = today();
    if (s.day !== day) { s.day = day; s.count = 0; }
    if ((s.count || 0) >= (cfg.settings.dailyCap || 2)) return false;
    if (s.dismissed && s.dismissed[ruleId] && now < s.dismissed[ruleId]) return false;
    if (s.lastShown && now - s.lastShown < (cfg.settings.cooldownHours || 24) * 3600000) return false;
    return true;
  }
  function markShown() { var s = loadState(); s.day = today(); s.count = (s.count || 0) + 1; s.lastShown = Date.now(); saveState(s); }
  function markDismissed(id) { var s = loadState(); s.dismissed = s.dismissed || {}; s.dismissed[id] = Date.now() + (cfg.settings.dismissDays || 14) * 86400000; saveState(s); }
  function post(url, data) { return fetch(url, {method:'POST', credentials:'same-origin', headers:{'Content-Type':'application/json','X-WP-Nonce':cfg.nonce}, body:JSON.stringify(data)}).then(function(r){return r.json().then(function(j){if(!r.ok) throw new Error(j.message || 'Request failed'); return j;});}); }
  function context(host, extra) {
    extra = extra || {};
    return {
      trigger: extra.trigger || host.getAttribute('data-trigger') || 'always',
      route_id: extra.route_id || host.getAttribute('data-route') || document.body.getAttribute('data-sc-rl-route') || '',
      query_topic: extra.query_topic || host.getAttribute('data-topic') || '',
      confidence: Number(extra.confidence || document.body.getAttribute('data-sc-rl-confidence') || 0),
      source_count: Number(extra.source_count || document.body.getAttribute('data-sc-rl-source-count') || 0),
      session_ref: extra.session_ref || '', answer_ref: extra.answer_ref || '', article_map: extra.article_map || '',
      consent: extra.consent !== undefined ? !!extra.consent : host.getAttribute('data-consent') !== 'false',
      page_url: window.location.href
    };
  }
  function render(host, result, ctx) {
    var x = result.experience; if (!x || !allowed(x.id)) return;
    host.innerHTML = '<section class="sc-rl-adaptive-card" role="region" aria-labelledby="sc-rl-adaptive-title-'+x.id+'"><button type="button" class="sc-rl-adaptive-close" aria-label="Dismiss">×</button><p class="sc-rl-adaptive-kicker">Research experience</p><h3 id="sc-rl-adaptive-title-'+x.id+'"></h3><p class="sc-rl-adaptive-message"></p><div class="sc-rl-adaptive-rating" hidden><label>Rating (1–5) <input type="number" min="1" max="5"></label></div><label class="sc-rl-adaptive-response">Your response<textarea rows="4"></textarea></label><div class="sc-rl-adaptive-actions"><button type="button" class="sc-rl-adaptive-primary"></button><button type="button" class="sc-rl-adaptive-later">Not now</button></div><p class="sc-rl-adaptive-status" aria-live="polite"></p></section>';
    var card=host.firstElementChild, title=card.querySelector('h3'), msg=card.querySelector('.sc-rl-adaptive-message'), primary=card.querySelector('.sc-rl-adaptive-primary'), status=card.querySelector('.sc-rl-adaptive-status');
    title.textContent=x.title || 'Help improve this research experience'; msg.textContent=x.message || ''; primary.textContent=x.button_label || 'Continue';
    if (x.experience_type === 'survey' || x.experience_type === 'feature_suggestion') card.querySelector('.sc-rl-adaptive-rating').hidden=false;
    markShown();
    function respond(action) {
      status.textContent='Saving…';
      return post(cfg.respondUrl,{rule_id:x.id,receipt:result.receipt,action:action,route_id:ctx.route_id,query_topic:ctx.query_topic,session_ref:ctx.session_ref,answer_ref:ctx.answer_ref,response:card.querySelector('textarea').value,rating:card.querySelector('input[type=number]').value}).then(function(data){
        if (x.destination_url && (action==='submitted'||action==='handoff')) window.location.href=x.destination_url + (x.destination_url.indexOf('?')<0?'?':'&') + 'sc_rl_receipt=' + encodeURIComponent(result.receipt);
        else { status.textContent='Thank you. Your response was recorded.'; setTimeout(function(){host.innerHTML='';},1200); }
        return data;
      }).catch(function(e){status.textContent=e.message;});
    }
    primary.addEventListener('click',function(){respond(x.experience_type==='inline_feedback'?'submitted':'handoff');});
    card.querySelector('.sc-rl-adaptive-later').addEventListener('click',function(){respond('later'); host.innerHTML='';});
    card.querySelector('.sc-rl-adaptive-close').addEventListener('click',function(){markDismissed(x.id); respond('dismissed'); host.innerHTML='';});
  }
  function evaluate(host, extra) {
    var ctx=context(host,extra); setTimeout(function(){post(cfg.evaluateUrl,ctx).then(function(r){if(r.eligible) render(host,r,ctx);}).catch(function(){});},(cfg.settings.minimumSeconds||0)*1000);
  }
  function hosts() { return Array.prototype.slice.call(document.querySelectorAll('[data-sc-rl-adaptive-host]')); }
  document.addEventListener('DOMContentLoaded',function(){hosts().forEach(function(h){evaluate(h);});});
  document.addEventListener('sc:research-librarian:adaptive-context',function(e){var hs=hosts(); if(!hs.length){var h=document.createElement('div');h.setAttribute('data-sc-rl-adaptive-host','');document.body.appendChild(h);hs=[h];}hs.forEach(function(h){evaluate(h,e.detail||{});});});
  window.SCRLAdaptiveEvaluate=function(detail){document.dispatchEvent(new CustomEvent('sc:research-librarian:adaptive-context',{detail:detail||{}}));};
})();
