#!/usr/bin/env bash
set -Eeuo pipefail

VERSION="12.0.5"
ROOT="/opt/sustainable-catalyst/research-librarian-ai"
LIVE_BACKEND="$ROOT/backend"
COMPOSE="$ROOT/compose.yml"
ENV_FILE="$ROOT/.env.contabo"
CORE_ENV="/opt/sustainable-catalyst/core/.env.production"
CORE_CONTAINER="sc-core"
SERVICE="research-librarian"
CONTAINER="sc-research-librarian"
BACKUP_ROOT="/opt/sustainable-catalyst/backups/research-librarian-ai"
ARCHIVE="${1:-/tmp/sustainable-catalyst-research-librarian-backend-v12.0.5.zip}"
TMP="$(mktemp -d /tmp/sc-rl-v1205.XXXXXX)"
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

grep -q '__version__ = "12.0.5"' "$INIT" || fail "backend package version mismatch"

for f in \
  app/main.py \
  app/api/auth.py \
  app/contracts/identity_session_access.py \
  app/services/identity_session_access.py \
  app/services/independent_web_app.py \
  app/webapp/index.html \
  app/webapp/app.js \
  migrations/039_identity_session_access_runtime.sql \
  tests/test_v1205_identity_session_access_runtime.py
do
  [[ -f "$SRC_BACKEND/$f" ]] || fail "required v12.0.5 file missing: $f"
done

grep -q 'hashlib.scrypt' "$SRC_BACKEND/app/services/identity_session_access.py" || fail "scrypt password hashing missing"
grep -q 'secrets.token_urlsafe(48)' "$SRC_BACKEND/app/services/identity_session_access.py" || fail "opaque session token generation missing"
grep -q 'httponly=True' "$SRC_BACKEND/app/api/auth.py" || fail "HttpOnly identity cookie missing"
grep -q 'samesite="strict"' "$SRC_BACKEND/app/api/auth.py" || fail "SameSite Strict identity cookie missing"
grep -q 'sc_rl_identities' "$SRC_BACKEND/migrations/039_identity_session_access_runtime.sql" || fail "identity migration missing"
grep -q 'sc_rl_identity_sessions' "$SRC_BACKEND/migrations/039_identity_session_access_runtime.sql" || fail "identity-session migration missing"

if grep -qE 'X-SC-RL-Key|SC_RL_BACKEND_API_KEY|localStorage|sessionStorage' "$SRC_BACKEND/app/webapp/app.js"; then
  fail "standalone browser app contains prohibited backend-key or browser-storage dependency"
fi

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

python3 - "$COMPOSE" <<'PYCOMPOSE1205'
from pathlib import Path
import re,sys
p=Path(sys.argv[1])
s=p.read_text()
s=re.sub(r'(?m)^(\s*image:\s*sustainable-catalyst-research-librarian:).*$', r'\g<1>12.0.5', s)
s=re.sub(r'(?m)^(\s*SC_RL_RELEASE_VERSION:\s*)["\']?[^"\'\n]+["\']?\s*$', r'\g<1>"12.0.5"', s)
p.write_text(s)
PYCOMPOSE1205

python3 - "$ENV_FILE" "$CORE_ENV" <<'PYENV1205'
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
    raise SystemExit('SC_RL_BACKEND_API_KEY is required for server integration and identity provisioning.')

updates={
    'SC_RL_RELEASE_VERSION':'12.0.5',
    'SC_RL_CORE_ENABLED':'true',
    'SC_RL_CORE_BASE_URL':'http://sc-core:8090',
    'SC_RL_CORE_MINIMUM_VERSION':'3.3.0',
    'SC_RL_CORE_SUPPORTED_MAJOR':'3',
    'SC_RL_CORE_FAIL_CLOSED_WRITES':'true',
    'SC_RL_ASYNC_JOBS_ENABLED':'true',
    'SC_RL_IDENTITY_SESSION_TTL_SECONDS':'28800',
    'SC_RL_IDENTITY_COOKIE_NAME':'sc_rl_identity_session',
    'SC_RL_IDENTITY_COOKIE_SECURE':'true',
    'SC_RL_IDENTITY_LOGIN_FAILURE_LIMIT':'8',
    'SC_RL_IDENTITY_LOGIN_LOCK_SECONDS':'900',
}
if core_key:updates['SC_RL_CORE_WRITE_API_KEY']=core_key
set_values(sys.argv[1],updates)
print('PASS: Research Librarian identity/access environment aligned (secrets not displayed).')
PYENV1205

cd "$ROOT"
docker compose -f "$COMPOSE" config --quiet

if grep -qE '^[[:space:]]*build:' "$COMPOSE"; then
  docker compose -f "$COMPOSE" build "$SERVICE"
else
  docker build -t "sustainable-catalyst-research-librarian:${VERSION}" "$LIVE_BACKEND"
fi

docker compose -f "$COMPOSE" up -d --force-recreate "$SERVICE"

for i in $(seq 1 90); do
  if curl -fsS http://127.0.0.1:8093/health >"$TMP/health.json" 2>/dev/null && python3 - "$TMP/health.json" <<'PYHEALTH1205' >/dev/null 2>&1
