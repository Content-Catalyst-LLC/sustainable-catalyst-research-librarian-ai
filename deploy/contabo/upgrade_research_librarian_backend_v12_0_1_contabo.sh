#!/usr/bin/env bash
set -Eeuo pipefail

VERSION="12.0.1"
ROOT="/opt/sustainable-catalyst/research-librarian-ai"
LIVE_BACKEND="$ROOT/backend"
COMPOSE="$ROOT/compose.yml"
ENV_FILE="$ROOT/.env.contabo"
CORE_ENV="/opt/sustainable-catalyst/core/.env.production"
CORE_CONTAINER="sc-core"
SERVICE="research-librarian"
CONTAINER="sc-research-librarian"
BACKUP_ROOT="/opt/sustainable-catalyst/backups/research-librarian-ai"
ARCHIVE="${1:-/tmp/sustainable-catalyst-research-librarian-backend-v12.0.1.zip}"
TMP="$(mktemp -d /tmp/sc-rl-v1201.XXXXXX)"
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

grep -q '__version__ = "12.0.1"' "$INIT" || fail "backend package version mismatch"

for f in   app/main.py   app/api/core.py   app/contracts/runtime_authority_wordpress_decoupling.py   app/services/runtime_authority_wordpress_decoupling.py   tests/test_v1201_runtime_authority_wordpress_decoupling.py   migrations/036_runtime_authority_wordpress_decoupling.sql
do
  [[ -f "$SRC_BACKEND/$f" ]] || fail "required backend file missing: $f"
done

grep -q 'RUNTIME_AUTHORITY_SCHEMA' "$SRC_BACKEND/app/contracts/runtime_authority_wordpress_decoupling.py" || fail "runtime-authority contract missing"
grep -q '/runtime-authority/manifest' "$SRC_BACKEND/app/api/core.py" || fail "runtime-authority manifest API missing"
grep -q '"runtime_authority": "python-fastapi-backend"' "$SRC_BACKEND/app/main.py" || fail "health runtime-authority declaration missing"
grep -q '"wordpress_required": False' "$SRC_BACKEND/app/main.py" || fail "health WordPress optionality declaration missing"

echo "=== BACKUP RESEARCH LIBRARIAN ==="
mkdir -p "$BACKUP_ROOT"
stamp="$(date +%Y%m%d-%H%M%S)"
tar -C "$ROOT" -czf "$BACKUP_ROOT/backend-before-v${VERSION}-${stamp}.tgz" backend
cp -a "$COMPOSE" "$BACKUP_ROOT/compose-before-v${VERSION}-${stamp}.yml"
cp -a "$ENV_FILE" "$BACKUP_ROOT/env-before-v${VERSION}-${stamp}"

echo "=== INSTALL v${VERSION} BACKEND ==="
rsync -a   --exclude='data/'   --exclude='__pycache__/'   --exclude='.pytest_cache/'   --exclude='*.pyc'   --exclude='.env'   --exclude='.env.*'   "$SRC_BACKEND/" "$LIVE_BACKEND/"

python3 - "$COMPOSE" <<'PYCOMPOSE1201'
from pathlib import Path
import re,sys
p=Path(sys.argv[1])
s=p.read_text()
s=re.sub(r'(?m)^(\s*image:\s*sustainable-catalyst-research-librarian:).*$', r'\g<1>12.0.1', s)
s=re.sub(r'(?m)^(\s*SC_RL_RELEASE_VERSION:\s*)["\']?[^"\'\n]+["\']?\s*$', r'\g<1>"12.0.1"', s)
p.write_text(s)
PYCOMPOSE1201

python3 - "$ENV_FILE" "$CORE_ENV" <<'PYENV1201'
from pathlib import Path
import sys
def parse(path):
    out={}
    try: content=Path(path).read_text()
    except (FileNotFoundError,PermissionError,OSError): return out
    for raw in content.splitlines():
        line=raw.strip()
        if not line or line.startswith('#') or '=' not in line: continue
        k,v=line.split('=',1); out[k.strip()]=v.strip().strip('"').strip("'")
    return out
def set_values(path,updates):
    p=Path(path); lines=p.read_text().splitlines(); result=[]; done=set()
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
    raise SystemExit('SC_CORE_WRITE_API_KEY is missing and no existing Librarian Core write key is configured.')
