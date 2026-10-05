#!/usr/bin/env bash
set -Eeuo pipefail

VERSION="12.2.0"
ROOT="/opt/sustainable-catalyst/research-librarian-ai"
LIVE_BACKEND="$ROOT/backend"
COMPOSE="$ROOT/compose.yml"
ENV_FILE="$ROOT/.env.contabo"
CORE_ENV="/opt/sustainable-catalyst/core/.env.production"
CORE_CONTAINER="sc-core"
SERVICE="research-librarian"
CONTAINER="sc-research-librarian"
BACKUP_ROOT="/opt/sustainable-catalyst/backups/research-librarian-ai"
ARCHIVE="${1:-/tmp/sustainable-catalyst-research-librarian-backend-v12.2.0.zip}"
TMP="$(mktemp -d /tmp/sc-rl-v1220.XXXXXX)"
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

grep -q '__version__ = "12.2.0"' "$INIT" || fail "backend package version mismatch"

for f in \
  app/main.py \
  app/api/multilingual_research.py \
  app/contracts/multilingual_cross_language_research.py \
  app/services/multilingual_cross_language_research.py \
  migrations/042_multilingual_cross_language_research_intelligence.sql \
  tests/test_v1220_multilingual_cross_language_research_intelligence.py
do
  [[ -f "$SRC_BACKEND/$f" ]] || fail "required v12.2.0 file missing: $f"
done

grep -q '"analyze_original_language_first": True' "$SRC_BACKEND/app/services/multilingual_cross_language_research.py" || fail "original-language-first boundary missing"
grep -q '"translation_is_derived_representation": True' "$SRC_BACKEND/app/services/multilingual_cross_language_research.py" || fail "translation-derived boundary missing"
grep -q '"global_source_federation": False' "$SRC_BACKEND/app/services/multilingual_cross_language_research.py" || fail "v12.3 federation boundary missing"
grep -q '"automatic_entity_resolution": False' "$SRC_BACKEND/app/services/multilingual_cross_language_research.py" || fail "v12.4 entity-resolution boundary missing"

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

python3 - "$COMPOSE" <<'PYCOMPOSE1220'
from pathlib import Path
import re,sys
p=Path(sys.argv[1])
s=p.read_text()
s=re.sub(r'(?m)^(\s*image:\s*sustainable-catalyst-research-librarian:).*$', r'\g<1>12.2.0', s)
s=re.sub(r'(?m)^(\s*SC_RL_RELEASE_VERSION:\s*)["\']?[^"\'\n]+["\']?\s*$', r'\g<1>"12.2.0"', s)
p.write_text(s)
PYCOMPOSE1220

python3 - "$ENV_FILE" "$CORE_ENV" <<'PYENV1220'
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
                done.add(k); continue
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
    'SC_RL_RELEASE_VERSION':'12.2.0',
    'SC_RL_CORE_ENABLED':'true',
    'SC_RL_CORE_BASE_URL':'http://sc-core:8090',
    'SC_RL_CORE_MINIMUM_VERSION':'3.3.0',
    'SC_RL_CORE_SUPPORTED_MAJOR':'3',
    'SC_RL_CORE_FAIL_CLOSED_WRITES':'true',
    'SC_RL_ASYNC_JOBS_ENABLED':'true',
}
if core_key: updates['SC_RL_CORE_WRITE_API_KEY']=core_key
set_values(sys.argv[1],updates)
print('PASS: Research Librarian v12.2.0 environment aligned (secrets not displayed).')
PYENV1220

cd "$ROOT"
docker compose -f "$COMPOSE" config --quiet

if grep -qE '^[[:space:]]*build:' "$COMPOSE"; then
  docker compose -f "$COMPOSE" build "$SERVICE"
else
  docker build -t "sustainable-catalyst-research-librarian:${VERSION}" "$LIVE_BACKEND"
fi

docker compose -f "$COMPOSE" up -d --force-recreate "$SERVICE"

for i in $(seq 1 90); do
  if curl -fsS http://127.0.0.1:8093/health >"$TMP/health.json" 2>/dev/null && python3 - "$TMP/health.json" <<'PYHEALTH1220' >/dev/null 2>&1
import json,sys
x=json.load(open(sys.argv[1]))
assert x.get('version')=='12.2.0'
assert x.get('ready') is True
assert x.get('runtime_authority')=='python-fastapi-backend'
assert x.get('wordpress_required') is False
assert x.get('neural_research_intelligence') is True
assert x.get('multilingual_cross_language_research') is True
assert x.get('multilingual_research_runtime')=='12.2.0'
assert x.get('multilingual_research_store_backend')=='postgres'
assert x.get('original_language_first') is True
assert x.get('translation_is_derived_representation') is True
PYHEALTH1220
  then
    break
  fi
  if [[ "$i" == 90 ]]; then
    docker logs --tail=300 "$CONTAINER" >&2 || true
    cat "$TMP/health.json" >&2 2>/dev/null || true
    fail "Research Librarian v12.2.0 did not become ready"
  fi
  sleep 2
