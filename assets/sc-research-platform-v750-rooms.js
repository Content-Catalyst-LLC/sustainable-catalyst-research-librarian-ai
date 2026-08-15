(() => {
  'use strict';
  const cfg = window.SCRLPlatformV7 || {};
  const root = document.querySelector('[data-sc-rl-v7-workspace]');
  if (!root || !cfg.authenticated) return;

  const run = root.querySelector('[data-sc-rl-v750-room-run]');
  const panel = root.querySelector('[data-sc-rl-v750-room-panel]');
  const select = root.querySelector('[data-sc-rl-v750-room-select]');
  const refresh = root.querySelector('[data-sc-rl-v750-room-refresh]');
  const content = root.querySelector('[data-sc-rl-v750-room-content]');
  const createForm = root.querySelector('[data-sc-rl-v750-room-create]');
  const createStatus = root.querySelector('[data-sc-rl-v750-room-create-status]');
  const roomProject = root.querySelector('[data-sc-rl-v750-room-project]');
  const memberForm = root.querySelector('[data-sc-rl-v750-member-form]');
  const memberStatus = root.querySelector('[data-sc-rl-v750-member-status]');
  const evidenceForm = root.querySelector('[data-sc-rl-v750-evidence-form]');
  const evidenceStatus = root.querySelector('[data-sc-rl-v750-evidence-status]');
  const roomObject = root.querySelector('[data-sc-rl-v750-room-object]');
  const questionForm = root.querySelector('[data-sc-rl-v750-room-question-form]');
  const questionStatus = root.querySelector('[data-sc-rl-v750-room-question-status]');
  const disagreementForm = root.querySelector('[data-sc-rl-v750-disagreement-form]');
  const disagreementStatus = root.querySelector('[data-sc-rl-v750-disagreement-status]');
  const contextRoom = root.querySelector('[data-sc-rl-v750-context-room]');
  const headers = { 'Content-Type': 'application/json', 'X-WP-Nonce': cfg.nonce };

  let rooms = [];
  let libraryObjects = [];
  let projects = [];
  let currentBundle = null;
  let currentSynthesis = null;
  let currentQuestions = [];
  let currentDisagreements = [];
  let editingDisagreement = null;

  const escapeHTML = value => String(value || '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
  const titleCase = value => String(value || '').replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

  async function request(path, options = {}) {
    const response = await fetch(cfg.root + path, { credentials: 'same-origin', ...options, headers: { ...headers, ...(options.headers || {}) } });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.message || body.detail || 'The Research Room request failed.');
    return body;
  }

  function currentRoomId() { return select ? String(select.value || '') : ''; }
  function currentMember() { return currentBundle && currentBundle.current_member ? currentBundle.current_member : {}; }
  function roleCanWrite() { return ['owner','editor','researcher'].includes(String(currentMember().role || 'viewer')); }
  function roleCanManage() { return ['owner','editor'].includes(String(currentMember().role || 'viewer')); }

  function populateSelects() {
    const roomOptions = '<option value="">Choose a room</option>' + rooms.map(room => `<option value="${escapeHTML(room.room_id)}">${escapeHTML(room.title || 'Research Room')}</option>`).join('');
    if (select) {
      const previous = select.value;
      select.innerHTML = roomOptions;
      if (rooms.some(room => room.room_id === previous)) select.value = previous;
    }
    if (contextRoom) {
      const previous = contextRoom.value;
      contextRoom.innerHTML = '<option value="">No Research Room</option>' + rooms.map(room => `<option value="${escapeHTML(room.room_id)}">${escapeHTML(room.title || 'Research Room')}</option>`).join('');
      if (rooms.some(room => room.room_id === previous)) contextRoom.value = previous;
    }
    if (roomProject) roomProject.innerHTML = '<option value="">No project</option>' + projects.map(project => `<option value="${escapeHTML(project.project_id)}">${escapeHTML(project.title)}</option>`).join('');
    if (roomObject) roomObject.innerHTML = '<option value="">Choose a Library object</option>' + libraryObjects.map(item => `<option value="${escapeHTML(item.object_id)}">${escapeHTML(item.title || item.object_id)} · ${escapeHTML(titleCase(item.source_scope || 'my-library'))}</option>`).join('');
  }

  function setRoomFormsVisible() {
    const hasRoom = Boolean(currentRoomId() && currentBundle);
    if (memberForm) memberForm.hidden = !(hasRoom && roleCanManage());
    if (evidenceForm) evidenceForm.hidden = !(hasRoom && roleCanWrite());
    if (questionForm) questionForm.hidden = !(hasRoom && roleCanWrite());
    if (disagreementForm) disagreementForm.hidden = !(hasRoom && roleCanWrite());
  }

  function memberName(ref) {
    const members = Array.isArray(currentBundle?.members) ? currentBundle.members : [];
    const member = members.find(item => String(item.member_ref || '') === String(ref || ''));
    return member ? (member.display_name || titleCase(member.role || 'member')) : String(ref || 'Unknown participant');
  }

  function renderRoom() {
    if (!content) return;
    if (!currentBundle || !currentBundle.room) {
      content.innerHTML = '<p>Create or select a Research Room to inspect shared research state.</p>';
      setRoomFormsVisible();
      return;
    }
    const room = currentBundle.room;
    const members = Array.isArray(currentBundle.members) ? currentBundle.members : [];
    const synthesis = currentSynthesis || currentBundle.synthesis || {};
    const evidence = Array.isArray(synthesis.shared_evidence) ? synthesis.shared_evidence : [];
    const questions = Array.isArray(currentQuestions) ? currentQuestions : [];
    const disagreements = Array.isArray(currentDisagreements) ? currentDisagreements : [];
    const activity = Array.isArray(synthesis.recent_activity) ? synthesis.recent_activity : [];
    const role = String(currentMember().role || 'viewer');
    const counts = synthesis.counts || {};

    const membersMarkup = members.length ? members.map(member => `<article><strong>${escapeHTML(member.display_name || member.member_ref)}</strong><span>${escapeHTML(titleCase(member.role || 'member'))}</span><small>${escapeHTML(titleCase(member.status || 'active'))}</small></article>`).join('') : '<p>No members were returned.</p>';
    const evidenceMarkup = evidence.length ? evidence.map(item => `<article><strong>${escapeHTML(item.title || item.object_id)}</strong><span>${escapeHTML(titleCase(item.state || 'proposed'))}</span><small>Contributed by ${escapeHTML(memberName(item.contributed_by_ref))} · Original scope: ${escapeHTML(titleCase(item.source_scope || 'unknown'))}</small></article>`).join('') : '<p>No evidence has been shared with this room yet.</p>';
    const questionMarkup = questions.length ? questions.map(item => {
      const canDisposition = String(item.created_by_ref || '') === String(currentMember().member_ref || '') || roleCanManage();
      const actions = canDisposition && String(item.status || 'open') === 'open' ? `<div class="sc-rl-v750-inline-actions"><button type="button" data-room-question-id="${escapeHTML(item.question_id)}" data-room-question-status="resolved">Resolve</button><button type="button" data-room-question-id="${escapeHTML(item.question_id)}" data-room-question-status="deferred">Defer</button></div>` : '';
      return `<article><strong>${escapeHTML(item.question)}</strong><span>${escapeHTML(titleCase(item.status || 'open'))}</span><small>Asked by ${escapeHTML(memberName(item.created_by_ref))}</small>${actions}</article>`;
    }).join('') : '<p>No collaborative questions have been recorded.</p>';
    const disagreementMarkup = disagreements.length ? disagreements.map(item => {
      const positions = Array.isArray(item.positions) ? item.positions : [];
      const positionMarkup = positions.length ? positions.map(position => `<li><strong>${escapeHTML(memberName(position.participant_ref))}:</strong> ${escapeHTML(position.position)}</li>`).join('') : '<li>No participant positions yet.</li>';
      const actions = roleCanWrite() ? `<div class="sc-rl-v750-inline-actions"><button type="button" data-room-disagreement-position="${escapeHTML(item.disagreement_id)}">Add/update my position</button>${roleCanManage() && String(item.status || 'open') === 'open' ? `<button type="button" data-room-disagreement-resolve="${escapeHTML(item.disagreement_id)}">Resolve</button>` : ''}</div>` : '';
      return `<article><strong>${escapeHTML(item.statement)}</strong><span>${escapeHTML(titleCase(item.status || 'open'))}</span><ul>${positionMarkup}</ul>${actions}</article>`;
    }).join('') : '<p>No disagreements have been recorded.</p>';
    const activityMarkup = activity.length ? activity.slice(0,10).map(item => `<article><strong>${escapeHTML(titleCase(item.event_type || 'activity'))}</strong><span>${escapeHTML(memberName(item.actor_ref))}</span><small>${escapeHTML(item.created_utc || '')}</small></article>`).join('') : '<p>No recent room activity.</p>';

    content.innerHTML = `<div class="sc-rl-v750-room-heading"><div><span>${escapeHTML(titleCase(room.status || 'active'))} · ${escapeHTML(titleCase(role))}</span><h4>${escapeHTML(room.title)}</h4><p>${escapeHTML(room.objective || 'No shared objective recorded.')}</p></div><button type="button" data-room-use-context>Use as Librarian context</button></div><div class="sc-rl-v750-room-summary"><article><span>${Number(counts.members || members.length || 0)}</span><strong>Members</strong></article><article><span>${evidence.length}</span><strong>Shared evidence</strong></article><article><span>${questions.filter(q => String(q.status || 'open') === 'open').length}</span><strong>Open questions</strong></article><article><span>${disagreements.filter(d => String(d.status || 'open') === 'open').length}</span><strong>Open disagreements</strong></article></div><div class="sc-rl-v750-room-grid"><section><h4>Participants</h4>${membersMarkup}</section><section><h4>Shared evidence state</h4>${evidenceMarkup}</section><section><h4>Collaborative questions</h4>${questionMarkup}</section><section><h4>Disagreements</h4>${disagreementMarkup}</section><section><h4>Recent participant activity</h4>${activityMarkup}</section></div><p class="sc-rl-v750-governance-note"><strong>Collaboration boundary:</strong> Room inclusion is not a truth judgment. A participant position remains attributed to that participant. Room synthesis is workflow context, not verified evidence, and publication still requires human editorial review.</p>`;
    setRoomFormsVisible();
  }

  async function loadBase() {
    const [roomBody, libraryBody, projectBody] = await Promise.all([request('rooms'), request('library/objects?limit=500'), request('projects')]);
    rooms = Array.isArray(roomBody.rooms) ? roomBody.rooms : [];
    libraryObjects = Array.isArray(libraryBody.objects) ? libraryBody.objects : [];
    projects = Array.isArray(projectBody.projects) ? projectBody.projects : [];
    populateSelects();
  }

  async function loadRoom(roomId) {
    const id = String(roomId || currentRoomId());
    if (!id) { currentBundle = null; currentSynthesis = null; currentQuestions = []; currentDisagreements = []; renderRoom(); return; }
    if (content) content.innerHTML = '<p>Loading collaborative Research Room state…</p>';
    const [bundle, synthesis, questionsBody, disagreementsBody] = await Promise.all([
      request(`rooms/${encodeURIComponent(id)}`),
      request(`rooms/${encodeURIComponent(id)}/synthesis`),
      request(`rooms/${encodeURIComponent(id)}/questions`),
      request(`rooms/${encodeURIComponent(id)}/disagreements`)
    ]);
    currentBundle = bundle;
    currentSynthesis = synthesis;
    currentQuestions = Array.isArray(questionsBody.questions) ? questionsBody.questions : [];
    currentDisagreements = Array.isArray(disagreementsBody.disagreements) ? disagreementsBody.disagreements : [];
    renderRoom();
  }

  async function refreshRooms(preferredId = '') {
    await loadBase();
    const id = preferredId || currentRoomId();
    if (id && select) select.value = id;
    if (id) await loadRoom(id);
  }

  run?.addEventListener('click', async () => {
    panel.hidden = false;
    run.disabled = true;
    try { await refreshRooms(); }
    catch (e) { if (content) content.innerHTML = `<div class="sc-rl-v7-error"><strong>Research Rooms unavailable</strong><p>${escapeHTML(e.message)}</p></div>`; }
    finally { run.disabled = false; }
  });
  refresh?.addEventListener('click', () => loadRoom().catch(e => { if (content) content.textContent = e.message; }));
  select?.addEventListener('change', () => loadRoom(select.value).catch(e => { if (content) content.textContent = e.message; }));

  createForm?.addEventListener('submit', async event => {
    event.preventDefault();
    const data = new FormData(createForm);
    if (createStatus) createStatus.textContent = 'Creating Research Room…';
    try {
      const room = await request('rooms', { method:'POST', body:JSON.stringify({ title:data.get('title'), objective:data.get('objective'), project_id:data.get('project_id') || '' }) });
      createForm.reset();
      if (createStatus) createStatus.textContent = 'Research Room created.';
      await refreshRooms(room.room_id);
    } catch (e) { if (createStatus) createStatus.textContent = e.message; }
  });

  memberForm?.addEventListener('submit', async event => {
    event.preventDefault();
    const roomId = currentRoomId();
    const data = new FormData(memberForm);
    if (memberStatus) memberStatus.textContent = 'Updating membership…';
    try {
      await request(`rooms/${encodeURIComponent(roomId)}/members`, { method:'POST', body:JSON.stringify({ member_identity:data.get('member_identity'), role:data.get('role'), status:'active' }) });
      memberForm.reset(); if (memberStatus) memberStatus.textContent = 'Participant added.'; await loadRoom(roomId);
    } catch (e) { if (memberStatus) memberStatus.textContent = e.message; }
  });

  evidenceForm?.addEventListener('submit', async event => {
    event.preventDefault();
    const roomId = currentRoomId();
    const data = new FormData(evidenceForm);
    if (evidenceStatus) evidenceStatus.textContent = 'Sharing evidence…';
    try {
      await request(`rooms/${encodeURIComponent(roomId)}/evidence`, { method:'POST', body:JSON.stringify({ object_id:data.get('object_id'), state:data.get('state'), note:data.get('note') }) });
      evidenceForm.reset(); if (evidenceStatus) evidenceStatus.textContent = 'Evidence shared with room.'; await loadRoom(roomId);
    } catch (e) { if (evidenceStatus) evidenceStatus.textContent = e.message; }
  });

  questionForm?.addEventListener('submit', async event => {
    event.preventDefault();
    const roomId = currentRoomId();
    const data = new FormData(questionForm);
    if (questionStatus) questionStatus.textContent = 'Saving room question…';
    try {
      await request(`rooms/${encodeURIComponent(roomId)}/questions`, { method:'POST', body:JSON.stringify({ question:data.get('question'), status:'open' }) });
      questionForm.reset(); if (questionStatus) questionStatus.textContent = 'Question added.'; await loadRoom(roomId);
    } catch (e) { if (questionStatus) questionStatus.textContent = e.message; }
  });

  disagreementForm?.addEventListener('submit', async event => {
    event.preventDefault();
    const roomId = currentRoomId();
    const data = new FormData(disagreementForm);
    const existing = editingDisagreement;
    if (disagreementStatus) disagreementStatus.textContent = existing ? 'Updating your attributed position…' : 'Recording disagreement…';
    try {
      await request(`rooms/${encodeURIComponent(roomId)}/disagreements`, { method:'POST', body:JSON.stringify({ disagreement_id:existing?.disagreement_id || '', statement:existing?.statement || data.get('statement'), position:data.get('position'), status:existing?.status || 'open' }) });
      editingDisagreement = null; disagreementForm.reset();
      const statement = disagreementForm.querySelector('[name="statement"]'); if (statement) statement.disabled = false;
      if (disagreementStatus) disagreementStatus.textContent = 'Attributed position saved.';
      await loadRoom(roomId);
    } catch (e) { if (disagreementStatus) disagreementStatus.textContent = e.message; }
  });

  content?.addEventListener('click', async event => {
    const roomId = currentRoomId();
    const useContext = event.target.closest('[data-room-use-context]');
    if (useContext) {
      useContext.disabled = true;
      try {
        const room = currentBundle.room;
        await request('contexts', { method:'POST', body:JSON.stringify({ title:room.title, scopes:['current-research-room'], room_id:room.room_id, active:true }) });
        window.localStorage.removeItem('sc_rl_research_context_v720');
        window.location.reload();
      } catch (e) { window.alert(e.message); useContext.disabled = false; }
      return;
    }

    const questionButton = event.target.closest('[data-room-question-id]');
    if (questionButton) {
      const question = currentQuestions.find(item => String(item.question_id || '') === String(questionButton.dataset.roomQuestionId || ''));
      if (!question) return;
      questionButton.disabled = true;
      try {
        await request(`rooms/${encodeURIComponent(roomId)}/questions`, { method:'POST', body:JSON.stringify({ question_id:question.question_id, question:question.question, status:questionButton.dataset.roomQuestionStatus || 'resolved', linked_object_ids:question.linked_object_ids || [] }) });
        await loadRoom(roomId);
      } catch (e) { window.alert(e.message); questionButton.disabled = false; }
      return;
    }

    const positionButton = event.target.closest('[data-room-disagreement-position]');
    if (positionButton) {
      editingDisagreement = currentDisagreements.find(item => String(item.disagreement_id || '') === String(positionButton.dataset.roomDisagreementPosition || '')) || null;
      if (!editingDisagreement || !disagreementForm) return;
      disagreementForm.hidden = false;
      const statement = disagreementForm.querySelector('[name="statement"]');
      const position = disagreementForm.querySelector('[name="position"]');
      if (statement) { statement.value = editingDisagreement.statement || ''; statement.disabled = true; }
      const own = (editingDisagreement.positions || []).find(item => String(item.participant_ref || '') === String(currentMember().member_ref || ''));
      if (position) { position.value = own?.position || ''; position.focus(); }
      return;
    }

    const resolveButton = event.target.closest('[data-room-disagreement-resolve]');
    if (resolveButton) {
      const disagreement = currentDisagreements.find(item => String(item.disagreement_id || '') === String(resolveButton.dataset.roomDisagreementResolve || ''));
      if (!disagreement) return;
      resolveButton.disabled = true;
      try {
        await request(`rooms/${encodeURIComponent(roomId)}/disagreements`, { method:'POST', body:JSON.stringify({ disagreement_id:disagreement.disagreement_id, statement:disagreement.statement, status:'resolved', position:'', resolution:'Resolved by Research Room leadership after explicit review.' }) });
        await loadRoom(roomId);
      } catch (e) { window.alert(e.message); resolveButton.disabled = false; }
    }
  });

  // Populate room selectors without forcing the panel open.
  loadBase().catch(() => {});
})();
