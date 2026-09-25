#!/usr/bin/env bash
set -Eeuo pipefail
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"
VERSION="9.7.0"
TAG="v${VERSION}"
REPO_URL="git@github.com:Content-Catalyst-LLC/sustainable-catalyst-research-librarian-ai.git"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ZIP_PATH="${1:-$SCRIPT_DIR/sustainable-catalyst-research-librarian-ai-v9.7.0-repository.zip}"
REPO_DIR="${2:-$HOME/Downloads/sustainable-catalyst-research-librarian-ai-repo-v970-clean}"
fail(){ printf 'ERROR: %s\n' "$*" >&2; exit 1; }
run_clean(){ env -u VIRTUAL_ENV -u PYTHONHOME -u PYTHONPATH -u PYTHONEXECUTABLE -u __PYVENV_LAUNCHER__ -u CONDA_PREFIX -u CONDA_DEFAULT_ENV -u PYENV_VERSION "$@"; }
for c in git unzip rsync php node shasum awk grep find bash; do command -v "$c" >/dev/null 2>&1 || fail "$c is required"; done
[[ -f "$ZIP_PATH" ]] || fail "Release ZIP not found: $ZIP_PATH"
printf 'Release archive: %s\nSHA-256: %s\n' "$ZIP_PATH" "$(shasum -a 256 "$ZIP_PATH"|awk '{print $1}')"
find_python(){ local c r m p; local -a a=(); [[ -n "${SC_RL_PYTHON:-}" ]]&&a+=("$SC_RL_PYTHON"); if command -v brew >/dev/null 2>&1; then p="$(brew --prefix python@3.12 2>/dev/null||true)"; [[ -n "$p" ]]&&a+=("$p/bin/python3.12"); p="$(brew --prefix python@3.13 2>/dev/null||true)"; [[ -n "$p" ]]&&a+=("$p/bin/python3.13"); fi; a+=(python3.12 python3.13 python3); for c in "${a[@]}"; do r="$(command -v "$c" 2>/dev/null||true)"; [[ -n "$r" ]]||continue; m="$(run_clean "$r" -c 'import sys;print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null||true)"; [[ "$m" == 3.12 || "$m" == 3.13 ]]&&{ printf '%s\n' "$r"; return; }; done; }
PYTHON_BIN="$(find_python||true)"; [[ -n "$PYTHON_BIN" ]]||fail "Python 3.12 or 3.13 is required."
TMP="$(mktemp -d "${TMPDIR:-/tmp}/sc-rl-v970.XXXXXX")"; trap 'rm -rf "$TMP"' EXIT
unzip -q "$ZIP_PATH" -d "$TMP/release"
SRC="$(find "$TMP/release" -maxdepth 2 -type f -name sustainable-catalyst-research-librarian-ai.php -print -quit | xargs -I{} dirname {})"
[[ -n "$SRC" && -f "$SRC/sustainable-catalyst-research-librarian-ai.php" ]]||fail "Expected repository root missing."
for f in \
 backend/app/contracts/unified_research_runtime.py \
 backend/app/services/unified_research_runtime.py \
 backend/tests/test_v900_unified_research_runtime.py \
 backend/app/contracts/research_workflow.py \
 backend/app/services/research_workflow.py \
 backend/tests/test_v910_research_workflow.py \
 backend/migrations/006_research_workflow_automation.sql \
 docs/V910_RESEARCH_AUTOMATION_DURABLE_WORKFLOW_ENGINE.md \
 data/research_librarian_research_workflow_manifest_v9.1.0.json \
 tests/v910-research-automation-durable-workflow-contract-test.php \
 RELEASE_MANIFEST_V910.json \
 deploy/contabo/upgrade_research_librarian_backend_v9_1_0_contabo.sh \
 backend/app/contracts/scholarly_research.py \
 backend/app/services/scholarly_research.py \
 backend/tests/test_v920_scholarly_research.py \
 backend/migrations/007_original_scholarly_research_environment.sql \
 docs/V920_ORIGINAL_RESEARCH_SCHOLARLY_RESEARCH_ENVIRONMENT.md \
 data/research_librarian_scholarly_research_manifest_v9.2.0.json \
 tests/v920-original-scholarly-research-environment-contract-test.php \
 RELEASE_MANIFEST_V920.json \
 deploy/contabo/upgrade_research_librarian_backend_v9_2_0_contabo.sh \
 backend/app/contracts/peer_review.py \
 backend/app/services/peer_review.py \
 backend/tests/test_v930_peer_review.py \
 backend/migrations/008_peer_review_replication_validation.sql \
 docs/V930_PEER_REVIEW_REPLICATION_SCHOLARLY_VALIDATION_ENVIRONMENT.md \
 data/research_librarian_peer_review_manifest_v9.3.0.json \
 tests/v930-peer-review-replication-validation-contract-test.php \
 RELEASE_MANIFEST_V930.json \
 backend/app/contracts/scholarly_publication.py \
 backend/app/services/scholarly_publication.py \
 backend/tests/test_v940_scholarly_publication.py \
 backend/migrations/009_scholarly_publication_dissemination.sql \
 docs/V940_SCHOLARLY_PUBLICATION_CITATION_RESEARCH_DISSEMINATION.md \
 data/research_librarian_scholarly_publication_manifest_v9.4.0.json \
 tests/v940-scholarly-publication-dissemination-contract-test.php \
 RELEASE_MANIFEST_V940.json \
 deploy/contabo/upgrade_research_librarian_backend_v9_4_0_contabo.sh \
 backend/app/contracts/research_knowledge_graph.py \
 backend/app/services/research_knowledge_graph.py \
 backend/tests/test_v950_research_knowledge_graph.py \
 backend/migrations/010_research_knowledge_graph_publication_intelligence.sql \
 docs/V950_RESEARCH_KNOWLEDGE_GRAPH_PUBLICATION_INTELLIGENCE.md \
 data/research_librarian_research_knowledge_graph_manifest_v9.5.0.json \
 tests/v950-research-knowledge-graph-publication-intelligence-contract-test.php \
 RELEASE_MANIFEST_V950.json \
 deploy/contabo/upgrade_research_librarian_backend_v9_5_0_contabo.sh \
 backend/app/contracts/ai_research_context.py \
 backend/app/services/ai_research_context.py \
 backend/tests/test_v960_ai_research_context.py \
 backend/migrations/011_ai_aware_retrieval_context_engineering.sql \
 docs/V960_AI_AWARE_RETRIEVAL_RESEARCH_CONTEXT_ENGINEERING.md \
 data/research_librarian_ai_research_context_manifest_v9.6.0.json \
 tests/v960-ai-aware-retrieval-research-context-contract-test.php \
 RELEASE_MANIFEST_V960.json \
 deploy/contabo/upgrade_research_librarian_backend_v9_6_0_contabo.sh \
 backend/app/contracts/rag_evaluation.py \
 backend/app/services/rag_evaluation.py \
 backend/tests/test_v970_rag_evaluation.py \
 backend/migrations/012_rag_evaluation_evidence_grounding.sql \
 docs/V970_RAG_EVALUATION_EVIDENCE_GROUNDING_FRAMEWORK.md \
 data/research_librarian_rag_evaluation_manifest_v9.7.0.json \
 tests/v970-rag-evaluation-evidence-grounding-contract-test.php \
 RELEASE_MANIFEST_V970.json \
 deploy/contabo/upgrade_research_librarian_backend_v9_7_0_contabo.sh; do
  [[ -f "$SRC/$f" ]]||fail "required file missing: $f"
