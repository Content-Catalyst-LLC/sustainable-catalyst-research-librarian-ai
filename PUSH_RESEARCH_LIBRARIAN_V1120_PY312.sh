#!/usr/bin/env bash
set -Eeuo pipefail
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"
VERSION="11.2.0"; TAG="v${VERSION}"
REPO_URL="git@github.com:Content-Catalyst-LLC/sustainable-catalyst-research-librarian-ai.git"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ZIP_PATH="${1:-$SCRIPT_DIR/sustainable-catalyst-research-librarian-ai-v11.2.0-repository.zip}"
REPO_DIR="${2:-$HOME/Downloads/sustainable-catalyst-research-librarian-ai-repo-v1120-clean}"
fail(){ printf 'ERROR: %s\n' "$*" >&2; exit 1; }
run_clean(){ env -u VIRTUAL_ENV -u PYTHONHOME -u PYTHONPATH -u PYTHONEXECUTABLE -u __PYVENV_LAUNCHER__ -u CONDA_PREFIX -u CONDA_DEFAULT_ENV -u PYENV_VERSION "$@"; }
for c in git unzip rsync php node shasum awk grep find bash; do command -v "$c" >/dev/null 2>&1 || fail "$c is required"; done
[[ -f "$ZIP_PATH" ]] || fail "Release ZIP not found: $ZIP_PATH"
printf 'Release archive: %s\nSHA-256: %s\n' "$ZIP_PATH" "$(shasum -a 256 "$ZIP_PATH"|awk '{print $1}')"
find_python(){ local c r m p; local -a a=(); [[ -n "${SC_RL_PYTHON:-}" ]]&&a+=("$SC_RL_PYTHON"); if command -v brew >/dev/null 2>&1; then p="$(brew --prefix python@3.12 2>/dev/null||true)"; [[ -n "$p" ]]&&a+=("$p/bin/python3.12"); p="$(brew --prefix python@3.13 2>/dev/null||true)"; [[ -n "$p" ]]&&a+=("$p/bin/python3.13"); fi; a+=(python3.12 python3.13 python3); for c in "${a[@]}"; do r="$(command -v "$c" 2>/dev/null||true)"; [[ -n "$r" ]]||continue; m="$(run_clean "$r" -c 'import sys;print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null||true)"; [[ "$m" == 3.12 || "$m" == 3.13 ]]&&{ printf '%s\n' "$r"; return; }; done; }
PYTHON_BIN="$(find_python||true)"; [[ -n "$PYTHON_BIN" ]]||fail "Python 3.12 or 3.13 is required."
TMP="$(mktemp -d "${TMPDIR:-/tmp}/sc-rl-v1120.XXXXXX")"; trap 'rm -rf "$TMP"' EXIT
unzip -q "$ZIP_PATH" -d "$TMP/release"
SRC="$(find "$TMP/release" -maxdepth 2 -type f -name sustainable-catalyst-research-librarian-ai.php -print -quit | xargs -I{} dirname {})"
[[ -n "$SRC" && -f "$SRC/sustainable-catalyst-research-librarian-ai.php" ]]||fail "Expected repository root missing."
for f in \
 backend/app/contracts/study_protocol_preregistration.py backend/app/services/study_protocol_preregistration.py backend/tests/test_v1110_study_protocol_preregistration.py backend/migrations/026_study_protocol_preregistration_engine.sql \
 backend/app/contracts/statistical_analysis_planning_intelligence.py backend/app/services/statistical_analysis_planning_intelligence.py backend/tests/test_v1120_statistical_analysis_planning_intelligence.py backend/migrations/027_statistical_analysis_planning_intelligence.sql \
 docs/V1110_STUDY_PROTOCOL_PREREGISTRATION_ENGINE.md docs/V1120_STATISTICAL_ANALYSIS_PLANNING_INTELLIGENCE.md \
 data/research_librarian_study_protocol_preregistration_manifest_v11.1.0.json data/research_librarian_statistical_analysis_planning_intelligence_manifest_v11.2.0.json \
 tests/v1110-study-protocol-preregistration-contract-test.php tests/v1120-statistical-analysis-planning-intelligence-contract-test.php RELEASE_MANIFEST_V1120.json deploy/contabo/upgrade_research_librarian_backend_v11_2_0_contabo.sh; do
  [[ -f "$SRC/$f" ]]||fail "required file missing: $f"
