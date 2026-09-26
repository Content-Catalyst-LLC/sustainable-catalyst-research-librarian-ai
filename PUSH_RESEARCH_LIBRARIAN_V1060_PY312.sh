#!/usr/bin/env bash
set -Eeuo pipefail
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"
VERSION="10.6.0"; TAG="v${VERSION}"
REPO_URL="git@github.com:Content-Catalyst-LLC/sustainable-catalyst-research-librarian-ai.git"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ZIP_PATH="${1:-$SCRIPT_DIR/sustainable-catalyst-research-librarian-ai-v10.6.0-repository.zip}"
REPO_DIR="${2:-$HOME/Downloads/sustainable-catalyst-research-librarian-ai-repo-v1060-clean}"
fail(){ printf 'ERROR: %s\n' "$*" >&2; exit 1; }
run_clean(){ env -u VIRTUAL_ENV -u PYTHONHOME -u PYTHONPATH -u PYTHONEXECUTABLE -u __PYVENV_LAUNCHER__ -u CONDA_PREFIX -u CONDA_DEFAULT_ENV -u PYENV_VERSION "$@"; }
for c in git unzip rsync php node shasum awk grep find bash; do command -v "$c" >/dev/null 2>&1 || fail "$c is required"; done
[[ -f "$ZIP_PATH" ]] || fail "Release ZIP not found: $ZIP_PATH"
printf 'Release archive: %s\nSHA-256: %s\n' "$ZIP_PATH" "$(shasum -a 256 "$ZIP_PATH"|awk '{print $1}')"
find_python(){ local c r m p; local -a a=(); [[ -n "${SC_RL_PYTHON:-}" ]]&&a+=("$SC_RL_PYTHON"); if command -v brew >/dev/null 2>&1; then p="$(brew --prefix python@3.12 2>/dev/null||true)"; [[ -n "$p" ]]&&a+=("$p/bin/python3.12"); p="$(brew --prefix python@3.13 2>/dev/null||true)"; [[ -n "$p" ]]&&a+=("$p/bin/python3.13"); fi; a+=(python3.12 python3.13 python3); for c in "${a[@]}"; do r="$(command -v "$c" 2>/dev/null||true)"; [[ -n "$r" ]]||continue; m="$(run_clean "$r" -c 'import sys;print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null||true)"; [[ "$m" == 3.12 || "$m" == 3.13 ]]&&{ printf '%s\n' "$r"; return; }; done; }
PYTHON_BIN="$(find_python||true)"; [[ -n "$PYTHON_BIN" ]]||fail "Python 3.12 or 3.13 is required."
TMP="$(mktemp -d "${TMPDIR:-/tmp}/sc-rl-v1060.XXXXXX")"; trap 'rm -rf "$TMP"' EXIT
unzip -q "$ZIP_PATH" -d "$TMP/release"
SRC="$(find "$TMP/release" -maxdepth 2 -type f -name sustainable-catalyst-research-librarian-ai.php -print -quit | xargs -I{} dirname {})"
[[ -n "$SRC" && -f "$SRC/sustainable-catalyst-research-librarian-ai.php" ]]||fail "Expected repository root missing."
for f in \
 backend/app/contracts/systematic_review_evidence_synthesis.py backend/app/services/systematic_review_evidence_synthesis.py backend/tests/test_v1040_systematic_review_evidence_synthesis.py backend/migrations/019_systematic_review_evidence_synthesis.sql \
 backend/app/contracts/scholarly_literature_intelligence.py backend/app/services/scholarly_literature_intelligence.py backend/tests/test_v1050_scholarly_literature_intelligence.py backend/migrations/020_scholarly_citation_literature_intelligence.sql \
 docs/V1050_SCHOLARLY_CITATION_LITERATURE_INTELLIGENCE.md data/research_librarian_scholarly_literature_intelligence_manifest_v10.5.0.json tests/v1050-scholarly-citation-literature-intelligence-contract-test.php RELEASE_MANIFEST_V1050.json \
 deploy/contabo/upgrade_research_librarian_backend_v10_5_0_contabo.sh \
 backend/app/contracts/argument_claim_counterclaim_intelligence.py backend/app/services/argument_claim_counterclaim_intelligence.py backend/tests/test_v1060_argument_claim_counterclaim_intelligence.py backend/migrations/021_argument_claim_counterclaim_intelligence.sql \
 docs/V1060_ARGUMENT_CLAIM_COUNTERCLAIM_INTELLIGENCE.md data/research_librarian_argument_claim_counterclaim_intelligence_manifest_v10.6.0.json tests/v1060-argument-claim-counterclaim-intelligence-contract-test.php RELEASE_MANIFEST_V1060.json \
 deploy/contabo/upgrade_research_librarian_backend_v10_6_0_contabo.sh; do [[ -f "$SRC/$f" ]]||fail "required file missing: $f"; done
