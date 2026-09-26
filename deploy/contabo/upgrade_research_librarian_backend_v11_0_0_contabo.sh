#!/usr/bin/env bash
set -Eeuo pipefail
VERSION="11.0.0"
ROOT="/opt/sustainable-catalyst/research-librarian-ai"
LIVE_BACKEND="$ROOT/backend"
COMPOSE="$ROOT/compose.yml"
ENV_FILE="$ROOT/.env.contabo"
CORE_ENV="/opt/sustainable-catalyst/core/.env.production"
CORE_CONTAINER="sc-core"
SERVICE="research-librarian"
CONTAINER="sc-research-librarian"
BACKUP_ROOT="/opt/sustainable-catalyst/backups/research-librarian-ai"
ARCHIVE="${1:-/tmp/sustainable-catalyst-research-librarian-backend-v11.0.0.zip}"
TMP="$(mktemp -d /tmp/sc-rl-v1100.XXXXXX)"
trap 'rm -rf "$TMP"' EXIT
fail(){ echo "ERROR: $*" >&2; exit 1; }
for c in docker unzip rsync python3 curl tar grep; do command -v "$c" >/dev/null 2>&1 || fail "$c is required"; done
[[ -f "$ARCHIVE" ]] || fail "backend package not found: $ARCHIVE"
[[ -d "$ROOT" && -d "$LIVE_BACKEND" ]] || fail "runtime root/backend missing: $ROOT"
[[ -f "$COMPOSE" ]] || fail "compose file missing: $COMPOSE"
[[ -f "$ENV_FILE" ]] || fail "Research Librarian environment file missing: $ENV_FILE"
docker inspect "$CORE_CONTAINER" >/dev/null 2>&1 || fail "Platform Core container is not present: $CORE_CONTAINER"
unzip -tq "$ARCHIVE" >/dev/null || fail "invalid backend ZIP"
unzip -q "$ARCHIVE" -d "$TMP/package"
INIT="$(find "$TMP/package" -type f -path '*/backend/app/__init__.py' | head -1)"
[[ -n "$INIT" ]] || fail "backend/app/__init__.py missing from package"
SRC_BACKEND="$(dirname "$(dirname "$INIT")")"
grep -q '__version__ = "11.0.0"' "$INIT" || fail "backend package version mismatch"
for f in \
 app/clients/platform_core.py app/api/core.py app/async_jobs.py app/services/document_jobs.py \
 app/contracts/unified_scholarly_ai_environment.py app/services/unified_scholarly_ai_environment.py migrations/015_unified_scholarly_ai_research_environment.sql \
 app/contracts/research_gap_novelty_intelligence.py app/services/research_gap_novelty_intelligence.py tests/test_v1070_research_gap_novelty_intelligence.py migrations/022_research_gap_novelty_intelligence.sql \
 app/contracts/dataset_discovery_data_fitness.py app/services/dataset_discovery_data_fitness.py tests/test_v1080_dataset_discovery_data_fitness.py migrations/023_dataset_discovery_data_fitness.sql \
 app/contracts/computational_research_planning.py app/services/computational_research_planning.py tests/test_v1090_computational_research_planning.py migrations/024_computational_research_planning.sql \
 app/contracts/research_program_intelligence.py app/services/research_program_intelligence.py tests/test_v1100_research_program_intelligence.py migrations/025_research_program_intelligence.sql; do
  [[ -f "$SRC_BACKEND/$f" ]] || fail "required backend file missing: $f"