done
grep -q 'Version: 9.7.0' "$SRC/sustainable-catalyst-research-librarian-ai.php"||fail "Plugin version mismatch."
grep -q '__version__ = "9.7.0"' "$SRC/backend/app/__init__.py"||fail "Backend version mismatch."
grep -q 'UNIFIED_RESEARCH_RUNTIME_SCHEMA' "$SRC/backend/app/contracts/unified_research_runtime.py"||fail "v9.0 unified runtime contract missing."
grep -q 'def build_runtime_plan' "$SRC/backend/app/services/unified_research_runtime.py"||fail "v9.0 runtime planner missing."
grep -q 'def execute_safe_runtime' "$SRC/backend/app/services/unified_research_runtime.py"||fail "v9.0 runtime executor missing."
grep -q '/unified-research/execute' "$SRC/backend/app/api/core.py"||fail "v9.0 unified runtime API missing."
grep -q '"unified-research-runtime"' "$SRC/backend/app/async_jobs.py"||fail "v9.0 durable runtime job missing."
grep -q 'RESEARCH_WORKFLOW_SCHEMA' "$SRC/backend/app/contracts/research_workflow.py"||fail "v9.1 workflow contract missing."
grep -q 'class ResearchWorkflowStore' "$SRC/backend/app/services/research_workflow.py"||fail "v9.1 workflow store missing."
grep -q '/research-workflows/{workflow_id}/advance' "$SRC/backend/app/api/core.py"||fail "v9.1 workflow API missing."
grep -q '"research-workflow-advance"' "$SRC/backend/app/async_jobs.py"||fail "v9.1 workflow durable job missing."
grep -q 'SCHOLARLY_RESEARCH_SCHEMA' "$SRC/backend/app/contracts/scholarly_research.py"||fail "v9.2 scholarly research contract missing."
grep -q 'class ScholarlyResearchStore' "$SRC/backend/app/services/scholarly_research.py"||fail "v9.2 scholarly study store missing."
grep -q '/scholarly-research/studies/{study_id}/packages/freeze' "$SRC/backend/app/api/core.py"||fail "v9.2 scholarly package API missing."
grep -q '"scholarly-research-package"' "$SRC/backend/app/async_jobs.py"||fail "v9.2 scholarly package job missing."

