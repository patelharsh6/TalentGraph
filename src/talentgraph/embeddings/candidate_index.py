"""Step 6.1: Candidate index query helper (plan §6.4, §7.2).

Provides semantic nearest-neighbor search over the candidates collection using
either ChromaDB (`candidates` collection) or an in-memory Numpy store.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from talentgraph.config import get_settings
from talentgraph.embeddings.encoder import Encoder
from talentgraph.embeddings.vector_store import (
    ChromaVectorStore,
    Metadata,
    NumpyVectorStore,
    VectorHit,
    VectorStore,
)

ROOT = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_CANDIDATE_CACHE = ROOT / "data" / ".checkpoints" / "candidates_embedded.npz"


class CandidateIndex:
    """Query helper over the candidates embedding index."""

    def __init__(self, store: VectorStore, encoder: Encoder | None = None) -> None:
        self.store = store
        self.encoder = encoder or Encoder.get()

    def query(self, text: str, k: int = 10, where: Metadata | None = None) -> list[VectorHit]:
        """Embed a query text and return top-k nearest candidates."""
        vec = self.encoder.encode([text])[0]
        return self.store.query(vec, k=k, where=where)

    def query_vector(
        self, vector: NDArray[np.float32], k: int = 10, where: Metadata | None = None
    ) -> list[VectorHit]:
        """Return top-k nearest candidates for an existing embedding vector."""
        return self.store.query(vector, k=k, where=where)

    def upsert_candidate(
        self,
        candidate_id: str,
        document_text: str,
        metadata: Metadata,
    ) -> None:
        """Embed document text and upsert candidate record into the vector store."""
        vec = self.encoder.encode([document_text])[0]
        self.store.upsert(
            ids=[candidate_id],
            vectors=np.stack([vec]),
            metadatas=[metadata],
        )

    def count(self) -> int:
        return self.store.count()

    def ids(self) -> list[str]:
        return self.store.ids()

    @classmethod
    def from_numpy_cache(cls, cache_path: Path | str | None = None) -> CandidateIndex:
        """Load an in-memory NumpyVectorStore from a precomputed .npz file."""
        path = Path(cache_path or DEFAULT_CANDIDATE_CACHE)
        if not path.is_file():
            from scripts.index_candidates import build_candidate_embeddings

            path = build_candidate_embeddings(path)

        data = np.load(path, allow_pickle=True)
        ids = [str(x) for x in data["ids"]]
        vectors = data["vectors"].astype(np.float32)

        metas: list[Metadata] = []
        raw_metas = data.get("metas")
        if raw_metas is not None and len(raw_metas) == len(ids):
            for m in raw_metas:
                try:
                    metas.append(json.loads(str(m)))
                except Exception:
                    metas.append({})
        else:
            metas = [{} for _ in ids]

        store = NumpyVectorStore()
        store.upsert(ids, vectors, metas)
        return cls(store)


@lru_cache(maxsize=1)
def get_candidate_index(
    chroma_host: str | None = None,
    chroma_port: int | None = None,
    cache_path: Path | str | None = None,
) -> CandidateIndex:
    """Singleton getter for the candidate index."""
    settings = get_settings()
    host = chroma_host or settings.chroma_host
    port = chroma_port or settings.chroma_port

    try:
        store = ChromaVectorStore(host=host, port=port, collection="candidates")
        # Probe heartbeat to ensure Chroma is reachable
        store.heartbeat()
        return CandidateIndex(store)
    except Exception:
        # Fallback to local numpy store
        return CandidateIndex.from_numpy_cache(cache_path)