grep -q 'Version: 10.6.0' "$SRC/sustainable-catalyst-research-librarian-ai.php"||fail "Plugin version mismatch."
grep -q '__version__ = "10.6.0"' "$SRC/backend/app/__init__.py"||fail "Backend version mismatch."
grep -q 'SCHOLARLY_LITERATURE_INTELLIGENCE_SCHEMA' "$SRC/backend/app/contracts/scholarly_literature_intelligence.py"||fail "v10.5 literature-intelligence contract missing."
grep -q '/scholarly-literature-intelligence/projects/{intelligence_id}/citation-matrix' "$SRC/backend/app/api/core.py"||fail "v10.5 citation-matrix API missing."
grep -q '"scholarly-literature-intelligence-snapshot"' "$SRC/backend/app/async_jobs.py"||fail "v10.5 durable snapshot job missing."
grep -q 'human_gap_declaration_required.*True' "$SRC/backend/app/services/scholarly_literature_intelligence.py"||fail "v10.5 human-gap guardrail missing."
grep -q 'automatic_authority_ranking.*False' "$SRC/backend/app/services/scholarly_literature_intelligence.py"||fail "v10.5 authority-ranking guardrail missing."
grep -q 'automatic_seminal_work_classification.*False' "$SRC/backend/app/services/scholarly_literature_intelligence.py"||fail "v10.5 seminal-classification guardrail missing."
grep -q 'research_knowledge_graph_remains_citation_graph_authority.*True' "$SRC/backend/app/services/scholarly_literature_intelligence.py"||fail "v10.5 graph authority boundary missing."
grep -q 'literature-intelligence-plan' "$SRC/backend/app/services/unified_scholarly_ai_environment.py"||fail "v10.5 unified environment binding missing."
grep -q 'ARGUMENT_CLAIM_COUNTERCLAIM_INTELLIGENCE_SCHEMA' "$SRC/backend/app/contracts/argument_claim_counterclaim_intelligence.py"||fail "v10.6 argument-intelligence contract missing."
grep -q '/argument-claim-counterclaim-intelligence/projects/{argument_intelligence_id}/argument-map' "$SRC/backend/app/api/core.py"||fail "v10.6 argument-map API missing."
grep -q '"argument-claim-counterclaim-intelligence-snapshot"' "$SRC/backend/app/async_jobs.py"||fail "v10.6 durable snapshot job missing."
grep -q 'claim_acceptance_is_for_analysis_not_truth_status.*True' "$SRC/backend/app/services/argument_claim_counterclaim_intelligence.py"||fail "v10.6 analysis-not-truth guardrail missing."
grep -q 'automatic_argument_ranking.*False' "$SRC/backend/app/services/argument_claim_counterclaim_intelligence.py"||fail "v10.6 argument-ranking guardrail missing."
grep -q 'automatic_contradiction_resolution.*False' "$SRC/backend/app/services/argument_claim_counterclaim_intelligence.py"||fail "v10.6 contradiction-resolution guardrail missing."
grep -q 'argument-intelligence-plan' "$SRC/backend/app/services/unified_scholarly_ai_environment.py"||fail "v10.6 unified environment binding missing."
printf '=== VALIDATING Research Librarian v10.6.0 ===\n'
export SC_RL_SRC="$SRC"
find "$SRC" -type f -name '*.php' -print0 | while IFS= read -r -d '' f; do php -l "$f" >/dev/null || exit 1; done
find "$SRC" -type f -name '*.js' -print0 | while IFS= read -r -d '' f; do node --check "$f" >/dev/null || exit 1; done
run_clean "$PYTHON_BIN" - <<'PY_JSON'
import json, pathlib, os
src=pathlib.Path(os.environ['SC_RL_SRC'])
for p in src.rglob('*.json'): json.loads(p.read_text())
print('JSON validation passed.')
PY_JSON
for f in "$SRC"/tests/*test.php; do [[ "$(basename "$f")" == "live-ai-provider-contract-test.php" ]] && continue; php "$f" >/dev/null || fail "PHP contract failed: $(basename "$f")"; done
find "$SRC" -type f -name '*.sh' -print0 | while IFS= read -r -d '' f; do bash -n "$f" || exit 1; done
VENV="$TMP/venv"; run_clean "$PYTHON_BIN" -m venv "$VENV"; "$VENV/bin/pip" -q install -r "$SRC/backend/requirements.txt" pytest; (cd "$SRC/backend" && PYTHONPATH=. "$VENV/bin/pytest" -q)
if grep -RIE --exclude-dir=.git --exclude='*.md' --exclude='*.txt' '(BEGIN (RSA|OPENSSH|EC) PRIVATE KEY|AIza[0-9A-Za-z_-]{20,}|sk-[0-9A-Za-z]{20,})' "$SRC" >/dev/null; then fail "Secret-pattern scan failed."; fi
printf 'Release validation passed.\n'
rm -rf "$REPO_DIR"; git clone "$REPO_URL" "$REPO_DIR"; cd "$REPO_DIR"; git checkout main; git pull --ff-only origin main
rsync -a --delete --exclude='.git/' "$SRC/" "$REPO_DIR/"
git add -A
if git diff --cached --quiet; then fail "No release changes detected."; fi
git commit -m "Build Research Librarian v10.6.0 — Argument, Claim & Counterclaim Intelligence"
git push origin HEAD:main
if git rev-parse "$TAG" >/dev/null 2>&1 || git ls-remote --tags origin "refs/tags/$TAG" | grep -q .; then fail "Tag $TAG already exists."; fi
git tag -a "$TAG" -m "Research Librarian v10.6.0 — Argument, Claim & Counterclaim Intelligence"
git push origin "$TAG"
printf 'PASS: Research Librarian v10.6.0 committed, tagged, and pushed.\nDeploy the backend package to Contabo before installing the WordPress v10.6.0 package.\n'
