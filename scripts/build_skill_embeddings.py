"""Build or cache skill embeddings for offline/fast vector search (Step 3.3).

Generates L2-normalized embeddings for all 9,642 canonical skills using the base
sentence-transformer model (`all-MiniLM-L6-v2`) and saves them to
`data/.checkpoints/skills_embedded.npz`.
"""

import json
from pathlib import Path

import numpy as np

from talentgraph.config import get_settings
from talentgraph.db.repositories.taxonomy import get_taxonomy_repository
from talentgraph.embeddings.encoder import Encoder

ROOT = Path(__file__).resolve().parent.parent
CACHE_PATH = ROOT / "data" / ".checkpoints" / "skills_embedded.npz"


def build_skill_embeddings(out_path: Path | None = None) -> Path:
    target = out_path or CACHE_PATH
    target.parent.mkdir(parents=True, exist_ok=True)

    repo = get_taxonomy_repository()
    skills = repo.skills
    slug_to_aliases: dict[str, list[str]] = {}
    for a in repo.aliases:
        slug_to_aliases.setdefault(a.slug, []).append(a.alias)

    ids: list[str] = []
    texts: list[str] = []
    metas: list[str] = []

    for s in skills:
        top = [x for x in dict.fromkeys(slug_to_aliases.get(s.slug, [])) if x != s.name][:3]
        alias_str = ", ".join(top)
        alias_text = f" (also known as {alias_str})" if top else ""
        desc = f": {s.description}" if s.description else ""
        ids.append(s.slug)
        texts.append(f"{s.name}{alias_text}{desc}")
        metas.append(
            json.dumps(
                {
                    "type": s.type,
                    "level": s.level,
                    "parent_slug": s.parent_slug or "",
                    "name": s.name,
                }
            )
        )

    print(f"Encoding {len(texts)} skills with {get_settings().embedding_model}...")
    encoder = Encoder.get()
    vectors = encoder.encode(texts, batch_size=256)

    print(f"Saving embeddings to {target}...")
    np.savez_compressed(
        target,
        ids=np.array(ids),
        vectors=vectors,
        metas=np.array(metas),
        model_name=get_settings().embedding_model,
    )
    print(f"Done. Saved shape: {vectors.shape}")
    return target


if __name__ == "__main__":
    build_skill_embeddings()
