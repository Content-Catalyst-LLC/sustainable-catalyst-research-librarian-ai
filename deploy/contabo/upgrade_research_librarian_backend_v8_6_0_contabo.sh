#!/usr/bin/env bash
set -Eeuo pipefail

VERSION="8.6.0"
ROOT="${SC_TARGET_ROOT:-/opt/sustainable-catalyst/research-librarian-ai}"
LIVE_BACKEND="$ROOT/backend"
COMPOSE="${SC_TARGET_COMPOSE:-$ROOT/compose.yml}"
SERVICE="${SC_TARGET_SERVICE:-research-librarian}"
CONTAINER="${SC_TARGET_CONTAINER:-sc-research-librarian}"
CORE_ROOT="${SC_CORE_ROOT:-/opt/sustainable-catalyst/core}"
CORE_CONTAINER="${SC_CORE_CONTAINER:-sc-core}"
CORE_ENV="${SC_CORE_ENV:-$CORE_ROOT/.env.production}"
ENV_FILE="${SC_RL_ENV_FILE:-$ROOT/.env.contabo}"
ARCHIVE="${1:-/tmp/sustainable-catalyst-research-librarian-backend-v8.6.0.zip}"
BACKUP_ROOT="/opt/sustainable-catalyst/backups/research-librarian-v860"
TMP="$(mktemp -d /tmp/sc-rl-v860.XXXXXX)"
trap 'rm -rf "$TMP"' EXIT

fail(){ echo "ERROR: $*" >&2; exit 1; }
for cmd in unzip rsync docker python3 tar grep sed curl; do command -v "$cmd" >/dev/null || fail "$cmd is required"; done
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
PACKAGE_ROOT="$(dirname "$SRC_BACKEND")"
grep -q '__version__ = "8.6.0"' "$INIT" || fail "backend package version mismatch"
[[ -f "$SRC_BACKEND/app/clients/platform_core.py" ]] || fail "Platform Core client missing"
[[ -f "$SRC_BACKEND/app/api/core.py" ]] || fail "Platform Core API router missing"
[[ -f "$SRC_BACKEND/app/services/platform_core_integration.py" ]] || fail "Platform Core integration service missing"
[[ -f "$SRC_BACKEND/app/async_jobs.py" ]] || fail "v8.3 async job store missing"
[[ -f "$SRC_BACKEND/app/workers/document_worker.py" ]] || fail "v8.3 document worker missing"
[[ -f "$SRC_BACKEND/app/services/document_jobs.py" ]] || fail "v8.3 document-processing service missing"
[[ -f "$SRC_BACKEND/migrations/004_async_document_processing_runtime.sql" ]] || fail "v8.3 async Postgres migration contract missing"
[[ -f "$SRC_BACKEND/app/advanced_retrieval.py" ]] || fail "v8.4 advanced retrieval engine missing"
[[ -f "$SRC_BACKEND/tests/test_v840_advanced_retrieval.py" ]] || fail "v8.4 advanced retrieval tests missing"
[[ -f "$SRC_BACKEND/app/document_intelligence.py" ]] || fail "v8.5 document intelligence engine missing"
[[ -f "$SRC_BACKEND/app/api/documents.py" ]] || fail "v8.5 document intelligence API missing"
[[ -f "$SRC_BACKEND/app/contracts/documents.py" ]] || fail "v8.5 document parse contract missing"
[[ -f "$SRC_BACKEND/tests/test_v850_document_intelligence.py" ]] || fail "v8.5 document intelligence tests missing"
grep -q 'pypdf' "$SRC_BACKEND/requirements.txt" || fail "pypdf dependency missing"
[[ -f "$SRC_BACKEND/app/source_identity.py" ]] || fail "v8.6 source identity engine missing"
[[ -f "$SRC_BACKEND/app/api/sources.py" ]] || fail "v8.6 source identity API missing"
[[ -f "$SRC_BACKEND/app/contracts/sources.py" ]] || fail "v8.6 source identity contracts missing"
[[ -f "$SRC_BACKEND/tests/test_v860_source_identity.py" ]] || fail "v8.6 source identity tests missing"
[[ -f "$SRC_BACKEND/migrations/005_source_identity_citation_graph.sql" ]] || fail "v8.6 source identity migration missing"