import json,sys
x=json.load(open(sys.argv[1]))
assert x.get('version')=='12.0.5'
assert x.get('ready') is True
assert x.get('runtime_authority')=='python-fastapi-backend'
assert x.get('wordpress_required') is False
assert x.get('independent_api_version')=='v1'
assert x.get('persistent_research_sessions') is True
assert x.get('independent_web_app') is True
assert x.get('identity_sessions') is True
assert x.get('identity_access_runtime')=='12.0.5'
PYHEALTH1205
  then
    break
  fi

  if [[ "$i" == 90 ]]; then
    docker logs --tail=260 "$CONTAINER" >&2 || true
    cat "$TMP/health.json" >&2 2>/dev/null || true
    fail "Research Librarian v12.0.5 did not become ready"
  fi
  sleep 2
done

echo "=== VERIFY v12.0.5 IDENTITY, SESSION & ACCESS RUNTIME ==="
curl -fsS http://127.0.0.1:8093/research-librarian/ > "$TMP/app.html"
curl -fsS http://127.0.0.1:8093/research-librarian/app-manifest.json > "$TMP/app-manifest.json"
curl -fsS http://127.0.0.1:8093/research-librarian/assets/app.js > "$TMP/app.js"
curl -fsS http://127.0.0.1:8093/v1/research-librarian/auth/manifest > "$TMP/auth-manifest.json"

grep -q 'IDENTITY, SESSION & ACCESS RUNTIME' "$TMP/app.html" || fail "identity-aware web app marker missing"
grep -q '/auth/login' "$TMP/app.js" || fail "browser login runtime missing"
grep -q '/auth/me' "$TMP/app.js" || fail "browser current-identity runtime missing"
if grep -qE 'X-SC-RL-Key|SC_RL_BACKEND_API_KEY|localStorage|sessionStorage' "$TMP/app.js"; then
  fail "live browser JavaScript contains prohibited backend-key or browser-storage dependency"
fi

python3 - "$TMP/app-manifest.json" "$TMP/auth-manifest.json" <<'PYMANIFEST1205'
import json,sys
app=json.load(open(sys.argv[1]))
auth=json.load(open(sys.argv[2]))['data']
assert app['release']=='12.0.5'
assert app['milestone']=='12.0.5'
assert app['wordpress_required'] is False
assert app['authentication']['mode']=='backend-identity-session'
assert app['authentication']['production_user_identity'] is True
assert app['authentication']['backend_api_key_embedded'] is False
assert app['browser_state_policy']['identity_cookie_http_only'] is True
assert app['next_boundary']=='thin-wordpress-adapter'
assert auth['release']=='12.0.5'
assert auth['password_hash']=='scrypt'
assert auth['session_token_storage']=='sha256-hash-only'
assert auth['cookie_http_only'] is True
assert auth['cookie_same_site']=='strict'
assert auth['wordpress_required'] is False
assert auth['legacy_api_key_supported'] is True
PYMANIFEST1205

docker exec -i "$CONTAINER" python - <<'PYV1205VERIFY'
from app.main import app
from app.services.identity_session_access import get_identity_session_store
from app.services.independent_web_app import web_app_manifest
from app.services.independent_research_librarian_api import api_manifest, capabilities

store=get_identity_session_store()
assert store.backend=='postgres'
cap=store.capabilities()
assert cap['release']=='12.0.5'
assert cap['password_hash']=='scrypt'
assert cap['session_token_storage']=='sha256-hash-only'
assert cap['wordpress_required'] is False

with store._postgres() as c:
    row=c.execute("""
      SELECT
        to_regclass('sc_rl_identities') IS NOT NULL AS identities,
        to_regclass('sc_rl_identity_sessions') IS NOT NULL AS sessions,
        to_regclass('sc_rl_identity_access_events') IS NOT NULL AS events
    """).fetchone()
    assert row['identities'] and row['sessions'] and row['events']

m=web_app_manifest()
assert m['release']=='12.0.5'
assert m['authentication']['production_user_identity'] is True
assert m['authentication']['backend_api_key_embedded'] is False
assert m['capabilities']['identity_owned_sessions'] is True

api=api_manifest()
assert api['scope']['persistent_conversations'] is True
assert api['scope']['identity_sessions'] is True
assert api['next_boundary']=='thin-wordpress-adapter'

c=capabilities()
assert c['milestone']=='12.0.5'
assert c['identity_sessions'] is True

paths={getattr(r,'path','') for r in app.routes}
required={
 '/v1/research-librarian/auth/manifest',
 '/v1/research-librarian/auth/login',
 '/v1/research-librarian/auth/logout',
 '/v1/research-librarian/auth/me',
 '/v1/research-librarian/auth/provision',
 '/research-librarian/',
}
assert not(required-paths), required-paths

print('PASS: v12.0.5 durable identity/session tables active on Postgres')
print('PASS: authenticated research access + identity-owned research-session boundary active')
print('PASS: browser backend-key bridge removed; WordPress remains optional')
PYV1205VERIFY

echo "PASS: Research Librarian AI v12.0.5 Identity, Session & Access Runtime backend deployed and verified."
echo "NEXT: Provision the first owner identity if identity_count is 0, then install the WordPress v12.0.5 package."