grep -q 'PEER_REVIEW_SCHEMA' "$SRC/backend/app/contracts/peer_review.py"||fail "v9.3 peer review contract missing."
grep -q 'class PeerReviewStore' "$SRC/backend/app/services/peer_review.py"||fail "v9.3 peer review store missing."
grep -q '/scholarly-validation/studies/{study_id}/packages/freeze' "$SRC/backend/app/api/core.py"||fail "v9.3 validation package API missing."
grep -q '"peer-review-validation-package"' "$SRC/backend/app/async_jobs.py"||fail "v9.3 validation package job missing."

grep -q 'SCHOLARLY_PUBLICATION_SCHEMA' "$SRC/backend/app/contracts/scholarly_publication.py"||fail "v9.4 publication contract missing."
grep -q 'class ScholarlyPublicationStore' "$SRC/backend/app/services/scholarly_publication.py"||fail "v9.4 publication store missing."
grep -q '/scholarly-publication/publications/{publication_id}/knowledge-library-handoffs' "$SRC/backend/app/api/core.py"||fail "v9.4 Knowledge Library handoff API missing."
grep -q '"scholarly-publication-package"' "$SRC/backend/app/async_jobs.py"||fail "v9.4 publication package job missing."

grep -q 'RESEARCH_KNOWLEDGE_GRAPH_SCHEMA' "$SRC/backend/app/contracts/research_knowledge_graph.py"||fail "v9.5 graph contract missing."
grep -q 'class ResearchKnowledgeGraphStore' "$SRC/backend/app/services/research_knowledge_graph.py"||fail "v9.5 graph store missing."
grep -q '/research-knowledge-graph/publications/{publication_id}/intelligence' "$SRC/backend/app/api/core.py"||fail "v9.5 publication intelligence API missing."
grep -q '"research-knowledge-graph-snapshot"' "$SRC/backend/app/async_jobs.py"||fail "v9.5 graph snapshot job missing."
grep -q 'AI_RESEARCH_CONTEXT_SCHEMA' "$SRC/backend/app/contracts/ai_research_context.py"||fail "v9.6 AI research context contract missing."
grep -q 'class AIResearchContextStore' "$SRC/backend/app/services/ai_research_context.py"||fail "v9.6 AI research context store missing."
grep -q '/ai-research-context/contexts/{context_id}/lineage' "$SRC/backend/app/api/core.py"||fail "v9.6 AI context lineage API missing."
grep -q '"ai-research-context-snapshot"' "$SRC/backend/app/async_jobs.py"||fail "v9.6 AI context snapshot job missing."
grep -q 'RAG_EVALUATION_SCHEMA' "$SRC/backend/app/contracts/rag_evaluation.py"||fail "v9.7 RAG evaluation contract missing."
grep -q 'class RAGEvaluationStore' "$SRC/backend/app/services/rag_evaluation.py"||fail "v9.7 RAG evaluation store missing."
grep -q '/rag-evaluation/evaluations/{evaluation_id}/summary' "$SRC/backend/app/api/core.py"||fail "v9.7 RAG evaluation summary API missing."
grep -q '"rag-evaluation-snapshot"' "$SRC/backend/app/async_jobs.py"||fail "v9.7 RAG evaluation snapshot job missing."

rm -rf "$REPO_DIR"
git clone "$REPO_URL" "$REPO_DIR"
cd "$REPO_DIR"
git checkout main
git pull --ff-only origin main
rsync -a --delete --exclude='.git/' "$SRC/" "$REPO_DIR/"

echo "=== VALIDATING Research Librarian v9.7.0 ==="
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
while IFS= read -r -d '' f; do bash -n "$f"; done < <(find . -type f -name '*.sh' -print0)
echo "Shell syntax passed."
VENV="$TMP/venv"
run_clean "$PYTHON_BIN" -m venv "$VENV"
"$VENV/bin/python" -m pip install -q --upgrade pip
"$VENV/bin/python" -m pip install -q -r backend/requirements.txt
(cd backend && "$VENV/bin/python" -m pytest -q)
(cd backend && "$VENV/bin/python" -m compileall -q app)
if grep -RIE --exclude-dir=.git --exclude='*.md' --exclude='*.txt' '(sk-[A-Za-z0-9_-]{20,}|AIza[0-9A-Za-z_-]{25,}|BEGIN (RSA |OPENSSH |EC )?PRIVATE KEY)' . >/dev/null; then fail "Secret-pattern scan found a possible credential."; fi
echo "Secret-pattern scan passed."

git add -A
if git diff --cached --quiet; then fail "No v9.7.0 changes detected after applying release."; fi
git commit -m "Build Research Librarian v9.7.0 — RAG evaluation evidence-grounding framework"
git push origin main
if git rev-parse "$TAG" >/dev/null 2>&1; then fail "Tag $TAG already exists locally."; fi
git tag -a "$TAG" -m "Research Librarian v9.7.0 — RAG Evaluation & Evidence-Grounding Framework"
git push origin "$TAG"
echo "Research Librarian v9.7.0 validated and pushed successfully."
echo "Deploy the backend package to Contabo before installing the WordPress v9.7.0 package."