done
grep -q 'DATASET_DISCOVERY_FITNESS_SCHEMA' "$SRC_BACKEND/app/contracts/dataset_discovery_data_fitness.py" || fail "v10.8 dataset-fitness contract missing"
grep -q 'COMPUTATIONAL_RESEARCH_PLANNING_SCHEMA' "$SRC_BACKEND/app/contracts/computational_research_planning.py" || fail "v10.9 computational-planning contract missing"
grep -q '"computational-research-planning-snapshot"' "$SRC_BACKEND/app/async_jobs.py" || fail "v10.9 snapshot job missing"
grep -q '/computational-research-planning/plans/{computational_plan_id}/execution-graph' "$SRC_BACKEND/app/api/core.py" || fail "v10.9 execution graph endpoint missing"
grep -q 'human_method_and_runtime_approval_required.*True' "$SRC_BACKEND/app/services/computational_research_planning.py" || fail "v10.9 human approval guardrail missing"
grep -q 'automatic_execution.*False' "$SRC_BACKEND/app/services/computational_research_planning.py" || fail "v10.9 automatic-execution guardrail missing"
grep -q 'RESEARCH_PROGRAM_INTELLIGENCE_SCHEMA' "$SRC_BACKEND/app/contracts/research_program_intelligence.py" || fail "v11.0 research-program contract missing"
grep -q '"research-program-intelligence-snapshot"' "$SRC_BACKEND/app/async_jobs.py" || fail "v11.0 snapshot job missing"
grep -q '/research-program-intelligence/programs/{research_program_id}/program-graph' "$SRC_BACKEND/app/api/core.py" || fail "v11.0 program graph endpoint missing"
grep -q 'human_program_approval_required.*True' "$SRC_BACKEND/app/services/research_program_intelligence.py" || fail "v11.0 human approval guardrail missing"
grep -q 'automatic_research_prioritization.*False' "$SRC_BACKEND/app/services/research_program_intelligence.py" || fail "v11.0 automatic-prioritization guardrail missing"
grep -q 'automatic_resource_allocation.*False' "$SRC_BACKEND/app/services/research_program_intelligence.py" || fail "v11.0 automatic-resource-allocation guardrail missing"
grep -q 'automatic_execution.*False' "$SRC_BACKEND/app/services/research_program_intelligence.py" || fail "v11.0 automatic-execution guardrail missing"

echo "=== BACKUP RESEARCH LIBRARIAN ==="
mkdir -p "$BACKUP_ROOT"; stamp="$(date +%Y%m%d-%H%M%S)"
tar -C "$ROOT" -czf "$BACKUP_ROOT/backend-before-v${VERSION}-${stamp}.tgz" backend
cp -a "$COMPOSE" "$BACKUP_ROOT/compose-before-v${VERSION}-${stamp}.yml"
cp -a "$ENV_FILE" "$BACKUP_ROOT/env-before-v${VERSION}-${stamp}"

echo "=== INSTALL v${VERSION} BACKEND ==="
rsync -a --exclude='data/' --exclude='__pycache__/' --exclude='.pytest_cache/' --exclude='*.pyc' --exclude='.env' --exclude='.env.*' "$SRC_BACKEND/" "$LIVE_BACKEND/"
python3 - "$COMPOSE" <<'PYCOMPOSE1100'
from pathlib import Path
import re,sys
p=Path(sys.argv[1]); s=p.read_text()
s=re.sub(r'(?m)^(\s*image:\s*sustainable-catalyst-research-librarian:).*$', r'\g<1>11.0.0', s)
s=re.sub(r'(?m)^(\s*SC_RL_RELEASE_VERSION:\s*)["\']?[^"\'\n]+["\']?\s*$', r'\g<1>"11.0.0"', s)
p.write_text(s)
PYCOMPOSE1100
python3 - "$ENV_FILE" "$CORE_ENV" <<'PYENV1100'
from pathlib import Path
import sys
def parse(path):
    out={}
    try: content=Path(path).read_text()
    except (FileNotFoundError,PermissionError,OSError): return out
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
rl=parse(sys.argv[1]); core=parse(sys.argv[2]); core_key=core.get('SC_CORE_WRITE_API_KEY','').strip(); rl_key=rl.get('SC_RL_CORE_WRITE_API_KEY','').strip()
if not core_key and not rl_key: raise SystemExit('SC_CORE_WRITE_API_KEY is missing and no existing Librarian Core write key is configured.')
updates={'SC_RL_RELEASE_VERSION':'11.0.0','SC_RL_CORE_ENABLED':'true','SC_RL_CORE_BASE_URL':'http://sc-core:8090','SC_RL_CORE_MINIMUM_VERSION':'3.3.0','SC_RL_CORE_SUPPORTED_MAJOR':'3','SC_RL_CORE_FAIL_CLOSED_WRITES':'true','SC_RL_ASYNC_JOBS_ENABLED':'true'}
if core_key: updates['SC_RL_CORE_WRITE_API_KEY']=core_key
set_values(sys.argv[1],updates)
print('PASS: Research Librarian Core integration environment aligned (secret not displayed).')
PYENV1100