echo "=== BACKUP RESEARCH LIBRARIAN ==="
mkdir -p "$BACKUP_ROOT"
stamp="$(date +%Y%m%d-%H%M%S)"
tar -C "$ROOT" -czf "$BACKUP_ROOT/backend-before-v${VERSION}-${stamp}.tgz" backend
cp -a "$COMPOSE" "$BACKUP_ROOT/compose-before-v${VERSION}-${stamp}.yml"
cp -a "$ENV_FILE" "$BACKUP_ROOT/env-before-v${VERSION}-${stamp}"

echo "=== INSTALL v${VERSION} BACKEND ==="
rsync -a \
  --exclude='data/' --exclude='__pycache__/' --exclude='.pytest_cache/' \
  --exclude='*.pyc' --exclude='.env' --exclude='.env.*' \
  "$SRC_BACKEND/" "$LIVE_BACKEND/"

# Keep the existing service topology, but align the image tag when this compose
# uses the release image pattern.
python3 - "$COMPOSE" <<'PY'
from pathlib import Path
import re, sys
p=Path(sys.argv[1]); s=p.read_text()
s=re.sub(r'(?m)^(\s*image:\s*sustainable-catalyst-research-librarian:).*$', r'\g<1>8.6.0', s)
s=re.sub(r'(?m)^(\s*SC_RL_RELEASE_VERSION:\s*)["\']?[^"\'\n]+["\']?\s*$', r'\g<1>"8.6.0"', s)
p.write_text(s)
PY

# Copy the Core write secret server-side. It is never printed and never ships
# in the release bundle. Existing RL credentials are preserved.
python3 - "$ENV_FILE" "$CORE_ENV" <<'PY'
from pathlib import Path
import sys

def parse(path):
    out={}
    for raw in Path(path).read_text().splitlines():
        line=raw.strip()
        if not line or line.startswith('#') or '=' not in line: continue
        k,v=line.split('=',1); v=v.strip()
        if len(v)>=2 and v[0]==v[-1] and v[0] in {'"', "'"}: v=v[1:-1]
        out[k.strip()]=v
    return out

def set_values(path, updates):
    p=Path(path); lines=p.read_text().splitlines(); done=set(); result=[]
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
    raise SystemExit('SC_CORE_WRITE_API_KEY is missing from Core and SC_RL_CORE_WRITE_API_KEY is not already configured.')
updates={
    'SC_RL_RELEASE_VERSION':'8.6.0',
    'SC_RL_CORE_ENABLED':'true',
    'SC_RL_CORE_BASE_URL':'http://sc-core:8090',
    'SC_RL_CORE_MINIMUM_VERSION':'3.3.0',
    'SC_RL_CORE_SUPPORTED_MAJOR':'3',
    'SC_RL_CORE_FAIL_CLOSED_WRITES':'true',
    'SC_RL_ASYNC_JOBS_ENABLED':'true',
    'SC_RL_ASYNC_JOB_POLL_SECONDS':'1.0',
    'SC_RL_ASYNC_JOB_LEASE_SECONDS':'120',
    'SC_RL_ASYNC_JOB_RECLAIM_INTERVAL_SECONDS':'60',
    'SC_RL_ASYNC_JOB_RETRY_BASE_SECONDS':'5.0',
    'SC_RL_ASYNC_JOB_RETRY_MAX_SECONDS':'900',
}
if core_key: updates['SC_RL_CORE_WRITE_API_KEY']=core_key
set_values(sys.argv[1], updates)
print('PASS: Research Librarian Core integration environment aligned (secret not displayed).')
PY

cd "$ROOT"
docker compose -f "$COMPOSE" config --quiet

