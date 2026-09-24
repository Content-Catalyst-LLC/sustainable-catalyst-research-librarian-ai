Research Librarian AI v9.2.0 — Original Research & Scholarly Research Environment

Install order:
1. Run PUSH_RESEARCH_LIBRARIAN_V920_PY312.sh with the repository ZIP to validate, commit, push main and tag v9.2.0.
2. Copy the backend ZIP and deploy/contabo/upgrade_research_librarian_backend_v9_2_0_contabo.sh to Contabo.
3. Run the deployer and require /health version=9.2.0 and ready=true plus scholarly-research environment verification.
4. Install sustainable-catalyst-research-librarian-ai-wordpress-v9.2.0.zip in WordPress.

v9.2.0 preserves the v9.1 Core-env fallback repair: an absent or unreadable Platform Core .env.production file does not block deployment when the Librarian already has SC_RL_CORE_WRITE_API_KEY configured.

The scholarly environment preserves human authorship and explicit research governance. Frozen research packages are reproducibility snapshots, not peer-review certification or truth judgments.
