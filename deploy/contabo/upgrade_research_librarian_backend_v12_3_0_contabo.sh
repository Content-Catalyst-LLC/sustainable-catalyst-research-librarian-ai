#!/usr/bin/env bash
set -Eeuo pipefail

VERSION="12.3.0"
ROOT="/opt/sustainable-catalyst/research-librarian-ai"
LIVE_BACKEND="$ROOT/backend"
COMPOSE="$ROOT/compose.yml"
ENV_FILE="$ROOT/.env.contabo"
CORE_ENV="/opt/sustainable-catalyst/core/.env.production"
CORE_CONTAINER="sc-core"
SERVICE="research-librarian"
CONTAINER="sc-research-librarian"
BACKUP_ROOT="/opt/sustainable-catalyst/backups/research-librarian-ai"
ARCHIVE="${1:-/tmp/sustainable-catalyst-research-librarian-backend-v12.3.0.zip}"
TMP="$(mktemp -d /tmp/sc-rl-v1230.XXXXXX)"
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

grep -q '__version__ = "12.3.0"' "$INIT" || fail "backend package version mismatch"

for f in \
  app/main.py \
  app/api/global_source_federation.py \
  app/contracts/global_source_federation_original_language.py \
  app/services/global_source_federation_original_language.py \
  migrations/043_global_source_federation_original_language_research.sql \
  tests/test_v1230_global_source_federation_original_language_research.py
do
  [[ -f "$SRC_BACKEND/$f" ]] || fail "required v12.3.0 file missing: $f"
done

grep -q '"global_source_federation": True' "$SRC_BACKEND/app/services/global_source_federation_original_language.py" || fail "global-source-federation boundary missing"
grep -q '"original_language_is_primary_representation": True' "$SRC_BACKEND/app/services/global_source_federation_original_language.py" || fail "original-language boundary missing"
grep -q '"source_quality_separate_from_user_trust": True' "$SRC_BACKEND/app/services/global_source_federation_original_language.py" || fail "quality/trust separation missing"
grep -q '"automatic_entity_resolution": False' "$SRC_BACKEND/app/services/global_source_federation_original_language.py" || fail "v12.4 entity-resolution boundary missing"
grep -q '"automatic_toponym_resolution": False' "$SRC_BACKEND/app/services/global_source_federation_original_language.py" || fail "v12.4 toponym-resolution boundary missing"

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
s=re.sub(r'(?m)^(\s*image:\s*sustainable-catalyst-research-librarian:).*$', r'\g<1>12.3.0', s)
s=re.sub(r'(?m)^(\s*SC_RL_RELEASE_VERSION:\s*)["\']?[^"\'\n]+["\']?\s*$', r'\g<1>"12.3.0"', s)
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
    'SC_RL_RELEASE_VERSION':'12.3.0',
    'SC_RL_CORE_ENABLED':'true',
    'SC_RL_CORE_BASE_URL':'http://sc-core:8090',
    'SC_RL_CORE_MINIMUM_VERSION':'3.3.0',
    'SC_RL_CORE_SUPPORTED_MAJOR':'3',
    'SC_RL_CORE_FAIL_CLOSED_WRITES':'true',
    'SC_RL_ASYNC_JOBS_ENABLED':'true',
}
if core_key: updates['SC_RL_CORE_WRITE_API_KEY']=core_key
set_values(sys.argv[1],updates)
print('PASS: Research Librarian v12.3.0 environment aligned (secrets not displayed).')
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
assert x.get('version')=='12.3.0'
assert x.get('ready') is True
assert x.get('runtime_authority')=='python-fastapi-backend'
assert x.get('wordpress_required') is False
assert x.get('multilingual_cross_language_research') is True
assert x.get('global_source_federation') is True
assert x.get('global_source_federation_runtime')=='12.3.0'
assert x.get('global_source_federation_store_backend')=='postgres'
assert x.get('original_language_source_research') is True
assert x.get('source_quality_trust_separation') is True
PY
  then
    break
  fi
  if [[ "$i" == 90 ]]; then
    docker logs --tail=300 "$CONTAINER" >&2 || true
    cat "$TMP/health.json" >&2 2>/dev/null || true
    fail "Research Librarian v12.3.0 did not become ready"
  fi
  sleep 2
