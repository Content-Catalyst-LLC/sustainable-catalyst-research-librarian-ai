#!/usr/bin/env bash
set -Eeuo pipefail

VERSION="12.4.0"
ROOT="/opt/sustainable-catalyst/research-librarian-ai"
LIVE_BACKEND="$ROOT/backend"
COMPOSE="$ROOT/compose.yml"
ENV_FILE="$ROOT/.env.contabo"
CORE_ENV="/opt/sustainable-catalyst/core/.env.production"
CORE_CONTAINER="sc-core"
SERVICE="research-librarian"
CONTAINER="sc-research-librarian"
BACKUP_ROOT="/opt/sustainable-catalyst/backups/research-librarian-ai"
ARCHIVE="${1:-/tmp/sustainable-catalyst-research-librarian-backend-v12.4.0.zip}"
TMP="$(mktemp -d /tmp/sc-rl-v1240.XXXXXX)"
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

grep -q '__version__ = "12.4.0"' "$INIT" || fail "backend package version mismatch"

for f in \
  app/main.py \
  app/api/cross_language_entity_toponym_resolution.py \
  app/contracts/cross_language_entity_toponym_resolution.py \
  app/services/cross_language_entity_toponym_resolution.py \
  migrations/044_cross_language_entity_toponym_resolution.sql \
  tests/test_v1240_cross_language_entity_toponym_resolution.py
do
  [[ -f "$SRC_BACKEND/$f" ]] || fail "required v12.4.0 file missing: $f"
done

grep -q '"accepted_resolution_requires_human_review": True' "$SRC_BACKEND/app/services/cross_language_entity_toponym_resolution.py" || fail "human-review gate missing"
grep -q '"automatic_identity_promotion": False' "$SRC_BACKEND/app/services/cross_language_entity_toponym_resolution.py" || fail "identity-promotion boundary missing"
grep -q '"automatic_remote_geocoding": False' "$SRC_BACKEND/app/services/cross_language_entity_toponym_resolution.py" || fail "remote-geocoding boundary missing"
grep -q '"canonical_identity_promoted": False' "$SRC_BACKEND/app/services/cross_language_entity_toponym_resolution.py" || fail "canonical identity promotion boundary missing"

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

python3 - "$COMPOSE" <<'PY'
from pathlib import Path
import re,sys
p=Path(sys.argv[1])
s=p.read_text()
s=re.sub(r'(?m)^(\s*image:\s*sustainable-catalyst-research-librarian:).*$', r'\g<1>12.4.0', s)
s=re.sub(r'(?m)^(\s*SC_RL_RELEASE_VERSION:\s*)["\']?[^"\'\n]+["\']?\s*$', r'\g<1>"12.4.0"', s)
p.write_text(s)
PY

python3 - "$ENV_FILE" "$CORE_ENV" <<'PY'
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
if not rl.get('SC_RL_BACKEND_API_KEY','').strip():
    raise SystemExit('SC_RL_BACKEND_API_KEY is required for Independent API administration.')
updates={
    'SC_RL_RELEASE_VERSION':'12.4.0',
    'SC_RL_CORE_ENABLED':'true',
    'SC_RL_CORE_BASE_URL':'http://sc-core:8090',
    'SC_RL_CORE_MINIMUM_VERSION':'3.3.0',
    'SC_RL_CORE_SUPPORTED_MAJOR':'3',
    'SC_RL_CORE_FAIL_CLOSED_WRITES':'true',
    'SC_RL_ASYNC_JOBS_ENABLED':'true',
}
if core_key: updates['SC_RL_CORE_WRITE_API_KEY']=core_key
set_values(sys.argv[1],updates)
print('PASS: Research Librarian v12.4.0 environment aligned (secrets not displayed).')
PY

cd "$ROOT"
docker compose -f "$COMPOSE" config --quiet
if grep -qE '^[[:space:]]*build:' "$COMPOSE"; then
  docker compose -f "$COMPOSE" build "$SERVICE"
else
  docker build -t "sustainable-catalyst-research-librarian:${VERSION}" "$LIVE_BACKEND"
fi
docker compose -f "$COMPOSE" up -d --force-recreate "$SERVICE"

for i in $(seq 1 90); do
  if curl -fsS http://127.0.0.1:8093/health >"$TMP/health.json" 2>/dev/null && python3 - "$TMP/health.json" <<'PY' >/dev/null 2>&1