done

echo "=== VERIFY v12.2.0 MULTILINGUAL & CROSS-LANGUAGE RESEARCH ==="

curl -fsS \
  http://127.0.0.1:8093/v1/research-librarian/multilingual-research/manifest \
  > "$TMP/multilingual-manifest.json"

python3 - "$TMP/multilingual-manifest.json" <<'PYMANIFEST1220'
import json,sys
x=json.load(open(sys.argv[1]))['data']
assert x['release']=='12.2.0'
assert x['milestone']=='12.2.0'
assert x['runtime_authority']=='python-fastapi-backend'
assert x['wordpress_required'] is False
assert x['principles']['analyze_original_language_first'] is True
assert x['principles']['translation_is_derived_representation'] is True
assert x['principles']['transliteration_is_derived_representation'] is True
assert x['scope']['global_source_federation'] is False
assert x['scope']['automatic_entity_resolution'] is False
assert x['scope']['automatic_citation_resolution'] is False
assert x['scope']['automatic_evidence_resolution'] is False
assert x['database_migration']=='042_multilingual_cross_language_research_intelligence.sql'
assert x['next_boundary']=='global-source-federation-original-language-research'
PYMANIFEST1220

RL_KEY="$(docker exec "$CONTAINER" printenv SC_RL_BACKEND_API_KEY)"
[[ -n "$RL_KEY" ]] || fail "SC_RL_BACKEND_API_KEY missing in running container"

curl -fsS \
  -H "X-SC-RL-Key: $RL_KEY" \
  http://127.0.0.1:8093/v1/research-librarian/multilingual-research/capabilities \
  > "$TMP/multilingual-capabilities.json"

python3 - "$TMP/multilingual-capabilities.json" <<'PYCAPS1220'
import json,sys
x=json.load(open(sys.argv[1]))['data']
assert x['milestone']=='12.2.0'
assert x['original_language_lineage'] is True
assert x['derived_representation_lineage'] is True
assert x['parallel_text_alignment'] is True
assert x['cross_language_query_plans'] is True
assert x['cross_language_retrieval_receipts'] is True
assert x['immutable_snapshots'] is True
PYCAPS1220

docker exec -i "$CONTAINER" python - <<'PYVERIFY1220'
from pathlib import Path
import tempfile

from app.main import app
from app.contracts.multilingual_cross_language_research import (
    MultilingualResearchCreateRequest,
    LanguageProfileAddRequest,
    OriginalLanguageSourceTextAddRequest,
    DerivedLanguageRepresentationAddRequest,
    TextAlignmentAddRequest,
    CrossLanguageQueryPlanAddRequest,
    CrossLanguageRetrievalReceiptAddRequest,
    MultilingualResearchSnapshotRequest,
)
from app.services.multilingual_cross_language_research import (
    MultilingualCrossLanguageResearchStore,
    get_multilingual_cross_language_research_store,
)
from app.services.independent_research_librarian_api import api_manifest,capabilities

prod=get_multilingual_cross_language_research_store()
assert prod.backend=='postgres'

with prod._postgres() as c:
    for table in [
        'sc_rl_multilingual_research_projects',
        'sc_rl_multilingual_research_events',
        'sc_rl_multilingual_research_snapshots',
    ]:
        row=c.execute("SELECT to_regclass(%s) AS t",(table,)).fetchone()
        assert row['t'] is not None, table

