#!/usr/bin/env bash
set -Eeuo pipefail
VERSION="11.5.0"
ROOT="/opt/sustainable-catalyst/research-librarian-ai"
LIVE_BACKEND="$ROOT/backend"
COMPOSE="$ROOT/compose.yml"
ENV_FILE="$ROOT/.env.contabo"
CORE_ENV="/opt/sustainable-catalyst/core/.env.production"
CORE_CONTAINER="sc-core"
SERVICE="research-librarian"
CONTAINER="sc-research-librarian"
BACKUP_ROOT="/opt/sustainable-catalyst/backups/research-librarian-ai"
ARCHIVE="${1:-/tmp/sustainable-catalyst-research-librarian-backend-v11.5.0.zip}"
TMP="$(mktemp -d /tmp/sc-rl-v1150.XXXXXX)"
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
grep -q '__version__ = "11.5.0"' "$INIT" || fail "backend package version mismatch"
for f in \
 app/clients/platform_core.py app/api/core.py app/async_jobs.py app/services/document_jobs.py \
 app/contracts/unified_scholarly_ai_environment.py app/services/unified_scholarly_ai_environment.py \
 app/contracts/study_protocol_preregistration.py app/services/study_protocol_preregistration.py tests/test_v1110_study_protocol_preregistration.py migrations/026_study_protocol_preregistration_engine.sql \
 app/contracts/statistical_analysis_planning_intelligence.py app/services/statistical_analysis_planning_intelligence.py tests/test_v1120_statistical_analysis_planning_intelligence.py migrations/027_statistical_analysis_planning_intelligence.sql \
 app/contracts/causal_research_design_intelligence.py app/services/causal_research_design_intelligence.py tests/test_v1130_causal_research_design_intelligence.py migrations/028_causal_research_design_intelligence.sql \
 app/contracts/simulation_model_study_planner.py app/services/simulation_model_study_planner.py tests/test_v1150_simulation_model_study_planner.py migrations/029_simulation_model_study_planner.sql; do
  [[ -f "$SRC_BACKEND/$f" ]] || fail "required backend file missing: $f"