import json,sys
x=json.load(open(sys.argv[1]))
assert x.get('version')=='12.4.0'
assert x.get('ready') is True
assert x.get('runtime_authority')=='python-fastapi-backend'
assert x.get('wordpress_required') is False
assert x.get('global_source_federation') is True
assert x.get('cross_language_entity_toponym_resolution') is True
assert x.get('cross_language_resolution_runtime')=='12.4.0'
assert x.get('cross_language_resolution_store_backend')=='postgres'
assert x.get('human_confirmed_entity_resolution') is True
assert x.get('toponym_ambiguity_preserved') is True
assert x.get('automatic_identity_promotion') is False
PY
  then
    break
  fi
  if [[ "$i" == 90 ]]; then
    docker logs --tail=300 "$CONTAINER" >&2 || true
    cat "$TMP/health.json" >&2 2>/dev/null || true
    fail "Research Librarian v12.4.0 did not become ready"
  fi
  sleep 2
done

echo "=== VERIFY v12.4.0 CROSS-LANGUAGE ENTITY & TOPONYM RESOLUTION ==="
PREFIX="http://127.0.0.1:8093/v1/research-librarian/cross-language-entity-toponym-resolution"
curl -fsS "$PREFIX/manifest" > "$TMP/manifest.json"
python3 - "$TMP/manifest.json" <<'PY'
import json,sys
x=json.load(open(sys.argv[1]))['data']
assert x['release']=='12.4.0'
assert x['milestone']=='12.4.0'
assert x['runtime_authority']=='python-fastapi-backend'
assert x['wordpress_required'] is False
assert x['scope']['cross_language_entity_resolution'] is True
assert x['scope']['cross_language_toponym_resolution'] is True
assert x['scope']['automatic_identity_promotion'] is False
assert x['scope']['automatic_remote_geocoding'] is False
assert x['governance']['accepted_resolution_requires_human_review'] is True
assert x['database_migration']=='044_cross_language_entity_toponym_resolution.sql'
assert x['next_boundary']=='cross-language-citation-evidence-resolution'
PY

RL_KEY="$(docker exec "$CONTAINER" printenv SC_RL_BACKEND_API_KEY)"
[[ -n "$RL_KEY" ]] || fail "SC_RL_BACKEND_API_KEY missing in running container"
curl -fsS -H "X-SC-RL-Key: $RL_KEY" "$PREFIX/capabilities" > "$TMP/caps.json"
python3 - "$TMP/caps.json" <<'PY'
import json,sys
x=json.load(open(sys.argv[1]))['data']
assert x['milestone']=='12.4.0'
assert x['entity_mentions'] is True
assert x['entity_candidates'] is True
assert x['toponym_candidates'] is True
assert x['alias_alignment'] is True
assert x['human_review_gate'] is True
assert x['core_candidate_export'] is True
assert x['automatic_identity_promotion'] is False
PY

docker exec -i "$CONTAINER" python - <<'PY'
from app.main import app
from app.services.cross_language_entity_toponym_resolution import get_cross_language_entity_toponym_resolution_store
from app.services.independent_research_librarian_api import api_manifest, capabilities
prod=get_cross_language_entity_toponym_resolution_store()
assert prod.backend=='postgres'
with prod._postgres() as c:
    for table in [
        'sc_rl_cross_language_resolution_projects',
        'sc_rl_cross_language_resolution_events',
        'sc_rl_cross_language_resolution_snapshots',
    ]:
        row=c.execute("SELECT to_regclass(%s) AS t",(table,)).fetchone()
        assert row['t'] is not None, table
paths={getattr(route,'path','') for route in app.routes}
assert '/v1/research-librarian/cross-language-entity-toponym-resolution/manifest' in paths
assert '/v1/research-librarian/cross-language-entity-toponym-resolution/projects' in paths
m=api_manifest(); c=capabilities()
assert m['scope']['cross_language_entity_toponym_resolution'] is True
assert m['next_boundary']=='cross-language-citation-evidence-resolution'
assert c['milestone']=='12.4.0'
assert c['cross_language_entity_toponym_resolution'] is True
print('PASS: migration 044 cross-language resolution tables active on Postgres')
print('PASS: entity and toponym resolution API active')
print('PASS: human-review gate and competing-candidate preservation active')
print('PASS: canonical identity promotion remains explicit and external')
print('PASS: WordPress remains optional')
print('PASS: next boundary is v12.5.0 Cross-Language Citation & Evidence Resolution')
PY

echo "PASS: Research Librarian AI v12.4.0 Cross-Language Entity & Toponym Resolution backend deployed and verified."
echo "NEXT: v12.5.0 Cross-Language Citation & Evidence Resolution."
