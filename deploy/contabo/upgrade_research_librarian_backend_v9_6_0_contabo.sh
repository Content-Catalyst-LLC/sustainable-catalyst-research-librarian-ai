#!/usr/bin/env bash
set -Eeuo pipefail
VERSION="9.6.0"
ROOT="/opt/sustainable-catalyst/research-librarian-ai"
LIVE_BACKEND="$ROOT/backend"
COMPOSE="$ROOT/compose.yml"
ENV_FILE="$ROOT/.env.contabo"
CORE_ENV="/opt/sustainable-catalyst/core/.env.production"
CORE_CONTAINER="sc-core"
SERVICE="research-librarian"
CONTAINER="sc-research-librarian"
BACKUP_ROOT="/opt/sustainable-catalyst/backups/research-librarian-ai"
ARCHIVE="${1:-/tmp/sustainable-catalyst-research-librarian-backend-v9.6.0.zip}"
TMP="$(mktemp -d /tmp/sc-rl-v960.XXXXXX)"
trap 'rm -rf "$TMP"' EXIT
fail(){ echo "ERROR: $*" >&2; exit 1; }
for c in docker unzip rsync python3 curl tar grep; do command -v "$c" >/dev/null 2>&1 || fail "$c is required"; done
[[ -f "$ARCHIVE" ]] || fail "backend package not found: $ARCHIVE"
[[ -d "$ROOT" && -d "$LIVE_BACKEND" ]] || fail "runtime root/backend missing: $ROOT"
[[ -f "$COMPOSE" ]] || fail "compose file missing: $COMPOSE"
[[ -f "$ENV_FILE" ]] || fail "Research Librarian environment file missing: $ENV_FILE"
[[ -f "$CORE_ENV" ]] || echo "INFO: Platform Core env file not present/readable; using existing Librarian Core write key if configured."
docker inspect "$CORE_CONTAINER" >/dev/null 2>&1 || fail "Platform Core container is not present: $CORE_CONTAINER"
unzip -tq "$ARCHIVE" >/dev/null || fail "invalid backend ZIP"
unzip -q "$ARCHIVE" -d "$TMP/package"
INIT="$(find "$TMP/package" -type f -path '*/backend/app/__init__.py' | head -1)"
[[ -n "$INIT" ]] || fail "backend/app/__init__.py missing from package"
SRC_BACKEND="$(dirname "$(dirname "$INIT")")"
grep -q '__version__ = "9.6.0"' "$INIT" || fail "backend package version mismatch"
for f in \
 app/clients/platform_core.py app/api/core.py app/async_jobs.py app/services/document_jobs.py \
 app/contracts/argument_synthesis.py app/services/argument_synthesis.py tests/test_v8100_argument_synthesis.py \
 app/contracts/statistical_research.py app/services/statistical_research.py tests/test_v8110_statistical_research.py \
 app/contracts/visual_research.py app/services/visual_research.py tests/test_v8120_visual_research.py \
 app/contracts/unified_research_runtime.py app/services/unified_research_runtime.py tests/test_v900_unified_research_runtime.py \
 app/contracts/research_workflow.py app/services/research_workflow.py tests/test_v910_research_workflow.py migrations/006_research_workflow_automation.sql \
 app/contracts/scholarly_research.py app/services/scholarly_research.py tests/test_v920_scholarly_research.py migrations/007_original_scholarly_research_environment.sql \
 app/contracts/peer_review.py app/services/peer_review.py tests/test_v930_peer_review.py migrations/008_peer_review_replication_validation.sql \
 app/contracts/scholarly_publication.py app/services/scholarly_publication.py tests/test_v940_scholarly_publication.py migrations/009_scholarly_publication_dissemination.sql \
 app/contracts/research_knowledge_graph.py app/services/research_knowledge_graph.py tests/test_v950_research_knowledge_graph.py migrations/010_research_knowledge_graph_publication_intelligence.sql \
 app/contracts/ai_research_context.py app/services/ai_research_context.py tests/test_v960_ai_research_context.py migrations/011_ai_aware_retrieval_context_engineering.sql; do
  [[ -f "$SRC_BACKEND/$f" ]] || fail "required backend file missing: $f"
