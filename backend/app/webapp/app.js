(() => {
  "use strict";

  const state = {
    apiBase: "/v1/research-librarian",
    authenticated: false,
    access: null,
    sessionId: "",
    projectId: "",
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

  async function request(path, options={}) {
    const response = await fetch(state.apiBase + path, {
      credentials: "same-origin",
      cache: "no-store",
      ...options,
      headers: {
        ...(options.body !== undefined ? {"Content-Type":"application/json"} : {}),
        ...(options.headers || {}),
      },
    });

    const text = await response.text();
    let body = {};
    try { body = text ? JSON.parse(text) : {}; }
    catch { body = {detail:text}; }

    if (!response.ok) {
      const detail = body.detail || body.message || `${response.status} ${response.statusText}`;
      const error = new Error(detail);
      error.status = response.status;
      throw error;
    }
    return body.data ?? body;
  }

  async function publicJson(path) {
    const response = await fetch(path, {cache:"no-store", credentials:"same-origin"});
    if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
    return response.json();
  }

  function setRuntime(ok,label) {
    $("runtime-dot").className = "runtime-dot " + (ok ? "online" : "offline");
    $("runtime-label").textContent = label;
  }

  function renderSignedOut() {
    state.authenticated = false;
    state.access = null;
    state.sessionId = "";
    state.projectId = "";
    $("login-form").classList.remove("hidden");
    $("identity-card").classList.add("hidden");
    $("workspace").classList.add("locked");
    $("access-summary").innerHTML = '<div><span>Status</span><strong>Signed out</strong></div>';
    $("projects").innerHTML = "Sign in to load projects.";
    $("sessions").innerHTML = "Sign in to load sessions.";
    $("turns").innerHTML = '<div class="empty-state">Sign in and select a research session.</div>';
    $("session-summary").innerHTML = '<div><span>Status</span><strong>None selected</strong></div>';
  }

  function renderAccess(access) {
    state.authenticated = true;
    state.access = access;
    $("login-form").classList.add("hidden");
    $("identity-card").classList.remove("hidden");
    $("workspace").classList.remove("locked");
    $("identity-name").textContent = access.display_name || access.email || "Researcher";
    $("identity-meta").textContent = `${access.email || ""} · ${access.role || ""}`;
    $("access-summary").innerHTML = `
      <div><span>Identity</span><strong>${esc(access.display_name || access.email)}</strong></div>
      <div><span>Role</span><strong>${esc(access.role)}</strong></div>
      <div><span>Write</span><strong>${access.can_write ? "Allowed" : "Read only"}</strong></div>
      <div><span>Auth</span><strong>${esc(access.auth_mode)}</strong></div>`;
  }

  async function loadPublicRuntime() {
    try {
      const [health, authManifest, appManifest] = await Promise.all([
        publicJson("/health"),
        request("/auth/manifest"),
        publicJson("/research-librarian/app-manifest.json"),
      ]);
      setRuntime(Boolean(health.ok), health.ok ? "Backend online" : "Backend degraded");
      $("release-label").textContent = `v${health.version || appManifest.release || "12.0.5"}`;
      $("service-summary").innerHTML = `
        <div><span>Backend</span><strong>${esc(health.ok ? "Ready" : "Degraded")}</strong></div>
        <div><span>Release</span><strong>${esc(health.version || appManifest.release)}</strong></div>
        <div><span>Identity</span><strong>${health.identity_sessions ? "Active" : "Unavailable"}</strong></div>
        <div><span>WordPress</span><strong>${health.wordpress_required ? "Required" : "Optional"}</strong></div>`;
      $("setup-notice").classList.toggle("hidden", Number(authManifest.identity_count || 0) > 0);
    } catch (error) {
      setRuntime(false,"Backend unreachable");
      $("service-summary").innerHTML = '<div><span>Backend</span><strong>Offline</strong></div>';
    }
  }

  async function refreshAuth() {
    try {
      const access = await request("/auth/me");
      if (access.auth_mode !== "identity-session") {
        renderSignedOut();
        return false;
      }
      renderAccess(access);
      return true;
    } catch (error) {
      renderSignedOut();
      return false;
    }
  }

  async function login(email,password) {
    await request("/auth/login", {
      method:"POST",
      body:JSON.stringify({
        email,
        password,
        client_mode:"cookie",
        client_label:"independent-web-app-v12.0.5"
      })
    });
    if (!await refreshAuth()) throw new Error("Login succeeded but authenticated session could not be resolved.");
    await Promise.all([loadProjects(),loadSessions()]);
    toast("Signed in.");
  }

  async function logout() {
    try {
      if (state.authenticated) {
        await request("/auth/logout",{method:"POST",body:"{}"});
      }
    } finally {
      renderSignedOut();
      toast("Signed out.");
    }
  }

  async function loadProjects() {
    if (!state.authenticated) return;
    const data = await request("/projects?limit=100");
    const items = data.items || [];
    $("projects").className = "stack" + (items.length ? "" : " empty-state");
    $("projects").innerHTML = items.length ? items.map(p => `
      <button class="stack-item ${state.projectId===p.project_id?"active":""}" data-project="${esc(p.project_id)}">
        <strong>${esc(p.title || p.name || p.project_id)}</strong>
        <span>${esc(p.objective || p.project_id)}</span>
      </button>`).join("") : "No projects found.";
    document.querySelectorAll("[data-project]").forEach(el => {
      el.addEventListener("click", () => {
        state.projectId = el.dataset.project;
        document.querySelectorAll("[data-project]").forEach(x => x.classList.toggle("active",x===el));
        toast("Project context selected.");
      });
    });
  }

  async function loadSessions() {
    if (!state.authenticated) return;
    const data = await request("/sessions?limit=100");
    const items = data.items || [];
    $("sessions").className = "stack" + (items.length ? "" : " empty-state");
    $("sessions").innerHTML = items.length ? items.map(s => `
      <button class="stack-item ${state.sessionId===s.session_id?"active":""}" data-session="${esc(s.session_id)}">
        <strong>${esc(s.title || "Research session")}</strong>
        <span>${esc(s.state)} · ${Number(s.turn_count || 0)} turns</span>
      </button>`).join("") : "No persistent sessions yet.";
    document.querySelectorAll("[data-session]").forEach(el => {
      el.addEventListener("click", () => selectSession(el.dataset.session));
    });
  }

  async function createSession() {
    if (!state.authenticated) return toast("Sign in first.");
    const title=window.prompt("Session title","Research session");
    if (title===null) return;
    const session=await request("/sessions",{
      method:"POST",
      body:JSON.stringify({
        title:title.trim() || "Research session",
        project_id:state.projectId || "",
        client_ref:"",
        metadata:{surface:"independent-web-app",release:"12.0.5"}
      })
    });
    await loadSessions();
    await selectSession(session.session_id);
    toast("Persistent session created.");
  }

  async function selectSession(sessionId) {
    state.sessionId=sessionId;
    const [session,summary]=await Promise.all([
      request(`/sessions/${encodeURIComponent(sessionId)}`),
      request(`/sessions/${encodeURIComponent(sessionId)}/summary`)
    ]);
    state.projectId=session.project_id || state.projectId;
    $("session-title").textContent=session.title || "Research session";
    $("session-subtitle").textContent=session.research_context_ref || "Identity-owned persistent research session.";
    $("session-summary").innerHTML=`
      <div><span>State</span><strong>${esc(summary.state)}</strong></div>
      <div><span>Turns</span><strong>${Number(summary.turn_count || 0)}</strong></div>
      <div><span>Project</span><strong>${esc(summary.project_id || "—")}</strong></div>
      <div><span>Owner</span><strong>${esc(session.client_ref || "—")}</strong></div>`;
    await Promise.all([loadTurns(),loadSessions(),loadProjects()]);
  }

  async function loadTurns() {
    if (!state.sessionId) return;
    const data=await request(`/sessions/${encodeURIComponent(state.sessionId)}/turns?limit=5000`);
    const items=data.items || [];
    $("turns").innerHTML=items.length ? items.map(t => `
      <article class="turn" data-role="${esc(t.role)}">
        <div class="turn-head"><span>${esc(t.role)}</span><span>#${Number(t.sequence || 0)} · ${esc(t.created_utc || "")}</span></div>
        <div class="turn-body">${esc(t.content)}</div>
      </article>`).join("") : '<div class="empty-state">No turns in this session yet.</div>';
    $("turns").scrollTop=$("turns").scrollHeight;
  }

  async function saveTurn(role,content,metadata={}) {
    if (!state.sessionId) throw new Error("Select or create a session first.");
    await request(`/sessions/${encodeURIComponent(state.sessionId)}/turns`,{
      method:"POST",
      body:JSON.stringify({role,content,metadata:{surface:"independent-web-app",...metadata}})
    });
    await Promise.all([loadTurns(),selectSession(state.sessionId)]);
  }

  function renderRetrieval(data) {
    const matches=data.matches || [];
    $("retrieval-status").textContent=`${matches.length} result${matches.length===1?"":"s"} for “${data.query || ""}”`;
    $("retrieval-results").innerHTML=matches.length ? matches.map((m,i) => `
      <article class="result-card">
        <h3>${i+1}. ${esc(m.title || m.id || "Untitled source")}</h3>
        <p>${esc(m.excerpt || m.snippet || m.description || "")}</p>
        <div class="result-meta">
          <span>${esc(m.id || "")}</span>
          ${m.score!==undefined?`<span>score ${esc(m.score)}</span>`:""}
          ${m.url?`<span>${esc(m.url)}</span>`:""}
        </div>
      </article>`).join("") : '<div class="empty-state">No matching records.</div>';
  }

  async function runRetrieval(query) {
    $("retrieval-status").textContent="Retrieving…";
    const data=await request("/retrieve",{
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
    if (state.sessionId && state.access?.can_write) {
      await saveTurn("user",query,{kind:"retrieval-query"});
      await saveTurn("research-note",`Retrieval returned ${(data.matches || []).length} result(s).`,{
        kind:"retrieval-receipt",
        source_refs:(data.matches || []).map(x => x.id).filter(Boolean)
      });
    }
  }

  async function freezeSession() {
    if (!state.sessionId) return toast("Select a session first.");
    const snap=await request(`/sessions/${encodeURIComponent(state.sessionId)}/snapshots/freeze`,{
      method:"POST",
      body:JSON.stringify({
        actor_ref:state.access?.identity_ref || "",
        label:"web-app-session-snapshot",
        note:"Frozen from v12.0.5 identity-aware web app."
      })
    });
    toast(`Snapshot ${snap.snapshot_id} frozen.`);
  }

  $("login-form").addEventListener("submit",async e => {
    e.preventDefault();
    try {
      await login($("email").value.trim(),$("password").value);
      $("password").value="";
    } catch (error) {
      $("password").value="";
      toast(error.message);
    }
  });
  $("logout-button").addEventListener("click",() => logout().catch(e => toast(e.message)));
  $("refresh-projects").addEventListener("click",() => loadProjects().catch(e => toast(e.message)));
  $("new-session").addEventListener("click",() => createSession().catch(e => toast(e.message)));
  $("refresh-turns").addEventListener("click",() => loadTurns().catch(e => toast(e.message)));
  $("freeze-session").addEventListener("click",() => freezeSession().catch(e => toast(e.message)));

  $("turn-form").addEventListener("submit",async e => {
    e.preventDefault();
    const content=$("turn-content").value.trim();
    if (!content) return;
    try {
      await saveTurn($("turn-role").value,content);
      $("turn-content").value="";
      toast("Turn saved.");
    } catch (error) { toast(error.message); }
  });

  $("retrieval-form").addEventListener("submit",async e => {
    e.preventDefault();
    const query=$("retrieval-query").value.trim();
    if (!query) return;
    try { await runRetrieval(query); }
    catch (error) {
      $("retrieval-status").textContent="Retrieval failed.";
      toast(error.message);
    }
  });

  (async () => {
    await loadPublicRuntime();
    if (await refreshAuth()) {
      await Promise.all([loadProjects(),loadSessions()]);
    }
  })();
})();
