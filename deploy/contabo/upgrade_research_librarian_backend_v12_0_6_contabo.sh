#!/usr/bin/env bash
set -Eeuo pipefail

VERSION="12.0.6"
ROOT="/opt/sustainable-catalyst/research-librarian-ai"
LIVE_BACKEND="$ROOT/backend"
COMPOSE="$ROOT/compose.yml"
ENV_FILE="$ROOT/.env.contabo"
CORE_ENV="/opt/sustainable-catalyst/core/.env.production"
CORE_CONTAINER="sc-core"
SERVICE="research-librarian"
CONTAINER="sc-research-librarian"
BACKUP_ROOT="/opt/sustainable-catalyst/backups/research-librarian-ai"
ARCHIVE="${1:-/tmp/sustainable-catalyst-research-librarian-backend-v12.0.6.zip}"
TMP="$(mktemp -d /tmp/sc-rl-v1206.XXXXXX)"
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

grep -q '__version__ = "12.0.6"' "$INIT" || fail "backend package version mismatch"

for f in \
  app/main.py \
  app/api/wordpress_adapter.py \
  app/contracts/thin_wordpress_adapter.py \
  app/services/thin_wordpress_adapter.py \
  tests/test_v1206_thin_wordpress_adapter.py
do
  [[ -f "$SRC_BACKEND/$f" ]] || fail "required v12.0.6 file missing: $f"
done

grep -q '"wordpress_required": False' "$SRC_BACKEND/app/services/thin_wordpress_adapter.py" || fail "WordPress optionality contract missing"
grep -q '"arbitrary_paths_allowed": False' "$SRC_BACKEND/app/services/thin_wordpress_adapter.py" || fail "fixed proxy-path boundary missing"
grep -q '"backend_failure_behavior": "fail-closed-no-wordpress-research-fallback"' "$SRC_BACKEND/app/services/thin_wordpress_adapter.py" || fail "fail-closed adapter boundary missing"
grep -q '"thin_wordpress_adapter": True' "$SRC_BACKEND/app/main.py" || fail "health adapter declaration missing"

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

python3 - "$COMPOSE" <<'PYCOMPOSE1206'
from pathlib import Path
import re,sys
p=Path(sys.argv[1])
s=p.read_text()
s=re.sub(r'(?m)^(\s*image:\s*sustainable-catalyst-research-librarian:).*$', r'\g<1>12.0.6', s)
s=re.sub(r'(?m)^(\s*SC_RL_RELEASE_VERSION:\s*)["\']?[^"\'\n]+["\']?\s*$', r'\g<1>"12.0.6"', s)
p.write_text(s)
PYCOMPOSE1206

python3 - "$ENV_FILE" "$CORE_ENV" <<'PYENV1206'
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
    p=Path(path);lines=p.read_text().splitlines();result=[];done=set()
    for raw in lines:
        if '=' in raw and not raw.lstrip().startswith('#'):
            k=raw.split('=',1)[0].strip()
            if k in updates:
                result.append(f"{k}={updates[k]}")
                done.add(k);continue
        result.append(raw)
    for k,v in updates.items():
        if k not in done:result.append(f"{k}={v}")
    p.write_text('\n'.join(result).rstrip()+'\n')

rl=parse(sys.argv[1]);core=parse(sys.argv[2])
core_key=core.get('SC_CORE_WRITE_API_KEY','').strip()
rl_key=rl.get('SC_RL_CORE_WRITE_API_KEY','').strip()
if not core_key and not rl_key:
    raise SystemExit('SC_CORE_WRITE_API_KEY is missing and no existing Librarian Core write key is configured.')
if not rl.get('SC_RL_BACKEND_API_KEY','').strip():
    raise SystemExit('SC_RL_BACKEND_API_KEY is required for WordPress server integration.')

updates={
    'SC_RL_RELEASE_VERSION':'12.0.6',
    'SC_RL_CORE_ENABLED':'true',
    'SC_RL_CORE_BASE_URL':'http://sc-core:8090',
    'SC_RL_CORE_MINIMUM_VERSION':'3.3.0',
    'SC_RL_CORE_SUPPORTED_MAJOR':'3',
    'SC_RL_CORE_FAIL_CLOSED_WRITES':'true',
    'SC_RL_ASYNC_JOBS_ENABLED':'true',
}
if core_key:updates['SC_RL_CORE_WRITE_API_KEY']=core_key
set_values(sys.argv[1],updates)
print('PASS: Research Librarian v12.0.6 environment aligned (secrets not displayed).')
PYENV1206

cd "$ROOT"
docker compose -f "$COMPOSE" config --quiet

if grep -qE '^[[:space:]]*build:' "$COMPOSE"; then
  docker compose -f "$COMPOSE" build "$SERVICE"
