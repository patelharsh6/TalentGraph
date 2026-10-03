"""Process-wide sentence-transformers encoder (plan §4.3). Loaded once, warmed at startup."""

import threading
from typing import Any

import numpy as np
from numpy.typing import NDArray

from talentgraph.config import get_settings


class Encoder:
    _instance: "Encoder | None" = None
    _lock = threading.Lock()

    def __init__(self, model_name: str) -> None:
        from sentence_transformers import SentenceTransformer  # heavy import, keep lazy

        self.model_name = model_name
        self._model: Any = SentenceTransformer(model_name, device="cpu")

    @classmethod
    def get(cls) -> "Encoder":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(get_settings().embedding_model)
        return cls._instance

    @property
    def dim(self) -> int:
        return int(self._model.get_sentence_embedding_dimension())

    def encode(self, texts: list[str], *, batch_size: int = 64) -> NDArray[np.float32]:
        """L2-normalized embeddings, shape (len(texts), dim)."""
        vectors = self._model.encode(
            texts, batch_size=batch_size, normalize_embeddings=True, convert_to_numpy=True
        )
        return np.asarray(vectors, dtype=np.float32)
