from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

import chromadb


@dataclass(frozen=True)
class DbConfig:
    path: str = "./db_data"
    collection: str = "images"


class VectorDb:
    """
    Minimal ChromaDB wrapper with a single process-level lock for writes.
    Keeps call sites stable when you later swap DB engines.
    """

    def __init__(self, cfg: DbConfig = DbConfig()):
        self.cfg = cfg
        self._client = chromadb.PersistentClient(path=cfg.path)
        self._collection = self._client.get_or_create_collection(name=cfg.collection)
        self._write_lock = threading.Lock()

    def upsert(
        self,
        *,
        id: str,
        embedding: List[float],
        document: str,
        metadata: Any,
    ) -> None:
        with self._write_lock:
            self._collection.upsert(
                ids=[id],
                embeddings=[embedding],
                documents=[document],
                metadatas=[metadata],
            )

    def get(self, *, id: str) -> Optional[Dict[str, Any]]:
        """
        Best-effort get by id. Returns None if not found.
        """
        try:
            res = self._collection.get(ids=[id], include=["metadatas", "documents", "embeddings"])
            ids = res.get("ids") or []
            if not ids:
                return None
            return {
                "id": ids[0],
                "metadata": (res.get("metadatas") or [None])[0],
                "document": (res.get("documents") or [None])[0],
                "embedding": (res.get("embeddings") or [None])[0],
            }
        except Exception:
            return None

    def get_metadatas(self, *, ids: Sequence[str]) -> Dict[str, Any]:
        """
        Best-effort bulk metadata fetch by ids.

        Returns mapping {id: metadata} for ids that exist in the collection.
        Missing ids are omitted.
        """
        try:
            ids_in = [i for i in ids if isinstance(i, str) and i]
            if not ids_in:
                return {}
            res = self._collection.get(ids=ids_in, include=["metadatas"])
            out: Dict[str, Any] = {}
            got_ids = res.get("ids") or []
            got_metas = res.get("metadatas") or []
            for i, mid in enumerate(got_ids):
                if not isinstance(mid, str) or not mid:
                    continue
                meta = got_metas[i] if i < len(got_metas) else None
                out[mid] = meta
            return out
        except Exception:
            return {}

    def query(self, *, embedding: List[float], n_results: int = 10) -> Dict[str, Any]:
        return self._collection.query(query_embeddings=[embedding], n_results=n_results)

    def delete_ids(self, *, ids: Sequence[str]) -> int:
        """
        Best-effort bulk delete by ids.

        Returns how many ids were requested for deletion (not how many existed).
        """
        try:
            ids_in = [i for i in ids if isinstance(i, str) and i]
            if not ids_in:
                return 0
            with self._write_lock:
                self._collection.delete(ids=ids_in)
            return len(ids_in)
        except Exception:
            return 0