done
grep -q 'STUDY_PROTOCOL_PREREGISTRATION_SCHEMA' "$SRC_BACKEND/app/contracts/study_protocol_preregistration.py" || fail "v11.1 study protocol contract missing"
grep -q 'STATISTICAL_ANALYSIS_PLANNING_SCHEMA' "$SRC_BACKEND/app/contracts/statistical_analysis_planning_intelligence.py" || fail "v11.2 statistical planning contract missing"
grep -q '"statistical-analysis-planning-intelligence-snapshot"' "$SRC_BACKEND/app/async_jobs.py" || fail "v11.2 durable snapshot job missing"
grep -q '/statistical-analysis-planning-intelligence/plans/{statistical_analysis_plan_id}/runtime-handoffs' "$SRC_BACKEND/app/api/core.py" || fail "v11.2 runtime handoff endpoint missing"
grep -q 'human_statistical_approval_required.*True' "$SRC_BACKEND/app/services/statistical_analysis_planning_intelligence.py" || fail "v11.2 human approval guardrail missing"
grep -q 'existing_statistical_research_layer_remains_runtime_core_bridge.*True' "$SRC_BACKEND/app/services/statistical_analysis_planning_intelligence.py" || fail "v11.2 v8.11 bridge boundary missing"
grep -q 'automatic_model_selection.*False' "$SRC_BACKEND/app/services/statistical_analysis_planning_intelligence.py" || fail "v11.2 model-selection guardrail missing"
grep -q 'automatic_power_calculation.*False' "$SRC_BACKEND/app/services/statistical_analysis_planning_intelligence.py" || fail "v11.2 power-calculation guardrail missing"
grep -q 'automatic_significance_inference.*False' "$SRC_BACKEND/app/services/statistical_analysis_planning_intelligence.py" || fail "v11.2 significance guardrail missing"
grep -q 'automatic_causality_inference.*False' "$SRC_BACKEND/app/services/statistical_analysis_planning_intelligence.py" || fail "v11.2 causality guardrail missing"
grep -q 'automatic_execution.*False' "$SRC_BACKEND/app/services/statistical_analysis_planning_intelligence.py" || fail "v11.2 execution guardrail missing"
grep -q 'CAUSAL_RESEARCH_DESIGN_SCHEMA' "$SRC_BACKEND/app/contracts/causal_research_design_intelligence.py" || fail "v11.3 causal design contract missing"
grep -q '"causal-research-design-intelligence-snapshot"' "$SRC_BACKEND/app/async_jobs.py" || fail "v11.3 durable snapshot job missing"
grep -q '/causal-research-design-intelligence/designs/{causal_design_id}/runtime-handoffs' "$SRC_BACKEND/app/api/core.py" || fail "v11.3 causal handoff endpoint missing"
grep -q 'human_causal_design_approval_required.*True' "$SRC_BACKEND/app/services/causal_research_design_intelligence.py" || fail "v11.3 human causal-design approval guardrail missing"
grep -q 'automatic_causal_identification.*False' "$SRC_BACKEND/app/services/causal_research_design_intelligence.py" || fail "v11.3 causal identification guardrail missing"
grep -q 'automatic_adjustment_set_selection.*False' "$SRC_BACKEND/app/services/causal_research_design_intelligence.py" || fail "v11.3 adjustment-set guardrail missing"
grep -q 'automatic_instrument_validation.*False' "$SRC_BACKEND/app/services/causal_research_design_intelligence.py" || fail "v11.3 instrument guardrail missing"
grep -q 'automatic_causal_estimation.*False' "$SRC_BACKEND/app/services/causal_research_design_intelligence.py" || fail "v11.3 estimation guardrail missing"
grep -q 'automatic_causality_inference.*False' "$SRC_BACKEND/app/services/causal_research_design_intelligence.py" || fail "v11.3 causality guardrail missing"
grep -q 'SIMULATION_MODEL_STUDY_SCHEMA' "$SRC_BACKEND/app/contracts/simulation_model_study_planner.py" || fail "v11.4 simulation/model study contract missing"
grep -q '"simulation-model-study-planner-snapshot"' "$SRC_BACKEND/app/async_jobs.py" || fail "v11.4 durable snapshot job missing"
grep -q '/simulation-model-study-planner/studies/{simulation_study_id}/runtime-handoffs' "$SRC_BACKEND/app/api/core.py" || fail "v11.4 runtime handoff endpoint missing"
grep -q 'human_model_study_approval_required.*True' "$SRC_BACKEND/app/services/simulation_model_study_planner.py" || fail "v11.4 human approval guardrail missing"
grep -q 'automatic_model_selection.*False' "$SRC_BACKEND/app/services/simulation_model_study_planner.py" || fail "v11.4 model selection guardrail missing"
grep -q 'automatic_calibration.*False' "$SRC_BACKEND/app/services/simulation_model_study_planner.py" || fail "v11.4 calibration guardrail missing"
grep -q 'automatic_validation.*False' "$SRC_BACKEND/app/services/simulation_model_study_planner.py" || fail "v11.4 validation guardrail missing"
grep -q 'automatic_simulation_execution.*False' "$SRC_BACKEND/app/services/simulation_model_study_planner.py" || fail "v11.4 simulation execution guardrail missing"
grep -q 'REPRODUCTION_REPLICATION_SCHEMA' "$SRC_BACKEND/app/contracts/reproduction_replication_intelligence.py" || fail "v11.5 reproduction/replication contract missing"
grep -q '"reproduction-replication-intelligence-snapshot"' "$SRC_BACKEND/app/async_jobs.py" || fail "v11.5 durable snapshot job missing"
grep -q '/reproduction-replication-intelligence/projects/{reproduction_replication_id}/runtime-handoffs' "$SRC_BACKEND/app/api/core.py" || fail "v11.5 runtime handoff endpoint missing"
grep -q 'automatic_reproduction_verdict.*False' "$SRC_BACKEND/app/services/reproduction_replication_intelligence.py" || fail "v11.5 reproduction verdict guardrail missing"
grep -q 'automatic_replication_verdict.*False' "$SRC_BACKEND/app/services/reproduction_replication_intelligence.py" || fail "v11.5 replication verdict guardrail missing"

echo "=== BACKUP RESEARCH LIBRARIAN ==="
mkdir -p "$BACKUP_ROOT"; stamp="$(date +%Y%m%d-%H%M%S)"
tar -C "$ROOT" -czf "$BACKUP_ROOT/backend-before-v${VERSION}-${stamp}.tgz" backend
cp -a "$COMPOSE" "$BACKUP_ROOT/compose-before-v${VERSION}-${stamp}.yml"
cp -a "$ENV_FILE" "$BACKUP_ROOT/env-before-v${VERSION}-${stamp}"