done
grep -q '"unified-research-runtime"' "$SRC_BACKEND/app/async_jobs.py" || fail "v9.0 unified runtime job type missing"
grep -q '/unified-research/execute' "$SRC_BACKEND/app/api/core.py" || fail "v9.0 unified runtime endpoint missing"
grep -q '"research-workflow-advance"' "$SRC_BACKEND/app/async_jobs.py" || fail "v9.1 workflow automation job type missing"
grep -q '/research-workflows/{workflow_id}/advance' "$SRC_BACKEND/app/api/core.py" || fail "v9.1 workflow endpoint missing"
grep -q '"scholarly-research-package"' "$SRC_BACKEND/app/async_jobs.py" || fail "v9.2 scholarly package job type missing"
grep -q '/scholarly-research/studies/{study_id}/packages/freeze' "$SRC_BACKEND/app/api/core.py" || fail "v9.2 scholarly research endpoint missing"
grep -q '"peer-review-validation-package"' "$SRC_BACKEND/app/async_jobs.py" || fail "v9.3 peer review package job type missing"
grep -q '/scholarly-validation/studies/{study_id}/packages/freeze' "$SRC_BACKEND/app/api/core.py" || fail "v9.3 scholarly validation endpoint missing"
grep -q '"scholarly-publication-package"' "$SRC_BACKEND/app/async_jobs.py" || fail "v9.4 scholarly publication package job type missing"
grep -q '/scholarly-publication/publications/{publication_id}/knowledge-library-handoffs' "$SRC_BACKEND/app/api/core.py" || fail "v9.4 scholarly publication handoff endpoint missing"

echo "=== BACKUP RESEARCH LIBRARIAN ==="
mkdir -p "$BACKUP_ROOT"
stamp="$(date +%Y%m%d-%H%M%S)"
tar -C "$ROOT" -czf "$BACKUP_ROOT/backend-before-v${VERSION}-${stamp}.tgz" backend
cp -a "$COMPOSE" "$BACKUP_ROOT/compose-before-v${VERSION}-${stamp}.yml"
cp -a "$ENV_FILE" "$BACKUP_ROOT/env-before-v${VERSION}-${stamp}"

echo "=== INSTALL v${VERSION} BACKEND ==="
rsync -a --exclude='data/' --exclude='__pycache__/' --exclude='.pytest_cache/' --exclude='*.pyc' --exclude='.env' --exclude='.env.*' "$SRC_BACKEND/" "$LIVE_BACKEND/"
python3 - "$COMPOSE" <<'PY'
from pathlib import Path
import re,sys
p=Path(sys.argv[1]); s=p.read_text()
s=re.sub(r'(?m)^(\s*image:\s*sustainable-catalyst-research-librarian:).*$', r'\g<1>9.6.0', s)
s=re.sub(r'(?m)^(\s*SC_RL_RELEASE_VERSION:\s*)["\']?[^"\'\n]+["\']?\s*$', r'\g<1>"9.6.0"', s)
p.write_text(s)
PY
python3 - "$ENV_FILE" "$CORE_ENV" <<'PY'
from pathlib import Path
import sys
def parse(path):
    out={}
    try:
        content=Path(path).read_text()
    except (FileNotFoundError, PermissionError, OSError):
        return out
    for raw in content.splitlines():
        line=raw.strip()
        if not line or line.startswith('#') or '=' not in line: continue
        k,v=line.split('=',1); v=v.strip()
        if len(v)>=2 and v[0]==v[-1] and v[0] in {'"',"'"}: v=v[1:-1]
        out[k.strip()]=v
    return out
