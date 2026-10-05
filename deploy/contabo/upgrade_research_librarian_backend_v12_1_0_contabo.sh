#!/usr/bin/env bash
set -Eeuo pipefail

VERSION="12.1.0"
ROOT="/opt/sustainable-catalyst/research-librarian-ai"
LIVE_BACKEND="$ROOT/backend"
COMPOSE="$ROOT/compose.yml"
ENV_FILE="$ROOT/.env.contabo"
CORE_ENV="/opt/sustainable-catalyst/core/.env.production"
CORE_CONTAINER="sc-core"
SERVICE="research-librarian"
CONTAINER="sc-research-librarian"
BACKUP_ROOT="/opt/sustainable-catalyst/backups/research-librarian-ai"
ARCHIVE="${1:-/tmp/sustainable-catalyst-research-librarian-backend-v12.1.0.zip}"
TMP="$(mktemp -d /tmp/sc-rl-v1210.XXXXXX)"
trap 'rm -rf "$TMP"' EXIT

fail(){ echo "ERROR: $*" >&2; exit 1; }

for c in docker unzip rsync python3 curl tar grep; do
  command -v "$c" >/dev/null 2>&1 || fail "$c is required"
done

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

grep -q '__version__ = "12.1.0"' "$INIT" || fail "backend package version mismatch"

for f in \
  app/main.py \
  app/api/neural_research.py \
  app/contracts/neural_research_intelligence.py \
  app/services/neural_research_intelligence.py \
  migrations/041_neural_research_intelligence_foundation.sql \
  tests/test_v1210_neural_research_intelligence_foundation.py
do
  [[ -f "$SRC_BACKEND/$f" ]] || fail "required v12.1.0 file missing: $f"
done

grep -q '"librarian_execution_authority":False' "$SRC_BACKEND/app/services/neural_research_intelligence.py" || fail "neural execution boundary missing"
grep -q '"model_weights_stored":False' "$SRC_BACKEND/app/services/neural_research_intelligence.py" || fail "model-weight storage boundary missing"
grep -q '"platform_core_model_contract_authority":True' "$SRC_BACKEND/app/services/neural_research_intelligence.py" || fail "Platform Core authority boundary missing"

echo "=== BACKUP RESEARCH LIBRARIAN ==="
mkdir -p "$BACKUP_ROOT"
stamp="$(date +%Y%m%d-%H%M%S)"
tar -C "$ROOT" -czf "$BACKUP_ROOT/backend-before-v${VERSION}-${stamp}.tgz" backend
cp -a "$COMPOSE" "$BACKUP_ROOT/compose-before-v${VERSION}-${stamp}.yml"
cp -a "$ENV_FILE" "$BACKUP_ROOT/env-before-v${VERSION}-${stamp}"

echo "=== INSTALL v${VERSION} BACKEND ==="
rsync -a \
  --exclude='data/' \
  --exclude='__pycache__/' \
  --exclude='.pytest_cache/' \
  --exclude='*.pyc' \
  --exclude='.env' \
  --exclude='.env.*' \
  "$SRC_BACKEND/" "$LIVE_BACKEND/"

python3 - "$COMPOSE" <<'PYCOMPOSE1210'
from pathlib import Path
import re,sys
p=Path(sys.argv[1])
s=p.read_text()
s=re.sub(r'(?m)^(\s*image:\s*sustainable-catalyst-research-librarian:).*$', r'\g<1>12.1.0', s)
s=re.sub(r'(?m)^(\s*SC_RL_RELEASE_VERSION:\s*)["\']?[^"\'\n]+["\']?\s*$', r'\g<1>"12.1.0"', s)
p.write_text(s)
PYCOMPOSE1210

python3 - "$ENV_FILE" "$CORE_ENV" <<'PYENV1210'
from pathlib import Path
import sys

