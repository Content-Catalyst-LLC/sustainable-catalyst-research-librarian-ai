#!/usr/bin/env bash
set -Eeuo pipefail
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"
VERSION="10.2.0"; TAG="v${VERSION}"
REPO_URL="git@github.com:Content-Catalyst-LLC/sustainable-catalyst-research-librarian-ai.git"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ZIP_PATH="${1:-$SCRIPT_DIR/sustainable-catalyst-research-librarian-ai-v10.2.0-repository.zip}"
REPO_DIR="${2:-$HOME/Downloads/sustainable-catalyst-research-librarian-ai-repo-v1020-clean}"
fail(){ printf 'ERROR: %s\n' "$*" >&2; exit 1; }
run_clean(){ env -u VIRTUAL_ENV -u PYTHONHOME -u PYTHONPATH -u PYTHONEXECUTABLE -u __PYVENV_LAUNCHER__ -u CONDA_PREFIX -u CONDA_DEFAULT_ENV -u PYENV_VERSION "$@"; }
for c in git unzip rsync php node shasum awk grep find bash; do command -v "$c" >/dev/null 2>&1 || fail "$c is required"; done
[[ -f "$ZIP_PATH" ]] || fail "Release ZIP not found: $ZIP_PATH"
printf 'Release archive: %s\nSHA-256: %s\n' "$ZIP_PATH" "$(shasum -a 256 "$ZIP_PATH"|awk '{print $1}')"
find_python(){ local c r m p; local -a a=(); [[ -n "${SC_RL_PYTHON:-}" ]]&&a+=("$SC_RL_PYTHON"); if command -v brew >/dev/null 2>&1; then p="$(brew --prefix python@3.12 2>/dev/null||true)"; [[ -n "$p" ]]&&a+=("$p/bin/python3.12"); p="$(brew --prefix python@3.13 2>/dev/null||true)"; [[ -n "$p" ]]&&a+=("$p/bin/python3.13"); fi; a+=(python3.12 python3.13 python3); for c in "${a[@]}"; do r="$(command -v "$c" 2>/dev/null||true)"; [[ -n "$r" ]]||continue; m="$(run_clean "$r" -c 'import sys;print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null||true)"; [[ "$m" == 3.12 || "$m" == 3.13 ]]&&{ printf '%s\n' "$r"; return; }; done; }
PYTHON_BIN="$(find_python||true)"; [[ -n "$PYTHON_BIN" ]]||fail "Python 3.12 or 3.13 is required."
TMP="$(mktemp -d "${TMPDIR:-/tmp}/sc-rl-v1020.XXXXXX")"; trap 'rm -rf "$TMP"' EXIT
unzip -q "$ZIP_PATH" -d "$TMP/release"
SRC="$(find "$TMP/release" -maxdepth 2 -type f -name sustainable-catalyst-research-librarian-ai.php -print -quit | xargs -I{} dirname {})"
[[ -n "$SRC" && -f "$SRC/sustainable-catalyst-research-librarian-ai.php" ]]||fail "Expected repository root missing."
for f in \
 backend/app/contracts/ai_research_context.py backend/app/services/ai_research_context.py backend/tests/test_v960_ai_research_context.py backend/migrations/011_ai_aware_retrieval_context_engineering.sql \
 docs/V960_AI_AWARE_RETRIEVAL_RESEARCH_CONTEXT_ENGINEERING.md data/research_librarian_ai_research_context_manifest_v9.6.0.json tests/v960-ai-aware-retrieval-research-context-contract-test.php RELEASE_MANIFEST_V960.json \
 backend/app/contracts/rag_evaluation.py backend/app/services/rag_evaluation.py backend/tests/test_v970_rag_evaluation.py backend/migrations/012_rag_evaluation_evidence_grounding.sql \
 docs/V970_RAG_EVALUATION_EVIDENCE_GROUNDING_FRAMEWORK.md data/research_librarian_rag_evaluation_manifest_v9.7.0.json tests/v970-rag-evaluation-evidence-grounding-contract-test.php RELEASE_MANIFEST_V970.json \
 backend/app/contracts/ai_research_experiment.py backend/app/services/ai_research_experiment.py backend/tests/test_v980_ai_research_experiment.py backend/migrations/013_ai_research_experiment_orchestration.sql \
 docs/V980_AI_RESEARCH_EXPERIMENT_ORCHESTRATION.md data/research_librarian_ai_research_experiment_manifest_v9.8.0.json tests/v980-ai-research-experiment-orchestration-contract-test.php RELEASE_MANIFEST_V980.json \
 backend/app/contracts/model_aware_exchange.py backend/app/services/model_aware_exchange.py backend/tests/test_v990_model_aware_exchange.py backend/migrations/014_model_aware_research_cross_product_exchange.sql \
 docs/V990_MODEL_AWARE_RESEARCH_INTELLIGENCE_CROSS_PRODUCT_EXCHANGE.md data/research_librarian_model_aware_exchange_manifest_v9.9.0.json tests/v990-model-aware-research-cross-product-exchange-contract-test.php RELEASE_MANIFEST_V990.json \
 backend/app/contracts/unified_scholarly_ai_environment.py backend/app/services/unified_scholarly_ai_environment.py backend/tests/test_v1000_unified_scholarly_ai_environment.py backend/migrations/015_unified_scholarly_ai_research_environment.sql \
 docs/V1000_UNIFIED_SCHOLARLY_AI_RESEARCH_INTELLIGENCE_ENVIRONMENT.md data/research_librarian_unified_scholarly_ai_environment_manifest_v10.0.0.json tests/v1000-unified-scholarly-ai-research-environment-contract-test.php RELEASE_MANIFEST_V1000.json \
 deploy/contabo/upgrade_research_librarian_backend_v10_0_0_contabo.sh \
 backend/app/contracts/research_question_hypothesis.py backend/app/services/research_question_hypothesis.py backend/tests/test_v1010_research_question_hypothesis.py backend/migrations/016_research_question_hypothesis_intelligence.sql \
 docs/V1010_RESEARCH_QUESTION_HYPOTHESIS_INTELLIGENCE.md data/research_librarian_research_question_hypothesis_manifest_v10.1.0.json tests/v1010-research-question-hypothesis-intelligence-contract-test.php RELEASE_MANIFEST_V1010.json \
 deploy/contabo/upgrade_research_librarian_backend_v10_1_0_contabo.sh \
 backend/app/contracts/research_design_methodology.py backend/app/services/research_design_methodology.py backend/tests/test_v1020_research_design_methodology.py backend/migrations/017_research_design_methodology_planner.sql \
 docs/V1020_RESEARCH_DESIGN_METHODOLOGY_PLANNER.md data/research_librarian_research_design_methodology_manifest_v10.2.0.json tests/v1020-research-design-methodology-planner-contract-test.php RELEASE_MANIFEST_V1020.json \
 deploy/contabo/upgrade_research_librarian_backend_v10_2_0_contabo.sh; do [[ -f "$SRC/$f" ]]||fail "required file missing: $f"; done
