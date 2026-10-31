"""Taxonomy repository (Step 3.1, plan §6.2, ADR-0001).

Loads and caches the 4-level taxonomy (Domain -> Category -> Subcategory -> Skill),
alias index (15,000+ entries), implication rules and relation edges.
Cached in memory per taxonomy_version.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from talentgraph.config import get_settings


def normalize_alias_text(text: str) -> str:
    """Normalize alias text (identical to `aliases.csv:alias_normalized`)."""
    return re.sub(r"[\s\-_/.]+", " ", text.lower().strip()).strip()


@dataclass(frozen=True)
class TaxonomySkill:
    id: int
    slug: str
    name: str
    type: str  # technical | soft | domain
    level: int  # 0=domain, 1=category, 2=subcategory, 3=skill
    parent_slug: str | None
    description: str | None
    taxonomy_version: str


@dataclass(frozen=True)
class AliasRecord:
    alias: str
    alias_normalized: str
    slug: str
    ambiguous: bool
    source: str


@dataclass(frozen=True)
class ImplicationRecord:
    antecedent_slugs: tuple[str, ...]
    consequent_slug: str
    min_count: int = 1
    confidence: float = 0.8


@dataclass(frozen=True)
class RelationRecord:
    skill_slug: str
    related_slug: str
    kind: str  # related | prerequisite
    weight: float = 1.0


class TaxonomyRepository:
    """In-memory taxonomy repository loaded from CSV/YAML files."""

    def __init__(
        self,
        skills: list[TaxonomySkill],
        aliases: list[AliasRecord],
        implications: list[ImplicationRecord],
        relations: list[RelationRecord],
        taxonomy_version: str = "31.0",
    ) -> None:
        self.taxonomy_version = taxonomy_version
        self._skills = skills
        self._aliases = aliases
        self._implications = implications
        self._relations = relations

        # Fast lookup indices
        self._by_slug: dict[str, TaxonomySkill] = {s.slug: s for s in skills}
        self._by_id: dict[int, TaxonomySkill] = {s.id: s for s in skills}
        self._children: dict[str, list[TaxonomySkill]] = {}
        for s in skills:
            if s.parent_slug:
                self._children.setdefault(s.parent_slug, []).append(s)

        self._alias_by_norm: dict[str, AliasRecord] = {a.alias_normalized: a for a in aliases}
        self._implications_by_antecedent: dict[str, list[ImplicationRecord]] = {}
        for imp in implications:
            for ant in imp.antecedent_slugs:
                self._implications_by_antecedent.setdefault(ant, []).append(imp)

        self._relations_by_skill: dict[str, list[RelationRecord]] = {}
        for rel in relations:
            self._relations_by_skill.setdefault(rel.skill_slug, []).append(rel)

    @property
    def skills(self) -> list[TaxonomySkill]:
        return self._skills

    @property
    def slug_map(self) -> dict[str, TaxonomySkill]:
        return self._by_slug

    @property
    def alias_map(self) -> dict[str, AliasRecord]:
        return self._alias_by_norm

    @property
    def aliases(self) -> list[AliasRecord]:
        return self._aliases

    @property
    def implications(self) -> list[ImplicationRecord]:
        return self._implications

    @property
    def relations(self) -> list[RelationRecord]:
        return self._relations

    def get_skill(self, slug: str) -> TaxonomySkill | None:
        """Find a skill by its unique slug."""
        return self._by_slug.get(slug)

    def get_skill_by_id(self, skill_id: int) -> TaxonomySkill | None:
        """Find a skill by its database integer id."""
        return self._by_id.get(skill_id)

    def resolve_alias(self, text: str) -> AliasRecord | None:
        """Lookup an alias by exact normalized text."""
        norm = normalize_alias_text(text)
        return self._alias_by_norm.get(norm)

    def get_ancestors(self, slug: str) -> list[TaxonomySkill]:
        """Return the ancestor path from direct parent up to root domain (level 0)."""
        ancestors: list[TaxonomySkill] = []
        curr = self._by_slug.get(slug)
        while curr and curr.parent_slug:
            parent = self._by_slug.get(curr.parent_slug)
            if not parent:
                break
            ancestors.append(parent)
            curr = parent
        return ancestors

    def get_children(self, slug: str) -> list[TaxonomySkill]:
        """Return direct children of a domain, category, or subcategory."""
        return list(self._children.get(slug, []))

    def get_relations(self, slug: str, kind: str | None = None) -> list[RelationRecord]:
        """Return outgoing relation edges for a skill."""
        rels = self._relations_by_skill.get(slug, [])
        if kind is not None:
            return [r for r in rels if r.kind == kind]
        return list(rels)

    def get_implications_for(self, antecedent_slugs: set[str]) -> list[ImplicationRecord]:
        """Return implication rules triggered by the given set of active skill slugs."""
        candidates: set[ImplicationRecord] = set()
        for ant in antecedent_slugs:
            for imp in self._implications_by_antecedent.get(ant, []):
                candidates.add(imp)

        triggered: list[ImplicationRecord] = []
        for imp in candidates:
            matching_count = sum(1 for a in imp.antecedent_slugs if a in antecedent_slugs)
            if matching_count >= imp.min_count:
                triggered.append(imp)
        return triggered

    @classmethod
    def from_dir(cls, directory: Path | str | None = None) -> TaxonomyRepository:
        """Load taxonomy data from CSV and YAML files."""
        dir_path = Path(directory or get_settings().taxonomy_dir)
        skills_file = dir_path / "skills.csv"
        aliases_file = dir_path / "aliases.csv"
        implications_file = dir_path / "implications.yaml"
        relations_file = dir_path / "relations.yaml"

        skills: list[TaxonomySkill] = []
        version = "31.0"
        if skills_file.is_file():
            with skills_file.open(encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                for i, row in enumerate(reader, start=1):
                    version = row.get("taxonomy_version", version)
                    skills.append(
                        TaxonomySkill(
                            id=int(row.get("id", i)),
                            slug=row["slug"],
                            name=row["name"],
                            type=row.get("type", "technical"),
                            level=int(row.get("level", 3)),
                            parent_slug=row.get("parent_slug") or None,
                            description=row.get("description") or None,
                            taxonomy_version=version,
                        )
                    )

        aliases: list[AliasRecord] = []
        if aliases_file.is_file():
            with aliases_file.open(encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    aliases.append(
                        AliasRecord(
                            alias=row["alias"],
                            alias_normalized=row["alias_normalized"],
                            slug=row["slug"],
                            ambiguous=row.get("ambiguous", "").lower() in ("true", "1"),
                            source=row.get("source", "curated"),
                        )
                    )

        implications: list[ImplicationRecord] = []
        if implications_file.is_file():
            with implications_file.open(encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                for item in data.get("implications", []):
                    implications.append(
                        ImplicationRecord(
                            antecedent_slugs=tuple(item["antecedent_slugs"]),
                            consequent_slug=item["consequent_slug"],
                            min_count=int(item.get("min_count", 1)),
                            confidence=float(item.get("confidence", 0.8)),
                        )
                    )

        relations: list[RelationRecord] = []
        if relations_file.is_file():
            with relations_file.open(encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                for item in data.get("relations", []):
                    relations.append(
                        RelationRecord(
                            skill_slug=item["skill_slug"],
                            related_slug=item["related_slug"],
                            kind=item.get("kind", "related"),
                            weight=float(item.get("weight", 1.0)),
                        )
                    )

        return cls(
            skills=skills,
            aliases=aliases,
            implications=implications,
            relations=relations,
            taxonomy_version=version,
        )


@lru_cache(maxsize=4)
def get_taxonomy_repository(taxonomy_dir: str | None = None) -> TaxonomyRepository:
    """Cached singleton instance of the taxonomy repository."""
    path = taxonomy_dir or get_settings().taxonomy_dir
    return TaxonomyRepository.from_dir(path)
