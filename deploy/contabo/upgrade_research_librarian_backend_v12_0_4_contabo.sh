#!/usr/bin/env bash
set -Eeuo pipefail

VERSION="12.0.4"
ROOT="/opt/sustainable-catalyst/research-librarian-ai"
LIVE_BACKEND="$ROOT/backend"
COMPOSE="$ROOT/compose.yml"
ENV_FILE="$ROOT/.env.contabo"
CORE_ENV="/opt/sustainable-catalyst/core/.env.production"
CORE_CONTAINER="sc-core"
SERVICE="research-librarian"
CONTAINER="sc-research-librarian"
BACKUP_ROOT="/opt/sustainable-catalyst/backups/research-librarian-ai"
ARCHIVE="${1:-/tmp/sustainable-catalyst-research-librarian-backend-v12.0.4.zip}"
TMP="$(mktemp -d /tmp/sc-rl-v1204.XXXXXX)"
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

grep -q '__version__ = "12.0.4"' "$INIT" || fail "backend package version mismatch"

for f in \
  app/main.py \
  app/api/webapp.py \
  app/contracts/independent_web_app.py \
  app/services/independent_web_app.py \
  app/webapp/index.html \
  app/webapp/app.css \
  app/webapp/app.js \
  tests/test_v1204_independent_web_app_foundation.py
do
  [[ -f "$SRC_BACKEND/$f" ]] || fail "required v12.0.4 file missing: $f"
done

grep -q '/research-librarian/' "$SRC_BACKEND/app/api/webapp.py" || fail "web-app route missing"
grep -q '"wordpress_required": False' "$SRC_BACKEND/app/services/independent_web_app.py" || fail "WordPress-independence contract missing"
grep -q '"independent_web_app": True' "$SRC_BACKEND/app/main.py" || fail "health web-app declaration missing"
if grep -q 'SC_RL_BACKEND_API_KEY' "$SRC_BACKEND/app/webapp/app.js"; then
  fail "browser JavaScript contains backend environment secret name"
fi
if grep -qE 'localStorage|sessionStorage|document\.cookie' "$SRC_BACKEND/app/webapp/app.js"; then
  fail "browser JavaScript contains prohibited credential/state persistence"
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

python3 - "$COMPOSE" <<'PYCOMPOSE1204'
from pathlib import Path
import re,sys
p=Path(sys.argv[1])
s=p.read_text()
s=re.sub(r'(?m)^(\s*image:\s*sustainable-catalyst-research-librarian:).*$', r'\g<1>12.0.4', s)
s=re.sub(r'(?m)^(\s*SC_RL_RELEASE_VERSION:\s*)["\']?[^"\'\n]+["\']?\s*$', r'\g<1>"12.0.4"', s)
p.write_text(s)
PYCOMPOSE1204

python3 - "$ENV_FILE" "$CORE_ENV" <<'PYENV1204'
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
                done.add(k)
                continue
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
    'SC_RL_RELEASE_VERSION':'12.0.4',
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
PYENV1204

cd "$ROOT"
docker compose -f "$COMPOSE" config --quiet

if grep -qE '^[[:space:]]*build:' "$COMPOSE"; then
  docker compose -f "$COMPOSE" build "$SERVICE"
else
  docker build -t "sustainable-catalyst-research-librarian:${VERSION}" "$LIVE_BACKEND"
fi

docker compose -f "$COMPOSE" up -d --force-recreate "$SERVICE"

for i in $(seq 1 90); do
  if curl -fsS http://127.0.0.1:8093/health >"$TMP/health.json" 2>/dev/null && python3 - "$TMP/health.json" <<'PYHEALTH1204' >/dev/null 2>&1
