(() => {
  "use strict";

  const state = {
    apiKey: "",
    apiBase: "/v1/research-librarian",
    sessionId: "",
    projectId: "",
    connected: false,
  };

  const $ = (id) => document.getElementById(id);
  const esc = (value) => String(value ?? "").replace(/[&<>"']/g, c => ({
    "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"
  })[c]);

  function toast(message) {
    const el = $("toast");
    el.textContent = message;
    el.classList.add("show");
    clearTimeout(toast.timer);
    toast.timer = setTimeout(() => el.classList.remove("show"), 2600);
  }

  function headers(json=true) {
    const h = {};
    if (json) h["Content-Type"] = "application/json";
    if (state.apiKey) h["X-SC-RL-Key"] = state.apiKey;
    return h;
  }

  async function api(path, options={}) {
    const response = await fetch(state.apiBase + path, {
      ...options,
      headers: {...headers(options.body !== undefined), ...(options.headers || {})},
      cache: "no-store",
    });
    const text = await response.text();
    let body = {};
    try { body = text ? JSON.parse(text) : {}; } catch { body = {detail:text}; }
    if (!response.ok) {
      const detail = body.detail || body.message || `${response.status} ${response.statusText}`;
      throw new Error(detail);
    }
    return body.data ?? body;
  }

  async function publicJson(path) {
    const response = await fetch(path, {cache:"no-store"});
    if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
    return response.json();
  }

  function setRuntime(ok, label) {
    $("runtime-dot").className = "runtime-dot " + (ok ? "online" : "offline");
    $("runtime-label").textContent = label;
  }

  async function loadPublicRuntime() {
    try {
      const [health, manifest] = await Promise.all([
        publicJson("/health"),
        publicJson("/research-librarian/app-manifest.json"),
      ]);
      setRuntime(Boolean(health.ok), health.ok ? "Backend online" : "Backend degraded");
      $("release-label").textContent = `v${health.version || manifest.release || "12.0.4"}`;
      $("service-summary").innerHTML = `
        <div><span>Backend</span><strong>${esc(health.ok ? "Ready" : "Degraded")}</strong></div>
        <div><span>Release</span><strong>${esc(health.version || manifest.release)}</strong></div>
        <div><span>API</span><strong>${esc(manifest.api_base)}</strong></div>
        <div><span>WordPress</span><strong>${manifest.wordpress_required ? "Required" : "Optional"}</strong></div>
        <div><span>Identity</span><strong>${manifest.authentication.production_user_identity ? "Active" : "Deferred"}</strong></div>`;
    } catch (error) {
      setRuntime(false, "Backend unreachable");
      $("service-summary").innerHTML = `<div><span>Backend</span><strong>Offline</strong></div>`;
    }
  }

  async function connect(key) {
    state.apiKey = key.trim();
    if (!state.apiKey) throw new Error("API key required.");
    const manifest = await api("/manifest");
    state.connected = true;
    toast(`Connected to API ${manifest.api_version}`);
    await Promise.all([loadProjects(), loadSessions()]);
  }

  function disconnect() {
    state.apiKey = "";
    state.connected = false;
    state.sessionId = "";
    state.projectId = "";
    $("api-key").value = "";
    $("projects").innerHTML = "Connect to load projects.";
    $("sessions").innerHTML = "Connect to load sessions.";
    $("turns").innerHTML = '<div class="empty-state">Select or create a research session.</div>';
    $("session-summary").innerHTML = '<div><span>Status</span><strong>None selected</strong></div>';
    toast("Disconnected. API key cleared from memory.");
  }

  async function loadProjects() {
    const data = await api("/projects?limit=100");
    const items = data.items || [];
    $("projects").className = "stack" + (items.length ? "" : " empty-state");
    $("projects").innerHTML = items.length ? items.map(p => `
      <button class="stack-item ${state.projectId === p.project_id ? "active" : ""}" data-project="${esc(p.project_id)}">
        <strong>${esc(p.title || p.name || p.project_id)}</strong>
        <span>${esc(p.objective || p.project_id)}</span>
      </button>`).join("") : "No projects found.";
    document.querySelectorAll("[data-project]").forEach(el => {
      el.addEventListener("click", () => {
        state.projectId = el.dataset.project;
        document.querySelectorAll("[data-project]").forEach(x => x.classList.toggle("active", x === el));
        toast("Project context selected.");
      });
    });
  }

  async function loadSessions() {
    const data = await api("/sessions?limit=100");
    const items = data.items || [];
    $("sessions").className = "stack" + (items.length ? "" : " empty-state");
    $("sessions").innerHTML = items.length ? items.map(s => `
      <button class="stack-item ${state.sessionId === s.session_id ? "active" : ""}" data-session="${esc(s.session_id)}">
        <strong>${esc(s.title || "Research session")}</strong>
        <span>${esc(s.state)} · ${Number(s.turn_count || 0)} turns</span>
      </button>`).join("") : "No persistent sessions yet.";
    document.querySelectorAll("[data-session]").forEach(el => {
      el.addEventListener("click", () => selectSession(el.dataset.session));
    });
  }

  async function createSession() {
    if (!state.connected) return toast("Connect first.");
    const title = window.prompt("Session title", "Research session");
    if (title === null) return;
    const payload = {
      title: title.trim() || "Research session",
      project_id: state.projectId || "",
      client_ref: "independent-web-app-v12.0.4",
      metadata: {surface:"independent-web-app", release:"12.0.4"}
    };
    const session = await api("/sessions", {method:"POST", body:JSON.stringify(payload)});
    await loadSessions();
    await selectSession(session.session_id);
    toast("Persistent session created.");
  }

  async function selectSession(sessionId) {
    state.sessionId = sessionId;
    const [session, summary] = await Promise.all([
      api(`/sessions/${encodeURIComponent(sessionId)}`),
      api(`/sessions/${encodeURIComponent(sessionId)}/summary`)
    ]);
    state.projectId = session.project_id || state.projectId;
    $("session-title").textContent = session.title || "Research session";
    $("session-subtitle").textContent = session.research_context_ref || "Persistent backend research session.";
    $("session-summary").innerHTML = `
      <div><span>State</span><strong>${esc(summary.state)}</strong></div>
      <div><span>Turns</span><strong>${Number(summary.turn_count || 0)}</strong></div>
      <div><span>Project</span><strong>${esc(summary.project_id || "—")}</strong></div>
      <div><span>Scientist env</span><strong>${esc(summary.scientist_environment_id || "—")}</strong></div>
      <div><span>Client ref</span><strong>${esc(summary.client_ref || "—")}</strong></div>`;
    await Promise.all([loadTurns(), loadSessions(), loadProjects()]);
  }

  async function loadTurns() {
    if (!state.sessionId) return;
    const data = await api(`/sessions/${encodeURIComponent(state.sessionId)}/turns?limit=5000`);
    const items = data.items || [];
    $("turns").innerHTML = items.length ? items.map(t => `
      <article class="turn" data-role="${esc(t.role)}">
        <div class="turn-head">
          <span>${esc(t.role)}</span>
          <span>#${Number(t.sequence || 0)} · ${esc(t.created_utc || "")}</span>
        </div>
        <div class="turn-body">${esc(t.content)}</div>
      </article>`).join("") : '<div class="empty-state">No turns in this session yet.</div>';
    $("turns").scrollTop = $("turns").scrollHeight;
  }

  async function saveTurn(role, content, metadata={}) {
    if (!state.sessionId) throw new Error("Select or create a session first.");
    await api(`/sessions/${encodeURIComponent(state.sessionId)}/turns`, {
      method:"POST",
      body:JSON.stringify({
        role,
        content,
        metadata:{surface:"independent-web-app", ...metadata}
      })
    });
    await Promise.all([loadTurns(), selectSession(state.sessionId)]);
  }

  function renderRetrieval(data) {
    const matches = data.matches || [];
    $("retrieval-status").textContent = `${matches.length} result${matches.length === 1 ? "" : "s"} for “${data.query || ""}”`;
    $("retrieval-results").innerHTML = matches.length ? matches.map((m, i) => `
      <article class="result-card">
        <h3>${i+1}. ${esc(m.title || m.id || "Untitled source")}</h3>
        <p>${esc(m.excerpt || m.snippet || m.description || "")}</p>
        <div class="result-meta">
          <span>${esc(m.id || "")}</span>
          ${m.score !== undefined ? `<span>score ${esc(m.score)}</span>` : ""}
          ${m.url ? `<span>${esc(m.url)}</span>` : ""}
        </div>
      </article>`).join("") : '<div class="empty-state">No matching records.</div>';
  }

  async function runRetrieval(query) {
    if (!state.connected) throw new Error("Connect first.");
    $("retrieval-status").textContent = "Retrieving…";
    const data = await api("/retrieve", {
      method:"POST",
      body:JSON.stringify({
        query,
        limit:Number($("retrieval-limit").value || 10),
        include_semantic:$("semantic-toggle").checked,
        include_diagnostics:true,
        advanced:true,
        filters:{}
      })
    });
    renderRetrieval(data);
    if (state.sessionId) {
      await saveTurn("user", query, {kind:"retrieval-query"});
      await saveTurn("research-note", `Retrieval returned ${(data.matches || []).length} result(s).`, {
        kind:"retrieval-receipt",
        source_refs:(data.matches || []).map(x => x.id).filter(Boolean)
      });
    }
  }

  async function freezeSession() {
    if (!state.sessionId) return toast("Select a session first.");
    const snapshot = await api(`/sessions/${encodeURIComponent(state.sessionId)}/snapshots/freeze`, {
      method:"POST",
      body:JSON.stringify({
        actor_ref:"independent-web-app-operator",
        label:"web-app-session-snapshot",
        note:"Frozen from v12.0.4 Independent Web App Foundation."
      })
    });
    toast(`Snapshot ${snapshot.snapshot_id} frozen.`);
  }

  $("connection-form").addEventListener("submit", async e => {
    e.preventDefault();
    try { await connect($("api-key").value); }
    catch (error) { disconnect(); toast(error.message); }
  });
  $("disconnect-button").addEventListener("click", disconnect);
  $("refresh-projects").addEventListener("click", () => state.connected && loadProjects().catch(e => toast(e.message)));
  $("new-session").addEventListener("click", () => createSession().catch(e => toast(e.message)));
  $("refresh-turns").addEventListener("click", () => loadTurns().catch(e => toast(e.message)));
  $("freeze-session").addEventListener("click", () => freezeSession().catch(e => toast(e.message)));

  $("turn-form").addEventListener("submit", async e => {
    e.preventDefault();
    const content = $("turn-content").value.trim();
    if (!content) return;
    try {
      await saveTurn($("turn-role").value, content);
      $("turn-content").value = "";
      toast("Turn saved to backend.");
    } catch (error) { toast(error.message); }
  });

  $("retrieval-form").addEventListener("submit", async e => {
    e.preventDefault();
    const query = $("retrieval-query").value.trim();
    if (!query) return;
    try { await runRetrieval(query); }
    catch (error) {
      $("retrieval-status").textContent = "Retrieval failed.";
      toast(error.message);
    }
  });

  window.addEventListener("beforeunload", () => { state.apiKey = ""; });
  loadPublicRuntime();
})();