echo "=== INSTALL v${VERSION} BACKEND ==="
rsync -a --exclude='data/' --exclude='__pycache__/' --exclude='.pytest_cache/' --exclude='*.pyc' --exclude='.env' --exclude='.env.*' "$SRC_BACKEND/" "$LIVE_BACKEND/"
python3 - "$COMPOSE" <<'PYCOMPOSE1130'
from pathlib import Path
import re,sys
p=Path(sys.argv[1]); s=p.read_text()
s=re.sub(r'(?m)^(\s*image:\s*sustainable-catalyst-research-librarian:).*$', r'\g<1>11.5.0', s)
s=re.sub(r'(?m)^(\s*SC_RL_RELEASE_VERSION:\s*)["\']?[^"\'\n]+["\']?\s*$', r'\g<1>"11.5.0"', s)
p.write_text(s)
PYCOMPOSE1130
python3 - "$ENV_FILE" "$CORE_ENV" <<'PYENV1130'
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
updates={'SC_RL_RELEASE_VERSION':'11.5.0','SC_RL_CORE_ENABLED':'true','SC_RL_CORE_BASE_URL':'http://sc-core:8090','SC_RL_CORE_MINIMUM_VERSION':'3.3.0','SC_RL_CORE_SUPPORTED_MAJOR':'3','SC_RL_CORE_FAIL_CLOSED_WRITES':'true','SC_RL_ASYNC_JOBS_ENABLED':'true'}
if core_key: updates['SC_RL_CORE_WRITE_API_KEY']=core_key
set_values(sys.argv[1],updates)
print('PASS: Research Librarian Core integration environment aligned (secret not displayed).')
PYENV1130
cd "$ROOT"; docker compose -f "$COMPOSE" config --quiet
echo "=== BUILD IMAGE ==="
if grep -qE '^[[:space:]]*build:' "$COMPOSE"; then docker compose -f "$COMPOSE" build "$SERVICE"; else docker build -t "sustainable-catalyst-research-librarian:${VERSION}" "$LIVE_BACKEND"; fi
echo "=== RECREATE SERVICE ==="
docker compose -f "$COMPOSE" up -d --force-recreate "$SERVICE"
for i in $(seq 1 90); do
  if curl -fsS http://127.0.0.1:8093/health >"$TMP/health.json" 2>/dev/null && python3 - "$TMP/health.json" <<'PYHEALTH1130' >/dev/null 2>&1
import json,sys
x=json.load(open(sys.argv[1])); assert x.get('version')=='11.5.0' and x.get('ready') is True
PYHEALTH1130
  then break; fi
  if [[ "$i" == 90 ]]; then docker logs --tail=240 "$CONTAINER" >&2 || true; cat "$TMP/health.json" >&2 2>/dev/null || true; fail "Research Librarian v11.5.0 did not become ready"; fi
  sleep 2
done
python3 - "$TMP/health.json" <<'PYHEALTHPRINT1130'
import json,sys
x=json.load(open(sys.argv[1])); assert x.get('version')=='11.5.0' and x.get('ready') is True,x
print('PASS: Research Librarian /health reports 11.5.0 and ready=true')
PYHEALTHPRINT1130

echo "=== VERIFY PLATFORM CORE INTEGRATION ==="
docker exec -i "$CONTAINER" python - <<'PYCORE1130'
import asyncio
from app.services.unified_research_runtime import readiness
async def main():
    r=await readiness(); assert r['ready'] is True,r; assert r['core_compatible'] is True,r; assert r['core_write_ready'] is True,r
    print('PASS: Platform Core research/reasoning integration ready')
asyncio.run(main())
PYCORE1130

echo "=== VERIFY v11.1 STUDY PROTOCOL & PREREGISTRATION ENGINE ==="
docker exec -i "$CONTAINER" python - <<'PYV1110VERIFY'
import os
from app.services.study_protocol_preregistration import capabilities, StudyProtocolPreregistrationStore
from app.async_jobs import JOB_TYPES
from app.main import app
cap=capabilities(); assert cap['milestone']=='11.1' and cap['durable'] is True
assert cap['preregistration_baseline_is_immutable_once_frozen'] is True and cap['human_preregistration_approval_required'] is True
assert cap['automatic_preregistration'] is False and cap['automatic_execution'] is False and cap['automatic_truth_promotion'] is False
assert 'study-protocol-preregistration-snapshot' in JOB_TYPES
paths={getattr(r,'path','') for r in app.routes}; required={'/v1/core/study-protocol-preregistration/capabilities','/v1/core/study-protocol-preregistration/protocols/{study_protocol_id}/preregister','/v1/core/study-protocol-preregistration/snapshots/freeze'}
assert not(required-paths),required-paths
store=StudyProtocolPreregistrationStore()
if os.environ.get('SC_RL_DATABASE_BACKEND','').lower() in {'postgres','postgresql','neon'}: assert store.backend=='postgres'
print('PASS: v11.1 study protocol/preregistration engine active on',store.backend)
PYV1110VERIFY