cd "$ROOT"; docker compose -f "$COMPOSE" config --quiet
echo "=== BUILD IMAGE ==="
if grep -qE '^[[:space:]]*build:' "$COMPOSE"; then docker compose -f "$COMPOSE" build "$SERVICE"; else docker build -t "sustainable-catalyst-research-librarian:${VERSION}" "$LIVE_BACKEND"; fi
echo "=== RECREATE SERVICE ==="
docker compose -f "$COMPOSE" up -d --force-recreate "$SERVICE"
for i in $(seq 1 90); do
  if curl -fsS http://127.0.0.1:8093/health >"$TMP/health.json" 2>/dev/null && python3 - "$TMP/health.json" <<'PYHEALTH1100' >/dev/null 2>&1
import json,sys
x=json.load(open(sys.argv[1])); assert x.get('version')=='11.0.0' and x.get('ready') is True
PYHEALTH1100
  then break; fi
  if [[ "$i" == 90 ]]; then docker logs --tail=240 "$CONTAINER" >&2 || true; cat "$TMP/health.json" >&2 2>/dev/null || true; fail "Research Librarian v11.0.0 did not become ready"; fi
  sleep 2
done
python3 - "$TMP/health.json" <<'PYHEALTHPRINT1100'
import json,sys
x=json.load(open(sys.argv[1])); assert x.get('version')=='11.0.0' and x.get('ready') is True,x
print('PASS: Research Librarian /health reports 11.0.0 and ready=true')
PYHEALTHPRINT1100

echo "=== VERIFY PLATFORM CORE INTEGRATION ==="
docker exec -i "$CONTAINER" python - <<'PYCORE1100'
import asyncio
from app.services.unified_research_runtime import readiness
async def main():
    r=await readiness(); assert r['ready'] is True,r; assert r['core_compatible'] is True,r; assert r['core_write_ready'] is True,r
    print('PASS: Platform Core research/reasoning integration ready')
asyncio.run(main())
PYCORE1100

echo "=== VERIFY v10.8 DATASET DISCOVERY & DATA FITNESS INTELLIGENCE ==="
docker exec -i "$CONTAINER" python - <<'PYV1080VERIFY'
import os
from app.services.dataset_discovery_data_fitness import capabilities, DatasetDiscoveryDataFitnessStore
from app.async_jobs import JOB_TYPES
from app.main import app
cap=capabilities(); assert cap['milestone']=='10.8' and cap['durable'] is True
assert cap['human_fitness_decision_required'] is True
assert cap['automatic_dataset_suitability'] is False and cap['automatic_quality_certification'] is False and cap['automatic_ingestion'] is False
assert 'dataset-discovery-data-fitness-snapshot' in JOB_TYPES
paths={getattr(r,'path','') for r in app.routes}; required={'/v1/core/dataset-discovery-data-fitness/capabilities','/v1/core/dataset-discovery-data-fitness/projects','/v1/core/dataset-discovery-data-fitness/projects/{data_fitness_id}/coverage-matrix','/v1/core/dataset-discovery-data-fitness/projects/{data_fitness_id}/computational-planning-handoff','/v1/core/dataset-discovery-data-fitness/snapshots/freeze'}
assert not(required-paths),required-paths
store=DatasetDiscoveryDataFitnessStore()
if os.environ.get('SC_RL_DATABASE_BACKEND','').lower() in {'postgres','postgresql','neon'}: assert store.backend=='postgres'
print('PASS: v10.8 dataset discovery/data fitness intelligence active on',store.backend)
PYV1080VERIFY

