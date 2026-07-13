# Research Librarian AI Python Backend

This FastAPI service is the v6.2.1 knowledge-intelligence and endpoint-reliability engine for Sustainable Catalyst. WordPress remains the public interface, publishing system, feedback layer, and administrative bridge. Python handles full-library title-aware retrieval, grounded Gemini synthesis, short conversational continuity, related-title discovery, and production status reporting.

## Local development

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Environment variables are read from the process environment. Load `.env` with your preferred development tool.

## Render

The repository includes a root `render.yaml`. Create a new Render Blueprint or web service from the repository. Set `SC_RL_GEMINI_API_KEY` manually. Copy the generated `SC_RL_BACKEND_API_KEY` into **WordPress → Research Librarian AI → Python Intelligence**.

The free Render filesystem is ephemeral. The WordPress plugin therefore includes authenticated health verification, a one-click repair-and-resynchronize action, per-batch sync reporting, and scheduled synchronization. A paid persistent disk is optional, not required for initial operation.
