#!/usr/bin/env bash
set -Eeuo pipefail

VERSION="8.10.0"
ROOT="${SC_TARGET_ROOT:-/opt/sustainable-catalyst/research-librarian-ai}"
LIVE_BACKEND="$ROOT/backend"
COMPOSE="${SC_TARGET_COMPOSE:-$ROOT/compose.yml}"
SERVICE="${SC_TARGET_SERVICE:-research-librarian}"
CONTAINER="${SC_TARGET_CONTAINER:-sc-research-librarian}"
CORE_ROOT="${SC_CORE_ROOT:-/opt/sustainable-catalyst/core}"
CORE_CONTAINER="${SC_CORE_CONTAINER:-sc-core}"
CORE_ENV="${SC_CORE_ENV:-$CORE_ROOT/.env.production}"
ENV_FILE="${SC_RL_ENV_FILE:-$ROOT/.env.contabo}"
ARCHIVE="${1:-/tmp/sustainable-catalyst-research-librarian-backend-v8.10.0.zip}"
BACKUP_ROOT="/opt/sustainable-catalyst/backups/research-librarian-v8100"
TMP="$(mktemp -d /tmp/sc-rl-v8100.XXXXXX)"
trap 'rm -rf "$TMP"' EXIT

fail(){ echo "ERROR: $*" >&2; exit 1; }
for cmd in unzip rsync docker python3 tar grep sed curl; do command -v "$cmd" >/dev/null || fail "$cmd is required"; done
[[ -f "$ARCHIVE" ]] || fail "backend package not found: $ARCHIVE"
[[ -d "$ROOT" && -d "$LIVE_BACKEND" ]] || fail "runtime root/backend missing: $ROOT"
[[ -f "$COMPOSE" ]] || fail "compose file missing: $COMPOSE"
[[ -f "$ENV_FILE" ]] || fail "Research Librarian environment file missing: $ENV_FILE"
[[ -f "$CORE_ENV" ]] || fail "Platform Core environment file missing: $CORE_ENV"
docker inspect "$CORE_CONTAINER" >/dev/null 2>&1 || fail "Platform Core container is not present: $CORE_CONTAINER"
unzip -tq "$ARCHIVE" >/dev/null || fail "invalid backend ZIP"
unzip -q "$ARCHIVE" -d "$TMP/package"
INIT="$(find "$TMP/package" -type f -path '*/backend/app/__init__.py' | head -1)"
[[ -n "$INIT" ]] || fail "backend/app/__init__.py missing from package"
SRC_BACKEND="$(dirname "$(dirname "$INIT")")"
PACKAGE_ROOT="$(dirname "$SRC_BACKEND")"
grep -q '__version__ = "8.10.0"' "$INIT" || fail "backend package version mismatch"
[[ -f "$SRC_BACKEND/app/clients/platform_core.py" ]] || fail "Platform Core client missing"
[[ -f "$SRC_BACKEND/app/api/core.py" ]] || fail "Platform Core API router missing"
[[ -f "$SRC_BACKEND/app/services/platform_core_integration.py" ]] || fail "Platform Core integration service missing"
[[ -f "$SRC_BACKEND/app/async_jobs.py" ]] || fail "v8.3 async job store missing"
[[ -f "$SRC_BACKEND/app/workers/document_worker.py" ]] || fail "v8.3 document worker missing"
[[ -f "$SRC_BACKEND/app/services/document_jobs.py" ]] || fail "v8.3 document-processing service missing"
[[ -f "$SRC_BACKEND/migrations/004_async_document_processing_runtime.sql" ]] || fail "v8.3 async Postgres migration contract missing"
[[ -f "$SRC_BACKEND/app/advanced_retrieval.py" ]] || fail "v8.4 advanced retrieval engine missing"
[[ -f "$SRC_BACKEND/tests/test_v840_advanced_retrieval.py" ]] || fail "v8.4 advanced retrieval tests missing"
[[ -f "$SRC_BACKEND/app/document_intelligence.py" ]] || fail "v8.5 document intelligence engine missing"
[[ -f "$SRC_BACKEND/app/api/documents.py" ]] || fail "v8.5 document intelligence API missing"
[[ -f "$SRC_BACKEND/app/contracts/documents.py" ]] || fail "v8.5 document parse contract missing"
[[ -f "$SRC_BACKEND/tests/test_v850_document_intelligence.py" ]] || fail "v8.5 document intelligence tests missing"
grep -q 'pypdf' "$SRC_BACKEND/requirements.txt" || fail "pypdf dependency missing"
[[ -f "$SRC_BACKEND/app/source_identity.py" ]] || fail "v8.6 source identity engine missing"
[[ -f "$SRC_BACKEND/app/api/sources.py" ]] || fail "v8.6 source identity API missing"
[[ -f "$SRC_BACKEND/app/contracts/sources.py" ]] || fail "v8.6 source identity contracts missing"
[[ -f "$SRC_BACKEND/tests/test_v860_source_identity.py" ]] || fail "v8.6 source identity tests missing"
[[ -f "$SRC_BACKEND/migrations/005_source_identity_citation_graph.sql" ]] || fail "v8.6 source identity migration missing"
[[ -f "$SRC_BACKEND/app/contracts/evidence_bridge.py" ]] || fail "v8.7 Core Evidence Bridge contract missing"
[[ -f "$SRC_BACKEND/app/services/core_evidence_bridge.py" ]] || fail "v8.7 Core Evidence Bridge service missing"
[[ -f "$SRC_BACKEND/tests/test_v870_core_evidence_bridge.py" ]] || fail "v8.7 Core Evidence Bridge tests missing"
[[ -f "$SRC_BACKEND/app/contracts/research_sync.py" ]] || fail "v8.8 Core research sync contract missing"
[[ -f "$SRC_BACKEND/app/services/core_research_sync.py" ]] || fail "v8.8 Core research sync service missing"
[[ -f "$SRC_BACKEND/tests/test_v880_core_research_object_sync.py" ]] || fail "v8.8 Core research sync tests missing"
[[ -f "$SRC_BACKEND/app/contracts/research_intelligence_extraction.py" ]] || fail "v8.9 research intelligence extraction contract missing"
[[ -f "$SRC_BACKEND/app/services/research_intelligence_extraction.py" ]] || fail "v8.9 research intelligence extraction service missing"
[[ -f "$SRC_BACKEND/tests/test_v890_finding_claim_evidence_extraction.py" ]] || fail "v8.9 research intelligence extraction tests missing"
[[ -f "$SRC_BACKEND/app/contracts/argument_synthesis.py" ]] || fail "v8.10 argument synthesis contract missing"
[[ -f "$SRC_BACKEND/app/services/argument_synthesis.py" ]] || fail "v8.10 argument synthesis service missing"
[[ -f "$SRC_BACKEND/tests/test_v8100_argument_synthesis.py" ]] || fail "v8.10 argument synthesis tests missing"

