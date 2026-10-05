from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib, json, sqlite3, threading
from pathlib import Path
from typing import Any, Iterator

from ..config import settings
from ..database_identity import validate_schema_name
from ..contracts.neural_research_intelligence import *

try:
    import psycopg
    from psycopg.rows import dict_row
    from psycopg.types.json import Jsonb
except ImportError:
    psycopg=None; dict_row=None; Jsonb=None

def _json(v:Any)->str:
    return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"),default=str)

def _sha(v:Any)->str:
    return hashlib.sha256(_json(v).encode("utf-8")).hexdigest()

def _now()->str:
    return datetime.now(timezone.utc).isoformat()

def _id(prefix:str,value:Any)->str:
    return prefix+_sha(value)[:32]

def _uniq(values:list[str])->list[str]:
    return list(dict.fromkeys(str(x).strip() for x in values if str(x).strip()))

class NeuralResearchIntelligenceStore:
    def __init__(self,sqlite_path:Path|None=None)->None:
        self.backend="postgres" if settings.database_backend=="postgres" and sqlite_path is None else "sqlite"
        self.sqlite_path=sqlite_path or (settings.data_dir/"neural_research_intelligence.sqlite3")
        self.database_schema=validate_schema_name(settings.database_schema)
        self._lock=threading.RLock()
        if self.backend=="postgres":
            if psycopg is None or Jsonb is None:
                raise RuntimeError("Postgres neural research intelligence storage requires psycopg.")
            self._migrate_postgres()
        else:
            self.sqlite_path.parent.mkdir(parents=True,exist_ok=True)
            self._migrate_sqlite()

    @contextmanager
    def _sqlite(self)->Iterator[sqlite3.Connection]:
        c=sqlite3.connect(self.sqlite_path,timeout=30,isolation_level=None)
        c.row_factory=sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA busy_timeout=30000")
        try:
            yield c
        finally:
            c.close()

    @contextmanager
    def _postgres(self,migration:bool=False)->Iterator[Any]:
        url=(settings.direct_database_url if migration else settings.database_url) or settings.database_url
        c=psycopg.connect(url,autocommit=False,row_factory=dict_row)
        c.execute(f'SET search_path TO "{self.database_schema}"')
        try:
            yield c
        finally:
            c.close()

    def _migrate_sqlite(self)->None:
        with self._lock,self._sqlite() as c:
            c.executescript("""
CREATE TABLE IF NOT EXISTS neural_research_projects(
 neural_research_id TEXT PRIMARY KEY,
 owner_ref TEXT NOT NULL,
 record_json TEXT NOT NULL,
 record_hash TEXT NOT NULL,
 created_utc TEXT NOT NULL,
 updated_utc TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_neural_research_projects_owner ON neural_research_projects(owner_ref);
CREATE TABLE IF NOT EXISTS neural_research_events(
 event_id INTEGER PRIMARY KEY AUTOINCREMENT,
 neural_research_id TEXT NOT NULL,
 event_type TEXT NOT NULL,
 actor_ref TEXT NOT NULL,
 payload_json TEXT NOT NULL,
 event_hash TEXT NOT NULL,
 created_utc TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_neural_research_events_project ON neural_research_events(neural_research_id);
CREATE TABLE IF NOT EXISTS neural_research_snapshots(
 snapshot_id TEXT PRIMARY KEY,
 neural_research_id TEXT NOT NULL,
 snapshot_hash TEXT NOT NULL,
 record_json TEXT NOT NULL,
 created_utc TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_neural_research_snapshots_project ON neural_research_snapshots(neural_research_id);
""")

    def _migrate_postgres(self)->None:
        with self._postgres(True) as c:
            for ddl in [
                """CREATE TABLE IF NOT EXISTS sc_rl_neural_research_projects(
 neural_research_id TEXT PRIMARY KEY,
 owner_ref TEXT NOT NULL,
 record JSONB NOT NULL,
 record_hash TEXT NOT NULL,
 created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),
 updated_utc TIMESTAMPTZ NOT NULL DEFAULT now()
)""",
                "CREATE INDEX IF NOT EXISTS idx_sc_rl_neural_research_projects_owner ON sc_rl_neural_research_projects(owner_ref)",
                """CREATE TABLE IF NOT EXISTS sc_rl_neural_research_events(
 event_id BIGSERIAL PRIMARY KEY,
 neural_research_id TEXT NOT NULL,
 event_type TEXT NOT NULL,
 actor_ref TEXT NOT NULL,
 payload JSONB NOT NULL,
 event_hash TEXT NOT NULL,
 created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
)""",
                "CREATE INDEX IF NOT EXISTS idx_sc_rl_neural_research_events_project ON sc_rl_neural_research_events(neural_research_id)",
                """CREATE TABLE IF NOT EXISTS sc_rl_neural_research_snapshots(
 snapshot_id TEXT PRIMARY KEY,
 neural_research_id TEXT NOT NULL,
 snapshot_hash TEXT NOT NULL,
 record JSONB NOT NULL,
 created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
)""",
                "CREATE INDEX IF NOT EXISTS idx_sc_rl_neural_research_snapshots_project ON sc_rl_neural_research_snapshots(neural_research_id)",
            ]:
                c.execute(ddl)
            c.commit()

    def _event(self,rid:str,typ:str,actor:str,payload:dict[str,Any])->None:
        created=_now()
        h=_sha({"neural_research_id":rid,"event_type":typ,"actor_ref":actor,"payload":payload,"created_utc":created})
        if self.backend=="postgres":
            with self._postgres() as c:
                c.execute(
                    "INSERT INTO sc_rl_neural_research_events(neural_research_id,event_type,actor_ref,payload,event_hash,created_utc) VALUES(%s,%s,%s,%s,%s,%s)",
                    (rid,typ,actor,Jsonb(payload),h,created),
                )
                c.commit()
        else:
            with self._lock,self._sqlite() as c:
                c.execute(
                    "INSERT INTO neural_research_events(neural_research_id,event_type,actor_ref,payload_json,event_hash,created_utc) VALUES(?,?,?,?,?,?)",
                    (rid,typ,actor,_json(payload),h,created),
                )

    def _save(self,rec:dict[str,Any])->dict[str,Any]:
        rec["updated_utc"]=_now()
        rec["record_hash"]=_sha({k:v for k,v in rec.items() if k!="record_hash"})
        if self.backend=="postgres":
            with self._postgres() as c:
                c.execute(
                    """INSERT INTO sc_rl_neural_research_projects(neural_research_id,owner_ref,record,record_hash,created_utc,updated_utc)
VALUES(%s,%s,%s,%s,%s,%s)
ON CONFLICT(neural_research_id) DO UPDATE SET owner_ref=EXCLUDED.owner_ref,record=EXCLUDED.record,record_hash=EXCLUDED.record_hash,updated_utc=EXCLUDED.updated_utc""",
                    (rec["neural_research_id"],rec["owner_ref"],Jsonb(rec),rec["record_hash"],rec["created_utc"],rec["updated_utc"]),
                )
                c.commit()
        else:
            with self._lock,self._sqlite() as c:
                c.execute(
                    "INSERT OR REPLACE INTO neural_research_projects(neural_research_id,owner_ref,record_json,record_hash,created_utc,updated_utc) VALUES(?,?,?,?,?,?)",
                    (rec["neural_research_id"],rec["owner_ref"],_json(rec),rec["record_hash"],rec["created_utc"],rec["updated_utc"]),
                )
        return rec

    def create(self,req:NeuralResearchCreateRequest)->dict[str,Any]:
        body=req.model_dump()
        actor=body.pop("actor_ref")
        seed={**body,"owner_ref":actor}
        rid=_id("neural-",seed)
        try:
            return self.get(rid)
        except ValueError:
            pass
        now=_now()
        rec={
            "schema":NEURAL_RESEARCH_SCHEMA,
            "neural_research_id":rid,
            "owner_ref":actor,
            **body,
            "model_references":[],
            "dataset_references":[],
            "representation_references":[],
            "inference_receipts":[],
            "runtime_handoffs":[],
            "review":{"state":"draft","actor_ref":actor,"note":"","updated_utc":now},
            "created_utc":now,
            "updated_utc":now,
            "governance":{
                "platform_core_model_contract_authority":True,
                "workspace_lab_workbench_execution_authority":True,
                "librarian_execution_authority":False,
                "model_weights_stored":False,
                "secrets_stored":False,
                "automatic_training":False,
                "automatic_inference":False,
                "automatic_model_ranking":False,
                "automatic_truth_promotion":False,
                "human_review_required":True,
            },
        }
        self._save(rec)
        self._event(rid,"neural-research.created",actor,{"project_ref":body.get("project_ref","")})
        return self.get(rid)

    def get(self,rid:str)->dict[str,Any]:
        if self.backend=="postgres":
            with self._postgres() as c:
                row=c.execute("SELECT record FROM sc_rl_neural_research_projects WHERE neural_research_id=%s",(rid,)).fetchone()
            if not row:
                raise ValueError("Neural research project not found.")
            return dict(row["record"])
        with self._lock,self._sqlite() as c:
            row=c.execute("SELECT record_json FROM neural_research_projects WHERE neural_research_id=?",(rid,)).fetchone()
        if not row:
            raise ValueError("Neural research project not found.")
        return json.loads(row["record_json"])

    def list(self,limit:int=100,owner_ref:str="")->dict[str,Any]:
        limit=max(1,min(500,int(limit)))
        if self.backend=="postgres":
            with self._postgres() as c:
                if owner_ref:
                    rows=c.execute(
                        "SELECT record FROM sc_rl_neural_research_projects WHERE owner_ref=%s ORDER BY updated_utc DESC LIMIT %s",
                        (owner_ref,limit),
                    ).fetchall()
                else:
                    rows=c.execute(
                        "SELECT record FROM sc_rl_neural_research_projects ORDER BY updated_utc DESC LIMIT %s",
                        (limit,),
                    ).fetchall()
            items=[dict(r["record"]) for r in rows]
        else:
            with self._lock,self._sqlite() as c:
                if owner_ref:
                    rows=c.execute(
                        "SELECT record_json FROM neural_research_projects WHERE owner_ref=? ORDER BY updated_utc DESC LIMIT ?",
                        (owner_ref,limit),
                    ).fetchall()
                else:
                    rows=c.execute(
                        "SELECT record_json FROM neural_research_projects ORDER BY updated_utc DESC LIMIT ?",
                        (limit,),
                    ).fetchall()
            items=[json.loads(r["record_json"]) for r in rows]
        return {"items":items,"count":len(items),"limit":limit,"owner_ref":owner_ref}

    def _append(self,rid:str,key:str,idkey:str,prefix:str,body:dict[str,Any],event_type:str,extra:dict[str,Any]|None=None)->dict[str,Any]:
        rec=self.get(rid)
        actor=body.pop("actor_ref")
        oid=_id(prefix,body)
        item={idkey:oid,**body,**(extra or {}),"created_utc":_now()}
        if not any(x.get(idkey)==oid for x in rec[key]):
            rec[key].append(item)
            self._save(rec)
            self._event(rid,event_type,actor,{idkey:oid})
        return self.get(rid)

    def add_model_reference(self,rid:str,req:NeuralModelReferenceAddRequest)->dict[str,Any]:
        body=req.model_dump()
        body["task_types"]=_uniq(body["task_types"])
        return self._append(
            rid,"model_references","model_reference_id","modelref-",body,"model-reference.added",
            {"reference_only":True,"weights_stored":False,"core_authority_preserved":True},
        )

    def add_dataset_reference(self,rid:str,req:NeuralDatasetReferenceAddRequest)->dict[str,Any]:
        body=req.model_dump()
        body["transformation_refs"]=_uniq(body["transformation_refs"])
        return self._append(
            rid,"dataset_references","dataset_reference_id","datasetref-",body,"dataset-reference.added",
            {"reference_only":True,"raw_dataset_copied":False},
        )

    def add_representation_reference(self,rid:str,req:NeuralRepresentationReferenceAddRequest)->dict[str,Any]:
        rec=self.get(rid)
        if req.model_reference_id and req.model_reference_id not in {x["model_reference_id"] for x in rec["model_references"]}:
            raise ValueError("model_reference_id is not registered.")
        body=req.model_dump()
        body["source_refs"]=_uniq(body["source_refs"])
        body["transformation_refs"]=_uniq(body["transformation_refs"])
        return self._append(
            rid,"representation_references","representation_reference_id","repr-",body,"representation-reference.added",
            {"representation_observed_not_interpreted":True,"vectors_stored_here":False},
        )

    def add_inference_receipt(self,rid:str,req:NeuralInferenceReceiptAddRequest)->dict[str,Any]:
        rec=self.get(rid)
        if req.model_reference_id not in {x["model_reference_id"] for x in rec["model_references"]}:
            raise ValueError("model_reference_id is not registered.")
        body=req.model_dump()
        body["input_refs"]=_uniq(body["input_refs"])
        body["output_refs"]=_uniq(body["output_refs"])
        return self._append(
            rid,"inference_receipts","inference_receipt_id","infer-",body,"inference-receipt.added",
            {"execution_performed_by_librarian":False,"receipt_is_observation_not_validity_verdict":True},
        )

    def prepare_handoff(self,rid:str,req:NeuralRuntimeHandoffPrepareRequest)->dict[str,Any]:
        rec=self.get(rid)
        known_models={x["model_reference_id"] for x in rec["model_references"]}
        known_datasets={x["dataset_reference_id"] for x in rec["dataset_references"]}
        known_reps={x["representation_reference_id"] for x in rec["representation_references"]}
        missing_models=[x for x in req.model_reference_ids if x not in known_models]
        missing_datasets=[x for x in req.dataset_reference_ids if x not in known_datasets]
        missing_reps=[x for x in req.representation_reference_ids if x not in known_reps]
        if missing_models or missing_datasets or missing_reps:
            raise ValueError(f"handoff references unknown objects: models={missing_models}, datasets={missing_datasets}, representations={missing_reps}")
        body=req.model_dump()
        body["model_reference_ids"]=_uniq(body["model_reference_ids"])
        body["dataset_reference_ids"]=_uniq(body["dataset_reference_ids"])
        body["representation_reference_ids"]=_uniq(body["representation_reference_ids"])
        body["expected_artifacts"]=_uniq(body["expected_artifacts"])
        actor=body.pop("actor_ref")
        packet={
            "schema":NEURAL_RUNTIME_HANDOFF_SCHEMA,
            "neural_research_id":rid,
            **body,
            "execution_requested":True,
            "execution_performed":False,
            "librarian_executes":False,
            "human_confirmation_required_at_target":True,
            "source_record_hash":rec["record_hash"],
        }
        hid=_id("neuralhandoff-",packet)
        packet["handoff_id"]=hid
        if not any(x["handoff_id"]==hid for x in rec["runtime_handoffs"]):
            rec["runtime_handoffs"].append(packet)
            self._save(rec)
            self._event(rid,"runtime-handoff.prepared",actor,{"handoff_id":hid,"target":req.target,"operation":req.operation})
        return {"handoff":packet,"project":self.get(rid)}

    def set_state(self,rid:str,req:NeuralResearchStateRequest)->dict[str,Any]:
        rec=self.get(rid)
        rec["review"]={"state":req.state,"actor_ref":req.actor_ref,"note":req.note,"updated_utc":_now()}
        self._save(rec)
        self._event(rid,"neural-research.state",req.actor_ref,{"state":req.state})
        return self.get(rid)

    def lineage(self,rid:str)->dict[str,Any]:
        rec=self.get(rid)
        return {
            "schema":NEURAL_RESEARCH_SCHEMA,
            "neural_research_id":rid,
            "record_hash":rec["record_hash"],
            "models":[
                {"model_reference_id":x["model_reference_id"],"model_ref":x["model_ref"],"model_hash":x.get("model_hash",""),"checkpoint_ref":x.get("checkpoint_ref",""),"core_model_ref":x.get("core_model_ref","")}
                for x in rec["model_references"]
            ],
            "datasets":[
                {"dataset_reference_id":x["dataset_reference_id"],"dataset_ref":x["dataset_ref"],"dataset_hash":x.get("dataset_hash",""),"transformation_refs":x.get("transformation_refs",[]),"core_dataset_ref":x.get("core_dataset_ref","")}
                for x in rec["dataset_references"]
            ],
            "representations":[
                {"representation_reference_id":x["representation_reference_id"],"model_reference_id":x.get("model_reference_id",""),"source_refs":x.get("source_refs",[]),"transformation_refs":x.get("transformation_refs",[]),"core_embedding_ref":x.get("core_embedding_ref","")}
                for x in rec["representation_references"]
            ],
            "inference_receipts":[
                {"inference_receipt_id":x["inference_receipt_id"],"model_reference_id":x["model_reference_id"],"execution_ref":x["execution_ref"],"runtime_target":x["runtime_target"],"checkpoint_ref":x.get("checkpoint_ref","")}
                for x in rec["inference_receipts"]
            ],
            "runtime_handoffs":[
                {"handoff_id":x["handoff_id"],"target":x["target"],"operation":x["operation"],"execution_performed":x["execution_performed"]}
                for x in rec["runtime_handoffs"]
            ],
            "governance":{"lineage_is_provenance_not_quality_score":True,"model_performance_not_inferred":True},
        }

    def readiness(self,rid:str)->dict[str,Any]:
        rec=self.get(rid)
        dims={
            "objective_present":bool(str(rec.get("objective","")).strip()),
            "model_reference_present":bool(rec["model_references"]),
            "dataset_reference_present":bool(rec["dataset_references"]),
            "provenance_hash_present":bool(rec.get("record_hash")),
            "execution_boundary_explicit":rec["governance"]["librarian_execution_authority"] is False,
        }
        blockers=[k.replace("_","-") for k,v in dims.items() if not v]
        return {
            "schema":NEURAL_RESEARCH_SCHEMA,
            "neural_research_id":rid,
            "ready_for_runtime_handoff":not blockers,
            "dimensions":dims,
            "blockers":blockers,
            "governance":{"readiness_is_structural_not_model_recommendation":True},
        }

    def core_candidate(self,rid:str)->dict[str,Any]:
        rec=self.get(rid)
        return {
            "schema":"sc-research-librarian-neural-core-candidate/1.0",
            "neural_research_id":rid,
            "record_hash":rec["record_hash"],
            "model_references":rec["model_references"],
            "dataset_references":rec["dataset_references"],
            "representation_references":rec["representation_references"],
            "inference_receipts":rec["inference_receipts"],
            "human_review_required":True,
            "platform_core_authority_required":True,
            "automatic_core_write":False,
            "automatic_truth_promotion":False,
        }

    def freeze_snapshot(self,req:NeuralResearchSnapshotRequest)->dict[str,Any]:
        rec=self.get(req.neural_research_id)
        payload={
            "schema":NEURAL_RESEARCH_SNAPSHOT_SCHEMA,
            "neural_research_id":req.neural_research_id,
            "record":rec,
            "lineage":self.lineage(req.neural_research_id),
            "readiness":self.readiness(req.neural_research_id),
            "label":req.label,
            "note":req.note,
            "frozen_utc":_now(),
            "governance":{"snapshot_is_provenance_not_model_validity_certification":True},
        }
        h=_sha(payload)
        sid="neuralsnap-"+h[:32]
        payload.update({"snapshot_id":sid,"snapshot_hash":h})
        if self.backend=="postgres":
            with self._postgres() as c:
                c.execute(
                    "INSERT INTO sc_rl_neural_research_snapshots(snapshot_id,neural_research_id,snapshot_hash,record) VALUES(%s,%s,%s,%s) ON CONFLICT(snapshot_id) DO NOTHING",
                    (sid,req.neural_research_id,h,Jsonb(payload)),
                )
                c.commit()
        else:
            with self._lock,self._sqlite() as c:
                c.execute(
                    "INSERT OR IGNORE INTO neural_research_snapshots(snapshot_id,neural_research_id,snapshot_hash,record_json,created_utc) VALUES(?,?,?,?,?)",
                    (sid,req.neural_research_id,h,_json(payload),payload["frozen_utc"]),
                )
        self._event(req.neural_research_id,"snapshot.frozen",req.actor_ref,{"snapshot_id":sid,"snapshot_hash":h})
        return payload

