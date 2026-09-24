#!/usr/bin/env bash
set -Eeuo pipefail
VERSION="9.0.0"
ROOT="/opt/sustainable-catalyst/research-librarian-ai"
LIVE_BACKEND="$ROOT/backend"
COMPOSE="$ROOT/compose.yml"
ENV_FILE="$ROOT/.env.contabo"
CORE_ENV="/opt/sustainable-catalyst/core/.env.production"
CORE_CONTAINER="sc-core"
SERVICE="research-librarian"
CONTAINER="sc-research-librarian"
BACKUP_ROOT="/opt/sustainable-catalyst/backups/research-librarian-ai"
ARCHIVE="${1:-/tmp/sustainable-catalyst-research-librarian-backend-v9.0.0.zip}"
TMP="$(mktemp -d /tmp/sc-rl-v900.XXXXXX)"
trap 'rm -rf "$TMP"' EXIT
fail(){ echo "ERROR: $*" >&2; exit 1; }
for c in docker unzip rsync python3 curl tar grep; do command -v "$c" >/dev/null 2>&1 || fail "$c is required"; done
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
grep -q '__version__ = "9.0.0"' "$INIT" || fail "backend package version mismatch"
for f in \
 app/clients/platform_core.py app/api/core.py app/async_jobs.py app/services/document_jobs.py \
 app/contracts/argument_synthesis.py app/services/argument_synthesis.py tests/test_v8100_argument_synthesis.py \
 app/contracts/statistical_research.py app/services/statistical_research.py tests/test_v8110_statistical_research.py \
 app/contracts/visual_research.py app/services/visual_research.py tests/test_v8120_visual_research.py \
 app/contracts/unified_research_runtime.py app/services/unified_research_runtime.py tests/test_v900_unified_research_runtime.py; do
  [[ -f "$SRC_BACKEND/$f" ]] || fail "required backend file missing: $f"
done
grep -q '"unified-research-runtime"' "$SRC_BACKEND/app/async_jobs.py" || fail "v9.0 unified runtime job type missing"
grep -q '/unified-research/execute' "$SRC_BACKEND/app/api/core.py" || fail "v9.0 unified runtime endpoint missing"

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
s=re.sub(r'(?m)^(\s*image:\s*sustainable-catalyst-research-librarian:).*$', r'\g<1>9.0.0', s)
s=re.sub(r'(?m)^(\s*SC_RL_RELEASE_VERSION:\s*)["\']?[^"\'\n]+["\']?\s*$', r'\g<1>"9.0.0"', s)
p.write_text(s)
PY
python3 - "$ENV_FILE" "$CORE_ENV" <<'PY'
from pathlib import Path
import sys
def parse(path):
    out={}
    for raw in Path(path).read_text().splitlines():
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
updates={'SC_RL_RELEASE_VERSION':'9.0.0','SC_RL_CORE_ENABLED':'true','SC_RL_CORE_BASE_URL':'http://sc-core:8090','SC_RL_CORE_MINIMUM_VERSION':'3.3.0','SC_RL_CORE_SUPPORTED_MAJOR':'3','SC_RL_CORE_FAIL_CLOSED_WRITES':'true','SC_RL_ASYNC_JOBS_ENABLED':'true'}
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
x=json.load(open(sys.argv[1])); assert x.get('version')=='9.0.0' and x.get('ready') is True
PY
  then break; fi
  if [[ "$i" == 90 ]]; then docker logs --tail=240 "$CONTAINER" >&2 || true; cat "$TMP/health.json" >&2 2>/dev/null || true; fail "Research Librarian v9.0.0 did not become ready"; fi
  sleep 2
done
python3 - "$TMP/health.json" <<'PY'
import json,sys
x=json.load(open(sys.argv[1])); assert x.get('version')=='9.0.0' and x.get('ready') is True,x
print('PASS: Research Librarian /health reports 9.0.0 and ready=true')
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

echo "=== VERIFY DURABLE ASYNC JOB RUNTIME ==="
docker exec -i "$CONTAINER" python - <<'PY'
import json,os,urllib.request
from app.async_jobs import JOB_TYPES
assert 'unified-research-runtime' in JOB_TYPES
key=os.environ['SC_RL_BACKEND_API_KEY']
req=urllib.request.Request('http://127.0.0.1:8093/v1/jobs/runtime',headers={'X-SC-RL-Key':key})
with urllib.request.urlopen(req,timeout=35) as r: data=json.load(r)
assert data['schema']=='sc-research-librarian-async-runtime/1.0' and data['durable'] is True,data
if os.environ.get('SC_RL_DATABASE_BACKEND','').lower() in {'postgres','postgresql','neon'}:
    assert data['storage_backend']=='postgres' and data['claim_strategy']=='for-update-skip-locked',data
print('PASS: durable unified research runtime job support active on',data['storage_backend'])
PY

echo "PASS: Research Librarian AI v9.0.0 Unified Research Intelligence Runtime backend deployed and verified."