echo "=== BACKUP RESEARCH LIBRARIAN ==="
mkdir -p "$BACKUP_ROOT"
stamp="$(date +%Y%m%d-%H%M%S)"
tar -C "$ROOT" -czf "$BACKUP_ROOT/backend-before-v${VERSION}-${stamp}.tgz" backend
cp -a "$COMPOSE" "$BACKUP_ROOT/compose-before-v${VERSION}-${stamp}.yml"
cp -a "$ENV_FILE" "$BACKUP_ROOT/env-before-v${VERSION}-${stamp}"

echo "=== INSTALL v${VERSION} BACKEND ==="
rsync -a \
  --exclude='data/' --exclude='__pycache__/' --exclude='.pytest_cache/' \
  --exclude='*.pyc' --exclude='.env' --exclude='.env.*' \
  "$SRC_BACKEND/" "$LIVE_BACKEND/"

# Keep the existing service topology, but align the image tag when this compose
# uses the release image pattern.
python3 - "$COMPOSE" <<'PY'
from pathlib import Path
import re, sys
p=Path(sys.argv[1]); s=p.read_text()
s=re.sub(r'(?m)^(\s*image:\s*sustainable-catalyst-research-librarian:).*$', r'\g<1>8.10.0', s)
s=re.sub(r'(?m)^(\s*SC_RL_RELEASE_VERSION:\s*)["\']?[^"\'\n]+["\']?\s*$', r'\g<1>"8.10.0"', s)
p.write_text(s)
PY

# Copy the Core write secret server-side. It is never printed and never ships
# in the release bundle. Existing RL credentials are preserved.
python3 - "$ENV_FILE" "$CORE_ENV" <<'PY'
from pathlib import Path
import sys

def parse(path):
    out={}
    for raw in Path(path).read_text().splitlines():
        line=raw.strip()
        if not line or line.startswith('#') or '=' not in line: continue
        k,v=line.split('=',1); v=v.strip()
        if len(v)>=2 and v[0]==v[-1] and v[0] in {'"', "'"}: v=v[1:-1]
        out[k.strip()]=v
    return out