def parse(path):
    out={}
    try: content=Path(path).read_text()
    except (FileNotFoundError,PermissionError,OSError): return out
    for raw in content.splitlines():
        line=raw.strip()
        if not line or line.startswith('#') or '=' not in line: continue
        k,v=line.split('=',1)
        out[k.strip()]=v.strip().strip('"').strip("'")
    return out

def set_values(path,updates):
    p=Path(path); lines=p.read_text().splitlines(); result=[]; done=set()
    for raw in lines:
        if '=' in raw and not raw.lstrip().startswith('#'):
            k=raw.split('=',1)[0].strip()
            if k in updates:
                result.append(f"{k}={updates[k]}")
                done.add(k); continue
        result.append(raw)
    for k,v in updates.items():
        if k not in done: result.append(f"{k}={v}")
    p.write_text('\n'.join(result).rstrip()+'\n')

rl=parse(sys.argv[1]); core=parse(sys.argv[2])
core_key=core.get('SC_CORE_WRITE_API_KEY','').strip()
rl_key=rl.get('SC_RL_CORE_WRITE_API_KEY','').strip()
if not core_key and not rl_key:
    raise SystemExit('SC_CORE_WRITE_API_KEY is missing and no existing Librarian Core write key is configured.')
if not rl.get('SC_RL_BACKEND_API_KEY','').strip():
    raise SystemExit('SC_RL_BACKEND_API_KEY is required for Independent API administration.')

updates={
    'SC_RL_RELEASE_VERSION':'12.1.0',
    'SC_RL_CORE_ENABLED':'true',
    'SC_RL_CORE_BASE_URL':'http://sc-core:8090',
    'SC_RL_CORE_MINIMUM_VERSION':'3.3.0',
    'SC_RL_CORE_SUPPORTED_MAJOR':'3',
    'SC_RL_CORE_FAIL_CLOSED_WRITES':'true',
    'SC_RL_ASYNC_JOBS_ENABLED':'true',
}
if core_key: updates['SC_RL_CORE_WRITE_API_KEY']=core_key
set_values(sys.argv[1],updates)
print('PASS: Research Librarian v12.1.0 environment aligned (secrets not displayed).')
PYENV1210

cd "$ROOT"
docker compose -f "$COMPOSE" config --quiet

if grep -qE '^[[:space:]]*build:' "$COMPOSE"; then
  docker compose -f "$COMPOSE" build "$SERVICE"
else
  docker build -t "sustainable-catalyst-research-librarian:${VERSION}" "$LIVE_BACKEND"
fi

docker compose -f "$COMPOSE" up -d --force-recreate "$SERVICE"

for i in $(seq 1 90); do
  if curl -fsS http://127.0.0.1:8093/health >"$TMP/health.json" 2>/dev/null && python3 - "$TMP/health.json" <<'PYHEALTH1210' >/dev/null 2>&1
import json,sys
x=json.load(open(sys.argv[1]))
assert x.get('version')=='12.1.0'
assert x.get('ready') is True
assert x.get('runtime_authority')=='python-fastapi-backend'
assert x.get('wordpress_required') is False
assert x.get('identity_sessions') is True
assert x.get('persistent_research_sessions') is True
assert x.get('independent_web_app') is True
assert x.get('independent_deployment_certification') is True
assert x.get('neural_research_intelligence') is True
assert x.get('neural_research_runtime')=='12.1.0'
assert x.get('neural_research_store_backend')=='postgres'
assert x.get('neural_execution_authority') is False
PYHEALTH1210
  then
    break
  fi
  if [[ "$i" == 90 ]]; then
    docker logs --tail=300 "$CONTAINER" >&2 || true
    cat "$TMP/health.json" >&2 2>/dev/null || true
    fail "Research Librarian v12.1.0 did not become ready"
  fi
  sleep 2
done

echo "=== VERIFY v12.1.0 NEURAL RESEARCH INTELLIGENCE FOUNDATION ==="

curl -fsS \
  http://127.0.0.1:8093/v1/research-librarian/neural-research/manifest \
  > "$TMP/neural-manifest.json"

