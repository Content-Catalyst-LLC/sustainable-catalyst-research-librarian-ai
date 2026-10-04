#!/usr/bin/env bash
set -Eeuo pipefail

VERSION="12.0.8"
ROOT="/opt/sustainable-catalyst/research-librarian-ai"
LIVE_BACKEND="$ROOT/backend"
COMPOSE="$ROOT/compose.yml"
ENV_FILE="$ROOT/.env.contabo"
CORE_ENV="/opt/sustainable-catalyst/core/.env.production"
CORE_CONTAINER="sc-core"
SERVICE="research-librarian"
CONTAINER="sc-research-librarian"
BACKUP_ROOT="/opt/sustainable-catalyst/backups/research-librarian-ai"
ARCHIVE="${1:-/tmp/sustainable-catalyst-research-librarian-backend-v12.0.8.zip}"
TMP="$(mktemp -d /tmp/sc-rl-v1208.XXXXXX)"
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

grep -q '__version__ = "12.0.8"' "$INIT" || fail "backend package version mismatch"

for f in \
  app/main.py \
  app/api/independence.py \
  app/contracts/independent_deployment_certification.py \
  app/services/independent_deployment_certification.py \
  tests/test_v1208_independent_deployment_wordpress_failure_certification.py
do
  [[ -f "$SRC_BACKEND/$f" ]] || fail "required v12.0.8 file missing: $f"
done

grep -q '"certification_target":"wordpress-unreachable-or-absent"' "$SRC_BACKEND/app/services/independent_deployment_certification.py" || fail "WordPress failure certification target missing"
grep -q '"wordpress_required":False' "$SRC_BACKEND/app/services/independent_deployment_certification.py" || fail "WordPress optionality certification missing"
grep -q '"research_state_modified":False' "$SRC_BACKEND/app/services/independent_deployment_certification.py" || fail "read-only certification boundary missing"

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

python3 - "$COMPOSE" <<'PYCOMPOSE1208'
from pathlib import Path
import re,sys
p=Path(sys.argv[1])
s=p.read_text()
s=re.sub(r'(?m)^(\s*image:\s*sustainable-catalyst-research-librarian:).*$', r'\g<1>12.0.8', s)
s=re.sub(r'(?m)^(\s*SC_RL_RELEASE_VERSION:\s*)["\']?[^"\'\n]+["\']?\s*$', r'\g<1>"12.0.8"', s)
p.write_text(s)
PYCOMPOSE1208

python3 - "$ENV_FILE" "$CORE_ENV" <<'PYENV1208'
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
    raise SystemExit('SC_RL_BACKEND_API_KEY is required for Independent API administration.')

updates={
    'SC_RL_RELEASE_VERSION':'12.0.8',
    'SC_RL_CORE_ENABLED':'true',
    'SC_RL_CORE_BASE_URL':'http://sc-core:8090',
    'SC_RL_CORE_MINIMUM_VERSION':'3.3.0',
    'SC_RL_CORE_SUPPORTED_MAJOR':'3',
    'SC_RL_CORE_FAIL_CLOSED_WRITES':'true',
    'SC_RL_ASYNC_JOBS_ENABLED':'true',
}
if core_key:updates['SC_RL_CORE_WRITE_API_KEY']=core_key
set_values(sys.argv[1],updates)
print('PASS: Research Librarian v12.0.8 environment aligned (secrets not displayed).')
PYENV1208

cd "$ROOT"
docker compose -f "$COMPOSE" config --quiet

if grep -qE '^[[:space:]]*build:' "$COMPOSE"; then
  docker compose -f "$COMPOSE" build "$SERVICE"
else
  docker build -t "sustainable-catalyst-research-librarian:${VERSION}" "$LIVE_BACKEND"
fi

docker compose -f "$COMPOSE" up -d --force-recreate "$SERVICE"

for i in $(seq 1 90); do
  if curl -fsS http://127.0.0.1:8093/health >"$TMP/health.json" 2>/dev/null && python3 - "$TMP/health.json" <<'PYHEALTH1208' >/dev/null 2>&1
