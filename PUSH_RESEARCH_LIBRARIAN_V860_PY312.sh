#!/usr/bin/env bash
set -Eeuo pipefail
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"
VERSION="8.6.0"
TAG="v${VERSION}"
REPO_URL="git@github.com:Content-Catalyst-LLC/sustainable-catalyst-research-librarian-ai.git"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ZIP_PATH="${1:-$SCRIPT_DIR/sustainable-catalyst-research-librarian-ai-v8.6.0-repository.zip}"
REPO_DIR="${2:-$HOME/Downloads/sustainable-catalyst-research-librarian-ai-repo-v860-clean}"
fail(){ printf 'ERROR: %s\n' "$*" >&2; exit 1; }
run_clean(){ env -u VIRTUAL_ENV -u PYTHONHOME -u PYTHONPATH -u PYTHONEXECUTABLE -u __PYVENV_LAUNCHER__ -u CONDA_PREFIX -u CONDA_DEFAULT_ENV -u PYENV_VERSION "$@"; }
for c in git unzip rsync php node ssh shasum awk grep find; do command -v "$c" >/dev/null 2>&1 || fail "$c is required"; done
[[ -f "$ZIP_PATH" ]] || fail "Release ZIP not found: $ZIP_PATH"
printf 'Release archive: %s\nSHA-256: %s\n' "$ZIP_PATH" "$(shasum -a 256 "$ZIP_PATH"|awk '{print $1}')"
find_python(){ local c r m p; local -a a=(); [[ -n "${SC_RL_PYTHON:-}" ]]&&a+=("$SC_RL_PYTHON"); if command -v brew >/dev/null 2>&1; then p="$(brew --prefix python@3.12 2>/dev/null||true)"; [[ -n "$p" ]]&&a+=("$p/bin/python3.12"); p="$(brew --prefix python@3.13 2>/dev/null||true)"; [[ -n "$p" ]]&&a+=("$p/bin/python3.13"); fi; a+=(python3.12 python3.13 python3); for c in "${a[@]}"; do r="$(command -v "$c" 2>/dev/null||true)"; [[ -n "$r" ]]||continue; m="$(run_clean "$r" -c 'import sys;print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null||true)"; [[ "$m" == 3.12 || "$m" == 3.13 ]]&&{ printf '%s\n' "$r"; return; }; done; }
PYTHON_BIN="$(find_python||true)"; [[ -n "$PYTHON_BIN" ]]||fail "Python 3.12 or 3.13 is required."
SSH_OUTPUT="$(ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -T git@github.com 2>&1||true)"; grep -qi 'successfully authenticated' <<<"$SSH_OUTPUT"||fail "GitHub SSH authentication is not ready. Run: ssh -T git@github.com"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/sc-rl-v860.XXXXXX")"; trap 'rm -rf "$TMP"' EXIT
unzip -q "$ZIP_PATH" -d "$TMP/release"
SRC="$(find "$TMP/release" -maxdepth 2 -type f -name sustainable-catalyst-research-librarian-ai.php -print -quit | xargs -I{} dirname {})"
[[ -n "$SRC" && -f "$SRC/sustainable-catalyst-research-librarian-ai.php" ]]||fail "Expected repository root missing."
for f in backend/app/source_identity.py backend/app/api/sources.py backend/app/contracts/sources.py backend/tests/test_v860_source_identity.py docs/V860_SOURCE_IDENTITY_DEDUPLICATION_CITATION_GRAPH.md data/research_librarian_source_identity_manifest_v8.6.0.json tests/v860-source-identity-citation-graph-contract-test.php backend/migrations/005_source_identity_citation_graph.sql RELEASE_MANIFEST_V860.json backend/app/document_intelligence.py backend/app/api/documents.py backend/app/contracts/documents.py backend/tests/test_v850_document_intelligence.py docs/V850_DOCUMENT_INTELLIGENCE_SCHOLARLY_PARSING.md data/research_librarian_document_intelligence_manifest_v8.5.0.json tests/v850-document-intelligence-scholarly-parsing-contract-test.php backend/app/advanced_retrieval.py backend/tests/test_v840_advanced_retrieval.py backend/app/async_jobs.py backend/app/clients/platform_core.py backend/migrations/004_async_document_processing_runtime.sql deploy/contabo/upgrade_research_librarian_backend_v8_6_0_contabo.sh; do [[ -f "$SRC/$f" ]]||fail "v8.6.0 required file missing: $f"; done
grep -q 'Version: 8.6.0' "$SRC/sustainable-catalyst-research-librarian-ai.php"||fail "Plugin version mismatch."
grep -q '__version__ = "8.6.0"' "$SRC/backend/app/__init__.py"||fail "Backend version mismatch."
grep -q 'DOCUMENT_INTELLIGENCE_SCHEMA' "$SRC/backend/app/document_intelligence.py"||fail "Document intelligence schema missing."
grep -q 'def parse_document' "$SRC/backend/app/document_intelligence.py"||fail "Document parser missing."
grep -q 'pypdf' "$SRC/backend/requirements.txt"||fail "PDF parsing dependency missing."
grep -q 'SOURCE_IDENTITY_SCHEMA' "$SRC/backend/app/source_identity.py"||fail "Source identity schema missing."
grep -q 'CITATION_GRAPH_SCHEMA' "$SRC/backend/app/source_identity.py"||fail "Citation graph schema missing."
grep -q 'SourceIdentityConflict' "$SRC/backend/app/source_identity.py"||fail "Fail-closed identity conflict contract missing."
grep -q 'APIRouter(prefix="/v1/sources"' "$SRC/backend/app/api/sources.py"||fail "Source identity API router missing."
grep -q '"source-identity"' "$SRC/backend/app/async_jobs.py"||fail "Source identity durable job type missing."
grep -q 'sc_rl_canonical_sources' "$SRC/backend/migrations/005_source_identity_citation_graph.sql"||fail "Canonical source Postgres migration missing."
grep -q 'sc_rl_citation_edges' "$SRC/backend/migrations/005_source_identity_citation_graph.sql"||fail "Citation graph Postgres migration missing."
grep -q 'APIRouter(prefix="/v1/documents"' "$SRC/backend/app/api/documents.py"||fail "Document API router missing."
grep -q 'ADVANCED_RETRIEVAL_SCHEMA' "$SRC/backend/app/advanced_retrieval.py"||fail "Advanced retrieval module missing schema contract."
grep -q 'def build_query_plan' "$SRC/backend/app/advanced_retrieval.py"||fail "Deterministic query planner missing."
grep -q 'def advanced_retrieve_with_diagnostics' "$SRC/backend/app/advanced_retrieval.py"||fail "Advanced retrieval orchestrator missing."
grep -q 'advanced-v8.4.0' "$SRC/backend/app/calibration.py"||fail "v8.4 advanced retrieval profile missing."
grep -q '/v1/retrieval/plan' "$SRC/backend/app/main.py"||fail "v8.4 query-plan endpoint missing."
grep -q 'FOR UPDATE SKIP LOCKED' "$SRC/backend/app/async_jobs.py"||fail "Postgres durable queue claim contract missing."
grep -q '/opt/sustainable-catalyst/research-librarian-ai' "$SRC/deploy/contabo/upgrade_research_librarian_backend_v8_6_0_contabo.sh"||fail "Correct VPS Research Librarian root missing."
grep -q 'SCHEMA_VERSION = 19' "$SRC/backend/app/store.py"||fail "Ancillary SQLite schema 19 missing."
grep -q 'CORE_MINIMUM_VERSION = "3.3.0"' "$SRC/backend/app/contracts/platform_core.py"||fail "Core v3.3 minimum contract missing."
grep -q 'http://sc-core:8090' "$SRC/compose.yml"||fail "VPS Core private DNS default missing."
if [[ -d "$REPO_DIR/.git" ]]; then :; else [[ ! -e "$REPO_DIR" ]]||fail "$REPO_DIR exists but is not a Git repository."; git clone "$REPO_URL" "$REPO_DIR"; fi
cd "$REPO_DIR"; git fetch origin --tags --prune; git switch main; git pull --ff-only origin main; git diff --quiet&&git diff --cached --quiet||fail "Repository has uncommitted changes."
git rev-parse -q --verify "refs/tags/$TAG" >/dev/null&&fail "Local tag exists." || true
git ls-remote --exit-code --tags origin "refs/tags/$TAG" >/dev/null 2>&1&&fail "Remote tag exists." || true
rsync -a --delete --exclude '.git/' --exclude '.venv/' --exclude '.pytest_cache/' --exclude '__pycache__/' --exclude '*.pyc' --exclude '*.sqlite3*' "$SRC/" "$REPO_DIR/"
PHP_COUNT=0; while IFS= read -r -d '' f; do php -l "$f" >/dev/null; PHP_COUNT=$((PHP_COUNT+1)); done < <(find . -type f -name '*.php' -print0); echo "PHP syntax passed: $PHP_COUNT files."
JS_COUNT=0; while IFS= read -r -d '' f; do node --check "$f" >/dev/null; JS_COUNT=$((JS_COUNT+1)); done < <(find assets -type f -name '*.js' -print0); echo "JavaScript syntax passed: $JS_COUNT files."
run_clean "$PYTHON_BIN" - <<'PY'
import json
from pathlib import Path
ps=list(Path('.').rglob('*.json'))
for p in ps: json.loads(p.read_text())
print(f'JSON validation passed: {len(ps)} files.')
PY
for f in tests/*.php; do TERM=dumb php "$f" >/dev/null; done; echo "WordPress contract/functional tests passed."
run_clean "$PYTHON_BIN" -m venv --copies "$TMP/venv"; VENV_PY="$TMP/venv/bin/python"; run_clean "$VENV_PY" -m pip install --quiet --upgrade pip; run_clean "$VENV_PY" -m pip install --quiet -r backend/requirements.txt
SC_RL_BACKEND_API_KEY=test-key SC_RL_DATA_DIR="$TMP/test-a" SC_RL_CORE_ENABLED=true run_clean "$VENV_PY" -m pytest -q backend/tests
(cd backend; SC_RL_BACKEND_API_KEY=test-key SC_RL_DATA_DIR="$TMP/test-b" SC_RL_CORE_ENABLED=true run_clean "$VENV_PY" -m pytest -q tests)
run_clean "$VENV_PY" -m compileall -q backend/app backend/tests
bash -n deploy/contabo/upgrade_research_librarian_backend_v8_6_0_contabo.sh
if grep -RInE --exclude-dir=.git --exclude-dir=.venv --exclude-dir=.pytest_cache --exclude-dir=__pycache__ --exclude='*.pyc' --exclude='PUSH_RESEARCH_LIBRARIAN_*.sh' '(BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY|github_pat_[A-Za-z0-9_]{20,}|ghp_[A-Za-z0-9]{30,}|sk-[A-Za-z0-9]{30,}|AIza[0-9A-Za-z_-]{30,})' .; then fail "Potential secret material detected."; fi
git add -A; git diff --cached --quiet&&fail "No v8.6.0 changes detected."
git commit -m "Build Research Librarian v${VERSION} — source identity, deduplication, and citation graph"
git tag -a "$TAG" -m "Research Librarian v${VERSION} — Source Identity, Deduplication & Citation Graph"
git push origin main; git push origin "$TAG"
printf '\nResearch Librarian v%s validated and pushed successfully.\n' "$VERSION"
printf 'Deploy the backend package to Contabo before installing the WordPress v8.6.0 package.\n'
