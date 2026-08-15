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
  const qualityRun = root.querySelector('[data-sc-rl-v730-quality-run]');
  const qualityPanel = root.querySelector('[data-sc-rl-v730-quality-panel]');
  const qualityContent = root.querySelector('[data-sc-rl-v730-quality-content]');
  const stateRun = root.querySelector('[data-sc-rl-v740-state-run]');
  const statePanel = root.querySelector('[data-sc-rl-v740-state-panel]');
  const stateContent = root.querySelector('[data-sc-rl-v740-state-content]');
  const questionForm = root.querySelector('[data-sc-rl-v740-question-form]');
  const questionCancel = root.querySelector('[data-sc-rl-v740-question-cancel]');
  const questionStatus = root.querySelector('[data-sc-rl-v740-question-status]');
  const headers = { 'Content-Type': 'application/json', 'X-WP-Nonce': cfg.nonce };
  let projects = [];
  let contexts = [];
  let stateQuestions = [];

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
    if (qualityPanel) qualityPanel.hidden = true;
    if (statePanel) statePanel.hidden = true;
    if (questionForm) questionForm.hidden = true;
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

  function renderQuality(body) {
    if (!qualityPanel || !qualityContent) return;
    qualityPanel.hidden = false;
    const summary = body && body.summary ? body.summary : {};
    const corpus = summary.corpus || {};
    const gapsBody = body && body.gaps ? body.gaps : {};
    const comparison = body && body.comparison ? body.comparison : {};
    const sources = Array.isArray(comparison.sources) ? comparison.sources : [];
    const gaps = Array.isArray(gapsBody.gaps) ? gapsBody.gaps : [];
    const levelText = Object.entries(corpus.evidence_levels || {}).map(([key,value]) => `${value} ${titleCase(key)}`).join(' · ') || 'Not classified';
    const methodText = Object.entries(corpus.methodology_states || {}).map(([key,value]) => `${value} ${titleCase(key)}`).join(' · ') || 'Not documented';
    const gapMarkup = gaps.length ? `<div class="sc-rl-v730-gap-list">${gaps.slice(0,8).map(g => `<article data-severity="${escapeHTML(g.severity)}"><span>${escapeHTML(g.severity)}</span><strong>${escapeHTML(titleCase(g.category))}</strong><p>${escapeHTML(g.statement)}</p><small>${escapeHTML(g.suggested_action)}</small></article>`).join('')}</div>` : '<div class="sc-rl-v730-no-gaps"><strong>No structural gaps detected by this metadata check.</strong><p>This does not prove the source set is complete or correct; human review is still required.</p></div>';
    const sourceMarkup = sources.length ? `<div class="sc-rl-v730-source-grid">${sources.slice(0,8).map(source => `<article data-object-id="${escapeHTML(source.object_id || '')}"><span>${escapeHTML(titleCase(source.evidence_level || 'unknown'))}</span><strong>${escapeHTML(source.title)}</strong><dl><div><dt>Type</dt><dd>${escapeHTML(source.source_type || 'Unknown')}</dd></div><div><dt>Publisher</dt><dd>${escapeHTML(source.publisher || source.institution || 'Not provided')}</dd></div><div><dt>Date</dt><dd>${escapeHTML(source.publication_date || 'Not provided')}</dd></div><div><dt>Methods</dt><dd>${escapeHTML(titleCase(source.methodology?.state || 'unknown'))}</dd></div><div><dt>Citation</dt><dd>${source.citation?.available ? 'Available' : 'Not provided'}</dd></div><div><dt>Access</dt><dd>${escapeHTML(titleCase(source.access_state || 'unknown'))}</dd></div></dl>${Array.isArray(source.limitations) && source.limitations.length ? `<p><b>Limitations:</b> ${escapeHTML(source.limitations.slice(0,2).join(' · '))}</p>` : '<p><b>Limitations:</b> Not documented.</p>'}${source.object_id ? `<div class="sc-rl-v740-source-actions" aria-label="Research state actions"><button type="button" data-sc-rl-v740-reading="reading">Reading</button><button type="button" data-sc-rl-v740-reading="reviewed">Reviewed</button><button type="button" data-sc-rl-v740-reading="rejected">Reject</button><button type="button" data-sc-rl-v740-contradiction="flagged">Flag contradiction</button></div>` : ''}</article>`).join('')}</div>` : '<p>No source objects were resolved for this context.</p>';
    qualityContent.innerHTML = `<div class="sc-rl-v730-quality-summary"><article><span>${Number(body.source_count || 0)}</span><strong>Sources</strong></article><article><span>${Number(corpus.independent_provider_count || 0)}</span><strong>Distinct providers</strong></article><article><span>${Number(summary.gap_count || 0)}</span><strong>Structural gaps</strong></article></div><div class="sc-rl-v730-quality-meta"><p><strong>Evidence levels:</strong> ${escapeHTML(levelText)}</p><p><strong>Methodology:</strong> ${escapeHTML(methodText)}</p></div><h4>Evidence gaps</h4>${gapMarkup}<h4>Source profiles</h4>${sourceMarkup}<p class="sc-rl-v730-governance-note"><strong>Interpretation boundary:</strong> These signals describe metadata completeness, provenance, methods visibility, access, citation state, and source mix. They are not a truth score, credibility score, or independent verification.</p>`;
  }

  function activeContext() {
    const id = contextSelect ? String(contextSelect.value || '') : '';
    return contexts.find(context => String(context.context_id || '') === id) || null;
  }

  function stateItemTitle(item) {
    return String(item?.object_title || item?.title || item?.object_id || 'Library object');
  }

  function renderState(body) {
    if (!statePanel || !stateContent) return;
    statePanel.hidden = false;
    const counts = body && body.counts ? body.counts : {};
    const reading = counts.reading_states || {};
    const contradiction = counts.contradiction_states || {};
    const questions = counts.question_states || {};
    const searches = Array.isArray(body?.recent_searches) ? body.recent_searches : [];
    const reviewQueue = Array.isArray(body?.review_queue) ? body.review_queue : [];
    const rejected = Array.isArray(body?.rejected_objects) ? body.rejected_objects : [];
    const flagged = Array.isArray(body?.flagged_contradictions) ? body.flagged_contradictions : [];
    stateQuestions = Array.isArray(body?.open_questions) ? body.open_questions : [];

    const listMarkup = (items, empty, renderer) => items.length
      ? `<div class="sc-rl-v740-state-list">${items.slice(0,12).map(renderer).join('')}</div>`
      : `<p class="sc-rl-v740-state-empty">${escapeHTML(empty)}</p>`;
    const searchMarkup = listMarkup(searches, 'No saved-context searches have been recorded yet.', item => `<article><strong>${escapeHTML(item.query || 'Research search')}</strong><small>${escapeHTML(item.created_utc || '')}</small></article>`);
    const queueMarkup = listMarkup(reviewQueue, 'Nothing is waiting for review.', item => `<article><strong>${escapeHTML(stateItemTitle(item))}</strong><span>${escapeHTML(titleCase(item.reading_state || 'unread'))}</span></article>`);
    const rejectedMarkup = listMarkup(rejected, 'No objects are currently rejected.', item => `<article><strong>${escapeHTML(stateItemTitle(item))}</strong><span>Rejected</span></article>`);
    const contradictionMarkup = listMarkup(flagged, 'No contradiction flags are open.', item => `<article><strong>${escapeHTML(stateItemTitle(item))}</strong><span>Needs review</span><button type="button" data-sc-rl-v740-state-object="${escapeHTML(item.object_id || '')}" data-sc-rl-v740-contradiction="resolved">Resolve flag</button></article>`);
    const questionMarkup = listMarkup(stateQuestions, 'No open research questions.', item => `<article data-question-id="${escapeHTML(item.question_id || '')}"><strong>${escapeHTML(item.question || 'Open question')}</strong><div class="sc-rl-v740-state-actions"><button type="button" data-sc-rl-v740-question-status="resolved">Resolve</button><button type="button" data-sc-rl-v740-question-status="deferred">Defer</button></div></article>`);

    stateContent.innerHTML = `<div class="sc-rl-v740-state-summary"><article><span>${Number(counts.activities || 0)}</span><strong>Activity events</strong></article><article><span>${Number(questions.open || stateQuestions.length || 0)}</span><strong>Open questions</strong></article><article><span>${Number((reading.unread || 0) + (reading.reading || 0))}</span><strong>Review queue</strong></article><article><span>${Number(reading.rejected || 0)}</span><strong>Rejected</strong></article><article><span>${Number(contradiction.flagged || 0)}</span><strong>Contradictions</strong></article></div><div class="sc-rl-v740-state-grid"><section><h4>Recent searches</h4>${searchMarkup}</section><section><h4>Review queue</h4>${queueMarkup}</section><section><h4>Open questions</h4><button type="button" class="sc-rl-v740-question-new" data-sc-rl-v740-question-new>Add question</button>${questionMarkup}</section><section><h4>Rejected objects</h4>${rejectedMarkup}</section><section><h4>Contradiction flags</h4>${contradictionMarkup}</section></div><p class="sc-rl-v740-governance-note"><strong>Research-state boundary:</strong> This is inspectable workflow memory, not evidence. Rejected objects remain in provenance, and open questions are not treated as facts or assumptions.</p>`;
  }

  async function loadResearchState() {
    if (!statePanel || !stateContent) return;
    const context = activeContext();
    statePanel.hidden = false;
    if (!context || !context.context_id) {
      stateContent.innerHTML = '<div class="sc-rl-v740-state-empty"><strong>Select a saved context first.</strong><p>Research state is owner-scoped and is only persisted for an authenticated Library, project, room, or saved research context.</p></div>';
      return;
    }
    stateContent.innerHTML = '<p>Loading persistent research state…</p>';
    if (stateRun) stateRun.disabled = true;
    try {
      const body = await request(`state?context_id=${encodeURIComponent(context.context_id)}`);
      renderState(body);
    } catch (e) {
      stateContent.innerHTML = `<div class="sc-rl-v7-error"><strong>Research state unavailable</strong><p>${escapeHTML(e.message)}</p></div>`;
    } finally {
      if (stateRun) stateRun.disabled = false;
    }
  }

  async function saveObjectState(objectId, patch) {
    const context = activeContext();
    if (!context || !context.context_id || !objectId) throw new Error('Select a saved context and a Library object first.');
    return request('state/object', {
      method: 'POST',
      body: JSON.stringify({ context_id: context.context_id, project_id: context.project_id || '', object_id: objectId, ...patch })
    });
  }

  async function saveQuestion(question) {
    const context = activeContext();
    if (!context || !context.context_id) throw new Error('Select a saved context before changing its question register.');
    return request('state/questions', {
      method: 'POST',
      body: JSON.stringify({ context_id: context.context_id, project_id: context.project_id || '', ...question })
    });
  }

  async function evaluateActiveContext() {
    if (!qualityPanel || !qualityContent) return;
    const id = contextSelect ? String(contextSelect.value || '') : '';
    qualityPanel.hidden = false;
    if (!id) {
      qualityContent.innerHTML = '<div class="sc-rl-v730-no-gaps"><strong>Select a saved context first.</strong><p>Create or select My Library, Current Project, Current Research Room, or an authenticated editorial context before running a source evaluation.</p></div>';
      return;
    }
    qualityContent.innerHTML = '<p>Evaluating source metadata and evidence structure…</p>';
    if (qualityRun) qualityRun.disabled = true;
    try {
      const body = await request(`contexts/${encodeURIComponent(id)}/evidence-quality`);
      renderQuality(body);
    } catch (e) {
      qualityContent.innerHTML = `<div class="sc-rl-v7-error"><strong>Evidence review unavailable</strong><p>${escapeHTML(e.message)}</p></div>`;
    } finally {
      if (qualityRun) qualityRun.disabled = false;
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
        const activityCount = Array.isArray(body.research_activity) ? body.research_activity.length : 0;
        const questionCount = Array.isArray(body.open_questions) ? body.open_questions.filter(item => String(item.status || 'open') === 'open').length : 0;
        const reviewCount = Array.isArray(body.object_states) ? body.object_states.filter(item => ['unread','reading'].includes(String(item.reading_state || 'unread'))).length : 0;
        detail.innerHTML = `<strong>Project context</strong><dl><div><dt>Investigations</dt><dd>${investigationCount}</dd></div><div><dt>Library objects</dt><dd>${objectCount}</dd></div><div><dt>Project entities</dt><dd>${entityCount}</dd></div><div><dt>Research activity</dt><dd>${activityCount}</dd></div><div><dt>Open questions</dt><dd>${questionCount}</dd></div><div><dt>Review queue</dt><dd>${reviewCount}</dd></div></dl><p>Library references and research state retain their original scope and remain distinct from verified evidence.</p>`;
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

  qualityRun?.addEventListener('click', evaluateActiveContext);
  stateRun?.addEventListener('click', loadResearchState);

  qualityContent?.addEventListener('click', async event => {
    const card = event.target.closest('[data-object-id]');
    if (!card) return;
    const objectId = String(card.dataset.objectId || '');
    const readingButton = event.target.closest('[data-sc-rl-v740-reading]');
    const contradictionButton = event.target.closest('[data-sc-rl-v740-contradiction]');
    if (!readingButton && !contradictionButton) return;
    event.target.disabled = true;
    try {
      if (readingButton) await saveObjectState(objectId, { reading_state: readingButton.dataset.scRlV740Reading || '' });
      if (contradictionButton) await saveObjectState(objectId, { contradiction_state: contradictionButton.dataset.scRlV740Contradiction || '' });
      await loadResearchState();
    } catch (e) {
      window.alert(e.message);
    } finally {
      event.target.disabled = false;
    }
  });

  stateContent?.addEventListener('click', async event => {
    if (event.target.closest('[data-sc-rl-v740-question-new]')) {
      if (questionForm) questionForm.hidden = false;
      const field = questionForm?.querySelector('textarea[name="question"], input[name="question"]');
      field?.focus();
      return;
    }
    const contradictionButton = event.target.closest('[data-sc-rl-v740-contradiction]');
    if (contradictionButton) {
      const objectId = String(contradictionButton.closest('[data-sc-rl-v740-state-object]')?.dataset.scRlV740StateObject || '');
      contradictionButton.disabled = true;
      try { await saveObjectState(objectId, { contradiction_state: contradictionButton.dataset.scRlV740Contradiction || 'resolved' }); await loadResearchState(); }
      catch (e) { window.alert(e.message); }
      finally { contradictionButton.disabled = false; }
      return;
    }
    const statusButton = event.target.closest('[data-sc-rl-v740-question-status]');
    if (!statusButton) return;
    const item = statusButton.closest('[data-question-id]');
    const questionId = String(item?.dataset.questionId || '');
    const existing = stateQuestions.find(question => String(question.question_id || '') === questionId);
    if (!existing) return;
    statusButton.disabled = true;
    try {
      await saveQuestion({ question_id: questionId, question: existing.question, status: statusButton.dataset.scRlV740QuestionStatus || 'open', linked_object_ids: existing.linked_object_ids || [], resolution: existing.resolution || '' });
      await loadResearchState();
    } catch (e) { window.alert(e.message); }
    finally { statusButton.disabled = false; }
  });

  questionForm?.addEventListener('submit', async event => {
    event.preventDefault();
    const data = new FormData(questionForm);
    const question = String(data.get('question') || '').trim();
    if (!question) { if (questionStatus) questionStatus.textContent = 'Enter a research question.'; return; }
    if (questionStatus) questionStatus.textContent = 'Saving question…';
    try {
      await saveQuestion({ question, status: 'open', linked_object_ids: [] });
      questionForm.reset();
      questionForm.hidden = true;
      if (questionStatus) questionStatus.textContent = '';
      await loadResearchState();
    } catch (e) { if (questionStatus) questionStatus.textContent = e.message; }
  });
  questionCancel?.addEventListener('click', () => { if (questionForm) questionForm.hidden = true; if (questionStatus) questionStatus.textContent = ''; });

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
