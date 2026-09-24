#!/usr/bin/env bash
set -Eeuo pipefail
VERSION="8.12.0"
ROOT="${SC_TARGET_ROOT:-/opt/sustainable-catalyst/research-librarian-ai}"
LIVE_BACKEND="$ROOT/backend"
COMPOSE="${SC_TARGET_COMPOSE:-$ROOT/compose.yml}"
SERVICE="${SC_TARGET_SERVICE:-research-librarian}"
CONTAINER="${SC_TARGET_CONTAINER:-sc-research-librarian}"
CORE_ROOT="${SC_CORE_ROOT:-/opt/sustainable-catalyst/core}"
CORE_CONTAINER="${SC_CORE_CONTAINER:-sc-core}"
CORE_ENV="${SC_CORE_ENV:-$CORE_ROOT/.env.production}"
ENV_FILE="${SC_RL_ENV_FILE:-$ROOT/.env.contabo}"
ARCHIVE="${1:-/tmp/sustainable-catalyst-research-librarian-backend-v8.12.0.zip}"
BACKUP_ROOT="/opt/sustainable-catalyst/backups/research-librarian-v8120"
TMP="$(mktemp -d /tmp/sc-rl-v8120.XXXXXX)"
trap 'rm -rf "$TMP"' EXIT
fail(){ echo "ERROR: $*" >&2; exit 1; }
for cmd in unzip rsync docker python3 tar grep curl; do command -v "$cmd" >/dev/null || fail "$cmd is required"; done
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
grep -q '__version__ = "8.12.0"' "$INIT" || fail "backend package version mismatch"
for f in \
 app/clients/platform_core.py app/api/core.py app/async_jobs.py app/services/document_jobs.py \
 app/contracts/argument_synthesis.py app/services/argument_synthesis.py tests/test_v8100_argument_synthesis.py \
 app/contracts/statistical_research.py app/services/statistical_research.py tests/test_v8110_statistical_research.py \
 app/contracts/visual_research.py app/services/visual_research.py tests/test_v8120_visual_research.py; do
  [[ -f "$SRC_BACKEND/$f" ]] || fail "required backend file missing: $f"
done
grep -q '"visual-research-plan"' "$SRC_BACKEND/app/async_jobs.py" || fail "v8.12 visual-research-plan job type missing"
grep -q '/v1/visual-reasoning/objects' "$SRC_BACKEND/app/clients/platform_core.py" || fail "Core visual object client missing"
grep -q '/v1/research/unified-runtime/visual-bindings' "$SRC_BACKEND/app/clients/platform_core.py" || fail "Core unified visual binding client missing"

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
s=re.sub(r'(?m)^(\s*image:\s*sustainable-catalyst-research-librarian:).*$', r'\g<1>8.12.0', s)
s=re.sub(r'(?m)^(\s*SC_RL_RELEASE_VERSION:\s*)["\']?[^"\'\n]+["\']?\s*$', r'\g<1>"8.12.0"', s)
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
updates={'SC_RL_RELEASE_VERSION':'8.12.0','SC_RL_CORE_ENABLED':'true','SC_RL_CORE_BASE_URL':'http://sc-core:8090','SC_RL_CORE_MINIMUM_VERSION':'3.3.0','SC_RL_CORE_SUPPORTED_MAJOR':'3','SC_RL_CORE_FAIL_CLOSED_WRITES':'true','SC_RL_ASYNC_JOBS_ENABLED':'true'}
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
x=json.load(open(sys.argv[1])); assert x.get('version')=='8.12.0' and x.get('ready') is True
PY
  then break; fi
  if [[ "$i" == 90 ]]; then docker logs --tail=240 "$CONTAINER" >&2 || true; cat "$TMP/health.json" >&2 2>/dev/null || true; fail "Research Librarian v8.12.0 did not become ready"; fi
  sleep 2