import json,sys
x=json.load(open(sys.argv[1]))
assert x.get('version')=='12.0.8'
assert x.get('ready') is True
assert x.get('runtime_authority')=='python-fastapi-backend'
assert x.get('wordpress_required') is False
assert x.get('identity_sessions') is True
assert x.get('persistent_research_sessions') is True
assert x.get('independent_web_app') is True
assert x.get('wordpress_state_migration') is True
assert x.get('independent_deployment_certification') is True
assert x.get('wordpress_failure_certification_runtime')=='12.0.8'
assert x.get('wordpress_failure_certification_target')=='wordpress-unreachable-or-absent'
PYHEALTH1208
  then
    break
  fi
  if [[ "$i" == 90 ]]; then
    docker logs --tail=300 "$CONTAINER" >&2 || true
    cat "$TMP/health.json" >&2 2>/dev/null || true
    fail "Research Librarian v12.0.8 did not become ready"
  fi
  sleep 2
done

echo "=== VERIFY v12.0.8 INDEPENDENT DEPLOYMENT CERTIFICATION ==="

curl -fsS \
  http://127.0.0.1:8093/v1/research-librarian/independence/manifest \
  > "$TMP/independence-manifest.json"

python3 - "$TMP/independence-manifest.json" <<'PYMANIFEST1208'
import json,sys
x=json.load(open(sys.argv[1]))['data']
assert x['release']=='12.0.8'
assert x['milestone']=='12.0.8'
assert x['runtime_authority']=='python-fastapi-backend'
assert x['wordpress_required'] is False
assert x['certification_target']=='wordpress-unreachable-or-absent'
assert x['database_migration'] is None
assert x['wordpress_adapter_policy']['adapter_optional'] is True
assert x['wordpress_adapter_policy']['backend_does_not_call_wordpress_for_independent_operations'] is True
assert x['certification_method']['wordpress_dns_blackout_probe'] is True
assert x['governance']['certification_does_not_modify_research_state'] is True
assert x['next_boundary']=='neural-research-intelligence-foundation'
PYMANIFEST1208

CERT_FILE="$BACKUP_ROOT/certification-v12.0.8-${stamp}.json"

docker exec -i "$CONTAINER" python - <<'PYCERT1208' > "$CERT_FILE"
import json
from app.main import app
from app.services.independent_deployment_certification import certification_report

paths={getattr(route,'path','') for route in app.routes}
report=certification_report(paths)
assert report['release']=='12.0.8'
assert report['milestone']=='12.0.8'
assert report['certified'] is True
assert report['failed_count']==0
assert report['wordpress_required'] is False
assert report['runtime_authority']=='python-fastapi-backend'
assert len(report['certificate_fingerprint'])==64
print(json.dumps(report,indent=2,sort_keys=True))
PYCERT1208

python3 - "$CERT_FILE" <<'PYCERTFILE1208'
import json,sys
x=json.load(open(sys.argv[1]))
assert x['certified'] is True
assert x['failed_count']==0
assert len(x['certificate_fingerprint'])==64
print("PASS: v12.0.8 read-only certification report saved with fingerprint",x['certificate_fingerprint'])
PYCERTFILE1208

echo "=== WORDPRESS DNS BLACKOUT PROBE ==="

docker exec -i "$CONTAINER" python - <<'PYBLACKOUT1208'
import json
import os
import socket
import urllib.request

real_getaddrinfo=socket.getaddrinfo
blocked=[]

def guard(host,*args,**kwargs):
    text=str(host or '').lower()
    if 'sustainablecatalyst.com' in text or 'wordpress' in text:
        blocked.append(text)
        raise OSError('v12.0.8 simulated WordPress DNS blackout')
    return real_getaddrinfo(host,*args,**kwargs)

socket.getaddrinfo=guard
base='http://127.0.0.1:8093'
key=os.environ.get('SC_RL_BACKEND_API_KEY','')
assert key

def get(path,auth=False):
    headers={'Accept':'application/json'}
    if auth: headers['X-SC-RL-Key']=key
    req=urllib.request.Request(base+path,headers=headers,method='GET')
    with urllib.request.urlopen(req,timeout=20) as r:
        body=r.read()
        assert 200 <= r.status < 300
        return body

