from __future__ import annotations

import json
from pathlib import Path
import threading
from typing import Iterable

from .config import settings
from .models import KnowledgeRecord, utc_now


class KnowledgeStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (settings.data_dir / "knowledge_index.json")
        self._lock = threading.RLock()
        self._records: dict[str, KnowledgeRecord] = {}
        self._meta: dict[str, str | int] = {
            "last_sync_utc": "",
            "source_site": "",
            "total_records": 0,
        }
        self.load()

    def load(self) -> None:
        with self._lock:
            if not self.path.exists():
                return
            try:
                payload = json.loads(self.path.read_text(encoding="utf-8"))
                records = payload.get("records", []) if isinstance(payload, dict) else []
                self._records = {record.id: record for record in (KnowledgeRecord.model_validate(item) for item in records)}
                meta = payload.get("meta", {}) if isinstance(payload, dict) else {}
                if isinstance(meta, dict):
                    self._meta.update(meta)
                self._meta["total_records"] = len(self._records)
            except (OSError, ValueError, TypeError):
                self._records = {}

    def save(self) -> None:
        payload = {
            "schema": "sc-research-librarian-knowledge-index/2.0",
            "meta": self._meta,
            "records": [record.model_dump() for record in self._records.values()],
        }
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        temporary.replace(self.path)

    def sync(self, records: Iterable[KnowledgeRecord], mode: str, source_site: str = "") -> dict[str, str | int]:
        incoming = list(records)
        with self._lock:
            if mode == "replace":
                self._records = {record.id: record for record in incoming}
            else:
                for record in incoming:
                    self._records[record.id] = record
            self._meta = {
                "last_sync_utc": utc_now(),
                "source_site": source_site,
                "total_records": len(self._records),
            }
            self.save()
            return dict(self._meta)

    def records(self) -> list[KnowledgeRecord]:
        with self._lock:
            return list(self._records.values())

    def summary(self) -> dict[str, str | int]:
        with self._lock:
            titles = {record.title.casefold().strip() for record in self._records.values() if record.title.strip()}
            return {
                **self._meta,
                "total_records": len(self._records),
                "indexed_titles": len(titles),
            }


store = KnowledgeStore()