grep -q 'Version: 10.2.0' "$SRC/sustainable-catalyst-research-librarian-ai.php"||fail "Plugin version mismatch."
grep -q '__version__ = "10.2.0"' "$SRC/backend/app/__init__.py"||fail "Backend version mismatch."
grep -q 'AI_RESEARCH_CONTEXT_SCHEMA' "$SRC/backend/app/contracts/ai_research_context.py"||fail "v9.6 context contract missing."
grep -q 'RAG_EVALUATION_SCHEMA' "$SRC/backend/app/contracts/rag_evaluation.py"||fail "v9.7 evaluation contract missing."
grep -q 'AI_RESEARCH_EXPERIMENT_SCHEMA' "$SRC/backend/app/contracts/ai_research_experiment.py"||fail "v9.8 experiment contract missing."
grep -q 'class AIResearchExperimentStore' "$SRC/backend/app/services/ai_research_experiment.py"||fail "v9.8 experiment store missing."
grep -q '/ai-research-experiments/experiments/{experiment_id}/evaluation-bindings' "$SRC/backend/app/api/core.py"||fail "v9.8 evaluation binding API missing."
grep -q '"ai-research-experiment-snapshot"' "$SRC/backend/app/async_jobs.py"||fail "v9.8 durable experiment snapshot job missing."
grep -q 'automatic_best_model_selection.*False' "$SRC/backend/app/services/ai_research_experiment.py"||fail "v9.8 best-model guardrail missing."
grep -q 'MODEL_AWARE_RESEARCH_SCHEMA' "$SRC/backend/app/contracts/model_aware_exchange.py"||fail "v9.9 model-aware research contract missing."
grep -q '/cross-product-exchange/exchanges/{exchange_id}/receipts' "$SRC/backend/app/api/core.py"||fail "v9.9 exchange receipt API missing."
grep -q '"model-aware-research-snapshot"' "$SRC/backend/app/async_jobs.py"||fail "v9.9 durable model-aware snapshot job missing."
grep -q 'automatic_delivery.*False' "$SRC/backend/app/services/model_aware_exchange.py"||fail "v9.9 automatic-delivery guardrail missing."

