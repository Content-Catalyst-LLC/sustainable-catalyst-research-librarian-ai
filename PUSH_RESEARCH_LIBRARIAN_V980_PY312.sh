#!/usr/bin/env bash
set -Eeuo pipefail
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"
VERSION="9.8.0"; TAG="v${VERSION}"
REPO_URL="git@github.com:Content-Catalyst-LLC/sustainable-catalyst-research-librarian-ai.git"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ZIP_PATH="${1:-$SCRIPT_DIR/sustainable-catalyst-research-librarian-ai-v9.8.0-repository.zip}"
REPO_DIR="${2:-$HOME/Downloads/sustainable-catalyst-research-librarian-ai-repo-v980-clean}"
fail(){ printf 'ERROR: %s\n' "$*" >&2; exit 1; }
run_clean(){ env -u VIRTUAL_ENV -u PYTHONHOME -u PYTHONPATH -u PYTHONEXECUTABLE -u __PYVENV_LAUNCHER__ -u CONDA_PREFIX -u CONDA_DEFAULT_ENV -u PYENV_VERSION "$@"; }
for c in git unzip rsync php node shasum awk grep find bash; do command -v "$c" >/dev/null 2>&1 || fail "$c is required"; done
[[ -f "$ZIP_PATH" ]] || fail "Release ZIP not found: $ZIP_PATH"
printf 'Release archive: %s\nSHA-256: %s\n' "$ZIP_PATH" "$(shasum -a 256 "$ZIP_PATH"|awk '{print $1}')"
find_python(){ local c r m p; local -a a=(); [[ -n "${SC_RL_PYTHON:-}" ]]&&a+=("$SC_RL_PYTHON"); if command -v brew >/dev/null 2>&1; then p="$(brew --prefix python@3.12 2>/dev/null||true)"; [[ -n "$p" ]]&&a+=("$p/bin/python3.12"); p="$(brew --prefix python@3.13 2>/dev/null||true)"; [[ -n "$p" ]]&&a+=("$p/bin/python3.13"); fi; a+=(python3.12 python3.13 python3); for c in "${a[@]}"; do r="$(command -v "$c" 2>/dev/null||true)"; [[ -n "$r" ]]||continue; m="$(run_clean "$r" -c 'import sys;print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null||true)"; [[ "$m" == 3.12 || "$m" == 3.13 ]]&&{ printf '%s\n' "$r"; return; }; done; }
PYTHON_BIN="$(find_python||true)"; [[ -n "$PYTHON_BIN" ]]||fail "Python 3.12 or 3.13 is required."
TMP="$(mktemp -d "${TMPDIR:-/tmp}/sc-rl-v980.XXXXXX")"; trap 'rm -rf "$TMP"' EXIT
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
 deploy/contabo/upgrade_research_librarian_backend_v9_8_0_contabo.sh; do [[ -f "$SRC/$f" ]]||fail "required file missing: $f"; done
grep -q 'Version: 9.8.0' "$SRC/sustainable-catalyst-research-librarian-ai.php"||fail "Plugin version mismatch."
grep -q '__version__ = "9.8.0"' "$SRC/backend/app/__init__.py"||fail "Backend version mismatch."
grep -q 'AI_RESEARCH_CONTEXT_SCHEMA' "$SRC/backend/app/contracts/ai_research_context.py"||fail "v9.6 context contract missing."
grep -q 'RAG_EVALUATION_SCHEMA' "$SRC/backend/app/contracts/rag_evaluation.py"||fail "v9.7 evaluation contract missing."
grep -q 'AI_RESEARCH_EXPERIMENT_SCHEMA' "$SRC/backend/app/contracts/ai_research_experiment.py"||fail "v9.8 experiment contract missing."
grep -q 'class AIResearchExperimentStore' "$SRC/backend/app/services/ai_research_experiment.py"||fail "v9.8 experiment store missing."
grep -q '/ai-research-experiments/experiments/{experiment_id}/evaluation-bindings' "$SRC/backend/app/api/core.py"||fail "v9.8 evaluation binding API missing."
grep -q '"ai-research-experiment-snapshot"' "$SRC/backend/app/async_jobs.py"||fail "v9.8 durable experiment snapshot job missing."
grep -q 'automatic_best_model_selection.*False' "$SRC/backend/app/services/ai_research_experiment.py"||fail "v9.8 best-model guardrail missing."

printf '=== VALIDATING Research Librarian v9.8.0 ===\n'
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
git commit -m "Build Research Librarian v9.8.0 — AI Research Experiment Orchestration"
git push origin main
if git rev-parse "$TAG" >/dev/null 2>&1; then fail "Tag $TAG already exists locally."; fi
git tag -a "$TAG" -m "Research Librarian v9.8.0 — AI Research Experiment Orchestration"
git push origin "$TAG"
printf 'Research Librarian v9.8.0 validated and pushed successfully.\nDeploy the backend package to Contabo before installing the WordPress v9.8.0 package.\n'