def set_values(path,updates):
    p=Path(path); lines=p.read_text().splitlines(); done=set(); result=[]
    for raw in lines:
        if '=' in raw and not raw.lstrip().startswith('#'):
            k=raw.split('=',1)[0].strip()
            if k in updates: result.append(f"{k}={updates[k]}"); done.add(k); continue
        result.append(raw)
    for k,v in updates.items():
        if k not in done: result.append(f"{k}={v}")
    p.write_text('\n'.join(result).rstrip()+'\n')
rl=parse(sys.argv[1]); core=parse(sys.argv[2])
core_key=core.get('SC_CORE_WRITE_API_KEY','').strip(); rl_key=rl.get('SC_RL_CORE_WRITE_API_KEY','').strip()
if not core_key and not rl_key: raise SystemExit('SC_CORE_WRITE_API_KEY is missing and no existing Librarian Core write key is configured.')
updates={'SC_RL_RELEASE_VERSION':'9.6.0','SC_RL_CORE_ENABLED':'true','SC_RL_CORE_BASE_URL':'http://sc-core:8090','SC_RL_CORE_MINIMUM_VERSION':'3.3.0','SC_RL_CORE_SUPPORTED_MAJOR':'3','SC_RL_CORE_FAIL_CLOSED_WRITES':'true','SC_RL_ASYNC_JOBS_ENABLED':'true'}
if core_key: updates['SC_RL_CORE_WRITE_API_KEY']=core_key
set_values(sys.argv[1],updates)
print('PASS: Research Librarian Core integration environment aligned (secret not displayed).')
PY

cd "$ROOT"
docker compose -f "$COMPOSE" config --quiet
echo "=== BUILD IMAGE ==="
if grep -qE '^[[:space:]]*build:' "$COMPOSE"; then docker compose -f "$COMPOSE" build "$SERVICE"; else docker build -t "sustainable-catalyst-research-librarian:${VERSION}" "$LIVE_BACKEND"; fi
echo "=== RECREATE SERVICE ==="
docker compose -f "$COMPOSE" up -d --force-recreate "$SERVICE"
for i in $(seq 1 90); do
  if curl -fsS http://127.0.0.1:8093/health >"$TMP/health.json" 2>/dev/null && python3 - "$TMP/health.json" <<'PY' >/dev/null 2>&1
import json,sys
x=json.load(open(sys.argv[1])); assert x.get('version')=='9.6.0' and x.get('ready') is True
PY
  then break; fi
  if [[ "$i" == 90 ]]; then docker logs --tail=240 "$CONTAINER" >&2 || true; cat "$TMP/health.json" >&2 2>/dev/null || true; fail "Research Librarian v9.6.0 did not become ready"; fi
  sleep 2
done
python3 - "$TMP/health.json" <<'PY'
import json,sys
x=json.load(open(sys.argv[1])); assert x.get('version')=='9.6.0' and x.get('ready') is True,x
print('PASS: Research Librarian /health reports 9.6.0 and ready=true')
PY

echo "=== VERIFY PLATFORM CORE + UNIFIED RESEARCH RUNTIME ==="
docker exec -i "$CONTAINER" python - <<'PY'
import asyncio
from app.services.unified_research_runtime import readiness, capabilities
async def main():
    r=await readiness()
    assert r['ready'] is True,r
    assert r['core_compatible'] is True,r
    assert r['core_write_ready'] is True,r
    assert not r['missing_or_failed_core_capabilities'],r
    cap=capabilities()
    assert cap['schema']=='sc-research-librarian-unified-research-intelligence-runtime/1.0'
    assert cap['automatic_core_writes'] is False
    assert cap['automatic_truth_promotion'] is False
    assert cap['specialist_computation_retained'] is True
    print('PASS: Platform Core research/reasoning capabilities support v9.0 unified runtime')
asyncio.run(main())
PY

