"""Data-access repositories."""

from talentgraph.db.repositories.taxonomy import (
    AliasRecord,
    ImplicationRecord,
    RelationRecord,
    TaxonomyRepository,
    TaxonomySkill,
    get_taxonomy_repository,
)

__all__ = [
    "AliasRecord",
    "ImplicationRecord",
    "RelationRecord",
    "TaxonomyRepository",
    "TaxonomySkill",
    "get_taxonomy_repository",
]