with tempfile.TemporaryDirectory() as td:
    store=MultilingualCrossLanguageResearchStore(sqlite_path=Path(td)/'multilingual.sqlite3')
    project=store.create(MultilingualResearchCreateRequest(
        actor_ref='identity:deploy-certification',
        title='v12.2.0 multilingual certification',
        objective='Certify original-language-first provenance and cross-language research objects.',
    ))
    rid=project['multilingual_research_id']

    fa=store.add_language_profile(rid,LanguageProfileAddRequest(
        actor_ref='identity:deploy-certification',
        language_tag='fa',
        language_name='Persian',
        script_code='Arab',
        direction='rtl',
        identification_method='source-metadata',
    ))['language_profiles'][-1]['language_profile_id']

    en=store.add_language_profile(rid,LanguageProfileAddRequest(
        actor_ref='identity:deploy-certification',
        language_tag='en',
        language_name='English',
        script_code='Latn',
        direction='ltr',
        identification_method='source-metadata',
    ))['language_profiles'][-1]['language_profile_id']

    project=store.add_source_text(rid,OriginalLanguageSourceTextAddRequest(
        actor_ref='identity:deploy-certification',
        label='Original Persian source',
        source_ref='library:source:cert-fa',
        language_profile_id=fa,
        text_ref='library:text:cert-fa',
    ))
    sid=project['source_texts'][-1]['source_text_id']

    project=store.add_derived_representation(rid,DerivedLanguageRepresentationAddRequest(
        actor_ref='identity:deploy-certification',
        label='Certification translation',
        source_text_id=sid,
        representation_type='translation',
        target_language_profile_id=en,
        derived_text_ref='workspace:translation:cert',
        method='hybrid',
        transformation_refs=['workspace:translation-job:cert'],
    ))
    did=project['derived_representations'][-1]['derived_representation_id']

    project=store.add_alignment(rid,TextAlignmentAddRequest(
        actor_ref='identity:deploy-certification',
        source_text_id=sid,
        derived_representation_id=did,
        granularity='sentence',
        alignment_ref='workspace:alignment:cert',
        segment_count=2,
        method='hybrid',
    ))
    assert project['alignments'][-1]['semantic_equivalence_not_inferred'] is True

    project=store.add_query_plan(rid,CrossLanguageQueryPlanAddRequest(
        actor_ref='identity:deploy-certification',
        label='Original-first query',
        query_ref='session:query:cert',
        source_language_profile_id=fa,
        target_language_profile_ids=[fa,en],
        strategy='original-language-first',
        derived_query_refs=['workspace:query:cert-en'],
    ))
    qid=project['query_plans'][-1]['query_plan_id']

    project=store.add_retrieval_receipt(rid,CrossLanguageRetrievalReceiptAddRequest(
        actor_ref='identity:deploy-certification',
        query_plan_id=qid,
        execution_ref='librarian:retrieval:cert',
        result_refs=['library:source:cert-fa'],
        result_language_profile_ids=[fa],
    ))
    assert project['retrieval_receipts'][-1]['cross_language_results_require_review'] is True

    lineage=store.lineage(rid)
    assert lineage['governance']['original_language_precedes_derived_representations'] is True
    ready=store.readiness(rid)
    assert ready['ready_for_cross_language_research'] is True
    core=store.core_candidate(rid)
    assert core['automatic_entity_resolution'] is False
    assert core['automatic_citation_resolution'] is False
    assert core['automatic_evidence_resolution'] is False
    snap=store.freeze_snapshot(MultilingualResearchSnapshotRequest(
        actor_ref='identity:deploy-certification',
        multilingual_research_id=rid,
    ))
    assert len(snap['snapshot_hash'])==64

paths={getattr(r,'path','') for r in app.routes}
required={
 '/v1/research-librarian/multilingual-research/manifest',
 '/v1/research-librarian/multilingual-research/capabilities',
 '/v1/research-librarian/multilingual-research/projects',
 '/v1/research-librarian/multilingual-research/projects/{multilingual_research_id}/language-profiles',
 '/v1/research-librarian/multilingual-research/projects/{multilingual_research_id}/source-texts',
 '/v1/research-librarian/multilingual-research/projects/{multilingual_research_id}/derived-representations',
 '/v1/research-librarian/multilingual-research/projects/{multilingual_research_id}/alignments',
 '/v1/research-librarian/multilingual-research/projects/{multilingual_research_id}/query-plans',
 '/v1/research-librarian/multilingual-research/projects/{multilingual_research_id}/retrieval-receipts',
 '/v1/research-librarian/multilingual-research/projects/{multilingual_research_id}/lineage',
 '/v1/research-librarian/multilingual-research/projects/{multilingual_research_id}/core-candidate',
 '/v1/research-librarian/multilingual-research/snapshots/freeze',
}
assert not(required-paths), required-paths

m=api_manifest()
c=capabilities()
assert m['scope']['multilingual_cross_language_research'] is True
assert m['next_boundary']=='global-source-federation-original-language-research'
assert c['milestone']=='12.2.0'
assert c['multilingual_cross_language_research'] is True
assert c['global_source_federation'] is False

print('PASS: migration 042 multilingual research tables active on Postgres')
print('PASS: original-language-first research lineage certified')
print('PASS: translation/transliteration remain derived representations with provenance')
print('PASS: cross-language query plans and retrieval receipts certified')
print('PASS: v12.3 global source federation remains deferred')
print('PASS: v12.4 entity/citation/evidence resolution remains deferred')
print('PASS: next boundary is v12.3.0 Global Source Federation & Original-Language Research')
PYVERIFY1220

echo "PASS: Research Librarian AI v12.2.0 Multilingual & Cross-Language Research Intelligence backend deployed and verified."
echo "NEXT: Install the optional WordPress v12.2.0 package and verify /wp-json/sc-research-librarian-ai/v1/multilingual-research."
