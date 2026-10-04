#!/usr/bin/env bash
set -Eeuo pipefail

VERSION="12.0.7"
ROOT="/opt/sustainable-catalyst/research-librarian-ai"
LIVE_BACKEND="$ROOT/backend"
COMPOSE="$ROOT/compose.yml"
ENV_FILE="$ROOT/.env.contabo"
CORE_ENV="/opt/sustainable-catalyst/core/.env.production"
CORE_CONTAINER="sc-core"
SERVICE="research-librarian"
CONTAINER="sc-research-librarian"
BACKUP_ROOT="/opt/sustainable-catalyst/backups/research-librarian-ai"
ARCHIVE="${1:-/tmp/sustainable-catalyst-research-librarian-backend-v12.0.7.zip}"
TMP="$(mktemp -d /tmp/sc-rl-v1207.XXXXXX)"
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

grep -q '__version__ = "12.0.7"' "$INIT" || fail "backend package version mismatch"

for f in \
  app/main.py \
  app/api/wordpress_migration.py \
  app/contracts/wordpress_state_migration.py \
  app/services/wordpress_state_migration.py \
  app/services/persistent_research_session_conversation.py \
  migrations/040_wordpress_state_migration_compatibility.sql \
  tests/test_v1207_wordpress_state_migration_compatibility.py
do
  [[ -f "$SRC_BACKEND/$f" ]] || fail "required v12.0.7 file missing: $f"
done

grep -q '"automatic_migration":False' "$SRC_BACKEND/app/services/wordpress_state_migration.py" || fail "explicit migration boundary missing"
grep -q '"legacy_state_not_deleted":True' "$SRC_BACKEND/app/services/wordpress_state_migration.py" || fail "legacy-state preservation boundary missing"
grep -q '"conflicts_fail_closed":True' "$SRC_BACKEND/app/services/wordpress_state_migration.py" || fail "conflict fail-closed boundary missing"
grep -q 'requested_turn_id' "$SRC_BACKEND/app/services/persistent_research_session_conversation.py" || fail "idempotent turn migration support missing"

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

python3 - "$COMPOSE" <<'PYCOMPOSE1207'
from pathlib import Path
import re,sys
p=Path(sys.argv[1])
s=p.read_text()
s=re.sub(r'(?m)^(\s*image:\s*sustainable-catalyst-research-librarian:).*$', r'\g<1>12.0.7', s)
s=re.sub(r'(?m)^(\s*SC_RL_RELEASE_VERSION:\s*)["\']?[^"\'\n]+["\']?\s*$', r'\g<1>"12.0.7"', s)
p.write_text(s)
PYCOMPOSE1207

python3 - "$ENV_FILE" "$CORE_ENV" <<'PYENV1207'
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
    raise SystemExit('SC_RL_BACKEND_API_KEY is required for WordPress migration server integration.')

updates={
    'SC_RL_RELEASE_VERSION':'12.0.7',
    'SC_RL_CORE_ENABLED':'true',
    'SC_RL_CORE_BASE_URL':'http://sc-core:8090',
    'SC_RL_CORE_MINIMUM_VERSION':'3.3.0',
    'SC_RL_CORE_SUPPORTED_MAJOR':'3',
    'SC_RL_CORE_FAIL_CLOSED_WRITES':'true',
    'SC_RL_ASYNC_JOBS_ENABLED':'true',
}
if core_key:updates['SC_RL_CORE_WRITE_API_KEY']=core_key
set_values(sys.argv[1],updates)
print('PASS: Research Librarian v12.0.7 environment aligned (secrets not displayed).')
PYENV1207

cd "$ROOT"
docker compose -f "$COMPOSE" config --quiet

if grep -qE '^[[:space:]]*build:' "$COMPOSE"; then
  docker compose -f "$COMPOSE" build "$SERVICE"
else
  docker build -t "sustainable-catalyst-research-librarian:${VERSION}" "$LIVE_BACKEND"
fi

docker compose -f "$COMPOSE" up -d --force-recreate "$SERVICE"

for i in $(seq 1 90); do
  if curl -fsS http://127.0.0.1:8093/health >"$TMP/health.json" 2>/dev/null && python3 - "$TMP/health.json" <<'PYHEALTH1207' >/dev/null 2>&1