echo "=== VERIFY v9.0 STAGE GRAPH + ROUTES ==="
docker exec -i "$CONTAINER" python - <<'PY'
from app.contracts.unified_research_runtime import UnifiedResearchRuntimePlanRequest
from app.services.unified_research_runtime import build_runtime_plan
from app.main import app
paths={getattr(r,'path',None) for r in app.routes}
required={'/v1/core/unified-research/capabilities','/v1/core/unified-research/readiness','/v1/core/unified-research/plan','/v1/core/unified-research/execute'}
assert not (required-paths), required-paths
plan=build_runtime_plan(UnifiedResearchRuntimePlanRequest(core_project_id='smoke-core-project',title='Smoke unified run',research_question='What does the evidence show?',source_refs=['source:smoke']))['plan']
assert len(plan['stages'])==12
assert plan['stage_order'][0]=='discovery' and plan['stage_order'][-1]=='reproducibility'
assert len(plan['reproducibility']['plan_hash'])==64
assert plan['governance']['core_write_performed_by_unified_execute'] is False
print('PASS: v9.0 deterministic 12-stage unified research graph active')
PY

echo "=== VERIFY v9.1 RESEARCH AUTOMATION & DURABLE WORKFLOW ENGINE ==="
docker exec -i "$CONTAINER" python - <<'PY'
from pathlib import Path
from app.services.research_workflow import capabilities, ResearchWorkflowStore
from app.async_jobs import JOB_TYPES
from app.main import app
cap=capabilities()
assert cap['schema']=='sc-research-librarian-research-workflow/1.0'
assert cap['durable'] is True and cap['resumable'] is True
assert cap['automatic_core_writes'] is False
assert 'research-workflow-advance' in JOB_TYPES
paths={getattr(r,'path',None) for r in app.routes}
required={'/v1/core/research-workflows/capabilities','/v1/core/research-workflows/{workflow_id}/advance','/v1/core/research-workflows/{workflow_id}/approvals'}
assert not(required-paths), required-paths
store=ResearchWorkflowStore()
if __import__('os').environ.get('SC_RL_DATABASE_BACKEND','').lower() in {'postgres','postgresql','neon'}:
    assert store.backend=='postgres'
print('PASS: v9.1 durable research workflow engine active on',store.backend)
PY

echo "=== VERIFY v9.2 ORIGINAL RESEARCH & SCHOLARLY RESEARCH ENVIRONMENT ==="
docker exec -i "$CONTAINER" python - <<'PY'
import os
from app.services.scholarly_research import capabilities, ScholarlyResearchStore
from app.async_jobs import JOB_TYPES
from app.main import app
cap=capabilities()
assert cap['schema']=='sc-research-librarian-original-scholarly-research/1.0'
assert cap['durable_study_registry'] is True
assert cap['immutable_revision_history'] is True
assert cap['protocol_freeze'] is True
assert cap['publication_readiness_gate'] is True
assert cap['automatic_authorship'] is False
assert cap['automatic_truth_promotion'] is False
assert 'scholarly-research-package' in JOB_TYPES
assert 'peer-review-validation-package' in JOB_TYPES
assert 'scholarly-publication-package' in JOB_TYPES
paths={getattr(r,'path',None) for r in app.routes}
required={'/v1/core/scholarly-research/capabilities','/v1/core/scholarly-research/studies','/v1/core/scholarly-research/studies/{study_id}/protocol/freeze','/v1/core/scholarly-research/studies/{study_id}/publication-readiness','/v1/core/scholarly-research/studies/{study_id}/packages/freeze'}
assert not(required-paths), required-paths
store=ScholarlyResearchStore()
if os.environ.get('SC_RL_DATABASE_BACKEND','').lower() in {'postgres','postgresql','neon'}:
    assert store.backend=='postgres'
print('PASS: v9.2 scholarly research environment active on',store.backend)
PY