import json,sys
x=json.load(open(sys.argv[1]))
assert x.get('version')=='12.0.4'
assert x.get('ready') is True
assert x.get('runtime_authority')=='python-fastapi-backend'
assert x.get('wordpress_required') is False
assert x.get('independent_api_version')=='v1'
assert x.get('persistent_research_sessions') is True
assert x.get('independent_web_app') is True
assert x.get('independent_web_app_path')=='/research-librarian/'
PYHEALTH1204
  then
    break
  fi

  if [[ "$i" == 90 ]]; then
    docker logs --tail=240 "$CONTAINER" >&2 || true
    cat "$TMP/health.json" >&2 2>/dev/null || true
    fail "Research Librarian v12.0.4 did not become ready"
  fi
  sleep 2
done

echo "=== VERIFY v12.0.4 INDEPENDENT WEB APP ==="
curl -fsS http://127.0.0.1:8093/research-librarian/ > "$TMP/app.html"
curl -fsS http://127.0.0.1:8093/research-librarian/app-manifest.json > "$TMP/app-manifest.json"
curl -fsS http://127.0.0.1:8093/research-librarian/assets/app.js > "$TMP/app.js"
curl -fsS http://127.0.0.1:8093/research-librarian/assets/app.css > "$TMP/app.css"

grep -q 'Independent Web App Foundation' "$TMP/app.html" || fail "standalone HTML shell missing expected release marker"
grep -q '/v1/research-librarian' "$TMP/app.html" || fail "standalone HTML shell missing independent API reference"

python3 - "$TMP/app-manifest.json" <<'PYMANIFEST1204'
import json,sys
x=json.load(open(sys.argv[1]))
assert x['release']=='12.0.4'
assert x['milestone']=='12.0.4'
assert x['entry_path']=='/research-librarian/'
assert x['api_base']=='/v1/research-librarian'
assert x['runtime_authority']=='python-fastapi-backend'
assert x['wordpress_required'] is False
assert x['canonical_state_location']=='python-postgres-backend'
assert x['browser_state_policy']['local_storage_used'] is False
assert x['browser_state_policy']['embedded_backend_secret'] is False
assert x['authentication']['key_embedded_in_app'] is False
assert x['authentication']['production_user_identity'] is False
assert x['next_boundary']=='identity-session-access-runtime'
PYMANIFEST1204

if grep -q 'SC_RL_BACKEND_API_KEY' "$TMP/app.js"; then
  fail "live browser JavaScript contains backend environment secret name"
fi
if grep -qE 'localStorage|sessionStorage|document\.cookie' "$TMP/app.js"; then
  fail "live browser JavaScript contains prohibited credential/state persistence"
fi

docker exec -i "$CONTAINER" python - <<'PYV1204VERIFY'
from app.main import app
from app.services.independent_web_app import web_app_manifest, web_app_capabilities
from app.services.independent_research_librarian_api import api_manifest, capabilities

m=web_app_manifest()
assert m['release']=='12.0.4'
assert m['wordpress_required'] is False
assert m['capabilities']['persistent_session_browser'] is True
assert m['capabilities']['retrieval'] is True
assert m['capabilities']['end_user_login'] is False

c=web_app_capabilities()
assert c['milestone']=='12.0.4'
assert c['standalone_browser_shell'] is True
assert c['browser_canonical_state'] is False
assert c['identity_sessions'] is False

api=api_manifest()
assert api['scope']['persistent_conversations'] is True
assert api['scope']['independent_web_app'] is True
assert api['scope']['identity_sessions'] is False
assert api['next_boundary']=='identity-session-access-runtime'

cap=capabilities()
assert cap['milestone']=='12.0.4'
assert cap['independent_web_app'] is True

paths={getattr(r,'path','') for r in app.routes}
required={
 '/research-librarian',
 '/research-librarian/',
 '/research-librarian/app-manifest.json',
 '/research-librarian/capabilities.json',
 '/research-librarian/assets/app.css',
 '/research-librarian/assets/app.js',
}
assert not(required-paths), required-paths

print('PASS: v12.0.4 standalone web-app routes and authority boundaries active')
print('PASS: canonical research state remains in backend; WordPress is optional')
print('PASS: identity/session access remains deferred to v12.0.5')
PYV1204VERIFY

echo "PASS: Research Librarian AI v12.0.4 Independent Web App Foundation backend deployed and verified."