done
python3 - "$TMP/health.json" <<'PY'
import json,sys
x=json.load(open(sys.argv[1])); assert x.get('version')=='8.12.0' and x.get('ready') is True,x
print('PASS: Research Librarian /health reports 8.12.0 and ready=true')
PY

echo "=== VERIFY PLATFORM CORE + VISUAL CONTRACTS ==="
docker exec -i "$CONTAINER" python - <<'PY'
import asyncio
from app.clients.platform_core import PlatformCoreClient
async def main():
    c=PlatformCoreClient()
    h=await c.health(); version=str(h.get('version') or '')
    parts=tuple(int(x) for x in version.split('.')[:3]); assert parts[0]==3 and parts>=(3,3,0),h
    v=await c.visual_reasoning_readiness(); u=await c.unified_visual_reasoning_readiness()
    assert v.get('renderer_neutral') is True,v
    assert v.get('automatic_truth_promotion') is False,v
    if 'contract' in u: assert u.get('contract')=='sc.visual-runtime.unified-reasoning.v1',u
    print('PASS: Platform Core',version,'Visual Reasoning Object Model reachable and renderer-neutral')
    print('PASS: Platform Core Unified Visual Reasoning reachable')
asyncio.run(main())
PY

echo "=== VERIFY v8.12 VISUAL RESEARCH INTELLIGENCE ==="
docker exec -i "$CONTAINER" python - <<'PY'
from app.contracts.visual_research import VISUAL_RESEARCH_SCHEMA, VisualResearchPlanRequest
from app.services.visual_research import capabilities, build_plan
from app.main import app
paths={getattr(r,'path',None) for r in app.routes}
required={'/v1/core/visual-research/capabilities','/v1/core/visual-research/readiness','/v1/core/visual-research/plan','/v1/core/visual-research/promote'}
assert not (required-paths), required-paths
cap=capabilities(); assert VISUAL_RESEARCH_SCHEMA=='sc-research-librarian-visual-research-intelligence/1.0'
assert cap['renderer_neutral_specs'] is True and cap['explicit_relation_only'] is True
assert cap['librarian_renders_visuals'] is False and cap['automatic_visual_truth_promotion'] is False
req=VisualResearchPlanRequest(core_project_id='smoke-project',core_session_id='smoke-session',title='Smoke visual',entities=[{'local_ref':'source-1','entity_type':'source','core_object_id':'core-source-1','label':'Source 1'},{'local_ref':'claim-1','entity_type':'claim','core_object_id':'core-claim-1','label':'Claim 1'}],relations=[{'relation_ref':'rel-1','source_local_ref':'source-1','target_local_ref':'claim-1','relation':'supports'}])
plan=build_plan(req)['plan']; assert plan['review_decision']=='pending'; assert plan['relations'][0]['relation_supplied_explicitly'] is True; assert plan['renderer_policy']['layout_computed_by_librarian'] is False
print('PASS: v8.12 renderer-neutral visual planning + human review gate active')
PY

echo "=== VERIFY DURABLE ASYNC JOB RUNTIME ==="
docker exec -i "$CONTAINER" python - <<'PY'
import json,os,urllib.request
key=os.environ['SC_RL_BACKEND_API_KEY']
req=urllib.request.Request('http://127.0.0.1:8093/v1/jobs/runtime',headers={'X-SC-RL-Key':key})
with urllib.request.urlopen(req,timeout=35) as r: data=json.load(r)
assert data['schema']=='sc-research-librarian-async-runtime/1.0' and data['durable'] is True,data
if os.environ.get('SC_RL_DATABASE_BACKEND','').lower() in {'postgres','postgresql','neon'}:
    assert data['storage_backend']=='postgres' and data['claim_strategy']=='for-update-skip-locked',data
print('PASS: durable async job runtime active on',data['storage_backend'])
PY

echo "PASS: Research Librarian AI v8.12.0 Visual Research Intelligence backend deployed and verified."
