#!/usr/bin/env bash
set -Eeuo pipefail
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"
VERSION="11.0.0"; TAG="v${VERSION}"
REPO_URL="git@github.com:Content-Catalyst-LLC/sustainable-catalyst-research-librarian-ai.git"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ZIP_PATH="${1:-$SCRIPT_DIR/sustainable-catalyst-research-librarian-ai-v11.0.0-repository.zip}"
REPO_DIR="${2:-$HOME/Downloads/sustainable-catalyst-research-librarian-ai-repo-v1100-clean}"
fail(){ printf 'ERROR: %s\n' "$*" >&2; exit 1; }
run_clean(){ env -u VIRTUAL_ENV -u PYTHONHOME -u PYTHONPATH -u PYTHONEXECUTABLE -u __PYVENV_LAUNCHER__ -u CONDA_PREFIX -u CONDA_DEFAULT_ENV -u PYENV_VERSION "$@"; }
for c in git unzip rsync php node shasum awk grep find bash; do command -v "$c" >/dev/null 2>&1 || fail "$c is required"; done
[[ -f "$ZIP_PATH" ]] || fail "Release ZIP not found: $ZIP_PATH"
printf 'Release archive: %s\nSHA-256: %s\n' "$ZIP_PATH" "$(shasum -a 256 "$ZIP_PATH"|awk '{print $1}')"
find_python(){ local c r m p; local -a a=(); [[ -n "${SC_RL_PYTHON:-}" ]]&&a+=("$SC_RL_PYTHON"); if command -v brew >/dev/null 2>&1; then p="$(brew --prefix python@3.12 2>/dev/null||true)"; [[ -n "$p" ]]&&a+=("$p/bin/python3.12"); p="$(brew --prefix python@3.13 2>/dev/null||true)"; [[ -n "$p" ]]&&a+=("$p/bin/python3.13"); fi; a+=(python3.12 python3.13 python3); for c in "${a[@]}"; do r="$(command -v "$c" 2>/dev/null||true)"; [[ -n "$r" ]]||continue; m="$(run_clean "$r" -c 'import sys;print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null||true)"; [[ "$m" == 3.12 || "$m" == 3.13 ]]&&{ printf '%s\n' "$r"; return; }; done; }
PYTHON_BIN="$(find_python||true)"; [[ -n "$PYTHON_BIN" ]]||fail "Python 3.12 or 3.13 is required."
TMP="$(mktemp -d "${TMPDIR:-/tmp}/sc-rl-v1100.XXXXXX")"; trap 'rm -rf "$TMP"' EXIT
unzip -q "$ZIP_PATH" -d "$TMP/release"
SRC="$(find "$TMP/release" -maxdepth 2 -type f -name sustainable-catalyst-research-librarian-ai.php -print -quit | xargs -I{} dirname {})"
[[ -n "$SRC" && -f "$SRC/sustainable-catalyst-research-librarian-ai.php" ]]||fail "Expected repository root missing."
for f in \
 backend/app/contracts/computational_research_planning.py backend/app/services/computational_research_planning.py backend/tests/test_v1090_computational_research_planning.py backend/migrations/024_computational_research_planning.sql \
 backend/app/contracts/research_program_intelligence.py backend/app/services/research_program_intelligence.py backend/tests/test_v1100_research_program_intelligence.py backend/migrations/025_research_program_intelligence.sql \
 docs/V1100_RESEARCH_PROGRAM_INTELLIGENCE.md data/research_librarian_research_program_intelligence_manifest_v11.0.0.json \
 tests/v1100-research-program-intelligence-contract-test.php RELEASE_MANIFEST_V1100.json deploy/contabo/upgrade_research_librarian_backend_v11_0_0_contabo.sh; do
  [[ -f "$SRC/$f" ]]||fail "required file missing: $f"
