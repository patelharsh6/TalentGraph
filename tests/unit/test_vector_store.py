import numpy as np

from talentgraph.embeddings.vector_store import NumpyVectorStore


def _unit(*xs: float) -> np.ndarray:
    v = np.array(xs, dtype=np.float32)
    return v / np.linalg.norm(v)


def test_query_orders_by_cosine_and_filters() -> None:
    store = NumpyVectorStore()
    store.upsert(
        ["python", "java", "excel"],
        np.stack([_unit(1, 0), _unit(0.8, 0.2), _unit(0, 1)]),
        [{"type": "technical"}, {"type": "technical"}, {"type": "business"}],
    )
    hits = store.query(_unit(1, 0), k=2)
    assert [h.id for h in hits] == ["python", "java"]
    assert hits[0].score > hits[1].score
    assert [h.id for h in store.query(_unit(1, 0), k=5, where={"type": "business"})] == ["excel"]


def test_upsert_replaces_and_delete_removes() -> None:
    store = NumpyVectorStore()
    store.upsert(["a"], np.stack([_unit(1, 0)]), [{"v": 1}])
    store.upsert(["a"], np.stack([_unit(0, 1)]), [{"v": 2}])
    assert store.count() == 1
    assert store.query(_unit(0, 1), k=1)[0].metadata == {"v": 2}
    assert store.ids() == ["a"]
    store.delete(["a"])
    assert store.count() == 0
    assert store.ids() == []