echo "=== VERIFY v11.2 STATISTICAL ANALYSIS PLANNING INTELLIGENCE ==="
docker exec -i "$CONTAINER" python - <<'PYV1120VERIFY'
import os
from app.services.statistical_analysis_planning_intelligence import capabilities, StatisticalAnalysisPlanningIntelligenceStore
from app.async_jobs import JOB_TYPES
from app.main import app
cap=capabilities(); assert cap['milestone']=='11.2' and cap['durable'] is True
assert cap['estimand_registry'] is True and cap['model_specification_registry'] is True and cap['assumption_check_registry'] is True
assert cap['power_and_sample_size_planning'] is True and cap['multiplicity_planning'] is True and cap['missing_data_planning'] is True and cap['sensitivity_analysis_registry'] is True
assert cap['human_statistical_approval_required'] is True and cap['existing_statistical_research_layer_remains_runtime_core_bridge'] is True
assert cap['automatic_method_selection'] is False and cap['automatic_model_selection'] is False and cap['automatic_power_calculation'] is False
assert cap['automatic_significance_inference'] is False and cap['automatic_causality_inference'] is False
assert cap['automatic_result_interpretation'] is False and cap['automatic_execution'] is False and cap['automatic_truth_promotion'] is False
assert 'statistical-analysis-planning-intelligence-snapshot' in JOB_TYPES
paths={getattr(r,'path','') for r in app.routes}; required={'/v1/core/statistical-analysis-planning-intelligence/capabilities','/v1/core/statistical-analysis-planning-intelligence/plans','/v1/core/statistical-analysis-planning-intelligence/plans/{statistical_analysis_plan_id}/analysis-matrix','/v1/core/statistical-analysis-planning-intelligence/plans/{statistical_analysis_plan_id}/runtime-handoffs','/v1/core/statistical-analysis-planning-intelligence/snapshots/freeze'}
assert not(required-paths),required-paths
store=StatisticalAnalysisPlanningIntelligenceStore()
if os.environ.get('SC_RL_DATABASE_BACKEND','').lower() in {'postgres','postgresql','neon'}: assert store.backend=='postgres'
print('PASS: v11.2 statistical analysis planning intelligence active on',store.backend)
PYV1120VERIFY

echo "=== VERIFY v11.3 CAUSAL RESEARCH DESIGN INTELLIGENCE ==="
docker exec -i "$CONTAINER" python - <<'PYV1130VERIFY'
import os
from app.services.causal_research_design_intelligence import capabilities, CausalResearchDesignIntelligenceStore
from app.async_jobs import JOB_TYPES
from app.main import app
cap=capabilities(); assert cap['milestone']=='11.3' and cap['durable'] is True
assert cap['causal_variable_role_registry'] is True and cap['directed_acyclic_graph'] is True and cap['causal_assumption_registry'] is True
assert cap['identification_strategy_registry'] is True and cap['diagnostic_planning'] is True and cap['negative_control_planning'] is True and cap['causal_sensitivity_planning'] is True
assert cap['human_causal_design_approval_required'] is True and cap['research_lab_and_specialist_runtimes_own_causal_execution'] is True
assert cap['automatic_causal_identification'] is False and cap['automatic_adjustment_set_selection'] is False and cap['automatic_instrument_validation'] is False
assert cap['automatic_causal_estimation'] is False and cap['automatic_causality_inference'] is False and cap['automatic_execution'] is False and cap['automatic_truth_promotion'] is False
assert 'causal-research-design-intelligence-snapshot' in JOB_TYPES
paths={getattr(r,'path','') for r in app.routes}; required={'/v1/core/causal-research-design-intelligence/capabilities','/v1/core/causal-research-design-intelligence/designs','/v1/core/causal-research-design-intelligence/designs/{causal_design_id}/causal-graph','/v1/core/causal-research-design-intelligence/designs/{causal_design_id}/runtime-handoffs','/v1/core/causal-research-design-intelligence/snapshots/freeze'}
assert not(required-paths),required-paths
store=CausalResearchDesignIntelligenceStore()
if os.environ.get('SC_RL_DATABASE_BACKEND','').lower() in {'postgres','postgresql','neon'}: assert store.backend=='postgres'
print('PASS: v11.3 causal research design intelligence active on',store.backend)
PYV1130VERIFY


