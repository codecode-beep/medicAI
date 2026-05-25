import json
import logging
import os
from typing import Any

import faiss
import numpy as np

from app.config import get_settings
from app.services.gemini_service import gemini_service

settings = get_settings()
logger = logging.getLogger("medintel")
EMBEDDING_DIM = 768


class FAISSStore:
    def __init__(self) -> None:
        self.index_path = settings.faiss_index_path
        self.metadata_path = f"{self.index_path}_metadata.json"
        os.makedirs(os.path.dirname(self.index_path) or ".", exist_ok=True)
        self.index: faiss.IndexFlatL2 | None = None
        self.metadata: list[dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.index_path):
            self.index = faiss.read_index(self.index_path)
            if os.path.exists(self.metadata_path):
                with open(self.metadata_path) as f:
                    self.metadata = json.load(f)
        else:
            self.index = faiss.IndexFlatL2(EMBEDDING_DIM)
            self.metadata = []

    def _save(self) -> None:
        if self.index is not None:
            faiss.write_index(self.index, self.index_path)
            with open(self.metadata_path, "w") as f:
                json.dump(self.metadata, f)

    async def add_documents(
        self,
        texts: list[str],
        user_id: int,
        report_id: int,
        chunk_type: str = "report",
    ) -> None:
        if not texts or self.index is None:
            return
        embeddings = []
        for text in texts:
            emb = await gemini_service.generate_embedding(text)
            embeddings.append(emb)

        vectors = np.array(embeddings, dtype=np.float32)
        self.index.add(vectors)
        for i, text in enumerate(texts):
            self.metadata.append({
                "user_id": user_id,
                "report_id": report_id,
                "chunk_type": chunk_type,
                "text": text,
                "index": len(self.metadata),
            })
        self._save()

    async def search(
        self,
        query: str,
        user_id: int,
        top_k: int = 5,
        report_id: int | None = None,
    ) -> list[dict[str, Any]]:
        if self.index is None or self.index.ntotal == 0:
            return []

        query_emb = await gemini_service.generate_embedding(query)
        query_vec = np.array([query_emb], dtype=np.float32)
        k = min(top_k * 3, self.index.ntotal)
        distances, indices = self.index.search(query_vec, k)

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(self.metadata):
                continue
            meta = self.metadata[idx]
            if meta["user_id"] != user_id:
                continue
            if report_id and meta["report_id"] != report_id:
                continue
            results.append({**meta, "score": float(dist)})
            if len(results) >= top_k:
                break
        return results


faiss_store = FAISSStore()
