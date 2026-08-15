#!/usr/bin/env bash
set -Eeuo pipefail
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"
RELEASE_VERSION="8.0.0"
RELEASE_TAG="v${RELEASE_VERSION}"
REPO_URL="git@github.com:Content-Catalyst-LLC/sustainable-catalyst-research-librarian-ai.git"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ZIP_PATH="${1:-$SCRIPT_DIR/sustainable-catalyst-research-librarian-ai-v8.0.0-repository.zip}"
REPO_DIR="${2:-$HOME/Downloads/sustainable-catalyst-research-librarian-ai-repo-v800-clean}"
fail(){ printf 'ERROR: %s\n' "$*" >&2; exit 1; }
run_clean(){ env -u VIRTUAL_ENV -u PYTHONHOME -u PYTHONPATH -u PYTHONEXECUTABLE -u __PYVENV_LAUNCHER__ -u CONDA_PREFIX -u CONDA_DEFAULT_ENV -u PYENV_VERSION "$@"; }
for c in git unzip rsync php node ssh shasum awk grep find; do command -v "$c" >/dev/null 2>&1 || fail "$c is required."; done
[[ -f "$ZIP_PATH" ]] || fail "Release ZIP not found: $ZIP_PATH"
printf 'Release archive: %s\nSHA-256: %s\n' "$ZIP_PATH" "$(shasum -a 256 "$ZIP_PATH"|awk '{print $1}')"
find_python(){ local c r m p; local -a a=(); [[ -n "${SC_RL_PYTHON:-}" ]]&&a+=("$SC_RL_PYTHON"); if command -v brew >/dev/null 2>&1; then p="$(brew --prefix python@3.12 2>/dev/null||true)"; [[ -n "$p" ]]&&a+=("$p/bin/python3.12"); p="$(brew --prefix python@3.13 2>/dev/null||true)"; [[ -n "$p" ]]&&a+=("$p/bin/python3.13"); fi; a+=(python3.12 python3.13 python3); for c in "${a[@]}"; do r="$(command -v "$c" 2>/dev/null||true)"; [[ -n "$r" ]]||continue; m="$(run_clean "$r" -c 'import sys;print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null||true)"; [[ "$m" == 3.12 || "$m" == 3.13 ]]&&{ printf '%s\n' "$r"; return; }; done; }
PYTHON_BIN="$(find_python||true)"; [[ -n "$PYTHON_BIN" ]]||fail "Python 3.12 or 3.13 is required."
SSH_OUTPUT="$(ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -T git@github.com 2>&1||true)"; grep -qi 'successfully authenticated' <<<"$SSH_OUTPUT"||fail "GitHub SSH authentication is not ready. Run: ssh -T git@github.com"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/sc-rl-v800.XXXXXX")"; trap 'rm -rf "$TMP"' EXIT
unzip -q "$ZIP_PATH" -d "$TMP/release"; SRC="$TMP/release/sustainable-catalyst-research-librarian-ai"
[[ -f "$SRC/sustainable-catalyst-research-librarian-ai.php" ]]||fail "Expected repository root missing."
for f in backend/app/research_lifecycle.py backend/tests/test_v800_research_lifecycle.py docs/V800_UNIFIED_RESEARCH_INTELLIGENCE_LIFECYCLE.md data/research_librarian_unified_lifecycle_manifest_v8.0.0.json tests/v800-unified-research-intelligence-lifecycle-contract-test.php assets/sc-research-platform-v800-lifecycle.js; do [[ -f "$SRC/$f" ]]||fail "v8.0.0 file missing: $f"; done
grep -q 'Version: 8.0.0' "$SRC/sustainable-catalyst-research-librarian-ai.php"||fail "Plugin version mismatch."
grep -q '__version__ = "8.0.0"' "$SRC/backend/app/__init__.py"||fail "Backend version mismatch."
grep -q 'SCHEMA_VERSION = 18' "$SRC/backend/app/store.py"||fail "Ancillary SQLite schema 18 missing."
grep -q 'INDEX_SCHEMA = "sc-research-librarian-knowledge-index/13.0"' "$SRC/backend/app/store.py"||fail "Knowledge index changed unexpectedly."
grep -q 'sc-connected-research-api/2.0' "$SRC/backend/app/platform_v7.py"||fail "API 2.0 missing."
grep -q 'sc-research-librarian-public-workspace/3.0' "$SRC/backend/app/main.py"||fail "Workspace 3.0 missing."
grep -q 'human_confirmed_transitions' "$SRC/backend/app/research_lifecycle.py"||fail "Human-confirmed lifecycle boundary missing."
grep -q 'automatic_stage_advancement' "$SRC/backend/app/research_lifecycle.py"||fail "No-auto-advance lifecycle boundary missing."
grep -q 'data-sc-rl-v800-lifecycle-run' "$SRC/includes/class-sc-rl-v700-connected-platform.php"||fail "Research lifecycle UI missing."
if [[ -d "$REPO_DIR/.git" ]]; then :; else [[ ! -e "$REPO_DIR" ]]||fail "$REPO_DIR exists but is not a Git repository."; git clone "$REPO_URL" "$REPO_DIR"; fi
cd "$REPO_DIR"; git fetch origin --tags --prune; git switch main; git pull --ff-only origin main; git diff --quiet&&git diff --cached --quiet||fail "Repository has uncommitted changes."
git rev-parse -q --verify "refs/tags/$RELEASE_TAG" >/dev/null&&fail "Local tag exists." || true
git ls-remote --exit-code --tags origin "refs/tags/$RELEASE_TAG" >/dev/null 2>&1&&fail "Remote tag exists." || true
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
SC_RL_BACKEND_API_KEY=test-key SC_RL_DATA_DIR="$TMP/test-a" run_clean "$VENV_PY" -m pytest -q backend/tests
(cd backend; SC_RL_BACKEND_API_KEY=test-key SC_RL_DATA_DIR="$TMP/test-b" run_clean "$VENV_PY" -m pytest -q tests)
run_clean "$VENV_PY" -m compileall -q backend/app backend/tests
if grep -RInE --exclude-dir=.git --exclude-dir=.venv --exclude-dir=.pytest_cache --exclude-dir=__pycache__ --exclude='*.pyc' --exclude='PUSH_RESEARCH_LIBRARIAN_*.sh' '(BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY|github_pat_[A-Za-z0-9_]{20,}|ghp_[A-Za-z0-9]{30,}|sk-[A-Za-z0-9]{30,}|AIza[0-9A-Za-z_-]{30,})' .; then fail "Potential secret material detected."; fi
bash -n PUSH_RESEARCH_LIBRARIAN_V800_PY312.sh
git add -A; git diff --cached --quiet&&fail "No v8.0.0 changes detected."
git commit -m "Build Research Librarian v${RELEASE_VERSION}"
git tag -a "$RELEASE_TAG" -m "Research Librarian v${RELEASE_VERSION} — Unified Research Intelligence & Research Lifecycle Orchestration"
git push origin main; git push origin "$RELEASE_TAG"
printf '\nResearch Librarian v%s validated and pushed successfully.\n' "$RELEASE_VERSION"
printf 'Render should auto-deploy main. Then install the v8.0.0 WordPress package and smoke-test lifecycle creation, stage readiness, explicit transitions, checkpoints, project backup lineage, federated Save to My Library, and Workspace promotion boundaries.\n'
