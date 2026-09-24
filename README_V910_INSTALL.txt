Research Librarian AI v9.1.0 — Research Automation & Durable Workflow Engine

Install order:
1. Run PUSH_RESEARCH_LIBRARIAN_V910_PY312.sh with the repository ZIP to validate, commit, push main and tag v9.1.0.
2. Copy the backend ZIP and deploy/contabo/upgrade_research_librarian_backend_v9_1_0_contabo.sh to Contabo.
3. Run the deployer and require /health version=9.1.0 and ready=true plus workflow-engine verification.
4. Install sustainable-catalyst-research-librarian-ai-wordpress-v9.1.0.zip in WordPress.

The workflow engine preserves explicit human gates and performs no automatic Platform Core research-object writes.