python3 - "$TMP/neural-manifest.json" <<'PYMANIFEST1210'
import json,sys
x=json.load(open(sys.argv[1]))['data']
assert x['release']=='12.1.0'
assert x['milestone']=='12.1.0'
assert x['runtime_authority']=='python-fastapi-backend'
assert x['wordpress_required'] is False
assert x['database_migration']=='041_neural_research_intelligence_foundation.sql'
assert x['execution']['librarian_executes_training'] is False
assert x['execution']['librarian_executes_inference'] is False
assert x['authority']['platform_core_model_contract_authority'] is True
assert x['authority']['specialist_runtime_execution_authority'] is True
assert x['governance']['model_weights_stored'] is False
assert x['governance']['secrets_stored'] is False
assert x['next_boundary']=='multilingual-cross-language-research-intelligence'
PYMANIFEST1210

RL_KEY="$(docker exec "$CONTAINER" printenv SC_RL_BACKEND_API_KEY)"
[[ -n "$RL_KEY" ]] || fail "SC_RL_BACKEND_API_KEY missing in running container"

curl -fsS \
  -H "X-SC-RL-Key: $RL_KEY" \
  http://127.0.0.1:8093/v1/research-librarian/neural-research/capabilities \
  > "$TMP/neural-capabilities.json"

python3 - "$TMP/neural-capabilities.json" <<'PYCAPS1210'
import json,sys
x=json.load(open(sys.argv[1]))['data']
assert x['milestone']=='12.1.0'
assert x['model_provenance'] is True
assert x['dataset_transformation_lineage'] is True
assert x['representation_lineage'] is True
assert x['inference_receipts'] is True
assert x['runtime_handoffs'] is True
assert x['immutable_snapshots'] is True
PYCAPS1210

docker exec -i "$CONTAINER" python - <<'PYVERIFY1210'
from pathlib import Path
import tempfile

from app.main import app
from app.contracts.neural_research_intelligence import (
    NeuralResearchCreateRequest,
    NeuralModelReferenceAddRequest,
    NeuralDatasetReferenceAddRequest,
    NeuralRepresentationReferenceAddRequest,
    NeuralInferenceReceiptAddRequest,
    NeuralRuntimeHandoffPrepareRequest,
    NeuralResearchSnapshotRequest,
)
from app.services.neural_research_intelligence import (
    NeuralResearchIntelligenceStore,
    get_neural_research_intelligence_store,
    neural_manifest,
)
from app.services.independent_research_librarian_api import api_manifest,capabilities
from app.services.independent_deployment_certification import certification_report

prod=get_neural_research_intelligence_store()
assert prod.backend=='postgres'

with prod._postgres() as c:
    tables=[
        'sc_rl_neural_research_projects',
        'sc_rl_neural_research_events',
        'sc_rl_neural_research_snapshots',
    ]
    for table in tables:
        row=c.execute("SELECT to_regclass(%s) AS t",(table,)).fetchone()
        assert row['t'] is not None, table

