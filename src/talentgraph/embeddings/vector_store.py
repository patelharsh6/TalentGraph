"""Vector store interface with ChromaDB (runtime) and NumPy (tests) implementations."""

from dataclasses import dataclass
from typing import Any, Protocol

import numpy as np
from numpy.typing import NDArray

Metadata = dict[str, str | int | float | bool]


@dataclass(frozen=True)
class VectorHit:
    id: str
    score: float  # cosine similarity, higher is closer
    metadata: Metadata


class VectorStore(Protocol):
    def upsert(
        self, ids: list[str], vectors: NDArray[np.float32], metadatas: list[Metadata]
    ) -> None: ...

    def query(
        self, vector: NDArray[np.float32], k: int, where: Metadata | None = None
    ) -> list[VectorHit]: ...

    def delete(self, ids: list[str]) -> None: ...

    def count(self) -> int: ...

    def ids(self) -> list[str]: ...


class NumpyVectorStore:
    """In-memory brute-force cosine store. Expects L2-normalized vectors."""

    def __init__(self) -> None:
        self._ids: list[str] = []
        self._vectors: list[NDArray[np.float32]] = []
        self._meta: list[Metadata] = []

    def upsert(
        self, ids: list[str], vectors: NDArray[np.float32], metadatas: list[Metadata]
    ) -> None:
        for id_, vec, meta in zip(ids, vectors, metadatas, strict=True):
            if id_ in self._ids:
                i = self._ids.index(id_)
                self._vectors[i], self._meta[i] = vec, meta
            else:
                self._ids.append(id_)
                self._vectors.append(vec)
                self._meta.append(meta)

    def query(
        self, vector: NDArray[np.float32], k: int, where: Metadata | None = None
    ) -> list[VectorHit]:
        if not self._ids:
            return []
        scores = np.stack(self._vectors) @ vector
        hits = [
            VectorHit(self._ids[i], float(scores[i]), self._meta[i])
            for i in np.argsort(-scores)
            if where is None or all(self._meta[i].get(key) == val for key, val in where.items())
        ]
        return hits[:k]

    def delete(self, ids: list[str]) -> None:
        for id_ in ids:
            if id_ in self._ids:
                i = self._ids.index(id_)
                del self._ids[i], self._vectors[i], self._meta[i]

    def count(self) -> int:
        return len(self._ids)

    def ids(self) -> list[str]:
        return list(self._ids)


class ChromaVectorStore:
    """ChromaDB HTTP client, one collection per store, cosine space."""

    def __init__(self, host: str, port: int, collection: str) -> None:
        import chromadb

        self._client: Any = chromadb.HttpClient(host=host, port=port)
        self._col: Any = self._client.get_or_create_collection(
            collection, metadata={"hnsw:space": "cosine"}
        )

    def upsert(
        self, ids: list[str], vectors: NDArray[np.float32], metadatas: list[Metadata]
    ) -> None:
        self._col.upsert(ids=ids, embeddings=vectors.tolist(), metadatas=metadatas)

    def query(
        self, vector: NDArray[np.float32], k: int, where: Metadata | None = None
    ) -> list[VectorHit]:
        res = self._col.query(query_embeddings=[vector.tolist()], n_results=k, where=where)
        return [
            VectorHit(id_, 1.0 - float(dist), meta or {})
            for id_, dist, meta in zip(
                res["ids"][0], res["distances"][0], res["metadatas"][0], strict=True
            )
        ]

    def delete(self, ids: list[str]) -> None:
        self._col.delete(ids=ids)

    def count(self) -> int:
        return int(self._col.count())

    def ids(self) -> list[str]:
        return [str(i) for i in self._col.get(include=[])["ids"]]

    def heartbeat(self) -> int:
        return int(self._client.heartbeat())
