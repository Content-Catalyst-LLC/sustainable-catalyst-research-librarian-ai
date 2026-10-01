#!/usr/bin/env bash
set -Eeuo pipefail

VERSION="12.0.2"
ROOT="/opt/sustainable-catalyst/research-librarian-ai"
LIVE_BACKEND="$ROOT/backend"
COMPOSE="$ROOT/compose.yml"
ENV_FILE="$ROOT/.env.contabo"
CORE_ENV="/opt/sustainable-catalyst/core/.env.production"
CORE_CONTAINER="sc-core"
SERVICE="research-librarian"
CONTAINER="sc-research-librarian"
BACKUP_ROOT="/opt/sustainable-catalyst/backups/research-librarian-ai"
ARCHIVE="${1:-/tmp/sustainable-catalyst-research-librarian-backend-v12.0.2.zip}"
TMP="$(mktemp -d /tmp/sc-rl-v1202.XXXXXX)"
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

grep -q '__version__ = "12.0.2"' "$INIT" || fail "backend package version mismatch"

for f in \
  app/main.py \
  app/api/independent.py \
  app/contracts/independent_research_librarian_api.py \
  app/services/independent_research_librarian_api.py \
  app/contracts/runtime_authority_wordpress_decoupling.py \
  app/services/runtime_authority_wordpress_decoupling.py \
  tests/test_v1202_independent_research_librarian_api.py \
  migrations/037_independent_research_librarian_api.sql
do
  [[ -f "$SRC_BACKEND/$f" ]] || fail "required backend file missing: $f"
done

grep -q 'prefix="/v1/research-librarian"' "$SRC_BACKEND/app/api/independent.py" || fail "independent API prefix missing"
grep -q 'INDEPENDENT_API_ENVELOPE_SCHEMA' "$SRC_BACKEND/app/contracts/independent_research_librarian_api.py" || fail "independent API envelope contract missing"
grep -q '"wordpress_required":False' "$SRC_BACKEND/app/services/independent_research_librarian_api.py" || fail "WordPress independence declaration missing"
grep -q 'independent_api_version": "v1"' "$SRC_BACKEND/app/main.py" || fail "health independent API declaration missing"

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

python3 - "$COMPOSE" <<'PYCOMPOSE1202'
from pathlib import Path
import re,sys
p=Path(sys.argv[1])
s=p.read_text()
s=re.sub(r'(?m)^(\s*image:\s*sustainable-catalyst-research-librarian:).*$', r'\g<1>12.0.2', s)
s=re.sub(r'(?m)^(\s*SC_RL_RELEASE_VERSION:\s*)["\']?[^"\'\n]+["\']?\s*$', r'\g<1>"12.0.2"', s)
p.write_text(s)
PYCOMPOSE1202

python3 - "$ENV_FILE" "$CORE_ENV" <<'PYENV1202'
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
    'SC_RL_RELEASE_VERSION':'12.0.2',
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
PYENV1202

cd "$ROOT"
docker compose -f "$COMPOSE" config --quiet

if grep -qE '^[[:space:]]*build:' "$COMPOSE"; then
  docker compose -f "$COMPOSE" build "$SERVICE"
else
  docker build -t "sustainable-catalyst-research-librarian:${VERSION}" "$LIVE_BACKEND"
fi

docker compose -f "$COMPOSE" up -d --force-recreate "$SERVICE"

for i in $(seq 1 90); do
  if curl -fsS http://127.0.0.1:8093/health >"$TMP/health.json" 2>/dev/null && python3 - "$TMP/health.json" <<'PYHEALTH1202' >/dev/null 2>&1
import json,sys
x=json.load(open(sys.argv[1]))
assert x.get('version')=='12.0.2'
assert x.get('ready') is True
assert x.get('runtime_authority')=='python-fastapi-backend'
assert x.get('wordpress_required') is False
assert x.get('independent_api_version')=='v1'
PYHEALTH1202
  then
    break
  fi

  if [[ "$i" == 90 ]]; then
    docker logs --tail=240 "$CONTAINER" >&2 || true
    cat "$TMP/health.json" >&2 2>/dev/null || true
    fail "Research Librarian v12.0.2 did not become ready"
  fi
  sleep 2
done

echo "=== VERIFY v12.0.2 INDEPENDENT RESEARCH LIBRARIAN API v1 ==="
docker exec -i "$CONTAINER" python - <<'PYV1202VERIFY'
import os
from app.main import app
from app.services.independent_research_librarian_api import (
    api_manifest,
    capabilities,
    IndependentAPIContractSnapshotStore,
)
from app.contracts.independent_research_librarian_api import IndependentAPIContractSnapshotRequest

manifest=api_manifest()
assert manifest['api_version']=='v1'
assert manifest['base_path']=='/v1/research-librarian'
assert manifest['runtime_authority']=='python-fastapi-backend'
assert manifest['wordpress_required'] is False
assert manifest['authentication']['scheme']=='backend-key-v1'
assert manifest['scope']['persistent_conversations'] is False
assert manifest['scope']['identity_sessions'] is False

cap=capabilities()
assert cap['milestone']=='12.0.2'
assert cap['direct_backend_access'] is True
assert cap['stable_response_envelope'] is True
assert cap['wordpress_required'] is False
assert cap['retrieval_api'] is True
assert cap['project_api'] is True
assert cap['scientist_environment_api'] is True
assert cap['contract_snapshots'] is True

paths={getattr(r,'path','') for r in app.routes}
required={
  '/v1/research-librarian/manifest',
  '/v1/research-librarian/capabilities',
  '/v1/research-librarian/status',
  '/v1/research-librarian/retrieve',
  '/v1/research-librarian/projects',
  '/v1/research-librarian/projects/{project_id}',
  '/v1/research-librarian/projects/{project_id}/investigations',
  '/v1/research-librarian/scientist-environments/{scientist_environment_id}',
  '/v1/research-librarian/scientist-environments/{scientist_environment_id}/dossier',
  '/v1/research-librarian/runtime-authority',
  '/v1/research-librarian/contract-snapshots/freeze',
}
assert not(required-paths),required-paths

store=IndependentAPIContractSnapshotStore()
if os.environ.get('SC_RL_DATABASE_BACKEND','').lower() in {'postgres','postgresql','neon'}:
    assert store.backend=='postgres'
snap=store.freeze(IndependentAPIContractSnapshotRequest(actor_ref='deployment-v12.0.2'))
assert len(snap['snapshot_hash'])==64
assert snap['manifest']['api_version']=='v1'

print('PASS: v12.0.2 independent API v1 active on',store.backend)
print('PASS: /v1/research-librarian contract registered without WordPress runtime dependency')
PYV1202VERIFY

echo "PASS: Research Librarian AI v12.0.2 Independent Research Librarian API v1 backend deployed and verified."
