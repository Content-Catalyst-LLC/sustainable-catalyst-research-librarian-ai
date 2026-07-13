# Install Research Librarian AI v6.3.1

## 1. Push the repository

Use `PUSH_RESEARCH_LIBRARIAN_V631_PY312.sh`. The script requires and verifies Python 3.12, clears macOS launcher overrides, validates the repository from both Python import layouts, and creates tag `v6.3.1`.

## 2. Deploy or update Render

Use `render.yaml` or configure:

- Root directory: `backend`
- Build: `pip install -r requirements.txt`
- Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health check: `/health`
- Python: `3.12.12`

Required secrets remain `SC_RL_BACKEND_API_KEY` and `SC_RL_GEMINI_API_KEY`. Recommended hardening settings are:

```text
SC_RL_STARTUP_WARMUP_SECONDS=12
SC_RL_STALLED_JOB_SECONDS=1800
SC_RL_MAX_REJECTION_DETAILS=100
SC_RL_MAX_RUNTIME_SNAPSHOTS=5
```

The free Render filesystem remains supported. WordPress is the canonical snapshot source; SQLite is the recoverable runtime index.

## 3. Install WordPress

Upload `sustainable-catalyst-research-librarian-ai-v6.3.1.zip`, replace the installed version, and activate it. Existing v6.3.0 settings and snapshots are retained.

## 4. Connect and validate

Open **Research Librarian AI → Python Intelligence**, save the backend URL and shared key, then run:

1. **Test Backend**
2. **Validate Snapshots**
3. **Transactional Full Sync**
4. Confirm backend and WordPress counts and checksums match

Keep automatic cold-start recovery enabled. Defaults are five retry attempts, 30-second initial retry delay, 900-second maximum delay, 30-minute stalled-job threshold, and 15-minute duplicate-alert suppression.

## 5. Operational recovery

- **Repair Stalled Jobs** marks expired transactions failed and clears their staged rows.
- **Recover Empty Backend** verifies and transfers the latest canonical snapshot.
- **Clear Pending Retries** stops a bounded retry cycle after a permanent configuration problem is corrected.
- **Export Operations Log** downloads JSON containing manifests, sync/recovery history, retry state, alert state, snapshot validation, and queue diagnostics.
- **Rollback Runtime Index** is allowed only when the selected runtime snapshot passes integrity validation.
