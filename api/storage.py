"""Almacenamiento de casos de prueba.

Usa MongoDB Atlas si `MONGODB_URI` está definido; si no, cae a un
archivo JSON local (útil para desarrollo sin red).
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from pymongo import MongoClient
    from pymongo.collection import Collection
except ImportError:  # pymongo no instalado aún en alguna máquina
    MongoClient = None
    Collection = None  # type: ignore


_LOCAL_FILE = Path(__file__).parent.parent / "data" / "cases.json"


class CaseStorage:
    def __init__(self) -> None:
        self.uri = os.environ.get("MONGODB_URI", "").strip()
        self.db_name = os.environ.get("MONGODB_DB", "mathlite")
        self._collection: Collection | None = None
        self._using_mongo = False
        if self.uri and MongoClient is not None:
            try:
                client = MongoClient(self.uri, serverSelectionTimeoutMS=3000)
                client.admin.command("ping")
                self._collection = client[self.db_name]["cases"]
                self._using_mongo = True
            except Exception as e:
                print(f"[storage] no se pudo conectar a Mongo ({e}); usando archivo local")
        if not self._using_mongo:
            _LOCAL_FILE.parent.mkdir(parents=True, exist_ok=True)
            if not _LOCAL_FILE.exists():
                _LOCAL_FILE.write_text("[]")

    @property
    def backend(self) -> str:
        return "mongodb-atlas" if self._using_mongo else "local-json"

    # ---------- helpers ----------
    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _read_local(self) -> list[dict[str, Any]]:
        return json.loads(_LOCAL_FILE.read_text())

    def _write_local(self, data: list[dict[str, Any]]) -> None:
        _LOCAL_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    # ---------- API ----------
    def list(self) -> list[dict[str, Any]]:
        if self._using_mongo:
            return [
                {**doc, "_id": str(doc["_id"])}
                for doc in self._collection.find().sort("created_at", -1).limit(100)
            ]
        return list(reversed(self._read_local()))

    def create(self, title: str, source: str, result: dict | None = None) -> dict[str, Any]:
        doc = {
            "_id": str(uuid.uuid4()),
            "title": title.strip() or "(sin título)",
            "source": source,
            "result_summary": result or {},
            "created_at": self._now(),
        }
        if self._using_mongo:
            self._collection.insert_one(doc)
        else:
            data = self._read_local()
            data.append(doc)
            self._write_local(data)
        return doc

    def delete(self, case_id: str) -> bool:
        if self._using_mongo:
            res = self._collection.delete_one({"_id": case_id})
            return res.deleted_count > 0
        data = self._read_local()
        new = [d for d in data if d["_id"] != case_id]
        if len(new) == len(data):
            return False
        self._write_local(new)
        return True


storage = CaseStorage()