with tempfile.TemporaryDirectory() as td:
    store=NeuralResearchIntelligenceStore(sqlite_path=Path(td)/'neural.sqlite3')
    project=store.create(NeuralResearchCreateRequest(
        actor_ref='identity:deploy-certification',
        title='v12.1.0 neural foundation certification',
        objective='Certify provenance objects and execution handoff boundaries.',
    ))
    rid=project['neural_research_id']
    project=store.add_model_reference(rid,NeuralModelReferenceAddRequest(
        actor_ref='identity:deploy-certification',
        label='Certification model',
        framework='pytorch',
        model_ref='workspace:model:certification',
        model_hash='sha256:certification-model',
        task_types=['retrieval'],
        checkpoint_ref='workspace:checkpoint:certification',
        core_model_ref='core:neural-model:certification',
    ))
    mid=project['model_references'][0]['model_reference_id']
    project=store.add_dataset_reference(rid,NeuralDatasetReferenceAddRequest(
        actor_ref='identity:deploy-certification',
        label='Certification dataset',
        dataset_ref='library:dataset:certification',
        dataset_hash='sha256:certification-dataset',
        transformation_refs=['workspace:transform:certification'],
        core_dataset_ref='core:dataset:certification',
    ))
    did=project['dataset_references'][0]['dataset_reference_id']
    project=store.add_representation_reference(rid,NeuralRepresentationReferenceAddRequest(
        actor_ref='identity:deploy-certification',
        label='Certification representation',
        source_refs=['library:source:certification'],
        model_reference_id=mid,
        dimensions=16,
        metric='cosine',
        core_embedding_ref='core:embedding:certification',
    ))
    repid=project['representation_references'][0]['representation_reference_id']
    project=store.add_inference_receipt(rid,NeuralInferenceReceiptAddRequest(
        actor_ref='identity:deploy-certification',
        model_reference_id=mid,
        execution_ref='workspace:job:certification',
        runtime_target='workspace',
        output_refs=['workspace:artifact:certification'],
    ))
    assert project['inference_receipts'][0]['execution_performed_by_librarian'] is False
    handoff=store.prepare_handoff(rid,NeuralRuntimeHandoffPrepareRequest(
        actor_ref='identity:deploy-certification',
        target='research-lab',
        operation='evaluation',
        objective='Evaluate certification model.',
        model_reference_ids=[mid],
        dataset_reference_ids=[did],
        representation_reference_ids=[repid],
    ))['handoff']
    assert handoff['execution_performed'] is False
    assert handoff['librarian_executes'] is False
    snap=store.freeze_snapshot(NeuralResearchSnapshotRequest(
        actor_ref='identity:deploy-certification',
        neural_research_id=rid,
    ))
    assert len(snap['snapshot_hash'])==64

paths={getattr(r,'path','') for r in app.routes}
required={
 '/v1/research-librarian/neural-research/manifest',
 '/v1/research-librarian/neural-research/capabilities',
 '/v1/research-librarian/neural-research/projects',
 '/v1/research-librarian/neural-research/projects/{neural_research_id}/models',
 '/v1/research-librarian/neural-research/projects/{neural_research_id}/datasets',
 '/v1/research-librarian/neural-research/projects/{neural_research_id}/representations',
 '/v1/research-librarian/neural-research/projects/{neural_research_id}/inference-receipts',
 '/v1/research-librarian/neural-research/projects/{neural_research_id}/handoffs',
 '/v1/research-librarian/neural-research/projects/{neural_research_id}/lineage',
 '/v1/research-librarian/neural-research/projects/{neural_research_id}/core-candidate',
 '/v1/research-librarian/neural-research/snapshots/freeze',
}
assert not(required-paths), required-paths

m=api_manifest()
c=capabilities()
assert m['scope']['neural_research_intelligence'] is True
assert m['next_boundary']=='multilingual-cross-language-research-intelligence'
assert c['milestone']=='12.1.0'
assert c['neural_research_intelligence'] is True
assert c['neural_runtime_execution'] is False

cert=certification_report(paths)
assert cert['certified'] is True
assert cert['wordpress_required'] is False

print('PASS: migration 041 neural research tables active on Postgres')
print('PASS: model/dataset/representation provenance objects certified')
print('PASS: inference receipts remain external execution observations')
print('PASS: runtime handoffs preserve Workspace/Lab/Workbench execution authority')
print('PASS: Platform Core neural contract authority preserved')
print('PASS: v12.0.8 WordPress-independence certification remains green')
print('PASS: next boundary is v12.2.0 Multilingual & Cross-Language Research Intelligence')
PYVERIFY1210

echo "PASS: Research Librarian AI v12.1.0 Neural Research Intelligence Foundation backend deployed and verified."
echo "NEXT: Install the optional WordPress v12.1.0 package and verify /wp-json/sc-research-librarian-ai/v1/neural-research-foundation."
