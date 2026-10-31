"""Skill index query helper (Step 3.3, plan §6.2).

Provides nearest-neighbor similarity search over the 9,642 canonical skills using
either ChromaDB (when running in container/compose) or an in-memory Numpy store
(offline / unit tests).
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
DEFAULT_CACHE_PATH = ROOT / "data" / ".checkpoints" / "skills_embedded.npz"


class SkillIndex:
    """Query helper over the skills embedding index."""

    def __init__(self, store: VectorStore, encoder: Encoder | None = None) -> None:
        self.store = store
        self.encoder = encoder or Encoder.get()

    def query(self, text: str, k: int = 5, where: Metadata | None = None) -> list[VectorHit]:
        """Embed a skill text and return the top-k nearest skills by cosine similarity."""
        vec = self.encoder.encode([text])[0]
        return self.store.query(vec, k=k, where=where)

    def query_vector(
        self, vector: NDArray[np.float32], k: int = 5, where: Metadata | None = None
    ) -> list[VectorHit]:
        """Return the top-k nearest skills for a precomputed embedding vector."""
        return self.store.query(vector, k=k, where=where)

    def count(self) -> int:
        return self.store.count()

    @classmethod
    def from_numpy_cache(cls, cache_path: Path | str | None = None) -> SkillIndex:
        """Load an in-memory NumpyVectorStore from a precomputed .npz file."""
        path = Path(cache_path or DEFAULT_CACHE_PATH)
        if not path.is_file():
            # If not yet precomputed, compute it once
            from scripts.build_skill_embeddings import build_skill_embeddings

            path = build_skill_embeddings(path)

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
            metas = [{"slug": id_} for id_ in ids]

        store = NumpyVectorStore()
        store.upsert(ids, vectors, metas)
        return cls(store=store)

    @classmethod
    def from_chroma_or_fallback(cls) -> SkillIndex:
        """Connect to ChromaDB if reachable and seeded; otherwise load the Numpy store."""
        settings = get_settings()
        try:
            chroma = ChromaVectorStore(settings.chroma_host, settings.chroma_port, "skills")
            if chroma.count() > 0:
                return cls(store=chroma)
        except Exception:
            pass
        return cls.from_numpy_cache()


@lru_cache(maxsize=1)
def get_skill_index() -> SkillIndex:
    """Cached singleton instance of the skill index."""
    return SkillIndex.from_chroma_or_fallback()