def set_values(path, updates):
    p=Path(path); lines=p.read_text().splitlines(); done=set(); result=[]
    for raw in lines:
        if '=' in raw and not raw.lstrip().startswith('#'):
            k=raw.split('=',1)[0].strip()
            if k in updates:
                result.append(f"{k}={updates[k]}"); done.add(k); continue
        result.append(raw)
    for k,v in updates.items():
        if k not in done: result.append(f"{k}={v}")
    p.write_text('\n'.join(result).rstrip()+'\n')

rl=parse(sys.argv[1]); core=parse(sys.argv[2])
core_key=core.get('SC_CORE_WRITE_API_KEY','').strip()
rl_key=rl.get('SC_RL_CORE_WRITE_API_KEY','').strip()
if not core_key and not rl_key:
    raise SystemExit('SC_CORE_WRITE_API_KEY is missing from Core and SC_RL_CORE_WRITE_API_KEY is not already configured.')
updates={
    'SC_RL_RELEASE_VERSION':'8.10.0',
    'SC_RL_CORE_ENABLED':'true',
    'SC_RL_CORE_BASE_URL':'http://sc-core:8090',
    'SC_RL_CORE_MINIMUM_VERSION':'3.3.0',
    'SC_RL_CORE_SUPPORTED_MAJOR':'3',
    'SC_RL_CORE_FAIL_CLOSED_WRITES':'true',
    'SC_RL_ASYNC_JOBS_ENABLED':'true',
    'SC_RL_ASYNC_JOB_POLL_SECONDS':'1.0',
    'SC_RL_ASYNC_JOB_LEASE_SECONDS':'120',
    'SC_RL_ASYNC_JOB_RECLAIM_INTERVAL_SECONDS':'60',
    'SC_RL_ASYNC_JOB_RETRY_BASE_SECONDS':'5.0',
    'SC_RL_ASYNC_JOB_RETRY_MAX_SECONDS':'900',
}
if core_key: updates['SC_RL_CORE_WRITE_API_KEY']=core_key
set_values(sys.argv[1], updates)
print('PASS: Research Librarian Core integration environment aligned (secret not displayed).')
PY

cd "$ROOT"
docker compose -f "$COMPOSE" config --quiet

echo "=== BUILD IMAGE ==="
if grep -qE '^[[:space:]]*build:' "$COMPOSE"; then
  docker compose -f "$COMPOSE" build "$SERVICE"
else
  docker build -t "sustainable-catalyst-research-librarian:${VERSION}" "$LIVE_BACKEND"
fi

echo "=== RECREATE SERVICE ==="
docker compose -f "$COMPOSE" up -d --force-recreate "$SERVICE"

for i in $(seq 1 90); do
  if curl -fsS http://127.0.0.1:8093/health >"$TMP/health.json" 2>/dev/null; then
    if python3 - "$TMP/health.json" <<'PY' >/dev/null 2>&1
import json,sys
x=json.load(open(sys.argv[1]))
assert x.get('version')=='8.10.0',x
assert x.get('ready') is True,x
PY
    then break; fi
  fi
  if [[ "$i" == 90 ]]; then docker logs --tail=240 "$CONTAINER" >&2 || true; cat "$TMP/health.json" >&2 2>/dev/null || true; fail "Research Librarian v8.10.0 did not become ready"; fi
  sleep 2
done
python3 - "$TMP/health.json" <<'PY'
import json,sys
x=json.load(open(sys.argv[1])); assert x.get('version')=='8.10.0' and x.get('ready') is True,x
print('PASS: Research Librarian /health reports 8.10.0 and ready=true')
PY

echo "=== VERIFY PLATFORM CORE NETWORK + CONTRACT ==="
docker exec -i "$CONTAINER" python - <<'PY'
import json, os, urllib.request

def get(url, headers=None):
    req=urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=35) as r: return json.load(r)
core=get('http://sc-core:8090/health')
assert core.get('ok') is True, core
version=str(core.get('version') or '')
parts=[int(x) for x in version.split('.')[:3]]
assert parts[0] == 3 and tuple(parts) >= (3,3,0), core
key=os.environ.get('SC_RL_BACKEND_API_KEY','')
assert key, 'SC_RL_BACKEND_API_KEY is missing in container'
rl=get('http://127.0.0.1:8093/v1/core/readiness', {'X-SC-RL-Key':key})
assert rl.get('compatible') is True, rl
assert rl.get('write_ready') is True, rl
assert rl.get('core_health',{}).get('version') == version, rl
failed=rl.get('failed_capabilities') or []
assert not failed, f'Core capability probes failed: {failed}'
print('PASS: Platform Core',version,'is compatible and write-ready')
print('PASS: required governed research/reasoning capabilities are reachable')
PY