def neural_manifest()->dict[str,Any]:
    return {
        "schema":NEURAL_RESEARCH_SCHEMA,
        "release":settings.release_version,
        "milestone":"12.1.0",
        "name":"Neural Research Intelligence Foundation",
        "runtime_authority":"python-fastapi-backend",
        "wordpress_required":False,
        "durable":True,
        "objects":[
            "neural-research-project",
            "model-reference",
            "dataset-reference",
            "representation-reference",
            "inference-receipt",
            "runtime-handoff",
            "provenance-snapshot",
        ],
        "execution":{
            "librarian_executes_training":False,
            "librarian_executes_inference":False,
            "workspace_execution_target":True,
            "research_lab_execution_target":True,
            "workbench_execution_target":True,
            "external_runtime_receipts_supported":True,
        },
        "authority":{
            "platform_core_model_contract_authority":True,
            "librarian_research_context_authority":True,
            "specialist_runtime_execution_authority":True,
        },
        "governance":{
            "model_weights_stored":False,
            "secrets_stored":False,
            "automatic_model_ranking":False,
            "automatic_scientific_validity_verdict":False,
            "automatic_truth_promotion":False,
            "human_review_required":True,
        },
        "database_migration":"041_neural_research_intelligence_foundation.sql",
        "next_boundary":"multilingual-cross-language-research-intelligence",
    }

def capabilities()->dict[str,Any]:
    m=neural_manifest()
    return {
        **m,
        "model_provenance":True,
        "dataset_transformation_lineage":True,
        "representation_lineage":True,
        "inference_receipts":True,
        "runtime_handoffs":True,
        "immutable_snapshots":True,
        "core_candidates":True,
    }

_store=None

def get_neural_research_intelligence_store()->NeuralResearchIntelligenceStore:
    global _store
    if _store is None:
        _store=NeuralResearchIntelligenceStore()
    return _store
