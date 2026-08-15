(() => {
  'use strict';
  const config = window.SCRLPlatformV7 || {};
  const workspace = document.querySelector('[data-sc-rl-v7-workspace]');
  if (!workspace || !config.authenticated) return;

  const run = workspace.querySelector('[data-sc-rl-v770-federation-run]');
  const panel = workspace.querySelector('[data-sc-rl-v770-federation-panel]');
  const form = workspace.querySelector('[data-sc-rl-v770-federation-form]');
  const status = workspace.querySelector('[data-sc-rl-v770-federation-status]');
  const content = workspace.querySelector('[data-sc-rl-v770-federation-content]');
  const history = workspace.querySelector('[data-sc-rl-v770-history]');
  const contextSelect = workspace.querySelector('[data-sc-rl-v720-context-select]');
  if (!run || !panel || !form || !content) return;

  let activeSearch = null;

  const root = String(config.root || '').replace(/\/+$/, '') + '/';
  async function request(path, options = {}) {
    const headers = Object.assign({ 'Accept': 'application/json' }, options.headers || {});
    if (options.method && options.method !== 'GET') {
      headers['Content-Type'] = 'application/json';
      headers['X-WP-Nonce'] = config.nonce || '';
    }
    const response = await fetch(root + path.replace(/^\/+/, ''), Object.assign({ credentials: 'same-origin', headers }, options));
    let body = {};
    try { body = await response.json(); } catch (_) { body = {}; }
    if (!response.ok) throw new Error(body.message || body.detail || `Federated research request failed (${response.status}).`);
    return body;
  }

  function contextId() { return String(contextSelect?.value || ''); }
  function clear(node) { while (node.firstChild) node.removeChild(node.firstChild); }
  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }
  function dateLabel(value) {
    const date = new Date(value || '');
    return Number.isNaN(date.getTime()) ? String(value || '') : date.toLocaleString();
  }
  function accessLabel(result) {
    const access = result && typeof result.access === 'object' ? result.access : {};
    if (access.is_open_access || access.state === 'open') return 'Open access';
    if (access.state && access.state !== 'unknown') return String(access.state).replace(/-/g, ' ');
    return 'Access unknown';
  }

  function providerBadges(result) {
    const wrap = el('div', 'sc-rl-v770-provider-badges');
    const providers = Array.isArray(result.providers) && result.providers.length ? result.providers : [result.provider_id].filter(Boolean);
    providers.forEach(provider => wrap.appendChild(el('span', 'sc-rl-v770-provider', provider)));
    return wrap;
  }

  function renderSearch(search) {
    activeSearch = search;
    clear(content);
    const top = el('div', 'sc-rl-v770-search-summary');
    const heading = el('div');
    heading.appendChild(el('strong', '', search.query || 'Federated search'));
    heading.appendChild(el('small', '', `${search.result_count || (search.results || []).length || 0} normalized results · ${String(search.status || 'complete')} · ${dateLabel(search.created_utc)}`));
    top.appendChild(heading);
    const failures = Array.isArray(search.provider_outcomes) ? search.provider_outcomes.filter(item => item && item.ok === false) : [];
    if (failures.length) top.appendChild(el('p', 'sc-rl-v770-provider-failures', `Provider issues: ${failures.map(item => item.provider_id || item.provider || 'provider').join(', ')}. Partial results remain visible.`));
    content.appendChild(top);

    const results = Array.isArray(search.results) ? search.results : [];
    if (!results.length) {
      content.appendChild(el('p', '', 'No external records matched this search. Provider status and the saved search remain available for audit.'));
      return;
    }
    const list = el('div', 'sc-rl-v770-results');
    results.forEach(result => {
      const card = el('article', 'sc-rl-v770-result');
      card.dataset.resultId = String(result.result_id || '');
      card.appendChild(providerBadges(result));
      card.appendChild(el('h4', '', result.title || 'Untitled external record'));
      const meta = [
        Array.isArray(result.authors) && result.authors.length ? result.authors.slice(0, 4).join(', ') : '',
        result.published_year || '',
        result.record_type || '',
        accessLabel(result),
      ].filter(Boolean).join(' · ');
      card.appendChild(el('p', 'sc-rl-v770-result-meta', meta));
      if (result.abstract) card.appendChild(el('p', 'sc-rl-v770-result-abstract', String(result.abstract).slice(0, 700)));
      const actions = el('div', 'sc-rl-v770-result-actions');
      if (result.landing_url) {
        const link = el('a', '', 'Open provider record');
        link.href = result.landing_url;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        actions.appendChild(link);
      }
      const save = el('button', '', 'Save to My Library');
      save.type = 'button';
      save.dataset.scRlV770Save = String(result.result_id || '');
      actions.appendChild(save);
      card.appendChild(actions);
      const note = el('small', 'sc-rl-v770-boundary', 'External discovery only. Saving creates a private external-reference object; it does not create editorial approval or a truth judgment.');
      card.appendChild(note);
      list.appendChild(card);
    });
    content.appendChild(list);
  }

  function renderHistory(body) {
    clear(content);
    const searches = Array.isArray(body.searches) ? body.searches : [];
    if (!searches.length) { content.appendChild(el('p', '', 'No saved federated searches yet.')); return; }
    const list = el('div', 'sc-rl-v770-history-list');
    searches.forEach(search => {
      const item = el('button', 'sc-rl-v770-history-item');
      item.type = 'button';
      item.dataset.searchId = String(search.search_id || '');
      item.appendChild(el('strong', '', search.query || 'Federated search'));
      item.appendChild(el('small', '', `${search.result_count || (search.results || []).length || 0} results · ${dateLabel(search.created_utc)}`));
      list.appendChild(item);
    });
    content.appendChild(list);
  }

  run.addEventListener('click', () => {
    panel.hidden = !panel.hidden;
    if (!panel.hidden) form.querySelector('input[name="query"]')?.focus();
  });

  form.addEventListener('submit', async event => {
    event.preventDefault();
    const data = new FormData(form);
    const query = String(data.get('query') || '').trim();
    if (query.length < 2) { if (status) status.textContent = 'Enter a research query.'; return; }
    const providers = Array.from(form.querySelectorAll('input[name="providers"]:checked')).map(input => input.value);
    if (!providers.length) { if (status) status.textContent = 'Choose at least one external provider.'; return; }
    if (status) status.textContent = 'Searching external research providers…';
    content.setAttribute('aria-busy', 'true');
    try {
      const body = await request('federation/searches', { method: 'POST', body: JSON.stringify({ query, context_id: contextId(), providers, limit_per_provider: 8, result_limit: 40 }) });
      renderSearch(body);
      if (status) status.textContent = body.status === 'partial' ? 'Search complete with provider issues. Partial results are preserved.' : 'Federated search complete.';
    } catch (error) {
      if (status) status.textContent = error.message;
    } finally { content.removeAttribute('aria-busy'); }
  });

  history?.addEventListener('click', async () => {
    if (status) status.textContent = 'Loading recent federated searches…';
    try {
      const suffix = contextId() ? `&context_id=${encodeURIComponent(contextId())}` : '';
      const body = await request(`federation/searches?limit=20${suffix}`);
      renderHistory(body);
      if (status) status.textContent = 'Recent federated searches loaded.';
    } catch (error) { if (status) status.textContent = error.message; }
  });

  content.addEventListener('click', async event => {
    const historyItem = event.target.closest('[data-search-id]');
    if (historyItem) {
      try { renderSearch(await request(`federation/searches/${encodeURIComponent(historyItem.dataset.searchId || '')}`)); }
      catch (error) { if (status) status.textContent = error.message; }
      return;
    }
    const button = event.target.closest('[data-sc-rl-v770-save]');
    if (!button || !activeSearch?.search_id) return;
    button.disabled = true;
    const old = button.textContent;
    button.textContent = 'Saving…';
    try {
      const body = await request(`federation/searches/${encodeURIComponent(activeSearch.search_id)}/results/${encodeURIComponent(button.dataset.scRlV770Save || '')}/save`, { method: 'POST', body: JSON.stringify({ context_id: contextId(), tags: ['federated-discovery'] }) });
      button.textContent = 'Saved to My Library';
      button.dataset.savedObjectId = String(body.library_object?.object_id || '');
      if (status) status.textContent = 'Saved as a private external-reference Library object with provider provenance preserved.';
    } catch (error) {
      button.disabled = false;
      button.textContent = old;
      if (status) status.textContent = error.message;
    }
  });
})();