echo "=== VERIFY v11.4 SIMULATION & MODEL STUDY PLANNER ==="
docker exec -i "$CONTAINER" python - <<'PYV1150VERIFY'
import os
from app.services.simulation_model_study_planner import capabilities, SimulationModelStudyPlannerStore
from app.async_jobs import JOB_TYPES
from app.main import app
cap=capabilities(); assert cap['milestone']=='11.4' and cap['durable'] is True
assert cap['model_specification_registry'] is True and cap['scenario_set_registry'] is True and cap['calibration_planning'] is True and cap['validation_planning'] is True
assert cap['uncertainty_planning'] is True and cap['sensitivity_planning'] is True and cap['ensemble_planning'] is True and cap['compute_budget_planning'] is True
assert cap['human_model_study_approval_required'] is True and cap['specialist_runtimes_own_simulation_execution'] is True
assert cap['automatic_model_selection'] is False and cap['automatic_calibration'] is False and cap['automatic_validation'] is False
assert cap['automatic_simulation_execution'] is False and cap['automatic_forecast_acceptance'] is False and cap['automatic_causal_inference'] is False and cap['automatic_truth_promotion'] is False
assert 'simulation-model-study-planner-snapshot' in JOB_TYPES
paths={getattr(r,'path','') for r in app.routes}; required={'/v1/core/simulation-model-study-planner/capabilities','/v1/core/simulation-model-study-planner/studies','/v1/core/simulation-model-study-planner/studies/{simulation_study_id}/study-matrix','/v1/core/simulation-model-study-planner/studies/{simulation_study_id}/runtime-handoffs','/v1/core/simulation-model-study-planner/snapshots/freeze'}
assert not(required-paths),required-paths
store=SimulationModelStudyPlannerStore()
if os.environ.get('SC_RL_DATABASE_BACKEND','').lower() in {'postgres','postgresql','neon'}: assert store.backend=='postgres'
print('PASS: v11.4 simulation/model study planner active on',store.backend)
PYV1150VERIFY

echo "=== VERIFY v11.5 REPRODUCTION & REPLICATION INTELLIGENCE ==="
docker exec -i "$CONTAINER" python - <<'PYV1150VERIFY'
import os
from app.services.reproduction_replication_intelligence import capabilities, ReproductionReplicationIntelligenceStore
from app.async_jobs import JOB_TYPES
from app.main import app
cap=capabilities(); assert cap['milestone']=='11.5' and cap['durable'] is True
assert cap['reproduction_replication_distinction'] is True and cap['comparability_criteria'] is True and cap['human_outcome_assessment'] is True
assert cap['specialist_runtimes_own_execution'] is True and cap['platform_core_remains_governed_research_object_authority'] is True
assert cap['automatic_reproduction_verdict'] is False and cap['automatic_replication_verdict'] is False
assert cap['automatic_claim_acceptance'] is False and cap['automatic_causal_inference'] is False and cap['automatic_execution'] is False and cap['automatic_truth_promotion'] is False
assert 'reproduction-replication-intelligence-snapshot' in JOB_TYPES
paths={getattr(r,'path','') for r in app.routes}; required={'/v1/core/reproduction-replication-intelligence/capabilities','/v1/core/reproduction-replication-intelligence/projects','/v1/core/reproduction-replication-intelligence/projects/{reproduction_replication_id}/comparison-matrix','/v1/core/reproduction-replication-intelligence/projects/{reproduction_replication_id}/runtime-handoffs','/v1/core/reproduction-replication-intelligence/snapshots/freeze'}
assert not(required-paths),required-paths
store=ReproductionReplicationIntelligenceStore()
if os.environ.get('SC_RL_DATABASE_BACKEND','').lower() in {'postgres','postgresql','neon'}: assert store.backend=='postgres'
print('PASS: v11.5 reproduction/replication intelligence active on',store.backend)
PYV1150VERIFY

echo "=== VERIFY DURABLE ASYNC JOB RUNTIME ==="
docker exec -i "$CONTAINER" python - <<'PYJOBS1120'
from app.async_jobs import JOB_TYPES
for job in ['study-protocol-preregistration-snapshot','statistical-analysis-planning-intelligence-snapshot','causal-research-design-intelligence-snapshot','simulation-model-study-planner-snapshot','reproduction-replication-intelligence-snapshot']: assert job in JOB_TYPES
print('PASS: v11.1/v11.2/v11.3/v11.4/v11.5 durable snapshot jobs registered')
PYJOBS1120

echo "PASS: Research Librarian AI v11.5.0 Reproduction & Replication Intelligence backend deployed and verified."