echo "=== BUILD IMAGE ==="
if grep -qE '^[[:space:]]*build:' "$COMPOSE"; then
  docker compose -f "$COMPOSE" build "$SERVICE"
else
  docker build -t "sustainable-catalyst-research-librarian:${VERSION}" "$LIVE_BACKEND"
fi

echo "=== RECREATE SERVICE ==="
docker compose -f "$COMPOSE" up -d --force-recreate "$SERVICE"

for i in $(seq 1 90); do
  if curl -fsS http://127.0.0.1:8093/health >"$TMP/health.json" 2>/dev/null; then
    if python3 - "$TMP/health.json" <<'PY' >/dev/null 2>&1
import json,sys
x=json.load(open(sys.argv[1]))
assert x.get('version')=='8.6.0',x
assert x.get('ready') is True,x
PY
    then break; fi
  fi
  if [[ "$i" == 90 ]]; then docker logs --tail=240 "$CONTAINER" >&2 || true; cat "$TMP/health.json" >&2 2>/dev/null || true; fail "Research Librarian v8.6.0 did not become ready"; fi
  sleep 2
done
python3 - "$TMP/health.json" <<'PY'
import json,sys
x=json.load(open(sys.argv[1])); assert x.get('version')=='8.6.0' and x.get('ready') is True,x
print('PASS: Research Librarian /health reports 8.6.0 and ready=true')
PY

echo "=== VERIFY PLATFORM CORE NETWORK + CONTRACT ==="
docker exec -i "$CONTAINER" python - <<'PY'
import json, os, urllib.request

def get(url, headers=None):
    req=urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=35) as r: return json.load(r)
core=get('http://sc-core:8090/health')
assert core.get('ok') is True, core
version=str(core.get('version') or '')
parts=[int(x) for x in version.split('.')[:3]]
assert parts[0] == 3 and tuple(parts) >= (3,3,0), core
key=os.environ.get('SC_RL_BACKEND_API_KEY','')
assert key, 'SC_RL_BACKEND_API_KEY is missing in container'
rl=get('http://127.0.0.1:8093/v1/core/readiness', {'X-SC-RL-Key':key})
assert rl.get('compatible') is True, rl
assert rl.get('write_ready') is True, rl
assert rl.get('core_health',{}).get('version') == version, rl
failed=rl.get('failed_capabilities') or []
assert not failed, f'Core capability probes failed: {failed}'
print('PASS: Platform Core',version,'is compatible and write-ready')
print('PASS: required governed research/reasoning capabilities are reachable')
PY

echo "=== VERIFY v8.6 SOURCE IDENTITY + CORE/JOB/RETRIEVAL ROUTES ==="
docker exec -i "$CONTAINER" python - <<'PY'
from app.main import app
from app.store import SCHEMA_VERSION
paths={getattr(r,'path',None) for r in app.routes}
required={
'/v1/core/architecture','/v1/core/readiness','/v1/core/bindings',
'/v1/core/research-objects/promote','/v1/core/research-projects/synchronize',
'/v1/core/exchange/packages','/v1/jobs/runtime','/v1/jobs','/v1/jobs/documents',
'/v1/retrieval/plan','/v1/retrieve','/v1/retrieve/explain',
'/v1/documents/capabilities','/v1/documents/parse','/v1/documents/parse/async',
'/v1/sources/capabilities','/v1/sources/resolve','/v1/sources/{source_id}','/v1/sources/{source_id}/graph','/v1/sources/{source_id}/citations'}
missing=required-paths
assert not missing,missing
assert SCHEMA_VERSION==19,SCHEMA_VERSION
print('PASS: v8.6 source identity + Core + async job + retrieval routes registered')
print('PASS: ancillary SQLite schema 19 active')
PY

