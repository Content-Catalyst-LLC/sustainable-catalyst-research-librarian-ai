from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import base64
import hashlib
import hmac
import json
from pathlib import Path
import secrets
import sqlite3
import threading
from typing import Any, Iterator
import uuid

from ..config import settings
from ..database_identity import validate_schema_name
from ..contracts.identity_session_access import (
    IDENTITY_SCHEMA,
    AUTH_SESSION_SCHEMA,
    ACCESS_CONTEXT_SCHEMA,
    IdentityProvisionRequest,
)

try:
    import psycopg
    from psycopg.rows import dict_row
    from psycopg.types.json import Jsonb
except ImportError:
    psycopg=None
    dict_row=None
    Jsonb=None


ROLE_PERMISSIONS: dict[str, tuple[str, ...]] = {
    "owner": (
        "research:read","research:write","project:read","project:write",
        "session:read","session:write","identity:admin",
    ),
    "editor": (
        "research:read","research:write","project:read","project:write",
        "session:read","session:write",
    ),
    "researcher": (
        "research:read","research:write","project:read","project:write",
        "session:read","session:write",
    ),
    "viewer": ("research:read","project:read","session:read"),
}
WRITE_ROLES = frozenset({"owner","editor","researcher"})
ADMIN_ROLES = frozenset({"owner"})


def _now_dt() -> datetime:
    return datetime.now(timezone.utc)

def _now() -> str:
    return _now_dt().isoformat()

def _normalize_email(value: str) -> str:
    email=(value or "").strip().lower()
    if len(email)<3 or "@" not in email or email.startswith("@") or email.endswith("@"):
        raise ValueError("A valid email address is required.")
    return email

def _token_hash(token: str) -> str:
    return hashlib.sha256((token or "").encode("utf-8")).hexdigest()

def _password_hash(password: str, salt: bytes) -> str:
    raw=hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=2**14,
        r=8,
        p=1,
        dklen=32,
    )
    return base64.urlsafe_b64encode(raw).decode("ascii")

def _new_password_material(password: str) -> tuple[str,str]:
    salt=secrets.token_bytes(16)
    return base64.urlsafe_b64encode(salt).decode("ascii"), _password_hash(password,salt)

def _verify_password(password: str, salt_text: str, expected: str) -> bool:
    try:
        salt=base64.urlsafe_b64decode(salt_text.encode("ascii"))
        actual=_password_hash(password,salt)
        return hmac.compare_digest(actual,expected)
    except Exception:
        return False