echo "=== VERIFY v8.9 RESEARCH OBJECT SYNCHRONIZATION + v8.7 EVIDENCE BRIDGE + SOURCE/CORE/JOB/RETRIEVAL ROUTES ==="
docker exec -i "$CONTAINER" python - <<'PY'
from app.main import app
from app.store import SCHEMA_VERSION
paths={getattr(r,'path',None) for r in app.routes}
required={
'/v1/core/architecture','/v1/core/readiness','/v1/core/bindings',
'/v1/core/research-objects/promote','/v1/core/research-projects/synchronize',
'/v1/core/exchange/packages','/v1/core/evidence/capabilities','/v1/core/evidence/source-snapshots/promote','/v1/core/evidence/passages/promote','/v1/jobs/runtime','/v1/jobs','/v1/jobs/documents',
'/v1/retrieval/plan','/v1/retrieve','/v1/retrieve/explain',
'/v1/documents/capabilities','/v1/documents/parse','/v1/documents/parse/async',
'/v1/sources/capabilities','/v1/sources/resolve','/v1/sources/{source_id}','/v1/sources/{source_id}/graph','/v1/sources/{source_id}/citations'}
missing=required-paths
assert not missing,missing
assert SCHEMA_VERSION==19,SCHEMA_VERSION
print('PASS: v8.7 evidence bridge + source identity + Core + async job + retrieval routes registered')
print('PASS: ancillary SQLite schema 19 active')
PY

echo "=== VERIFY ADVANCED RETRIEVAL CONTRACT ==="
docker exec -i "$CONTAINER" python - <<'PY'
from app.advanced_retrieval import ADVANCED_RETRIEVAL_SCHEMA, build_query_plan
from app.calibration import sanitize_retrieval_config
plan=build_query_plan('Compare solar storage versus wind storage',4)
assert plan['variant_count'] >= 3, plan
assert plan['generative_expansion'] is False, plan
config=sanitize_retrieval_config({})
assert config['profile']=='advanced-v8.4.0', config
assert config['advanced']['enabled'] is True, config
assert ADVANCED_RETRIEVAL_SCHEMA=='sc-research-librarian-advanced-retrieval/1.0'
print('PASS: v8.4 deterministic query planning + advanced retrieval profile active')
PY

echo "=== VERIFY v8.5 DOCUMENT INTELLIGENCE ==="
docker exec -i "$CONTAINER" python - <<'PY'
from app.document_intelligence import DOCUMENT_INTELLIGENCE_SCHEMA, parse_document
r=parse_document(content='# Smoke Study\n\n## Abstract\nEvidence with DOI 10.1234/smoke.1.\n\n## References\n1. Example, A. (2026). Smoke reference.',media_type='text/markdown',filename='smoke.md')
assert r['schema']==DOCUMENT_INTELLIGENCE_SCHEMA,r
assert r['title']=='Smoke Study',r
assert r['section_count']>=2,r
assert '10.1234/smoke.1' in [x.lower() for x in r['identifiers']['doi']],r
assert r['governance']['llm_extraction'] is False,r
print('PASS: v8.5 deterministic scholarly document parsing active')
PY

echo "=== VERIFY v8.6 SOURCE IDENTITY + CITATION GRAPH ==="
docker exec -i "$CONTAINER" python - <<'PY'
import os
from app.source_identity import SOURCE_IDENTITY_SCHEMA, CITATION_GRAPH_SCHEMA, get_source_graph_store, identity_candidate, normalize_identifier
assert SOURCE_IDENTITY_SCHEMA=='sc-research-librarian-source-identity/1.0'
assert CITATION_GRAPH_SCHEMA=='sc-research-librarian-citation-graph/1.0'
assert normalize_identifier('doi','https://doi.org/10.1234/ABC')=='10.1234/abc'
candidate=identity_candidate({'parsed_document':{'title':'Smoke','identifiers':{'doi':['10.1234/main','10.1234/cited']},'references':[{'identifiers':{'doi':['10.1234/cited']}}]}})
assert candidate['identifiers']['doi']==['10.1234/main'],candidate
runtime=get_source_graph_store().runtime()
assert runtime['durable'] is True and runtime['citation_graph'] is True,runtime
if os.environ.get('SC_RL_DATABASE_BACKEND','').lower() in {'postgres','postgresql','neon'}:
    assert runtime['storage_backend']=='postgres',runtime