echo "=== VERIFY v9.3 PEER REVIEW, REPLICATION & SCHOLARLY VALIDATION ==="
docker exec -i "$CONTAINER" python - <<'PY'
import os
from app.services.peer_review import capabilities, PeerReviewStore
from app.async_jobs import JOB_TYPES
from app.main import app
cap=capabilities()
assert cap['schema']=='sc-research-librarian-peer-review-replication-validation/1.0'
assert cap['durable_peer_review_registry'] is True
assert cap['structured_review_rounds'] is True
assert cap['replication_attempt_registry'] is True
assert cap['explicit_editorial_decisions'] is True
assert cap['automatic_replication_judgment'] is False
assert cap['machine_peer_review_certification'] is False
assert cap['automatic_truth_promotion'] is False
assert 'peer-review-validation-package' in JOB_TYPES
assert 'scholarly-publication-package' in JOB_TYPES
paths={getattr(r,'path',None) for r in app.routes}
required={'/v1/core/scholarly-validation/capabilities','/v1/core/scholarly-validation/studies/{study_id}/rounds','/v1/core/scholarly-validation/studies/{study_id}/replications','/v1/core/scholarly-validation/studies/{study_id}/editorial-decisions','/v1/core/scholarly-validation/studies/{study_id}/packages/freeze'}
assert not(required-paths), required-paths
store=PeerReviewStore()
if os.environ.get('SC_RL_DATABASE_BACKEND','').lower() in {'postgres','postgresql','neon'}: assert store.backend=='postgres'
print('PASS: v9.3 peer-review/replication validation environment active on',store.backend)
PY



echo "=== VERIFY v9.4 SCHOLARLY PUBLICATION, CITATION & RESEARCH DISSEMINATION ==="
docker exec -i "$CONTAINER" python - <<'PY'
import os
from app.services.scholarly_publication import capabilities, ScholarlyPublicationStore
from app.async_jobs import JOB_TYPES
from app.main import app
cap=capabilities()
assert cap['schema']=='sc-research-librarian-scholarly-publication/1.0'
assert cap['durable_publication_registry'] is True
assert cap['versioned_publication_records'] is True
assert cap['citation_exports'] is True
assert cap['knowledge_library_handoff'] is True
assert cap['doi_minting'] is False
assert cap['automatic_authorship'] is False
assert cap['automatic_editorial_acceptance'] is False
assert cap['automatic_publication'] is False
assert cap['automatic_core_writes'] is False
assert 'scholarly-publication-package' in JOB_TYPES
paths={getattr(r,'path',None) for r in app.routes}
required={'/v1/core/scholarly-publication/capabilities','/v1/core/scholarly-publication/studies/{study_id}/publications','/v1/core/scholarly-publication/publications/{publication_id}/citation-exports','/v1/core/scholarly-publication/publications/{publication_id}/knowledge-library-handoffs','/v1/core/scholarly-publication/publications/{publication_id}/packages/freeze'}
assert not(required-paths), required-paths
store=ScholarlyPublicationStore()
if os.environ.get('SC_RL_DATABASE_BACKEND','').lower() in {'postgres','postgresql','neon'}: assert store.backend=='postgres'
print('PASS: v9.4 scholarly publication/dissemination environment active on',store.backend)
PY

