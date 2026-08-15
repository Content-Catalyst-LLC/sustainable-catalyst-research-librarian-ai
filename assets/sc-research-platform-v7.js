(() => {
  'use strict';
  const cfg = window.SCRLPlatformV7 || {};
  const root = document.querySelector('[data-sc-rl-v7-workspace]');
  if (!root || !cfg.authenticated) return;

  const list = root.querySelector('[data-sc-rl-v7-projects]');
  const form = root.querySelector('[data-sc-rl-v7-project-form]');
  const status = root.querySelector('[data-sc-rl-v7-form-status]');
  const refresh = root.querySelector('[data-sc-rl-v7-refresh]');
  const librarySummary = root.querySelector('[data-sc-rl-v720-library-summary]');
  const contextSelect = root.querySelector('[data-sc-rl-v720-context-select]');
  const contextLabel = root.querySelector('[data-sc-rl-v720-context-label]');
  const contextDetail = root.querySelector('[data-sc-rl-v720-context-detail]');
  const contextNew = root.querySelector('[data-sc-rl-v720-context-new]');
  const contextForm = root.querySelector('[data-sc-rl-v720-context-form]');
  const contextCancel = root.querySelector('[data-sc-rl-v720-context-cancel]');
  const contextStatus = root.querySelector('[data-sc-rl-v720-context-status]');
  const contextProject = root.querySelector('[data-sc-rl-v720-context-project]');
  const headers = { 'Content-Type': 'application/json', 'X-WP-Nonce': cfg.nonce };
  let projects = [];
  let contexts = [];

  const escapeHTML = value => String(value || '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
  const titleCase = value => String(value || '').replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

  async function request(path, options = {}) {
    const response = await fetch(cfg.root + path, { credentials: 'same-origin', ...options, headers: { ...headers, ...(options.headers || {}) } });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.message || body.detail || 'The research workspace request failed.');
    return body;
  }

  function setActiveContext(id, label, detail) {
    const contextId = String(id || '');
    const contextName = String(label || 'Sustainable Catalyst Collection');
    try {
      if (contextId) {
        window.localStorage.setItem('sc_rl_research_context_v720', contextId);
        window.localStorage.setItem('sc_rl_research_context_label_v720', contextName);
      } else {
        window.localStorage.removeItem('sc_rl_research_context_v720');
        window.localStorage.removeItem('sc_rl_research_context_label_v720');
      }
    } catch (e) {}
    if (contextLabel) contextLabel.textContent = contextName;
    if (contextDetail) contextDetail.textContent = detail || (contextId ? 'This context will be carried into authenticated Research Librarian questions.' : 'Public editorial collection only.');
    if (contextSelect) contextSelect.value = contextId;
    window.dispatchEvent(new CustomEvent('sc-rl-context-changed', { detail: { contextId, label: contextName } }));
  }

  function renderProjects(items) {
    projects = items || [];
    if (contextProject) {
      contextProject.innerHTML = '<option value="">No project</option>' + projects.map(p => `<option value="${escapeHTML(p.project_id)}">${escapeHTML(p.title)}</option>`).join('');
    }
    if (!projects.length) {
      list.innerHTML = '<div class="sc-rl-v7-empty"><strong>No persistent projects yet.</strong><p>Create the first project to begin a connected investigation.</p></div>';
      return;
    }
    list.innerHTML = `<div class="sc-rl-v7-project-grid">${projects.map(p => `<article class="sc-rl-v7-project-card" data-project-id="${escapeHTML(p.project_id)}"><span>${escapeHTML(p.status)}</span><h4>${escapeHTML(p.title)}</h4><p>${escapeHTML(p.objective || 'No objective recorded yet.')}</p><div class="sc-rl-v720-project-actions"><button type="button" data-context>Use as context</button><button type="button" data-open>Open project</button><button type="button" data-backup>Export backup</button></div><div hidden data-project-detail class="sc-rl-v720-project-detail"></div></article>`).join('')}</div>`;
  }

  function renderLibrary(objects) {
    if (!librarySummary) return;
    const rows = Array.isArray(objects) ? objects : [];
    const counts = rows.reduce((acc, item) => { const key = item.object_type || 'source'; acc[key] = (acc[key] || 0) + 1; return acc; }, {});
    if (!rows.length) {
      librarySummary.innerHTML = '<strong>Library objects</strong><p>No private Library objects have been synchronized to Research Librarian yet. Public editorial retrieval remains available.</p>';
      return;
    }
    const chips = Object.keys(counts).sort().map(key => `<span><b>${counts[key]}</b> ${escapeHTML(titleCase(key))}</span>`).join('');
    librarySummary.innerHTML = `<strong>My Library · ${rows.length} objects</strong><div class="sc-rl-v720-object-counts">${chips}</div><p>These objects retain their personal Library identity and are not treated as Sustainable Catalyst editorial recommendations.</p>`;
  }

  function renderContexts(body) {
    contexts = Array.isArray(body && body.contexts) ? body.contexts : [];
    const active = body && body.active ? body.active : null;
    if (contextSelect) {
      contextSelect.innerHTML = '<option value="">Sustainable Catalyst Collection</option>' + contexts.map(c => `<option value="${escapeHTML(c.context_id)}">${escapeHTML(c.title)}</option>`).join('');
    }
    let stored = '';
    try { stored = window.localStorage.getItem('sc_rl_research_context_v720') || ''; } catch (e) {}
    const selected = contexts.find(c => c.context_id === stored) || active;
    if (selected) {
      const scopes = Array.isArray(selected.scopes) ? selected.scopes.map(titleCase).join(' · ') : 'Authenticated context';
      setActiveContext(selected.context_id, selected.title, scopes);
    } else {
      setActiveContext('', 'Sustainable Catalyst Collection', 'Public editorial collection only.');
    }
  }

  async function loadAll() {
    if (list) list.setAttribute('aria-busy', 'true');
    try {
      const [projectBody, libraryBody, contextBody] = await Promise.all([
        request('projects'),
        request('library/objects?limit=500'),
        request('contexts')
      ]);
      renderProjects(projectBody.projects || []);
      renderLibrary(libraryBody.objects || []);
      renderContexts(contextBody || {});
    } catch (e) {
      if (list) list.innerHTML = `<div class="sc-rl-v7-error"><strong>Research workspace unavailable</strong><p>${escapeHTML(e.message)}</p></div>`;
      if (librarySummary) librarySummary.innerHTML = `<strong>Library object status unavailable</strong><p>${escapeHTML(e.message)}</p>`;
    } finally {
      if (list) list.removeAttribute('aria-busy');
    }
  }

  async function createProjectContext(project) {
    const body = await request('contexts', {
      method: 'POST',
      body: JSON.stringify({
        title: project.title,
        scopes: ['sustainable-catalyst-collection', 'my-library', 'current-project'],
        project_id: project.project_id,
        active: true
      })
    });
    await loadContextsOnly(body.context_id);
  }

  async function loadContextsOnly(preferredId) {
    const body = await request('contexts');
    renderContexts(body);
    if (preferredId) {
      const selected = (body.contexts || []).find(c => c.context_id === preferredId);
      if (selected) setActiveContext(selected.context_id, selected.title, (selected.scopes || []).map(titleCase).join(' · '));
    }
  }

  form?.addEventListener('submit', async event => {
    event.preventDefault();
    const data = new FormData(form);
    status.textContent = 'Creating project…';
    try {
      await request('projects', { method:'POST', body:JSON.stringify({title:data.get('title'), objective:data.get('objective')}) });
      form.reset(); status.textContent='Project created.'; await loadAll();
    } catch(e) { status.textContent=e.message; }
  });

  refresh?.addEventListener('click', loadAll);

  list?.addEventListener('click', async event => {
    const card = event.target.closest('[data-project-id]');
    if (!card) return;
    const id = card.dataset.projectId;
    const project = projects.find(p => p.project_id === id) || { project_id:id, title:'Project research' };
    if (event.target.matches('[data-context]')) {
      event.target.disabled = true;
      try { await createProjectContext(project); }
      catch (e) { window.alert(e.message); }
      finally { event.target.disabled = false; }
    }
    if (event.target.matches('[data-open]')) {
      const detail = card.querySelector('[data-project-detail]');
      try {
        const body = await request(`projects/${encodeURIComponent(id)}`);
        const objectCount = Array.isArray(body.library_objects) ? body.library_objects.length : 0;
        const investigationCount = Array.isArray(body.investigations) ? body.investigations.length : 0;
        const entityCount = Array.isArray(body.entities) ? body.entities.length : 0;
        detail.innerHTML = `<strong>Project context</strong><dl><div><dt>Investigations</dt><dd>${investigationCount}</dd></div><div><dt>Library objects</dt><dd>${objectCount}</dd></div><div><dt>Project entities</dt><dd>${entityCount}</dd></div></dl><p>Library references remain linked to their original source scope rather than copied into a generic evidence bucket.</p>`;
        detail.hidden = false;
      } catch(e) { detail.textContent=e.message; detail.hidden=false; }
    }
    if (event.target.matches('[data-backup]')) {
      try {
        const body = await request(`projects/${encodeURIComponent(id)}/backup`, { method:'POST', body:'{}' });
        const blob = new Blob([JSON.stringify(body,null,2)], {type:'application/json'});
        const a = document.createElement('a'); a.href=URL.createObjectURL(blob); a.download=`research-project-${id}.json`; a.click(); setTimeout(()=>URL.revokeObjectURL(a.href),2000);
      } catch(e) { window.alert(e.message); }
    }
  });

  contextSelect?.addEventListener('change', async () => {
    const id = contextSelect.value;
    if (!id) { setActiveContext('', 'Sustainable Catalyst Collection', 'Public editorial collection only.'); return; }
    const selected = contexts.find(c => c.context_id === id);
    if (!selected) return;
    try {
      const updated = await request('contexts', { method:'POST', body:JSON.stringify({ ...selected, active:true }) });
      setActiveContext(updated.context_id, updated.title, (updated.scopes || []).map(titleCase).join(' · '));
    } catch (e) { if (contextDetail) contextDetail.textContent = e.message; }
  });

  contextNew?.addEventListener('click', () => { if (contextForm) contextForm.hidden = false; });
  contextCancel?.addEventListener('click', () => { if (contextForm) contextForm.hidden = true; });
  contextForm?.addEventListener('submit', async event => {
    event.preventDefault();
    const data = new FormData(contextForm);
    const scope = String(data.get('scope') || 'my-library');
    const projectId = scope === 'current-project' ? String(data.get('project_id') || '') : '';
    if (scope === 'current-project' && !projectId) { contextStatus.textContent = 'Choose a project for Current Project context.'; return; }
    contextStatus.textContent = 'Saving context…';
    try {
      const body = await request('contexts', { method:'POST', body:JSON.stringify({ title:data.get('title'), scopes:[scope], project_id:projectId, active:true }) });
      contextStatus.textContent = 'Context saved.';
      contextForm.hidden = true;
      await loadContextsOnly(body.context_id);
    } catch (e) { contextStatus.textContent = e.message; }
  });

  loadAll();
})();