echo "=== VERIFY ADVANCED RETRIEVAL CONTRACT ==="
docker exec -i "$CONTAINER" python - <<'PY'
from app.advanced_retrieval import ADVANCED_RETRIEVAL_SCHEMA, build_query_plan
from app.calibration import sanitize_retrieval_config
plan=build_query_plan('Compare solar storage versus wind storage',4)
assert plan['variant_count'] >= 3, plan
assert plan['generative_expansion'] is False, plan
config=sanitize_retrieval_config({})
assert config['profile']=='advanced-v8.4.0', config
assert config['advanced']['enabled'] is True, config
assert ADVANCED_RETRIEVAL_SCHEMA=='sc-research-librarian-advanced-retrieval/1.0'
print('PASS: v8.4 deterministic query planning + advanced retrieval profile active')
PY

echo "=== VERIFY v8.5 DOCUMENT INTELLIGENCE ==="
docker exec -i "$CONTAINER" python - <<'PY'
from app.document_intelligence import DOCUMENT_INTELLIGENCE_SCHEMA, parse_document
r=parse_document(content='# Smoke Study\n\n## Abstract\nEvidence with DOI 10.1234/smoke.1.\n\n## References\n1. Example, A. (2026). Smoke reference.',media_type='text/markdown',filename='smoke.md')
assert r['schema']==DOCUMENT_INTELLIGENCE_SCHEMA,r
assert r['title']=='Smoke Study',r
assert r['section_count']>=2,r
assert '10.1234/smoke.1' in [x.lower() for x in r['identifiers']['doi']],r
assert r['governance']['llm_extraction'] is False,r
print('PASS: v8.5 deterministic scholarly document parsing active')
PY

echo "=== VERIFY v8.6 SOURCE IDENTITY + CITATION GRAPH ==="
docker exec -i "$CONTAINER" python - <<'PY'
import os
from app.source_identity import SOURCE_IDENTITY_SCHEMA, CITATION_GRAPH_SCHEMA, get_source_graph_store, identity_candidate, normalize_identifier
assert SOURCE_IDENTITY_SCHEMA=='sc-research-librarian-source-identity/1.0'
assert CITATION_GRAPH_SCHEMA=='sc-research-librarian-citation-graph/1.0'
assert normalize_identifier('doi','https://doi.org/10.1234/ABC')=='10.1234/abc'
candidate=identity_candidate({'parsed_document':{'title':'Smoke','identifiers':{'doi':['10.1234/main','10.1234/cited']},'references':[{'identifiers':{'doi':['10.1234/cited']}}]}})
assert candidate['identifiers']['doi']==['10.1234/main'],candidate
runtime=get_source_graph_store().runtime()
assert runtime['durable'] is True and runtime['citation_graph'] is True,runtime
if os.environ.get('SC_RL_DATABASE_BACKEND','').lower() in {'postgres','postgresql','neon'}:
    assert runtime['storage_backend']=='postgres',runtime
print('PASS: v8.6 canonical source identity and citation graph runtime active on',runtime['storage_backend'])
PY

echo "=== VERIFY DURABLE ASYNC JOB QUEUE ==="
docker exec -i "$CONTAINER" python - <<'PY'
import json, os, urllib.request
key=os.environ.get('SC_RL_BACKEND_API_KEY','')
assert key, 'SC_RL_BACKEND_API_KEY missing'
req=urllib.request.Request('http://127.0.0.1:8093/v1/jobs/runtime',headers={'X-SC-RL-Key':key})
with urllib.request.urlopen(req,timeout=35) as r: data=json.load(r)
assert data.get('schema')=='sc-research-librarian-async-runtime/1.0',data
assert data.get('durable') is True,data
backend=data.get('storage_backend')
assert backend in {'postgres','sqlite'},data
if os.environ.get('SC_RL_DATABASE_BACKEND','').lower() in {'postgres','postgresql','neon'}:
    assert backend=='postgres',data
    assert data.get('claim_strategy')=='for-update-skip-locked',data
print('PASS: durable async job runtime active on',backend)
PY

echo "PASS: Research Librarian AI v${VERSION} document intelligence backend deployed and verified."