grep -q 'UNIFIED_SCHOLARLY_AI_ENVIRONMENT_SCHEMA' "$SRC/backend/app/contracts/unified_scholarly_ai_environment.py"||fail "v10 unified environment contract missing."
grep -q '/unified-research-environment/environments/{environment_id}/dossier' "$SRC/backend/app/api/core.py"||fail "v10 unified dossier API missing."
grep -q '"unified-research-environment-snapshot"' "$SRC/backend/app/async_jobs.py"||fail "v10 unified environment snapshot job missing."
grep -q 'component_authority_remains_with_source_system.*True' "$SRC/backend/app/services/unified_scholarly_ai_environment.py"||fail "v10 source-authority guardrail missing."
grep -q 'automatic_truth_promotion.*False' "$SRC/backend/app/services/unified_scholarly_ai_environment.py"||fail "v10 truth-promotion guardrail missing."
grep -q 'RESEARCH_QUESTION_HYPOTHESIS_SCHEMA' "$SRC/backend/app/contracts/research_question_hypothesis.py"||fail "v10.1 question/hypothesis contract missing."
grep -q '/research-question-hypothesis/plans/{plan_id}/core-candidates' "$SRC/backend/app/api/core.py"||fail "v10.1 Core candidate API missing."
grep -q '"research-question-hypothesis-snapshot"' "$SRC/backend/app/async_jobs.py"||fail "v10.1 durable question/hypothesis snapshot job missing."
grep -q 'platform_core_is_governed_question_hypothesis_authority.*True' "$SRC/backend/app/services/research_question_hypothesis.py"||fail "v10.1 Core authority guardrail missing."
grep -q 'automatic_hypothesis_acceptance.*False' "$SRC/backend/app/services/research_question_hypothesis.py"||fail "v10.1 hypothesis-acceptance guardrail missing."
grep -q 'automatic_causal_inference.*False' "$SRC/backend/app/services/research_question_hypothesis.py"||fail "v10.1 causal-inference guardrail missing."
grep -q 'research-question-plan' "$SRC/backend/app/services/unified_scholarly_ai_environment.py"||fail "v10.1 unified environment binding missing."
grep -q 'RESEARCH_DESIGN_METHODOLOGY_SCHEMA' "$SRC/backend/app/contracts/research_design_methodology.py"||fail "v10.2 methodology contract missing."
grep -q '/research-design-methodology/plans/{plan_id}/comparison' "$SRC/backend/app/api/core.py"||fail "v10.2 methodology comparison API missing."
grep -q '"research-design-methodology-snapshot"' "$SRC/backend/app/async_jobs.py"||fail "v10.2 durable methodology snapshot job missing."
grep -q 'human_method_selection_required.*True' "$SRC/backend/app/services/research_design_methodology.py"||fail "v10.2 human-method-selection guardrail missing."
grep -q 'automatic_method_selection.*False' "$SRC/backend/app/services/research_design_methodology.py"||fail "v10.2 automatic-method-selection guardrail missing."
grep -q 'research-design-plan' "$SRC/backend/app/services/unified_scholarly_ai_environment.py"||fail "v10.2 unified environment design binding missing."

printf '=== VALIDATING Research Librarian v10.2.0 ===\n'
find "$SRC" -type f -name '*.php' -print0 | while IFS= read -r -d '' f; do php -l "$f" >/dev/null || exit 1; done
printf 'PHP syntax passed.\n'
find "$SRC" -type f -name '*.js' -print0 | while IFS= read -r -d '' f; do node --check "$f" >/dev/null || exit 1; done
printf 'JavaScript syntax passed.\n'
run_clean "$PYTHON_BIN" - <<PY
import json, pathlib
for p in pathlib.Path(r'''$SRC''').rglob('*.json'): json.loads(p.read_text())
print('JSON validation passed.')
PY
for f in "$SRC"/tests/*test.php; do php "$f" >/dev/null || fail "PHP contract failed: $(basename "$f")"; done
printf 'WordPress contract/functional tests passed.\n'
find "$SRC" -type f -name '*.sh' -print0 | while IFS= read -r -d '' f; do bash -n "$f" || exit 1; done
printf 'Shell syntax passed.\n'
VENV="$TMP/venv"; run_clean "$PYTHON_BIN" -m venv "$VENV"; "$VENV/bin/pip" -q install -r "$SRC/backend/requirements.txt" pytest; (cd "$SRC/backend" && PYTHONPATH=. "$VENV/bin/pytest" -q)
if grep -RIE --exclude-dir=.git --exclude='*.md' --exclude='*.txt' '(BEGIN (RSA|OPENSSH|EC) PRIVATE KEY|AIza[0-9A-Za-z_-]{20,}|sk-[0-9A-Za-z]{20,})' "$SRC" >/dev/null; then fail "Secret-pattern scan failed."; fi
printf 'Secret-pattern scan passed.\n'
rm -rf "$REPO_DIR"; git clone "$REPO_URL" "$REPO_DIR"; cd "$REPO_DIR"; git checkout main; git pull --ff-only origin main
rsync -a --delete --exclude='.git/' "$SRC/" "$REPO_DIR/"
git add -A
git commit -m "Build Research Librarian v10.2.0 — Research Design & Methodology Planner"
git push origin main
if git rev-parse "$TAG" >/dev/null 2>&1; then fail "Tag $TAG already exists locally."; fi
git tag -a "$TAG" -m "Research Librarian v10.2.0 — Research Design & Methodology Planner"
git push origin "$TAG"
printf 'Research Librarian v10.2.0 validated and pushed successfully.\nDeploy the backend package to Contabo before installing the WordPress v10.2.0 package.\n'
