(() => {
  'use strict';
  const cfg = window.SCRLPlatformV7 || {};
  const root = document.querySelector('[data-sc-rl-v7-workspace]');
  if (!root || !cfg.authenticated) return;

  const run = root.querySelector('[data-sc-rl-v800-lifecycle-run]');
  const panel = root.querySelector('[data-sc-rl-v800-lifecycle-panel]');
  const select = root.querySelector('[data-sc-rl-v800-lifecycle-select]');
  const refresh = root.querySelector('[data-sc-rl-v800-lifecycle-refresh]');
  const create = root.querySelector('[data-sc-rl-v800-lifecycle-create]');
  const status = root.querySelector('[data-sc-rl-v800-lifecycle-status]');
  const content = root.querySelector('[data-sc-rl-v800-lifecycle-content]');
  if (!run || !panel || !select || !content) return;

  const headers = { 'Content-Type': 'application/json', 'X-WP-Nonce': cfg.nonce };
  const stages = ['frame', 'discover', 'evaluate', 'organize', 'collaborate', 'synthesize', 'promote', 'preserve'];
  let lifecycles = [];

  const esc = value => String(value || '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
  const titleCase = value => String(value || '').replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  const contextId = () => {
    try { return window.localStorage.getItem('sc_rl_research_context_v720') || ''; } catch (e) { return ''; }
  };

  async function request(path, options = {}) {
    const response = await fetch(cfg.root + path, { credentials: 'same-origin', ...options, headers: { ...headers, ...(options.headers || {}) } });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.message || body.detail || 'The research lifecycle request failed.');
    return body;
  }

  function stageCard(stage, summary) {
    const readiness = summary?.stage_readiness?.[stage] || {};
    const current = String(summary?.current_stage || '') === stage;
    const ready = !!readiness.ready;
    const optional = !!readiness.optional;
    const blockers = Array.isArray(readiness.blockers) ? readiness.blockers : [];
    return `<article class="sc-rl-v800-stage${current ? ' is-current' : ''}${ready ? ' is-ready' : ''}">
      <div><span>${current ? 'Current' : (ready ? 'Ready' : (optional ? 'Optional' : 'Needs work'))}</span><strong>${esc(titleCase(stage))}</strong></div>
      ${blockers.length ? `<p>${esc(blockers[0])}</p>` : '<p>Current research signals satisfy this stage’s descriptive readiness check.</p>'}
      ${current ? '' : `<button type="button" data-sc-rl-v800-transition="${esc(stage)}">Move to ${esc(titleCase(stage))}</button>`}
    </article>`;
  }

  function render(body) {
    const summary = body?.summary || {};
    const signals = summary.signals || {};
    const actions = Array.isArray(summary.recommended_actions) ? summary.recommended_actions : [];
    const checkpoints = Array.isArray(body?.checkpoints) ? body.checkpoints : [];
    const events = Array.isArray(body?.events) ? body.events : [];
    content.innerHTML = `<div class="sc-rl-v800-lifecycle-heading">
      <div><span>${esc(titleCase(body.status || 'active'))} · Human-confirmed</span><h4>${esc(body.title || 'Research lifecycle')}</h4><p>Current stage: <strong>${esc(titleCase(summary.current_stage || body.current_stage || 'frame'))}</strong>. Readiness is workflow guidance only.</p></div>
      <button type="button" data-sc-rl-v800-checkpoint>Create checkpoint</button>
    </div>
    <div class="sc-rl-v800-lifecycle-metrics">
      <article><span>${Number(signals.saved_sources || 0)}</span><strong>Saved sources</strong></article>
      <article><span>${Number(signals.reviewed_sources || 0)}</span><strong>Reviewed</strong></article>
      <article><span>${Number(signals.open_questions || 0)}</span><strong>Open questions</strong></article>
      <article><span>${Number(signals.checkpoints || checkpoints.length || 0)}</span><strong>Checkpoints</strong></article>
    </div>
    <div class="sc-rl-v800-stage-grid">${stages.map(stage => stageCard(stage, summary)).join('')}</div>
    <section class="sc-rl-v800-next-actions"><h4>Next actions</h4>${actions.length ? `<ol>${actions.map(item => `<li><strong>${esc(titleCase(item.stage || ''))}:</strong> ${esc(item.action || '')}</li>`).join('')}</ol>` : '<p>No deterministic next action is currently required.</p>'}</section>
    <section class="sc-rl-v800-lineage"><h4>Lifecycle lineage</h4><p>${events.length} recorded lifecycle events · ${checkpoints.length} immutable checkpoints.</p></section>
    <p class="sc-rl-v800-boundary"><strong>Governance boundary:</strong> lifecycle stage, readiness, and checkpoints are inspectable workflow metadata. They are not evidence, a truth score, editorial approval, or publication.</p>`;

    content.querySelectorAll('[data-sc-rl-v800-transition]').forEach(button => button.addEventListener('click', async () => {
      const target = String(button.dataset.scRlV800Transition || '');
      const currentSummary = body.summary || {};
      const blockerRows = currentSummary.stage_readiness?.[target]?.blockers || [];
      const blockerText = blockerRows.length ? `\n\nReadiness notes:\n- ${blockerRows.join('\n- ')}` : '';
      if (!window.confirm(`Move this research lifecycle to ${titleCase(target)}? This is an explicit workflow transition and does not certify the research.${blockerText}`)) return;
      const reason = window.prompt('Optional transition note or reason:', '') || '';
      button.disabled = true;
      try {
        const next = await request(`lifecycles/${encodeURIComponent(body.lifecycle_id)}/transition`, { method: 'POST', body: JSON.stringify({ target_stage: target, reason, confirmed: true, blockers_acknowledged: blockerRows }) });
        await load(next.lifecycle_id || body.lifecycle_id);
      } catch (error) { window.alert(error.message); }
      finally { button.disabled = false; }
    }));

    const checkpoint = content.querySelector('[data-sc-rl-v800-checkpoint]');
    if (checkpoint) checkpoint.addEventListener('click', async () => {
      const note = window.prompt('Checkpoint note (optional):', '') || '';
      checkpoint.disabled = true;
      try {
        await request(`lifecycles/${encodeURIComponent(body.lifecycle_id)}/checkpoint`, { method: 'POST', body: JSON.stringify({ note }) });
        await load(body.lifecycle_id);
      } catch (error) { window.alert(error.message); }
      finally { checkpoint.disabled = false; }
    });
  }

  async function load(id) {
    const lifecycleId = String(id || select.value || '');
    if (!lifecycleId) { content.innerHTML = '<p>Create or select a lifecycle to inspect stage readiness and next actions.</p>'; return; }
    content.innerHTML = '<p>Loading unified research lifecycle…</p>';
    try {
      const body = await request(`lifecycles/${encodeURIComponent(lifecycleId)}`);
      render(body);
    } catch (error) { content.innerHTML = `<p>${esc(error.message)}</p>`; }
  }

  async function loadList(preferred = '') {
    const body = await request('lifecycles?limit=100');
    lifecycles = Array.isArray(body.lifecycles) ? body.lifecycles : [];
    select.innerHTML = '<option value="">Choose a lifecycle</option>' + lifecycles.map(item => `<option value="${esc(item.lifecycle_id)}">${esc(item.title || 'Research lifecycle')} · ${esc(titleCase(item.current_stage || 'frame'))}</option>`).join('');
    const wanted = String(preferred || select.value || '');
    if (wanted && lifecycles.some(item => item.lifecycle_id === wanted)) select.value = wanted;
  }

  run.addEventListener('click', async () => {
    panel.hidden = !panel.hidden;
    if (panel.hidden) return;
    try { await loadList(); if (select.value) await load(select.value); } catch (error) { content.innerHTML = `<p>${esc(error.message)}</p>`; }
  });
  refresh?.addEventListener('click', async () => { try { await loadList(select.value); await load(select.value); } catch (error) { content.innerHTML = `<p>${esc(error.message)}</p>`; } });
  select.addEventListener('change', () => load(select.value));

  create?.addEventListener('submit', async event => {
    event.preventDefault();
    const data = new FormData(create);
    if (status) status.textContent = 'Creating lifecycle…';
    try {
      const body = await request('lifecycles', { method: 'POST', body: JSON.stringify({ title: String(data.get('title') || 'Research lifecycle'), context_id: contextId(), current_stage: 'frame', status: 'active' }) });
      if (status) status.textContent = 'Lifecycle created.';
      await loadList(body.lifecycle_id);
      select.value = body.lifecycle_id;
      await load(body.lifecycle_id);
    } catch (error) { if (status) status.textContent = error.message; }
  });
})();