print('PASS: v8.6 canonical source identity and citation graph runtime active on',runtime['storage_backend'])
PY

echo "=== VERIFY v8.7 CORE EVIDENCE BRIDGE ==="
docker exec -i "$CONTAINER" python - <<'PY'
from app.contracts.evidence_bridge import CORE_EVIDENCE_BRIDGE_SCHEMA, CorePassageEvidencePromotionRequest
from app.services.core_evidence_bridge import evidence_bridge_capabilities
cap=evidence_bridge_capabilities()
assert CORE_EVIDENCE_BRIDGE_SCHEMA=='sc-research-librarian-core-evidence-bridge/1.0'
assert cap['source_snapshot_promotion'] is True,cap
assert cap['passage_evidence_promotion'] is True,cap
assert cap['automatic_claim_creation'] is False,cap
assert cap['automatic_stance_inference'] is False,cap
assert cap['automatic_confidence_inference'] is False,cap
assert cap['default_stance']=='neutral',cap
assert cap['default_review_status']=='unreviewed',cap
sample=CorePassageEvidencePromotionRequest(local_evidence_id='smoke-passage',canonical_source_id='source:smoke',source_snapshot_local_id='snapshot:smoke',statement='Smoke passage')
assert sample.stance=='neutral' and sample.review_status=='unreviewed' and sample.confidence is None
print('PASS: v8.7 Core Evidence Bridge governance defaults active')
PY

echo "=== VERIFY v8.9 CORE RESEARCH OBJECT SYNCHRONIZATION ==="
docker exec -i "$CONTAINER" python - <<'PY'
from app.contracts.research_sync import CORE_RESEARCH_SYNC_SCHEMA, CORE_PROJECT_STATE_CONTRACT
from app.services.core_research_sync import capabilities
from app.main import app
paths={getattr(r,'path',None) for r in app.routes}
required={'/v1/core/research-sync/capabilities','/v1/core/research-sync/plan','/v1/core/research-sync/synchronize'}
missing=required-paths
assert not missing,missing
cap=capabilities()
assert CORE_RESEARCH_SYNC_SCHEMA=='sc-research-librarian-core-research-sync/1.0'
assert CORE_PROJECT_STATE_CONTRACT=='sc.research.project-state-versioning-reproducibility.v1'
assert cap['immutable_project_state_versions'] is True,cap
assert cap['research_context_bindings'] is True,cap
assert cap['research_room_bindings'] is True,cap
assert cap['automatic_truth_promotion'] is False,cap
assert cap['automatic_workflow_advancement'] is False,cap
print('PASS: v8.9 Core Research Object Synchronization routes and governance boundaries active')
PY

docker exec -i "$CONTAINER" python - <<'PY'
import json, os, urllib.request
key=os.environ.get('SC_RL_BACKEND_API_KEY','')
assert key,'SC_RL_BACKEND_API_KEY missing'
req=urllib.request.Request('http://127.0.0.1:8093/v1/core/readiness',headers={'X-SC-RL-Key':key})
with urllib.request.urlopen(req,timeout=35) as r: data=json.load(r)
caps=data.get('capabilities',{})
project_state=caps.get('project_state',{})
research_intel=caps.get('finding_claim_evidence_intelligence',{})
assert project_state.get('ok') is True,project_state
assert research_intel.get('ok') is True,research_intel
assert (project_state.get('data') or {}).get('contract')=='sc.research.project-state-versioning-reproducibility.v1',project_state
assert (research_intel.get('data') or {}).get('contract')=='sc.research.finding-claim-evidence.v1',research_intel
print('PASS: Platform Core project-state/versioning capability reachable')
print('PASS: Platform Core Finding, Claim & Evidence Intelligence capability reachable')
PY

