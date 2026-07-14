(() => {
  'use strict';
  const cfg = window.SCRLPlatformV7 || {};
  const root = document.querySelector('[data-sc-rl-v7-workspace]');
  if (!root || !cfg.authenticated) return;
  const list = root.querySelector('[data-sc-rl-v7-projects]');
  const form = root.querySelector('[data-sc-rl-v7-project-form]');
  const status = root.querySelector('[data-sc-rl-v7-form-status]');
  const headers = { 'Content-Type': 'application/json', 'X-WP-Nonce': cfg.nonce };
  const escapeHTML = value => String(value || '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
  async function request(path, options = {}) {
    const response = await fetch(cfg.root + path, { credentials: 'same-origin', ...options, headers: { ...headers, ...(options.headers || {}) } });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.message || body.detail || 'The research workspace request failed.');
    return body;
  }
  function render(projects) {
    if (!projects.length) { list.innerHTML = '<div class="sc-rl-v7-empty"><strong>No persistent projects yet.</strong><p>Create the first project to begin a connected investigation.</p></div>'; return; }
    list.innerHTML = `<div class="sc-rl-v7-project-grid">${projects.map(p => `<article class="sc-rl-v7-project-card" data-project-id="${escapeHTML(p.project_id)}"><span>${escapeHTML(p.status)}</span><h4>${escapeHTML(p.title)}</h4><p>${escapeHTML(p.objective || 'No objective recorded yet.')}</p><div><button type="button" data-open>Open project</button><button type="button" data-backup>Export backup</button></div><pre hidden data-project-detail></pre></article>`).join('')}</div>`;
  }
  async function load() { list.setAttribute('aria-busy','true'); try { const body = await request('projects'); render(body.projects || []); } catch (e) { list.innerHTML = `<div class="sc-rl-v7-error"><strong>Projects unavailable</strong><p>${escapeHTML(e.message)}</p></div>`; } finally { list.removeAttribute('aria-busy'); } }
  form?.addEventListener('submit', async event => { event.preventDefault(); const data = new FormData(form); status.textContent = 'Creating project…'; try { await request('projects', { method:'POST', body:JSON.stringify({title:data.get('title'),objective:data.get('objective')}) }); form.reset(); status.textContent='Project created.'; await load(); } catch(e) { status.textContent=e.message; } });
  root.querySelector('[data-sc-rl-v7-refresh]')?.addEventListener('click', load);
  list?.addEventListener('click', async event => { const card=event.target.closest('[data-project-id]'); if(!card) return; const id=card.dataset.projectId; if(event.target.matches('[data-open]')) { const pre=card.querySelector('[data-project-detail]'); try { const body=await request(`projects/${encodeURIComponent(id)}`); pre.textContent=JSON.stringify(body,null,2); pre.hidden=false; } catch(e){ pre.textContent=e.message; pre.hidden=false; } } if(event.target.matches('[data-backup]')) { try { const body=await request(`projects/${encodeURIComponent(id)}/backup`,{method:'POST',body:'{}'}); const blob=new Blob([JSON.stringify(body,null,2)],{type:'application/json'}); const a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download=`research-project-${id}.json`; a.click(); setTimeout(()=>URL.revokeObjectURL(a.href),2000); } catch(e){ window.alert(e.message); } } });
  load();
})();