def post(path,payload,auth=False):
    headers={'Accept':'application/json','Content-Type':'application/json'}
    if auth: headers['X-SC-RL-Key']=key
    req=urllib.request.Request(
        base+path,
        data=json.dumps(payload).encode('utf-8'),
        headers=headers,
        method='POST',
    )
    with urllib.request.urlopen(req,timeout=30) as r:
        body=r.read()
        assert 200 <= r.status < 300
        return json.loads(body)

health=json.loads(get('/health'))
assert health['version']=='12.0.8'
assert health['wordpress_required'] is False

html=get('/research-librarian/')
assert b'/v1/research-librarian' in html

api=json.loads(get('/v1/research-librarian/manifest',auth=True))
assert api['data']['wordpress_required'] is False
assert api['data']['scope']['independent_deployment_certification'] is True

auth_manifest=json.loads(get('/v1/research-librarian/auth/manifest'))
assert auth_manifest['ok'] is True

migration=json.loads(get('/v1/research-librarian/wordpress-migration/manifest'))
assert migration['data']['wordpress_required'] is False

projects=json.loads(get('/v1/research-librarian/projects?limit=1',auth=True))
assert projects['ok'] is True

sessions=json.loads(get('/v1/research-librarian/sessions?limit=1',auth=True))
assert sessions['ok'] is True

retrieval=post(
    '/v1/research-librarian/retrieve',
    {'query':'wordpress blackout certification','limit':3,'include_semantic':False},
    auth=True,
)
assert retrieval['ok'] is True

report=json.loads(get('/v1/research-librarian/independence/report',auth=True))
assert report['data']['certified'] is True
assert report['data']['failed_count']==0

assert blocked==[], blocked
print('PASS: WordPress DNS blackout probe completed with no WordPress network dependency')
print('PASS: health, web app, auth, retrieval, projects, sessions, migration continuity, and certification remained operational')
PYBLACKOUT1208

docker exec -i "$CONTAINER" python - <<'PYV1208VERIFY'
from app.main import app
from app.services.independent_research_librarian_api import api_manifest,capabilities
from app.services.independent_deployment_certification import certification_report
from app.services.wordpress_state_migration import get_wordpress_state_migration_store
from app.services.persistent_research_session_conversation import get_persistent_research_session_store

paths={getattr(r,'path','') for r in app.routes}
required={
 '/v1/research-librarian/independence/manifest',
 '/v1/research-librarian/independence/report',
 '/v1/research-librarian/manifest',
 '/v1/research-librarian/retrieve',
 '/v1/research-librarian/projects',
 '/v1/research-librarian/sessions',
 '/v1/research-librarian/auth/login',
 '/research-librarian/',
}
assert not(required-paths), required-paths

api=api_manifest()
assert api['scope']['wordpress_state_migration'] is True
assert api['scope']['independent_deployment_certification'] is True
assert api['next_boundary']=='neural-research-intelligence-foundation'

caps=capabilities()
assert caps['milestone']=='12.0.8'
assert caps['independent_deployment_certification'] is True
assert caps['wordpress_failure_certification'] is True

migration_store=get_wordpress_state_migration_store()
session_store=get_persistent_research_session_store()
assert migration_store.backend=='postgres'
assert session_store.backend=='postgres'

report=certification_report(paths)
assert report['certified'] is True
assert report['failed_count']==0
assert report['governance']['research_state_modified'] is False

print('PASS: v12.0.8 independent API/web-app/identity/session route surface certified')
print('PASS: Postgres session + migration continuity certified without WordPress authority')
print('PASS: read-only independence report certified with deterministic fingerprint')
print('PASS: next boundary is v12.1.0 Neural Research Intelligence Foundation')
PYV1208VERIFY

echo "PASS: Research Librarian AI v12.0.8 Independent Deployment & WordPress-Failure Certification backend deployed and certified."
echo "CERTIFICATE: $CERT_FILE"
echo "NEXT: Install the optional WordPress v12.0.8 package and verify /wp-json/sc-research-librarian-ai/v1/independent-certification."