echo "=== VERIFY v10.9 COMPUTATIONAL RESEARCH PLANNING ==="
docker exec -i "$CONTAINER" python - <<'PYV1090VERIFY'
import os
from app.services.computational_research_planning import capabilities, ComputationalResearchPlanningStore
from app.async_jobs import JOB_TYPES
from app.main import app
cap=capabilities(); assert cap['milestone']=='10.9' and cap['durable'] is True
assert cap['analysis_step_registry'] is True and cap['runtime_target_registry'] is True and cap['dependency_graph'] is True
assert cap['human_method_and_runtime_approval_required'] is True
assert cap['upstream_dataset_fitness_is_inherited_not_rejudged'] is True
assert cap['automatic_method_selection'] is False and cap['automatic_runtime_selection'] is False
assert cap['automatic_execution'] is False and cap['automatic_result_interpretation'] is False and cap['automatic_truth_promotion'] is False
assert cap['specialist_runtimes_own_execution'] is True
assert 'computational-research-planning-snapshot' in JOB_TYPES
paths={getattr(r,'path','') for r in app.routes}; required={'/v1/core/computational-research-planning/capabilities','/v1/core/computational-research-planning/plans','/v1/core/computational-research-planning/plans/{computational_plan_id}/execution-graph','/v1/core/computational-research-planning/plans/{computational_plan_id}/execution-handoffs','/v1/core/computational-research-planning/snapshots/freeze'}
assert not(required-paths),required-paths
store=ComputationalResearchPlanningStore()
if os.environ.get('SC_RL_DATABASE_BACKEND','').lower() in {'postgres','postgresql','neon'}: assert store.backend=='postgres'
print('PASS: v10.9 computational research planning active on',store.backend)
PYV1090VERIFY

echo "=== VERIFY v11.0 RESEARCH PROGRAM INTELLIGENCE ==="
docker exec -i "$CONTAINER" python - <<'PYV1100VERIFY'
import os
from app.services.research_program_intelligence import capabilities, ResearchProgramIntelligenceStore
from app.async_jobs import JOB_TYPES
from app.main import app
cap=capabilities(); assert cap['milestone']=='11.0' and cap['durable'] is True
assert cap['workstream_registry'] is True and cap['milestone_dependency_graph'] is True and cap['program_handoffs'] is True
assert cap['human_program_approval_required'] is True
assert cap['component_authority_remains_with_source_system'] is True and cap['specialist_runtimes_own_execution'] is True
assert cap['automatic_research_prioritization'] is False and cap['automatic_resource_allocation'] is False
assert cap['automatic_milestone_completion'] is False and cap['automatic_scientific_judgment'] is False
assert cap['automatic_execution'] is False and cap['automatic_truth_promotion'] is False
assert 'research-program-intelligence-snapshot' in JOB_TYPES
paths={getattr(r,'path','') for r in app.routes}; required={'/v1/core/research-program-intelligence/capabilities','/v1/core/research-program-intelligence/programs','/v1/core/research-program-intelligence/programs/{research_program_id}/program-graph','/v1/core/research-program-intelligence/programs/{research_program_id}/handoffs','/v1/core/research-program-intelligence/snapshots/freeze'}
assert not(required-paths),required-paths
store=ResearchProgramIntelligenceStore()
if os.environ.get('SC_RL_DATABASE_BACKEND','').lower() in {'postgres','postgresql','neon'}: assert store.backend=='postgres'
print('PASS: v11.0 research program intelligence active on',store.backend)
PYV1100VERIFY

echo "=== VERIFY DURABLE ASYNC JOB RUNTIME ==="
docker exec -i "$CONTAINER" python - <<'PYJOBS1100'
from app.async_jobs import JOB_TYPES
for job in ['dataset-discovery-data-fitness-snapshot','computational-research-planning-snapshot','research-program-intelligence-snapshot']: assert job in JOB_TYPES
print('PASS: v10.8/v10.9/v11.0 durable snapshot jobs registered')
PYJOBS1100

echo "PASS: Research Librarian AI v11.0.0 Research Program Intelligence backend deployed and verified."