done

echo "=== VERIFY v12.3.0 GLOBAL SOURCE FEDERATION ==="
curl -fsS http://127.0.0.1:8093/v1/research-librarian/global-source-federation/manifest > "$TMP/manifest.json"
python3 - "$TMP/manifest.json" <<'PY'
import json,sys
x=json.load(open(sys.argv[1]))['data']
assert x['release']=='12.3.0'
assert x['milestone']=='12.3.0'
assert x['runtime_authority']=='python-fastapi-backend'
assert x['wordpress_required'] is False
assert x['scope']['global_source_federation'] is True
assert x['scope']['original_language_source_research'] is True
assert x['scope']['new_source_ingestion'] is True
assert x['scope']['source_quality_trust_separation'] is True
assert x['scope']['automatic_remote_crawling'] is False
assert x['scope']['automatic_entity_resolution'] is False
assert x['scope']['automatic_toponym_resolution'] is False
assert x['database_migration']=='043_global_source_federation_original_language_research.sql'
assert x['next_boundary']=='cross-language-entity-toponym-resolution'
PY

RL_KEY="$(docker exec "$CONTAINER" printenv SC_RL_BACKEND_API_KEY)"
[[ -n "$RL_KEY" ]] || fail "SC_RL_BACKEND_API_KEY missing in running container"
curl -fsS -H "X-SC-RL-Key: $RL_KEY" http://127.0.0.1:8093/v1/research-librarian/global-source-federation/capabilities > "$TMP/caps.json"
python3 - "$TMP/caps.json" <<'PY'
import json,sys
x=json.load(open(sys.argv[1]))['data']
assert x['milestone']=='12.3.0'
assert x['global_source_registry'] is True
assert x['original_language_acquisition_lineage'] is True
assert x['ingestion_receipts'] is True
assert x['quality_trust_separation'] is True
assert x['federation_query_plans'] is True
assert x['federation_retrieval_receipts'] is True
assert x['immutable_snapshots'] is True
PY

docker exec -i "$CONTAINER" python - <<'PY'
from app.main import app
from app.services.global_source_federation_original_language import get_global_source_federation_original_language_store
from app.services.independent_research_librarian_api import api_manifest, capabilities
prod=get_global_source_federation_original_language_store()
assert prod.backend=='postgres'
with prod._postgres() as c:
    for table in ['sc_rl_global_source_federation_projects','sc_rl_global_source_federation_events','sc_rl_global_source_federation_snapshots']:
        row=c.execute("SELECT to_regclass(%s) AS t",(table,)).fetchone()
        assert row['t'] is not None, table
paths={getattr(route,'path','') for route in app.routes}
assert '/v1/research-librarian/global-source-federation/manifest' in paths
assert '/v1/research-librarian/global-source-federation/projects' in paths
m=api_manifest(); c=capabilities()
assert m['scope']['global_source_federation'] is True
assert m['scope']['original_language_source_research'] is True
assert m['next_boundary']=='cross-language-entity-toponym-resolution'
assert c['milestone']=='12.3.0'
assert c['global_source_federation'] is True
print('PASS: migration 043 global source federation tables active on Postgres')
print('PASS: global source federation API and original-language lineage active')
print('PASS: source-quality signals remain separate from user trust preferences')
print('PASS: WordPress remains optional')
print('PASS: next boundary is v12.4.0 Cross-Language Entity & Toponym Resolution')
PY

echo "PASS: Research Librarian AI v12.3.0 Global Source Federation & Original-Language Research backend deployed and verified."
echo "NEXT: Optional WordPress v12.3.0 adapter may be installed; backend operation does not require WordPress."