echo "=== VERIFY v8.9 FINDING, CLAIM & EVIDENCE EXTRACTION PIPELINE ==="
docker exec -i "$CONTAINER" python - <<'PY'
from app.contracts.research_intelligence_extraction import RESEARCH_INTELLIGENCE_EXTRACTION_SCHEMA, ResearchIntelligenceExtractionRequest
from app.services.research_intelligence_extraction import capabilities, extract_candidates
from app.main import app
paths={getattr(r,'path',None) for r in app.routes}
required={'/v1/core/research-intelligence/capabilities','/v1/core/research-intelligence/extract','/v1/core/research-intelligence/promote'}
missing=required-paths
assert not missing,missing
cap=capabilities()
assert RESEARCH_INTELLIGENCE_EXTRACTION_SCHEMA=='sc-research-librarian-finding-claim-evidence-extraction/1.0'
assert cap['human_review_required_for_core_promotion'] is True,cap
assert cap['default_review_decision']=='pending',cap
assert cap['automatic_truth_determination'] is False,cap
request=ResearchIntelligenceExtractionRequest(core_project_id='smoke-project',passages=[{'local_evidence_id':'smoke-evidence','core_evidence_id':'core-evidence-smoke','text':'Observed emissions decreased after the intervention. The results suggest the effect may depend on baseline conditions.'}])
result=extract_candidates(request)
assert result['candidate_count']==2,result
assert all(x['review_decision']=='pending' for x in result['candidates']),result
assert all(x['evidence'][0]['relation']=='contextualizes' for x in result['candidates']),result
print('PASS: v8.9 deterministic candidate extraction + human review gate active')
PY

echo "=== VERIFY v8.10 ARGUMENT, CONTRADICTION & SYNTHESIS INTEGRATION ==="
docker exec -i "$CONTAINER" python - <<'PY'
import asyncio
from app.clients.platform_core import PlatformCoreClient
from app.contracts.argument_synthesis import ARGUMENT_SYNTHESIS_SCHEMA, CORE_ARGUMENT_CONTRACT, ArgumentSynthesisPlanRequest
from app.services.argument_synthesis import capabilities, build_plan
from app.main import app
paths={getattr(r,'path',None) for r in app.routes}
required={'/v1/core/argument-synthesis/capabilities','/v1/core/argument-synthesis/plan','/v1/core/argument-synthesis/promote','/v1/core/argument-synthesis/contradictions/{core_project_id:path}'}
missing=required-paths
assert not missing,missing
cap=capabilities()
assert ARGUMENT_SYNTHESIS_SCHEMA=='sc-research-librarian-argument-contradiction-synthesis/1.0'
assert CORE_ARGUMENT_CONTRACT=='sc.research.argument-evidentiary-synthesis.v1'
assert cap['human_review_required_for_core_promotion'] is True,cap
assert cap['automatic_relation_inference'] is False,cap
assert cap['automatic_argument_ranking'] is False,cap
assert cap['automatic_contradiction_resolution'] is False,cap
assert cap['automatic_synthesis_generation'] is False,cap
assert cap['automatic_conclusion_generation'] is False,cap
request=ArgumentSynthesisPlanRequest(core_project_id='smoke-project',title='Smoke argument',nodes=[{'local_ref':'claim-1','core_object_type':'claim','core_object_id':'core-claim-1','role':'premise'},{'local_ref':'finding-1','core_object_type':'finding','core_object_id':'core-finding-1','role':'support'}],relations=[{'source_local_ref':'finding-1','target_local_ref':'claim-1','relation':'supports'}])
plan=build_plan(request)['plan']
assert plan['review_decision']=='pending',plan
assert plan['relations'][0]['relation']=='supports' and plan['relations'][0]['relation_supplied_explicitly'] is True,plan
core=asyncio.run(PlatformCoreClient().argument_readiness())
assert core.get('contract')==CORE_ARGUMENT_CONTRACT,core
print('PASS: v8.10 reviewer-directed argument planning and Core argument contract active')
PY

echo "=== VERIFY DURABLE ASYNC JOB QUEUE ==="
docker exec -i "$CONTAINER" python - <<'PY'
import json, os, urllib.request
key=os.environ.get('SC_RL_BACKEND_API_KEY','')
assert key, 'SC_RL_BACKEND_API_KEY missing'
req=urllib.request.Request('http://127.0.0.1:8093/v1/jobs/runtime',headers={'X-SC-RL-Key':key})
with urllib.request.urlopen(req,timeout=35) as r: data=json.load(r)
assert data.get('schema')=='sc-research-librarian-async-runtime/1.0',data
assert data.get('durable') is True,data
backend=data.get('storage_backend')
assert backend in {'postgres','sqlite'},data
if os.environ.get('SC_RL_DATABASE_BACKEND','').lower() in {'postgres','postgresql','neon'}:
    assert backend=='postgres',data
    assert data.get('claim_strategy')=='for-update-skip-locked',data
print('PASS: durable async job runtime active on',backend)
PY

echo "PASS: Research Librarian AI v${VERSION} Argument, Contradiction & Synthesis Integration backend deployed and verified."