def _parse_utc(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value,datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        parsed=datetime.fromisoformat(str(value).replace("Z","+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except Exception:
        return None


@dataclass(frozen=True)
class IdentityAccessContext:
    auth_mode: str
    identity_id: str = ""
    email: str = ""
    display_name: str = ""
    role: str = ""
    permissions: tuple[str,...] = ()
    auth_session_id: str = ""

    @property
    def identity_ref(self) -> str:
        return f"identity:{self.identity_id}" if self.identity_id else ""

    @property
    def is_integration_key(self) -> bool:
        return self.auth_mode == "integration-key"

    @property
    def can_write(self) -> bool:
        return self.is_integration_key or self.role in WRITE_ROLES

    @property
    def is_admin(self) -> bool:
        return self.is_integration_key or self.role in ADMIN_ROLES

    def public(self) -> dict[str,Any]:
        return {
            "schema":ACCESS_CONTEXT_SCHEMA,
            "auth_mode":self.auth_mode,
            "identity_id":self.identity_id,
            "identity_ref":self.identity_ref,
            "email":self.email,
            "display_name":self.display_name,
            "role":self.role,
            "permissions":list(self.permissions),
            "auth_session_id":self.auth_session_id,
            "can_write":self.can_write,
            "is_admin":self.is_admin,
        }


class IdentitySessionStore:
    def __init__(self, sqlite_path: Path | None = None) -> None:
        self.backend = "postgres" if settings.database_backend == "postgres" and sqlite_path is None else "sqlite"
        self.sqlite_path = sqlite_path or (settings.data_dir / "identity_session_access.sqlite3")
        self.database_schema = validate_schema_name(settings.database_schema)
        self._lock=threading.RLock()
        if self.backend=="postgres":
            if psycopg is None or Jsonb is None:
                raise RuntimeError("Postgres identity/session storage requires psycopg.")
            self._migrate_postgres()
        else:
            self.sqlite_path.parent.mkdir(parents=True,exist_ok=True)
            self._migrate_sqlite()

    @contextmanager
    def _sqlite(self) -> Iterator[sqlite3.Connection]:
        c=sqlite3.connect(self.sqlite_path,timeout=30,isolation_level=None)
        c.row_factory=sqlite3.Row
        c.execute("PRAGMA foreign_keys=ON")
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA busy_timeout=30000")
        try: yield c
        finally: c.close()

    @contextmanager
    def _postgres(self, migration: bool=False) -> Iterator[Any]:
        url=(settings.direct_database_url if migration else settings.database_url) or settings.database_url
        c=psycopg.connect(url,autocommit=False,row_factory=dict_row)
        c.execute(f'SET search_path TO "{self.database_schema}"')
        try: yield c
        finally: c.close()

    def _migrate_sqlite(self) -> None:
        with self._lock,self._sqlite() as c:
            c.executescript("""
CREATE TABLE IF NOT EXISTS identities(
 identity_id TEXT PRIMARY KEY,
 email TEXT NOT NULL UNIQUE,
 display_name TEXT NOT NULL,
 role TEXT NOT NULL,
 status TEXT NOT NULL,
 password_salt TEXT NOT NULL,
 password_hash TEXT NOT NULL,
 failed_login_count INTEGER NOT NULL DEFAULT 0,
 locked_until TEXT,
 created_utc TEXT NOT NULL,
 updated_utc TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_identities_role ON identities(role,status);
CREATE TABLE IF NOT EXISTS identity_sessions(
 auth_session_id TEXT PRIMARY KEY,
 identity_id TEXT NOT NULL,
 token_hash TEXT NOT NULL UNIQUE,
 state TEXT NOT NULL,
 client_label TEXT NOT NULL DEFAULT '',
 created_utc TEXT NOT NULL,
 expires_utc TEXT NOT NULL,
 last_seen_utc TEXT NOT NULL,
 revoked_utc TEXT,
 revoke_reason TEXT NOT NULL DEFAULT '',
 FOREIGN KEY(identity_id) REFERENCES identities(identity_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_identity_sessions_identity
 ON identity_sessions(identity_id,state,expires_utc);
CREATE INDEX IF NOT EXISTS idx_identity_sessions_expiry
 ON identity_sessions(state,expires_utc);
CREATE TABLE IF NOT EXISTS identity_access_events(
 event_id TEXT PRIMARY KEY,
 identity_id TEXT NOT NULL DEFAULT '',
 auth_session_id TEXT NOT NULL DEFAULT '',
 action TEXT NOT NULL,
 outcome TEXT NOT NULL,
 metadata_json TEXT NOT NULL DEFAULT '{}',
 created_utc TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_identity_access_events_identity
 ON identity_access_events(identity_id,created_utc);
""")

    def _migrate_postgres(self) -> None:
        ddl=[
"""CREATE TABLE IF NOT EXISTS sc_rl_identities(
 identity_id TEXT PRIMARY KEY,email TEXT NOT NULL UNIQUE,display_name TEXT NOT NULL,
 role TEXT NOT NULL,status TEXT NOT NULL,password_salt TEXT NOT NULL,password_hash TEXT NOT NULL,
 failed_login_count INTEGER NOT NULL DEFAULT 0,locked_until TIMESTAMPTZ,
 created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),updated_utc TIMESTAMPTZ NOT NULL DEFAULT now())""",
"CREATE INDEX IF NOT EXISTS idx_sc_rl_identities_role ON sc_rl_identities(role,status)",
"""CREATE TABLE IF NOT EXISTS sc_rl_identity_sessions(
 auth_session_id TEXT PRIMARY KEY,identity_id TEXT NOT NULL,token_hash TEXT NOT NULL UNIQUE,
 state TEXT NOT NULL,client_label TEXT NOT NULL DEFAULT '',created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),
 expires_utc TIMESTAMPTZ NOT NULL,last_seen_utc TIMESTAMPTZ NOT NULL DEFAULT now(),
 revoked_utc TIMESTAMPTZ,revoke_reason TEXT NOT NULL DEFAULT '',
 FOREIGN KEY(identity_id) REFERENCES sc_rl_identities(identity_id) ON DELETE CASCADE)""",
"CREATE INDEX IF NOT EXISTS idx_sc_rl_identity_sessions_identity ON sc_rl_identity_sessions(identity_id,state,expires_utc DESC)",
"CREATE INDEX IF NOT EXISTS idx_sc_rl_identity_sessions_expiry ON sc_rl_identity_sessions(state,expires_utc)",
"""CREATE TABLE IF NOT EXISTS sc_rl_identity_access_events(
 event_id TEXT PRIMARY KEY,identity_id TEXT NOT NULL DEFAULT '',auth_session_id TEXT NOT NULL DEFAULT '',
 action TEXT NOT NULL,outcome TEXT NOT NULL,metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
 created_utc TIMESTAMPTZ NOT NULL DEFAULT now())""",
"CREATE INDEX IF NOT EXISTS idx_sc_rl_identity_access_events_identity ON sc_rl_identity_access_events(identity_id,created_utc DESC)",
        ]
        with self._lock,self._postgres(migration=True) as c:
            for statement in ddl:c.execute(statement)
            c.commit()

    def _event(self,action:str,outcome:str,identity_id:str="",auth_session_id:str="",metadata:dict[str,Any]|None=None)->None:
        event_id=f"iae-{uuid.uuid4().hex}"
        meta=metadata or {}
        now=_now()
        try:
            if self.backend=="postgres":
                with self._postgres() as c:
                    c.execute(
                        "INSERT INTO sc_rl_identity_access_events(event_id,identity_id,auth_session_id,action,outcome,metadata,created_utc) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                        (event_id,identity_id,auth_session_id,action,outcome,Jsonb(meta),now),
                    );c.commit()
            else:
                with self._sqlite() as c:
                    c.execute(
                        "INSERT INTO identity_access_events(event_id,identity_id,auth_session_id,action,outcome,metadata_json,created_utc) VALUES(?,?,?,?,?,?,?)",
                        (event_id,identity_id,auth_session_id,action,outcome,json.dumps(meta,sort_keys=True),now),
                    )
        except Exception:
            # Audit logging must never expose credentials or alter authentication outcome.
            pass

    def identity_count(self)->int:
        if self.backend=="postgres":
            with self._postgres() as c:return int(c.execute("SELECT count(*) AS n FROM sc_rl_identities").fetchone()["n"])
        with self._sqlite() as c:return int(c.execute("SELECT count(*) AS n FROM identities").fetchone()["n"])

    def _identity_row_by_email(self,email:str)->dict[str,Any]|None:
        if self.backend=="postgres":
            with self._postgres() as c:
                row=c.execute("SELECT * FROM sc_rl_identities WHERE email=%s",(email,)).fetchone()
                return dict(row) if row else None
        with self._sqlite() as c:
            row=c.execute("SELECT * FROM identities WHERE email=?",(email,)).fetchone()
            return dict(row) if row else None

    def _identity_row(self,identity_id:str)->dict[str,Any]|None:
        if self.backend=="postgres":
            with self._postgres() as c:
                row=c.execute("SELECT * FROM sc_rl_identities WHERE identity_id=%s",(identity_id,)).fetchone()
                return dict(row) if row else None
        with self._sqlite() as c:
            row=c.execute("SELECT * FROM identities WHERE identity_id=?",(identity_id,)).fetchone()
            return dict(row) if row else None

    @staticmethod
    def _public_identity(row:dict[str,Any])->dict[str,Any]:
        return {
            "schema":IDENTITY_SCHEMA,
            "identity_id":str(row["identity_id"]),
            "identity_ref":f"identity:{row['identity_id']}",
            "email":str(row["email"]),
            "display_name":str(row["display_name"]),
            "role":str(row["role"]),
            "status":str(row["status"]),
            "permissions":list(ROLE_PERMISSIONS.get(str(row["role"]),())),
            "created_utc":str(row.get("created_utc") or ""),
            "updated_utc":str(row.get("updated_utc") or ""),
        }

    def provision(self,req:IdentityProvisionRequest)->dict[str,Any]:
        email=_normalize_email(req.email)
        if self._identity_row_by_email(email):
            raise ValueError("An identity with that email already exists.")
        identity_id=f"rli-{uuid.uuid4().hex}"
        salt,pw_hash=_new_password_material(req.password)
        now=_now()
        if self.backend=="postgres":
            with self._lock,self._postgres() as c:
                c.execute(
                    """INSERT INTO sc_rl_identities(identity_id,email,display_name,role,status,password_salt,password_hash,created_utc,updated_utc)
                       VALUES(%s,%s,%s,%s,'active',%s,%s,%s,%s)""",
                    (identity_id,email,req.display_name.strip(),req.role,salt,pw_hash,now,now),
                );c.commit()
        else:
            with self._lock,self._sqlite() as c:
                c.execute(
                    """INSERT INTO identities(identity_id,email,display_name,role,status,password_salt,password_hash,failed_login_count,created_utc,updated_utc)
                       VALUES(?,?,?,?,?,?,?,?,?,?)""",
                    (identity_id,email,req.display_name.strip(),req.role,"active",salt,pw_hash,0,now,now),
                )
        self._event("identity-provisioned","success",identity_id=identity_id,metadata={"role":req.role})
        return self._public_identity(self._identity_row(identity_id) or {})

    def list_identities(self,limit:int=100)->list[dict[str,Any]]:
        limit=max(1,min(500,int(limit)))
        if self.backend=="postgres":
            with self._postgres() as c:
                rows=c.execute("SELECT * FROM sc_rl_identities ORDER BY created_utc ASC LIMIT %s",(limit,)).fetchall()
        else:
            with self._sqlite() as c:
                rows=c.execute("SELECT * FROM identities ORDER BY created_utc ASC LIMIT ?",(limit,)).fetchall()
        return [self._public_identity(dict(row)) for row in rows]

    def authenticate(self,email:str,password:str,client_label:str="")->tuple[dict[str,Any],str,dict[str,Any]]:
        normalized=_normalize_email(email)
        row=self._identity_row_by_email(normalized)
        generic="Invalid email or password."
        if not row:
            self._event("login","failure",metadata={"reason":"invalid-credentials"})
            raise ValueError(generic)
        identity_id=str(row["identity_id"])
        if str(row.get("status"))!="active":
            self._event("login","failure",identity_id=identity_id,metadata={"reason":"disabled"})
            raise PermissionError("Identity is disabled.")
        locked=_parse_utc(row.get("locked_until"))
        now_dt=_now_dt()
        if locked and locked>now_dt:
            self._event("login","failure",identity_id=identity_id,metadata={"reason":"locked"})
            raise PermissionError("Identity is temporarily locked after repeated failed logins.")
        if not _verify_password(password,str(row["password_salt"]),str(row["password_hash"])):
            failures=int(row.get("failed_login_count") or 0)+1
            locked_until=None
            if failures>=int(settings.identity_login_failure_limit):
                locked_until=now_dt+timedelta(seconds=int(settings.identity_login_lock_seconds))
                failures=0
            if self.backend=="postgres":
                with self._postgres() as c:
                    c.execute(
                        "UPDATE sc_rl_identities SET failed_login_count=%s,locked_until=%s,updated_utc=%s WHERE identity_id=%s",
                        (failures,locked_until,_now(),identity_id),
                    );c.commit()
            else:
                with self._sqlite() as c:
                    c.execute(
                        "UPDATE identities SET failed_login_count=?,locked_until=?,updated_utc=? WHERE identity_id=?",
                        (failures,locked_until.isoformat() if locked_until else None,_now(),identity_id),
                    )
            self._event("login","failure",identity_id=identity_id,metadata={"reason":"invalid-credentials"})
            raise ValueError(generic)

        token=secrets.token_urlsafe(48)
        token_hash=_token_hash(token)
        auth_session_id=f"rls-{uuid.uuid4().hex}"
        created=now_dt
        expires=created+timedelta(seconds=int(settings.identity_session_ttl_seconds))
        label=(client_label or "")[:160]
        if self.backend=="postgres":
            with self._postgres() as c:
                c.execute(
                    "UPDATE sc_rl_identities SET failed_login_count=0,locked_until=NULL,updated_utc=%s WHERE identity_id=%s",
                    (_now(),identity_id),
                )
                c.execute(
                    """INSERT INTO sc_rl_identity_sessions(auth_session_id,identity_id,token_hash,state,client_label,created_utc,expires_utc,last_seen_utc)
                       VALUES(%s,%s,%s,'active',%s,%s,%s,%s)""",
                    (auth_session_id,identity_id,token_hash,label,created,expires,created),
                );c.commit()
        else:
            with self._sqlite() as c:
                c.execute(
                    "UPDATE identities SET failed_login_count=0,locked_until=NULL,updated_utc=? WHERE identity_id=?",
                    (_now(),identity_id),
                )
                c.execute(
                    """INSERT INTO identity_sessions(auth_session_id,identity_id,token_hash,state,client_label,created_utc,expires_utc,last_seen_utc)
                       VALUES(?,?,?,?,?,?,?,?)""",
                    (auth_session_id,identity_id,token_hash,"active",label,created.isoformat(),expires.isoformat(),created.isoformat()),
                )
        self._event("login","success",identity_id=identity_id,auth_session_id=auth_session_id)
        identity=self._public_identity(self._identity_row(identity_id) or row)
        session={
            "schema":AUTH_SESSION_SCHEMA,
            "auth_session_id":auth_session_id,
            "identity_id":identity_id,
            "state":"active",
            "client_label":label,
            "created_utc":created.isoformat(),
            "expires_utc":expires.isoformat(),
        }
        return identity,token,session

    def resolve_token(self,token:str,touch:bool=True)->IdentityAccessContext|None:
        if not token:return None
        digest=_token_hash(token)
        if self.backend=="postgres":
            with self._postgres() as c:
                row=c.execute(
                    """SELECT s.*,i.email,i.display_name,i.role,i.status AS identity_status
                       FROM sc_rl_identity_sessions s JOIN sc_rl_identities i ON i.identity_id=s.identity_id
                       WHERE s.token_hash=%s""",(digest,)
                ).fetchone()
                row=dict(row) if row else None
        else:
            with self._sqlite() as c:
                r=c.execute(
                    """SELECT s.*,i.email,i.display_name,i.role,i.status AS identity_status
                       FROM identity_sessions s JOIN identities i ON i.identity_id=s.identity_id
                       WHERE s.token_hash=?""",(digest,)
                ).fetchone()
                row=dict(r) if r else None
        if not row:return None
        if str(row.get("state"))!="active" or str(row.get("identity_status"))!="active":return None
        expires=_parse_utc(row.get("expires_utc"))
        if not expires or expires<=_now_dt():
            self.revoke(str(row["auth_session_id"]),"expired")
            return None
        if touch:
            now=_now()
            if self.backend=="postgres":
                with self._postgres() as c:
                    c.execute("UPDATE sc_rl_identity_sessions SET last_seen_utc=%s WHERE auth_session_id=%s",(now,row["auth_session_id"]));c.commit()
            else:
                with self._sqlite() as c:
                    c.execute("UPDATE identity_sessions SET last_seen_utc=? WHERE auth_session_id=?",(now,row["auth_session_id"]))
        role=str(row["role"])
        return IdentityAccessContext(
            auth_mode="identity-session",
            identity_id=str(row["identity_id"]),
            email=str(row["email"]),
            display_name=str(row["display_name"]),
            role=role,
            permissions=ROLE_PERMISSIONS.get(role,()),
            auth_session_id=str(row["auth_session_id"]),
        )

    def sessions_for_identity(self,identity_id:str,limit:int=100)->list[dict[str,Any]]:
        limit=max(1,min(500,int(limit)))
        if self.backend=="postgres":
            with self._postgres() as c:
                rows=c.execute(
                    "SELECT * FROM sc_rl_identity_sessions WHERE identity_id=%s ORDER BY created_utc DESC LIMIT %s",
                    (identity_id,limit),
                ).fetchall()
        else:
            with self._sqlite() as c:
                rows=c.execute(
                    "SELECT * FROM identity_sessions WHERE identity_id=? ORDER BY created_utc DESC LIMIT ?",
                    (identity_id,limit),
                ).fetchall()
        out=[]
        for raw in rows:
            row=dict(raw)
            out.append({
                "schema":AUTH_SESSION_SCHEMA,
                "auth_session_id":str(row["auth_session_id"]),
                "identity_id":str(row["identity_id"]),
                "state":str(row["state"]),
                "client_label":str(row.get("client_label") or ""),
                "created_utc":str(row.get("created_utc") or ""),
                "expires_utc":str(row.get("expires_utc") or ""),
                "last_seen_utc":str(row.get("last_seen_utc") or ""),
                "revoked_utc":str(row.get("revoked_utc") or ""),
                "revoke_reason":str(row.get("revoke_reason") or ""),
            })
        return out

    def revoke(self,auth_session_id:str,reason:str="user-request")->bool:
        now=_now()
        reason=(reason or "user-request")[:240]
        if self.backend=="postgres":
            with self._postgres() as c:
                result=c.execute(
                    """UPDATE sc_rl_identity_sessions SET state='revoked',revoked_utc=%s,revoke_reason=%s
                       WHERE auth_session_id=%s AND state='active'""",(now,reason,auth_session_id)
                );c.commit()
                changed=result.rowcount>0
        else:
            with self._sqlite() as c:
                result=c.execute(
                    """UPDATE identity_sessions SET state='revoked',revoked_utc=?,revoke_reason=?
                       WHERE auth_session_id=? AND state='active'""",(now,reason,auth_session_id)
                )
                changed=result.rowcount>0
        if changed:self._event("session-revoked","success",auth_session_id=auth_session_id,metadata={"reason":reason})
        return bool(changed)

    def revoke_all_for_identity(self,identity_id:str,reason:str)->int:
        sessions=self.sessions_for_identity(identity_id,500)
        count=0
        for session in sessions:
            if session["state"]=="active" and self.revoke(session["auth_session_id"],reason):
                count+=1
        return count

    def update_role(self,identity_id:str,role:str)->dict[str,Any]:
        if role not in ROLE_PERMISSIONS:raise ValueError("Invalid identity role.")
        if self.backend=="postgres":
            with self._postgres() as c:
                result=c.execute("UPDATE sc_rl_identities SET role=%s,updated_utc=%s WHERE identity_id=%s",(role,_now(),identity_id));c.commit()
        else:
            with self._sqlite() as c:
                result=c.execute("UPDATE identities SET role=?,updated_utc=? WHERE identity_id=?",(role,_now(),identity_id))
        if result.rowcount<1:raise ValueError("Identity not found.")
        self.revoke_all_for_identity(identity_id,"role-changed")
        return self._public_identity(self._identity_row(identity_id) or {})

    def update_status(self,identity_id:str,status_value:str)->dict[str,Any]:
        if status_value not in {"active","disabled"}:raise ValueError("Invalid identity status.")
        if self.backend=="postgres":
            with self._postgres() as c:
                result=c.execute("UPDATE sc_rl_identities SET status=%s,updated_utc=%s WHERE identity_id=%s",(status_value,_now(),identity_id));c.commit()
        else:
            with self._sqlite() as c:
                result=c.execute("UPDATE identities SET status=?,updated_utc=? WHERE identity_id=?",(status_value,_now(),identity_id))
        if result.rowcount<1:raise ValueError("Identity not found.")
        if status_value!="active":self.revoke_all_for_identity(identity_id,"identity-disabled")
        return self._public_identity(self._identity_row(identity_id) or {})

    def change_password(self,identity_id:str,current_password:str,new_password:str)->None:
        row=self._identity_row(identity_id)
        if not row or not _verify_password(current_password,str(row["password_salt"]),str(row["password_hash"])):
            raise ValueError("Current password is incorrect.")
        salt,pw_hash=_new_password_material(new_password)
        if self.backend=="postgres":
            with self._postgres() as c:
                c.execute("UPDATE sc_rl_identities SET password_salt=%s,password_hash=%s,updated_utc=%s WHERE identity_id=%s",(salt,pw_hash,_now(),identity_id));c.commit()
        else:
            with self._sqlite() as c:
                c.execute("UPDATE identities SET password_salt=?,password_hash=?,updated_utc=? WHERE identity_id=?",(salt,pw_hash,_now(),identity_id))
        self.revoke_all_for_identity(identity_id,"password-changed")
        self._event("password-changed","success",identity_id=identity_id)

    def capabilities(self)->dict[str,Any]:
        return {
            "schema":ACCESS_CONTEXT_SCHEMA,
            "release":"12.0.5",
            "milestone":"12.0.5",
            "backend":self.backend,
            "identity_count":self.identity_count(),
            "password_hash":"scrypt",
            "session_token_storage":"sha256-hash-only",
            "cookie_http_only":True,
            "cookie_same_site":"strict",
            "cookie_secure":bool(settings.identity_cookie_secure),
            "session_ttl_seconds":int(settings.identity_session_ttl_seconds),
            "login_failure_limit":int(settings.identity_login_failure_limit),
            "login_lock_seconds":int(settings.identity_login_lock_seconds),
            "roles":{role:list(perms) for role,perms in ROLE_PERMISSIONS.items()},
            "wordpress_required":False,
            "legacy_api_key_supported":True,
            "canonical_identity_state":"python-backend",
            "next_boundary":"thin-wordpress-adapter",
        }


_STORE:IdentitySessionStore|None=None
_STORE_LOCK=threading.Lock()

def get_identity_session_store()->IdentitySessionStore:
    global _STORE
    if _STORE is None:
        with _STORE_LOCK:
            if _STORE is None:_STORE=IdentitySessionStore()
    return _STORE

def integration_key_context()->IdentityAccessContext:
    return IdentityAccessContext(
        auth_mode="integration-key",
        role="integration",
        permissions=("research:read","research:write","project:read","project:write","session:read","session:write","identity:admin"),
    )

def assert_session_access(session:dict[str,Any],access:IdentityAccessContext)->None:
    if access.is_integration_key:return
    if str(session.get("client_ref") or "")!=access.identity_ref:
        raise PermissionError("Research session is not owned by the authenticated identity.")

def identity_access_manifest()->dict[str,Any]:
    return get_identity_session_store().capabilities()