updates={
    'SC_RL_RELEASE_VERSION':'12.0.1',
    'SC_RL_CORE_ENABLED':'true',
    'SC_RL_CORE_BASE_URL':'http://sc-core:8090',
    'SC_RL_CORE_MINIMUM_VERSION':'3.3.0',
    'SC_RL_CORE_SUPPORTED_MAJOR':'3',
    'SC_RL_CORE_FAIL_CLOSED_WRITES':'true',
    'SC_RL_ASYNC_JOBS_ENABLED':'true',
}
if core_key: updates['SC_RL_CORE_WRITE_API_KEY']=core_key
set_values(sys.argv[1],updates)
print('PASS: Research Librarian environment aligned (secret not displayed).')
PYENV1201

cd "$ROOT"
docker compose -f "$COMPOSE" config --quiet

if grep -qE '^[[:space:]]*build:' "$COMPOSE"; then
  docker compose -f "$COMPOSE" build "$SERVICE"
else
  docker build -t "sustainable-catalyst-research-librarian:${VERSION}" "$LIVE_BACKEND"
fi

docker compose -f "$COMPOSE" up -d --force-recreate "$SERVICE"

for i in $(seq 1 90); do
  if curl -fsS http://127.0.0.1:8093/health >"$TMP/health.json" 2>/dev/null && python3 - "$TMP/health.json" <<'PYHEALTH1201' >/dev/null 2>&1
import json,sys
x=json.load(open(sys.argv[1]))
assert x.get('version')=='12.0.1'
assert x.get('ready') is True
assert x.get('runtime_authority')=='python-fastapi-backend'
assert x.get('wordpress_required') is False
PYHEALTH1201
  then
    break
  fi
  if [[ "$i" == 90 ]]; then
    docker logs --tail=240 "$CONTAINER" >&2 || true
    cat "$TMP/health.json" >&2 2>/dev/null || true
    fail "Research Librarian v12.0.1 did not become ready"
  fi
  sleep 2
done

echo "=== VERIFY v12.0.1 RUNTIME AUTHORITY & WORDPRESS DECOUPLING FOUNDATION ==="
docker exec -i "$CONTAINER" python - <<'PYV1201VERIFY'
import os
from app.services.runtime_authority_wordpress_decoupling import (
    capabilities,
    runtime_authority_manifest,
    wordpress_adapter_contract,
    dependency_map,
    independence_readiness,
    RuntimeAuthorityCertificationStore,
)
from app.main import app

cap=capabilities()
assert cap['milestone']=='12.0.1'
assert cap['python_runtime_authority'] is True
assert cap['wordpress_optional_interface'] is True
assert cap['wordpress_required_for_backend_runtime'] is False
assert cap['automatic_data_migration'] is False
assert cap['automatic_cutover'] is False

manifest=runtime_authority_manifest()
assert manifest['runtime_authority']=='python-fastapi-backend'
assert manifest['wordpress_required_for_backend_boot'] is False
assert manifest['wordpress_required_for_backend_health'] is False
assert manifest['wordpress_required_for_research_api'] is False
assert manifest['wordpress_required_for_persistence'] is False

adapter=wordpress_adapter_contract()
assert adapter['adapter_type']=='optional-wordpress-interface'
assert adapter['backend_is_source_of_runtime_truth'] is True
assert adapter['failure_behavior']['wordpress_unavailable']=='backend-remains-operational'

deps=dependency_map()
assert deps['wordpress_is_runtime_dependency'] is False

ready=independence_readiness()
assert ready['ready_for_progressive_wordpress_decoupling'] is True
assert ready['blockers']==[]
assert ready['next_boundary']=='independent-research-librarian-api-v1'

paths={getattr(r,'path','') for r in app.routes}
required={
  '/v1/core/runtime-authority/capabilities',
  '/v1/core/runtime-authority/manifest',
  '/v1/core/runtime-authority/wordpress-adapter-contract',
  '/v1/core/runtime-authority/dependency-map',
  '/v1/core/runtime-authority/independence-readiness',
  '/v1/core/runtime-authority/snapshots/freeze',
}
assert not(required-paths),required-paths

store=RuntimeAuthorityCertificationStore()
if os.environ.get('SC_RL_DATABASE_BACKEND','').lower() in {'postgres','postgresql','neon'}:
    assert store.backend=='postgres'

print('PASS: v12.0.1 runtime authority foundation active on',store.backend)
print('PASS: Python backend authoritative; WordPress classified as optional thin adapter')
PYV1201VERIFY

echo "PASS: Research Librarian AI v12.0.1 Runtime Authority & WordPress Decoupling Foundation backend deployed and verified."