import json,sys
x=json.load(open(sys.argv[1]))
assert x.get('version')=='12.0.7'
assert x.get('ready') is True
assert x.get('runtime_authority')=='python-fastapi-backend'
assert x.get('wordpress_required') is False
assert x.get('identity_sessions') is True
assert x.get('thin_wordpress_adapter') is True
assert x.get('wordpress_state_migration') is True
assert x.get('wordpress_state_migration_runtime')=='12.0.7'
assert x.get('wordpress_compatibility_aliases') is True
PYHEALTH1207
  then
    break
  fi
  if [[ "$i" == 90 ]]; then
    docker logs --tail=280 "$CONTAINER" >&2 || true
    cat "$TMP/health.json" >&2 2>/dev/null || true
    fail "Research Librarian v12.0.7 did not become ready"
  fi
  sleep 2
done

echo "=== VERIFY v12.0.7 WORDPRESS STATE MIGRATION & COMPATIBILITY ==="

curl -fsS \
  http://127.0.0.1:8093/v1/research-librarian/wordpress-migration/manifest \
  > "$TMP/migration-manifest.json"

python3 - "$TMP/migration-manifest.json" <<'PYMANIFEST1207'
import json,sys
x=json.load(open(sys.argv[1]))['data']
assert x['release']=='12.0.7'
assert x['milestone']=='12.0.7'
assert x['runtime_authority']=='python-fastapi-backend'
assert x['wordpress_required'] is False
assert x['migration_mode']=='explicit-prepare-apply'
assert x['automatic_migration'] is False
assert x['idempotency']['durable_receipts'] is True
assert x['idempotency']['durable_compatibility_aliases'] is True
assert x['governance']['conflicts_fail_closed'] is True
assert x['governance']['legacy_state_not_deleted'] is True
assert x['governance']['compatibility_aliases_do_not_grant_access'] is True
assert x['next_boundary']=='independent-deployment-wordpress-failure-certification'
PYMANIFEST1207

docker exec -i "$CONTAINER" python - <<'PYV1207VERIFY'
from app.main import app
from app.services.wordpress_state_migration import (
    get_wordpress_state_migration_store,
    migration_manifest,
)
from app.services.independent_research_librarian_api import api_manifest,capabilities
import inspect
from app.services.persistent_research_session_conversation import PersistentResearchSessionStore

store=get_wordpress_state_migration_store()
assert store.backend=='postgres'

with store._postgres() as c:
    row=c.execute("""
      SELECT
        to_regclass('sc_rl_wordpress_migration_runs') IS NOT NULL AS runs,
        to_regclass('sc_rl_wordpress_migration_candidates') IS NOT NULL AS candidates,
        to_regclass('sc_rl_wordpress_migration_receipts') IS NOT NULL AS receipts,
        to_regclass('sc_rl_wordpress_compatibility_aliases') IS NOT NULL AS aliases
    """).fetchone()
    assert row['runs'] and row['candidates'] and row['receipts'] and row['aliases']

m=migration_manifest()
assert m['release']=='12.0.7'
assert m['automatic_migration'] is False
assert m['governance']['legacy_state_not_deleted'] is True
assert m['governance']['conflicts_fail_closed'] is True

sig=inspect.signature(PersistentResearchSessionStore.add_turn)
assert 'requested_turn_id' in sig.parameters

api=api_manifest()
assert api['scope']['thin_wordpress_adapter'] is True
assert api['scope']['wordpress_state_migration'] is True
assert api['next_boundary']=='independent-deployment-wordpress-failure-certification'

caps=capabilities()
assert caps['milestone']=='12.0.7'
assert caps['wordpress_state_migration'] is True

paths={getattr(r,'path','') for r in app.routes}
required={
 '/v1/research-librarian/wordpress-migration/manifest',
 '/v1/research-librarian/wordpress-migration/capabilities',
 '/v1/research-librarian/wordpress-migration/prepare',
 '/v1/research-librarian/wordpress-migration/runs',
 '/v1/research-librarian/wordpress-migration/runs/{run_id}',
 '/v1/research-librarian/wordpress-migration/runs/{run_id}/apply',
 '/v1/research-librarian/wordpress-migration/resolve',
}
assert not(required-paths), required-paths

print('PASS: v12.0.7 durable migration runs/candidates/receipts/aliases active on Postgres')
print('PASS: explicit prepare/apply + conflict fail-closed migration boundary active')
print('PASS: deterministic compatibility aliases and idempotent turn migration certified')
print('PASS: legacy WordPress state remains preserved; WordPress remains non-authoritative')
PYV1207VERIFY

echo "PASS: Research Librarian AI v12.0.7 WordPress State Migration & Compatibility Layer backend deployed and verified."
echo "NEXT: Install the WordPress v12.0.7 package, inspect /state-migration inventory, then PREPARE before any explicit MIGRATE apply."
