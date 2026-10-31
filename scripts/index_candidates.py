"""Step 6.1: Back-fill and embed candidates into Chroma and NumPy checkpoint cache.

uv run python scripts/index_candidates.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from talentgraph.config import get_settings
from talentgraph.embeddings.encoder import Encoder
from talentgraph.embeddings.vector_store import ChromaVectorStore

ROOT = Path(__file__).resolve().parent.parent
PROFILES_DIR = ROOT / "data" / "profiles"
CACHE_PATH = ROOT / "data" / ".checkpoints" / "candidates_embedded.npz"


def build_candidate_embeddings(
    out_path: Path | None = None,
    profiles_dir: Path | None = None,
) -> Path:
    target = out_path or CACHE_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    p_dir = profiles_dir or PROFILES_DIR

    files = sorted(p_dir.glob("*.gt.json"))
    if not files:
        raise FileNotFoundError(f"No ground-truth profile files found in {p_dir}")

    ids: list[str] = []
    texts: list[str] = []
    metas: list[str] = []

    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        candidate_id = path.name.replace(".gt.json", "")

        summary = data.get("summary", "")
        skills = [s.get("raw") or s.get("canonical_slug", "") for s in data.get("skills", [])]
        titles = [exp.get("title", "") for exp in data.get("experience", []) if exp.get("title")]

        doc_text = f"Title: {', '.join(titles)}\nSummary: {summary}\nSkills: {', '.join(skills)}"

        meta_info = {
            "candidate_id": candidate_id,
            "pipeline_version": "0.1.0",
            "industry": data.get("meta", {}).get("industry", "general"),
            "seniority": data.get("meta", {}).get("seniority", "mid"),
            "total_years": float(data.get("meta", {}).get("total_experience_years", 3.0)),
        }

        ids.append(candidate_id)
        texts.append(doc_text)
        metas.append(json.dumps(meta_info))

    print(f"Encoding {len(texts)} candidate profiles with {get_settings().embedding_model}...")
    encoder = Encoder.get()
    vectors = encoder.encode(texts, batch_size=64)

    print(f"Saving candidate embeddings to {target}...")
    np.savez_compressed(
        target,
        ids=np.array(ids),
        vectors=vectors,
        metas=np.array(metas),
        model_name=get_settings().embedding_model,
    )
    print(f"Done. Saved shape: {vectors.shape}")

    # Also try Chroma if reachable
    settings = get_settings()
    try:
        chroma = ChromaVectorStore(
            host=settings.chroma_host,
            port=settings.chroma_port,
            collection="candidates",
        )
        chroma.heartbeat()
        parsed_metas = [json.loads(m) for m in metas]
        chroma.upsert(ids, vectors, parsed_metas)
        print(f"Successfully upserted {len(ids)} candidates into Chroma 'candidates' collection.")
    except Exception as exc:
        print(f"Chroma not reachable ({exc}); cached in-memory NumPy embeddings only.")

    return target


def main() -> int:
    parser = argparse.ArgumentParser(description="Index candidate profiles into vector store")
    parser.add_argument("--out", type=Path, default=CACHE_PATH)
    parser.add_argument("--profiles", type=Path, default=PROFILES_DIR)
    args = parser.parse_args()

    build_candidate_embeddings(out_path=args.out, profiles_dir=args.profiles)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
