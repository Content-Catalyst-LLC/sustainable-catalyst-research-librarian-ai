# Install Research Librarian AI v7.0.0

## Repository deployment

Use `PUSH_RESEARCH_LIBRARIAN_V700_PY312.sh`. It requires Python 3.12, clears macOS launcher overrides, validates both Python import layouts, runs all WordPress contracts, validates JSON and JavaScript, scans for secrets, pushes `main`, and creates tag `v7.0.0`.

```bash
cd ~/Downloads
chmod +x PUSH_RESEARCH_LIBRARIAN_V700_PY312.sh
./PUSH_RESEARCH_LIBRARIAN_V700_PY312.sh \
  "$HOME/Downloads/sustainable-catalyst-research-librarian-ai-v7.0.0.zip" \
  "$HOME/Downloads/sustainable-catalyst-research-librarian-ai-repo-v700-clean"
```

## Render

The repository retains Python 3.12.12 and the existing FastAPI start command. Deploy the new commit, then confirm `/health`, `/status`, `/v1/platform/api`, and `/v1/platform/summary`.

## WordPress

Upload `sustainable-catalyst-research-librarian-ai-wordpress-v7.0.0.zip` through **Plugins → Add Plugin → Upload Plugin**. Existing plugin settings and backend data remain compatible.

## Migration

SQLite migration is additive from schema 9 to schema 10. Existing records, chunks, embeddings, snapshots, benchmarks, governance traces, handoffs, receipts, artifacts, and recovery state remain intact. New tables are created for projects, investigations, entities, project events, and connected backups.

## Production verification

1. Run **Research Librarian AI → Python Intelligence → Test Backend**.
2. Run **Validate Snapshots** and verify the synchronized Library checksum.
3. Open **Settings → Connected Research Platform**.
4. Confirm `/v1/platform/api` reports `sc-connected-research-api/1.0`.
5. Create one private project and one investigation.
6. Create one workflow template and one uncertainty register.
7. Export a project backup and test a dry-run import.
8. Confirm no import publishes content or invokes a destination automatically.
9. Publish `[sc_connected_research_workspace]` only on an authenticated or appropriately protected page.
10. Keep human publication review enabled.

## Verify the public workspace

Confirm all eight research-mode controls remain keyboard-operable, the terminal prompt remains black with green text, answers and evidence remain light, and the connected project workspace does not replace the public site-scoped question flow.