done
grep -q 'Version: 11.0.0' "$SRC/sustainable-catalyst-research-librarian-ai.php"||fail "Plugin version mismatch."
grep -q '__version__ = "11.0.0"' "$SRC/backend/app/__init__.py"||fail "Backend version mismatch."
grep -q 'RESEARCH_PROGRAM_INTELLIGENCE_SCHEMA' "$SRC/backend/app/contracts/research_program_intelligence.py"||fail "v11.0 contract missing."
grep -q '/research-program-intelligence/programs/{research_program_id}/program-graph' "$SRC/backend/app/api/core.py"||fail "v11.0 program graph API missing."
grep -q '"research-program-intelligence-snapshot"' "$SRC/backend/app/async_jobs.py"||fail "v11.0 durable snapshot job missing."
grep -q 'human_program_approval_required.*True' "$SRC/backend/app/services/research_program_intelligence.py"||fail "v11.0 human approval guardrail missing."
grep -q 'automatic_research_prioritization.*False' "$SRC/backend/app/services/research_program_intelligence.py"||fail "v11.0 prioritization guardrail missing."
grep -q 'automatic_resource_allocation.*False' "$SRC/backend/app/services/research_program_intelligence.py"||fail "v11.0 resource allocation guardrail missing."
grep -q 'automatic_execution.*False' "$SRC/backend/app/services/research_program_intelligence.py"||fail "v11.0 execution guardrail missing."
grep -q 'research-program' "$SRC/backend/app/services/unified_scholarly_ai_environment.py"||fail "v11.0 unified environment binding missing."
printf '=== VALIDATING Research Librarian v11.0.0 ===\n'
export SC_RL_SRC="$SRC"
find "$SRC" -type f -name '*.php' -print0 | while IFS= read -r -d '' f; do php -l "$f" >/dev/null || exit 1; done
find "$SRC" -type f -name '*.js' -print0 | while IFS= read -r -d '' f; do node --check "$f" >/dev/null || exit 1; done
run_clean "$PYTHON_BIN" - <<'PYJSON1100'
import json,pathlib,os
for p in pathlib.Path(os.environ['SC_RL_SRC']).rglob('*.json'): json.loads(p.read_text())
print('JSON validation passed.')
PYJSON1100
for f in "$SRC"/tests/*test.php; do [[ "$(basename "$f")" == "live-ai-provider-contract-test.php" ]] && continue; php "$f" >/dev/null || fail "PHP contract failed: $(basename "$f")"; done
find "$SRC" -type f -name '*.sh' -print0 | while IFS= read -r -d '' f; do bash -n "$f" || exit 1; done
VENV="$TMP/venv"; run_clean "$PYTHON_BIN" -m venv "$VENV"; "$VENV/bin/pip" -q install -r "$SRC/backend/requirements.txt" pytest; (cd "$SRC/backend" && SC_RL_BACKEND_API_KEY=test-key PYTHONPATH=. "$VENV/bin/pytest" -q)
if grep -RIE --exclude-dir=.git --exclude='*.md' --exclude='*.txt' '(BEGIN (RSA|OPENSSH|EC) PRIVATE KEY|AIza[0-9A-Za-z_-]{20,}|sk-[0-9A-Za-z]{20,})' "$SRC" >/dev/null; then fail "Secret-pattern scan failed."; fi
printf 'Release validation passed.\n'
rm -rf "$REPO_DIR"; git clone "$REPO_URL" "$REPO_DIR"; cd "$REPO_DIR"; git checkout main; git pull --ff-only origin main
rsync -a --delete --exclude='.git/' "$SRC/" "$REPO_DIR/"
git add -A
if git diff --cached --quiet; then fail "No release changes detected."; fi
git commit -m "Build Research Librarian v11.0.0 — Research Program Intelligence"
git push origin HEAD:main
if git rev-parse "$TAG" >/dev/null 2>&1 || git ls-remote --tags origin "refs/tags/$TAG" | grep -q .; then fail "Tag $TAG already exists."; fi
git tag -a "$TAG" -m "Research Librarian v11.0.0 — Research Program Intelligence"
git push origin "$TAG"
printf 'PASS: Research Librarian v11.0.0 committed, tagged, and pushed.\nDeploy the backend package to Contabo before installing the WordPress v11.0.0 package.\n'