done
grep -q 'Version: 11.2.0' "$SRC/sustainable-catalyst-research-librarian-ai.php"||fail "Plugin version mismatch."
grep -q '__version__ = "11.2.0"' "$SRC/backend/app/__init__.py"||fail "Backend version mismatch."
grep -q 'STUDY_PROTOCOL_PREREGISTRATION_SCHEMA' "$SRC/backend/app/contracts/study_protocol_preregistration.py"||fail "v11.1 protocol contract missing."
grep -q 'STATISTICAL_ANALYSIS_PLANNING_SCHEMA' "$SRC/backend/app/contracts/statistical_analysis_planning_intelligence.py"||fail "v11.2 statistical planning contract missing."
grep -q '/statistical-analysis-planning-intelligence/plans/{statistical_analysis_plan_id}/runtime-handoffs' "$SRC/backend/app/api/core.py"||fail "v11.2 runtime handoff API missing."
grep -q '"statistical-analysis-planning-intelligence-snapshot"' "$SRC/backend/app/async_jobs.py"||fail "v11.2 durable snapshot job missing."
grep -q 'human_statistical_approval_required.*True' "$SRC/backend/app/services/statistical_analysis_planning_intelligence.py"||fail "v11.2 human approval guardrail missing."
grep -q 'existing_statistical_research_layer_remains_runtime_core_bridge.*True' "$SRC/backend/app/services/statistical_analysis_planning_intelligence.py"||fail "v11.2 v8.11 bridge boundary missing."
grep -q 'automatic_model_selection.*False' "$SRC/backend/app/services/statistical_analysis_planning_intelligence.py"||fail "v11.2 model selection guardrail missing."
grep -q 'automatic_power_calculation.*False' "$SRC/backend/app/services/statistical_analysis_planning_intelligence.py"||fail "v11.2 power guardrail missing."
grep -q 'automatic_significance_inference.*False' "$SRC/backend/app/services/statistical_analysis_planning_intelligence.py"||fail "v11.2 significance guardrail missing."
grep -q 'automatic_execution.*False' "$SRC/backend/app/services/statistical_analysis_planning_intelligence.py"||fail "v11.2 execution guardrail missing."
grep -q 'statistical-analysis-plan-intelligence' "$SRC/backend/app/services/unified_scholarly_ai_environment.py"||fail "v11.2 unified environment binding missing."
printf '=== VALIDATING Research Librarian v11.2.0 ===\n'
export SC_RL_SRC="$SRC"
find "$SRC" -type f -name '*.php' -print0 | while IFS= read -r -d '' f; do php -l "$f" >/dev/null || exit 1; done
find "$SRC" -type f -name '*.js' -print0 | while IFS= read -r -d '' f; do node --check "$f" >/dev/null || exit 1; done
run_clean "$PYTHON_BIN" - <<'PYJSON1120'
import json,pathlib,os
for p in pathlib.Path(os.environ['SC_RL_SRC']).rglob('*.json'): json.loads(p.read_text())
print('JSON validation passed.')
PYJSON1120
for f in "$SRC"/tests/*test.php; do [[ "$(basename "$f")" == "live-ai-provider-contract-test.php" ]] && continue; php "$f" >/dev/null || fail "PHP contract failed: $(basename "$f")"; done
find "$SRC" -type f -name '*.sh' -print0 | while IFS= read -r -d '' f; do bash -n "$f" || exit 1; done
VENV="$TMP/venv"; run_clean "$PYTHON_BIN" -m venv "$VENV"; "$VENV/bin/pip" -q install -r "$SRC/backend/requirements.txt" pytest; (cd "$SRC/backend" && SC_RL_BACKEND_API_KEY=test-key PYTHONPATH=. "$VENV/bin/pytest" -q)
if grep -RIE --exclude-dir=.git --exclude='*.md' --exclude='*.txt' '(BEGIN (RSA|OPENSSH|EC) PRIVATE KEY|AIza[0-9A-Za-z_-]{20,}|sk-[0-9A-Za-z]{20,})' "$SRC" >/dev/null; then fail "Secret-pattern scan failed."; fi
printf 'Release validation passed.\n'
rm -rf "$REPO_DIR"; git clone "$REPO_URL" "$REPO_DIR"; cd "$REPO_DIR"; git checkout main; git pull --ff-only origin main
rsync -a --delete --exclude='.git/' "$SRC/" "$REPO_DIR/"
git add -A
if git diff --cached --quiet; then fail "No release changes detected."; fi
git commit -m "Build Research Librarian v11.2.0 — Statistical Analysis Planning Intelligence"
git push origin HEAD:main
if git rev-parse "$TAG" >/dev/null 2>&1 || git ls-remote --tags origin "refs/tags/$TAG" | grep -q .; then fail "Tag $TAG already exists."; fi
git tag -a "$TAG" -m "Research Librarian v11.2.0 — Statistical Analysis Planning Intelligence"
git push origin "$TAG"
printf 'PASS: Research Librarian v11.2.0 committed, tagged, and pushed.\nDeploy the backend package to Contabo before installing the WordPress v11.2.0 package.\n'
