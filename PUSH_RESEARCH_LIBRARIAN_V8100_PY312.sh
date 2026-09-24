#!/usr/bin/env bash
set -Eeuo pipefail
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"
VERSION="8.10.0"
TAG="v${VERSION}"
REPO_URL="git@github.com:Content-Catalyst-LLC/sustainable-catalyst-research-librarian-ai.git"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ZIP_PATH="${1:-$SCRIPT_DIR/sustainable-catalyst-research-librarian-ai-v8.10.0-repository.zip}"
REPO_DIR="${2:-$HOME/Downloads/sustainable-catalyst-research-librarian-ai-repo-v8100-clean}"
fail(){ printf 'ERROR: %s\n' "$*" >&2; exit 1; }
run_clean(){ env -u VIRTUAL_ENV -u PYTHONHOME -u PYTHONPATH -u PYTHONEXECUTABLE -u __PYVENV_LAUNCHER__ -u CONDA_PREFIX -u CONDA_DEFAULT_ENV -u PYENV_VERSION "$@"; }
for c in git unzip rsync php node shasum awk grep find; do command -v "$c" >/dev/null 2>&1 || fail "$c is required"; done
[[ -f "$ZIP_PATH" ]] || fail "Release ZIP not found: $ZIP_PATH"
printf 'Release archive: %s\nSHA-256: %s\n' "$ZIP_PATH" "$(shasum -a 256 "$ZIP_PATH"|awk '{print $1}')"
find_python(){ local c r m p; local -a a=(); [[ -n "${SC_RL_PYTHON:-}" ]]&&a+=("$SC_RL_PYTHON"); if command -v brew >/dev/null 2>&1; then p="$(brew --prefix python@3.12 2>/dev/null||true)"; [[ -n "$p" ]]&&a+=("$p/bin/python3.12"); p="$(brew --prefix python@3.13 2>/dev/null||true)"; [[ -n "$p" ]]&&a+=("$p/bin/python3.13"); fi; a+=(python3.12 python3.13 python3); for c in "${a[@]}"; do r="$(command -v "$c" 2>/dev/null||true)"; [[ -n "$r" ]]||continue; m="$(run_clean "$r" -c 'import sys;print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null||true)"; [[ "$m" == 3.12 || "$m" == 3.13 ]]&&{ printf '%s\n' "$r"; return; }; done; }
PYTHON_BIN="$(find_python||true)"; [[ -n "$PYTHON_BIN" ]]||fail "Python 3.12 or 3.13 is required."
TMP="$(mktemp -d "${TMPDIR:-/tmp}/sc-rl-v8100.XXXXXX")"; trap 'rm -rf "$TMP"' EXIT
unzip -q "$ZIP_PATH" -d "$TMP/release"
SRC="$(find "$TMP/release" -maxdepth 2 -type f -name sustainable-catalyst-research-librarian-ai.php -print -quit | xargs -I{} dirname {})"
[[ -n "$SRC" && -f "$SRC/sustainable-catalyst-research-librarian-ai.php" ]]||fail "Expected repository root missing."
for f in backend/app/contracts/argument_synthesis.py backend/app/services/argument_synthesis.py backend/tests/test_v8100_argument_synthesis.py docs/V8100_ARGUMENT_CONTRADICTION_SYNTHESIS_INTEGRATION.md data/research_librarian_argument_synthesis_manifest_v8.10.0.json tests/v8100-argument-contradiction-synthesis-contract-test.php RELEASE_MANIFEST_V8100.json deploy/contabo/upgrade_research_librarian_backend_v8_10_0_contabo.sh; do [[ -f "$SRC/$f" ]]||fail "v8.10.0 required file missing: $f"; done
grep -q 'Version: 8.10.0' "$SRC/sustainable-catalyst-research-librarian-ai.php"||fail "Plugin version mismatch."
grep -q '__version__ = "8.10.0"' "$SRC/backend/app/__init__.py"||fail "Backend version mismatch."
grep -q 'ARGUMENT_SYNTHESIS_SCHEMA' "$SRC/backend/app/contracts/argument_synthesis.py"||fail "v8.10 argument synthesis contract missing."
grep -q 'def build_plan' "$SRC/backend/app/services/argument_synthesis.py"||fail "v8.10 argument planner missing."
grep -q 'def promote_plan' "$SRC/backend/app/services/argument_synthesis.py"||fail "v8.10 Core argument promotion missing."
grep -q '/argument-synthesis/promote' "$SRC/backend/app/api/core.py"||fail "v8.10 promotion API missing."
grep -q '"argument-synthesis-plan"' "$SRC/backend/app/async_jobs.py"||fail "v8.10 durable planning job missing."
grep -q '/v1/research/arguments/.*/nodes' "$SRC/backend/app/clients/platform_core.py"||fail "Platform Core argument-node client missing."

rm -rf "$REPO_DIR"
git clone "$REPO_URL" "$REPO_DIR"
cd "$REPO_DIR"
git checkout main
git pull --ff-only origin main
rsync -a --delete --exclude='.git/' "$SRC/" "$REPO_DIR/"

echo "=== VALIDATING Research Librarian v8.10.0 ==="
php_count=0
while IFS= read -r -d '' f; do php -l "$f" >/dev/null; php_count=$((php_count+1)); done < <(find . -type f -name '*.php' -print0)
echo "PHP syntax passed: $php_count files."
js_count=0
while IFS= read -r -d '' f; do node --check "$f" >/dev/null; js_count=$((js_count+1)); done < <(find . -type f -name '*.js' -print0)
echo "JavaScript syntax passed: $js_count files."
json_count="$(find . -type f -name '*.json' | wc -l | tr -d ' ')"
run_clean "$PYTHON_BIN" - <<'PY'
from pathlib import Path
import json
for p in Path('.').rglob('*.json'): json.loads(p.read_text())
PY
echo "JSON validation passed: $json_count files."
for t in tests/*.php; do php "$t" >/dev/null; done
echo "WordPress contract/functional tests passed."
VENV="$TMP/venv"
run_clean "$PYTHON_BIN" -m venv "$VENV"
"$VENV/bin/python" -m pip install -q --upgrade pip
"$VENV/bin/python" -m pip install -q -r backend/requirements.txt
(cd backend && "$VENV/bin/python" -m pytest -q)
(cd backend && "$VENV/bin/python" -m compileall -q app)

git add -A
if git diff --cached --quiet; then fail "No v8.10.0 changes detected after applying release."; fi
git commit -m "Build Research Librarian v8.10.0 — argument contradiction synthesis integration"
git push origin main
if git rev-parse "$TAG" >/dev/null 2>&1; then fail "Tag $TAG already exists locally."; fi
git tag -a "$TAG" -m "Research Librarian v8.10.0 — Argument, Contradiction & Synthesis Integration"
git push origin "$TAG"
echo "Research Librarian v8.10.0 validated and pushed successfully."
echo "Deploy the backend package to Contabo before installing the WordPress v8.10.0 package."