else
  docker build -t "sustainable-catalyst-research-librarian:${VERSION}" "$LIVE_BACKEND"
fi

docker compose -f "$COMPOSE" up -d --force-recreate "$SERVICE"

for i in $(seq 1 90); do
  if curl -fsS http://127.0.0.1:8093/health >"$TMP/health.json" 2>/dev/null && python3 - "$TMP/health.json" <<'PYHEALTH1206' >/dev/null 2>&1
import json,sys
x=json.load(open(sys.argv[1]))
assert x.get('version')=='12.0.6'
assert x.get('ready') is True
assert x.get('runtime_authority')=='python-fastapi-backend'
assert x.get('wordpress_required') is False
assert x.get('identity_sessions') is True
assert x.get('identity_access_runtime')=='12.0.5'
assert x.get('thin_wordpress_adapter') is True
assert x.get('thin_wordpress_adapter_contract')=='2.0'
PYHEALTH1206
  then
    break
  fi

  if [[ "$i" == 90 ]]; then
    docker logs --tail=260 "$CONTAINER" >&2 || true
    cat "$TMP/health.json" >&2 2>/dev/null || true
    fail "Research Librarian v12.0.6 did not become ready"
  fi
  sleep 2
done

echo "=== VERIFY v12.0.6 THIN WORDPRESS ADAPTER ==="

curl -fsS \
  http://127.0.0.1:8093/v1/research-librarian/wordpress-adapter/manifest \
  > "$TMP/adapter-manifest.json"

python3 - "$TMP/adapter-manifest.json" <<'PYMANIFEST1206'
import json,sys
x=json.load(open(sys.argv[1]))['data']
assert x['release']=='12.0.6'
assert x['milestone']=='12.0.6'
assert x['adapter_type']=='optional-wordpress-presentation-proxy'
assert x['backend_authoritative'] is True
assert x['wordpress_required'] is False
assert x['wordpress_runtime_authority'] is False
assert x['wordpress_identity_authority'] is False
assert x['wordpress_session_authority'] is False
assert x['wordpress_canonical_research_state'] is False
assert x['browser_backend_key_exposure'] is False
assert x['proxy_policy']['arbitrary_paths_allowed'] is False
assert x['proxy_policy']['arbitrary_hosts_allowed'] is False
assert x['proxy_policy']['arbitrary_methods_allowed'] is False
assert x['proxy_policy']['fixed_operation_allowlist'] is True
assert x['proxy_policy']['backend_failure_behavior']=='fail-closed-no-wordpress-research-fallback'
assert x['next_boundary']=='wordpress-state-migration-compatibility-layer'
PYMANIFEST1206

docker exec -i "$CONTAINER" python - <<'PYV1206VERIFY'
from app.main import app
from app.services.thin_wordpress_adapter import (
    thin_wordpress_adapter_manifest,
    thin_wordpress_adapter_capabilities,
)
from app.services.independent_research_librarian_api import api_manifest,capabilities

m=thin_wordpress_adapter_manifest()
assert m['release']=='12.0.6'
assert m['wordpress_required'] is False
assert m['wordpress_runtime_authority'] is False
assert m['wordpress_identity_authority'] is False
assert m['wordpress_session_authority'] is False
assert m['wordpress_storage_policy']['canonical_research_state'] is False
assert m['proxy_policy']['fixed_operation_allowlist'] is True
assert m['proxy_policy']['backend_failure_behavior']=='fail-closed-no-wordpress-research-fallback'

c=thin_wordpress_adapter_capabilities()
assert c['milestone']=='12.0.6'
assert c['operation_count'] > 0
assert c['next_boundary']=='wordpress-state-migration-compatibility-layer'

api=api_manifest()
assert api['scope']['identity_sessions'] is True
assert api['scope']['thin_wordpress_adapter'] is True
assert api['next_boundary']=='wordpress-state-migration-compatibility-layer'

caps=capabilities()
assert caps['milestone']=='12.0.6'
assert caps['thin_wordpress_adapter'] is True

paths={getattr(r,'path','') for r in app.routes}
required={
 '/v1/research-librarian/wordpress-adapter/manifest',
 '/v1/research-librarian/wordpress-adapter/capabilities',
 '/v1/research-librarian/auth/login',
 '/v1/research-librarian/sessions',
 '/research-librarian/',
}
assert not(required-paths), required-paths

print('PASS: v12.0.6 backend adapter manifest and Independent API boundary active')
print('PASS: identity/session authority remains in Python; WordPress remains optional')
print('PASS: fixed-operation/fail-closed adapter contract certified')
PYV1206VERIFY

echo "PASS: Research Librarian AI v12.0.6 Thin WordPress Adapter backend deployed and verified."
echo "NEXT: Install the WordPress v12.0.6 package, then verify /wp-json/sc-research-librarian-ai/v1/thin-adapter."