echo "=== VERIFY v9.5 RESEARCH KNOWLEDGE GRAPH & PUBLICATION INTELLIGENCE ==="
docker exec -i "$CONTAINER" python - <<'PY'
import os
from app.services.research_knowledge_graph import capabilities, ResearchKnowledgeGraphStore
from app.async_jobs import JOB_TYPES
from app.main import app
cap=capabilities()
assert cap['schema']=='sc-research-librarian-research-knowledge-graph/1.0'
assert cap['durable_graph_registry'] is True
assert cap['reviewable_edge_proposals'] is True
assert cap['publication_intelligence'] is True
assert cap['automatic_semantic_inference'] is False
assert cap['automatic_edge_acceptance'] is False
assert cap['automatic_impact_ranking'] is False
assert cap['automatic_truth_scoring'] is False
assert cap['automatic_core_writes'] is False
assert 'research-knowledge-graph-snapshot' in JOB_TYPES
paths={getattr(r,'path',None) for r in app.routes}
required={'/v1/core/research-knowledge-graph/capabilities','/v1/core/research-knowledge-graph/nodes','/v1/core/research-knowledge-graph/edges','/v1/core/research-knowledge-graph/edge-proposals','/v1/core/research-knowledge-graph/publications/{publication_id}/materialize','/v1/core/research-knowledge-graph/publications/{publication_id}/intelligence','/v1/core/research-knowledge-graph/snapshots/freeze'}
assert not(required-paths), required-paths
store=ResearchKnowledgeGraphStore()
if os.environ.get('SC_RL_DATABASE_BACKEND','').lower() in {'postgres','postgresql','neon'}: assert store.backend=='postgres'
print('PASS: v9.5 research knowledge graph/publication intelligence active on',store.backend)
PY

echo "=== VERIFY v9.6 AI-AWARE RETRIEVAL & RESEARCH CONTEXT ENGINEERING ==="
docker exec -i "$CONTAINER" python - <<'PY'
import os
from app.services.ai_research_context import capabilities, AIResearchContextStore
from app.async_jobs import JOB_TYPES
from app.main import app
cap=capabilities()
assert cap['schema']=='sc-research-librarian-ai-research-context/1.0'
assert cap['core_ai_object_refs_are_external'] is True
assert cap['automatic_model_registration'] is False
assert cap['model_training_execution'] is False
assert cap['automatic_grounding_certification'] is False
assert 'ai-research-context-snapshot' in JOB_TYPES
paths={getattr(r,'path',None) for r in app.routes}
required={'/v1/core/ai-research-context/capabilities','/v1/core/ai-research-context/contexts','/v1/core/ai-research-context/retrieval-runs','/v1/core/ai-research-context/contexts/{context_id}/lineage','/v1/core/ai-research-context/snapshots/freeze'}
assert not(required-paths), required-paths
store=AIResearchContextStore()
if os.environ.get('SC_RL_DATABASE_BACKEND','').lower() in {'postgres','postgresql','neon'}: assert store.backend=='postgres'
print('PASS: v9.6 AI-aware retrieval research context environment active on',store.backend)
PY

echo "=== VERIFY DURABLE ASYNC JOB RUNTIME ==="
docker exec -i "$CONTAINER" python - <<'PY'
import json,os,urllib.request
from app.async_jobs import JOB_TYPES
assert 'unified-research-runtime' in JOB_TYPES
assert 'scholarly-research-package' in JOB_TYPES
assert 'peer-review-validation-package' in JOB_TYPES
assert 'scholarly-publication-package' in JOB_TYPES
assert 'research-knowledge-graph-snapshot' in JOB_TYPES
assert 'ai-research-context-snapshot' in JOB_TYPES
key=os.environ['SC_RL_BACKEND_API_KEY']
req=urllib.request.Request('http://127.0.0.1:8093/v1/jobs/runtime',headers={'X-SC-RL-Key':key})
with urllib.request.urlopen(req,timeout=35) as r: data=json.load(r)
assert data['schema']=='sc-research-librarian-async-runtime/1.0' and data['durable'] is True,data
if os.environ.get('SC_RL_DATABASE_BACKEND','').lower() in {'postgres','postgresql','neon'}:
    assert data['storage_backend']=='postgres' and data['claim_strategy']=='for-update-skip-locked',data
print('PASS: durable unified/scholarly research job support active on',data['storage_backend'])
PY

echo "PASS: Research Librarian AI v9.6.0 AI-Aware Retrieval & Research Context Engineering backend deployed and verified."
