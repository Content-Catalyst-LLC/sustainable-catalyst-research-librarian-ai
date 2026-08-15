(() => {
  'use strict';
  const cfg = window.SCRLPlatformV7 || {};
  const root = document.querySelector('[data-sc-rl-v7-workspace]');
  if (!root || !cfg.authenticated || !cfg.root) return;

  const run = root.querySelector('[data-sc-rl-v760-workspace-run]');
  const panel = root.querySelector('[data-sc-rl-v760-workspace-panel]');
  const form = root.querySelector('[data-sc-rl-v760-workspace-form]');
  const status = root.querySelector('[data-sc-rl-v760-workspace-status]');
  const content = root.querySelector('[data-sc-rl-v760-workspace-content]');
  const contextSelect = root.querySelector('[data-sc-rl-v720-context-select]');
  const roomSelect = root.querySelector('[data-sc-rl-v750-room-select]');
  let currentPromotion = null;

  const esc = value => String(value ?? '').replace(/[&<>'"]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[ch]));
  const titleCase = value => String(value || '').replace(/[-_]/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

  async function request(path, options = {}) {
    const response = await fetch(cfg.root + path.replace(/^\//, ''), {
      credentials: 'same-origin',
      ...options,
      headers: { 'Content-Type': 'application/json', 'X-WP-Nonce': cfg.nonce, ...(options.headers || {}) }
    });
    let body = {};
    try { body = await response.json(); } catch (_) { body = {}; }
    if (!response.ok) throw new Error(body?.message || body?.data?.message || body?.detail || `Request failed (${response.status})`);
    return body;
  }

  function scopePayload() {
    const contextId = String(contextSelect?.value || '');
    const roomId = contextId ? '' : String(roomSelect?.value || '');
    return { context_id: contextId, room_id: roomId };
  }

  function downloadPacket(promotion) {
    const packet = promotion?.packet || {};
    const filename = `research-librarian-${promotion.artifact_type || 'workspace'}-${promotion.promotion_id || 'handoff'}.json`;
    const blob = new Blob([JSON.stringify(packet, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = filename; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
  }

  function renderPromotion(promotion) {
    currentPromotion = promotion || null;
    if (!content || !promotion) return;
    const packet = promotion.packet || {};
    const sources = Array.isArray(packet.sources) ? packet.sources : [];
    const questions = Array.isArray(packet.open_questions) ? packet.open_questions : [];
    const scopes = Array.isArray(packet.research_context?.scopes) ? packet.research_context.scopes.join(', ') : '';
    content.innerHTML = `<article class="sc-rl-v760-promotion-card">
      <div class="sc-rl-v760-promotion-heading"><div><span>${esc(titleCase(promotion.status || 'prepared'))}</span><h4>${esc(promotion.title || 'Workspace handoff')}</h4><p>${esc(titleCase(promotion.artifact_type || 'notebook'))} · ${sources.length} source${sources.length === 1 ? '' : 's'} · ${questions.length} open question${questions.length === 1 ? '' : 's'}</p></div><code>${esc(String(promotion.packet_fingerprint || '').slice(0, 16))}</code></div>
      <dl><div><dt>Context</dt><dd>${esc(packet.research_context?.title || scopes || 'Library scope')}</dd></div><div><dt>Project</dt><dd>${esc(packet.project?.title || 'No project')}</dd></div><div><dt>Room</dt><dd>${esc(packet.research_context?.room_id || 'No room')}</dd></div><div><dt>Import contract</dt><dd>${esc(packet.workspace_import_contract || '')}</dd></div></dl>
      <p class="sc-rl-v760-boundary"><strong>Promotion boundary:</strong> this packet is a research snapshot, not publication, editorial approval, or a truth judgment. Source ownership/scope and Research Room attribution remain intact.</p>
      <div class="sc-rl-v760-actions"><button type="button" data-sc-rl-v760-download>Download handoff JSON</button><a href="${esc(cfg.workspaceUrl || '/workspace/')}" target="_blank" rel="noopener">Open Workspace</a></div>
    </article>`;
  }

  function renderHistory(body) {
    if (!content) return;
    const promotions = Array.isArray(body?.promotions) ? body.promotions : [];
    if (!promotions.length) { content.innerHTML = '<p>No Workspace handoffs have been prepared yet.</p>'; return; }
    const rows = promotions.slice(0, 12).map(item => `<button type="button" class="sc-rl-v760-history-item" data-sc-rl-v760-promotion-id="${esc(item.promotion_id)}"><span>${esc(titleCase(item.artifact_type))}</span><strong>${esc(item.title)}</strong><small>${esc(titleCase(item.status))} · ${esc(item.updated_utc || '')}</small></button>`).join('');
    content.innerHTML = `<div class="sc-rl-v760-history"><h4>Recent promotion outbox</h4>${rows}</div>`;
  }

  async function loadHistory() {
    const body = await request('workspace/promotions?limit=50');
    renderHistory(body);
  }

  run?.addEventListener('click', async () => {
    panel.hidden = false; run.disabled = true;
    try { await loadHistory(); }
    catch (e) { if (content) content.innerHTML = `<div class="sc-rl-v7-error"><strong>Workspace handoff unavailable</strong><p>${esc(e.message)}</p></div>`; }
    finally { run.disabled = false; }
  });

  form?.addEventListener('submit', async event => {
    event.preventDefault();
    const data = new FormData(form);
    const scope = scopePayload();
    if (!scope.context_id && !scope.room_id) {
      if (status) status.textContent = 'Choose or create a saved Librarian context, or select a Research Room, before preparing a handoff.';
      return;
    }
    if (status) status.textContent = 'Preparing governed Workspace handoff…';
    try {
      const promotion = await request('workspace/promotions', { method:'POST', body:JSON.stringify({
        ...scope,
        artifact_type: data.get('artifact_type') || 'notebook',
        title: data.get('title') || '',
        notes: data.get('notes') || '',
        include_rejected: data.get('include_rejected') === '1',
        selected_object_ids: []
      }) });
      renderPromotion(promotion);
      if (status) status.textContent = 'Workspace handoff prepared. Nothing has been published or imported automatically.';
    } catch (e) { if (status) status.textContent = e.message; }
  });

  content?.addEventListener('click', async event => {
    const history = event.target.closest('[data-sc-rl-v760-promotion-id]');
    if (history) {
      try { renderPromotion(await request(`workspace/promotions/${encodeURIComponent(history.dataset.scRlV760PromotionId)}`)); }
      catch (e) { window.alert(e.message); }
      return;
    }
    const download = event.target.closest('[data-sc-rl-v760-download]');
    if (download && currentPromotion) {
      downloadPacket(currentPromotion);
      if (String(currentPromotion.status || '') === 'prepared') {
        try {
          currentPromotion = await request(`workspace/promotions/${encodeURIComponent(currentPromotion.promotion_id)}/receipt`, { method:'POST', body:JSON.stringify({
            packet_fingerprint: currentPromotion.packet_fingerprint,
            status: 'exported',
            workspace_artifact_type: currentPromotion.artifact_type,
            workspace_url: cfg.workspaceUrl || ''
          }) });
          renderPromotion(currentPromotion);
        } catch (_) { /* local download still succeeded; receipt can be retried later */ }
      }
    }
  });
})();
