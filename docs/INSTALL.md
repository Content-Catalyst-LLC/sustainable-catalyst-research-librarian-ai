# Install Research Librarian AI v6.3.0

## 1. Push the repository

Use `PUSH_RESEARCH_LIBRARIAN_V630_PY312.sh` to validate and push the complete repository to `Content-Catalyst-LLC/sustainable-catalyst-research-librarian-ai`.

The script requires Python 3.12, clears macOS virtual-environment launcher overrides, verifies the temporary interpreter, runs PHP/JavaScript/JSON/Python validation, and creates the `v6.3.0` tag.

## 2. Deploy or update the Python service on Render

Use the included `render.yaml`, or configure a Python web service with:

- Root directory: `backend`
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health check: `/health`
- Python: `3.12.12`

Set:

```text
SC_RL_BACKEND_API_KEY=<long random shared key>
SC_RL_GEMINI_API_KEY=<Gemini key>
SC_RL_GEMINI_MODEL=gemini-3.5-flash
SC_RL_CORS_ORIGINS=https://sustainablecatalyst.com
SC_RL_AI_PROVIDER=gemini
SC_RL_MAX_RUNTIME_SNAPSHOTS=5
```

The free Render filesystem may be erased during restart or redeploy. That is supported: SQLite is the runtime index, while WordPress stores the private canonical recovery snapshot.

## 3. Install the WordPress plugin

Upload `sustainable-catalyst-research-librarian-ai-v6.3.0.zip`, replace the existing version, and activate it.

## 4. Connect and synchronize

Open **Research Librarian AI → Python Intelligence** and configure:

- Enable Python intelligence
- Render backend URL
- The same `SC_RL_BACKEND_API_KEY`
- Automatic cold-start recovery enabled
- WordPress snapshot retention (five is the default)

Save the settings, select **Test Backend**, and then select **Transactional Full Sync**.

## 5. Verify durability

Confirm that:

- the backend reports `storage_engine: sqlite` and schema version 3;
- WordPress and backend record counts match;
- WordPress and backend checksums match;
- at least one private WordPress snapshot exists;
- the incremental queue is empty after synchronization;
- `/v1/knowledge/manifest` reports a completed index version.

The public shortcode remains:

```text
[sustainable_catalyst_research_librarian_ai]
```

## 6. Recovery operations

- **Process Incremental Queue** applies saved, unpublished, trashed, or deleted record changes.
- **Recover Empty Backend** restores the latest verified WordPress snapshot when the backend index is empty.
- **Create WordPress Snapshot** creates a recovery point without replacing the backend index.
- **Rollback Runtime Index** restores a backend safety snapshot created before a committed synchronization.
- **Repair and Resynchronize** repairs schedules, verifies connectivity, and performs a complete transactional sync.
