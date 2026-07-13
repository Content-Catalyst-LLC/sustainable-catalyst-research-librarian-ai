# Install Research Librarian AI v6.2.1

## 1. Push the repository

Push the complete repository to `Content-Catalyst-LLC/sustainable-catalyst-research-librarian-ai`.

## 2. Deploy the Python service on Render

Create a Render Blueprint from `render.yaml`, or create a Python web service with:

- Root directory: `backend`
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health check: `/health`

Set these environment variables:

```text
SC_RL_BACKEND_API_KEY=<long random shared key>
SC_RL_GEMINI_API_KEY=<Gemini key>
SC_RL_GEMINI_MODEL=gemini-3.5-flash
SC_RL_CORS_ORIGINS=https://sustainablecatalyst.com
SC_RL_AI_PROVIDER=gemini
```

## 3. Install the WordPress plugin

Upload `sustainable-catalyst-research-librarian-ai-v6.2.1.zip`, replace the existing version, and activate it.

## 4. Connect WordPress to Render

Open **Research Librarian AI → Python Intelligence** and enter:

- Enable Python intelligence
- Render backend URL
- The same `SC_RL_BACKEND_API_KEY`

Save, run **Test Backend and Integration Key**, then run **Repair Endpoint and Resynchronize**. Review the latest batch report before testing a public question.

## 5. Verify

The dashboard should show the number of indexed titles. The public shortcode remains:

```text
[sustainable_catalyst_research_librarian_ai]
```

Ask for an exact known article title and verify that it outranks the generic Platform route.
