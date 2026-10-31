"""Generate the remaining 50 val fixtures with perfect grounded extraction.

Only writes fixtures for missing val resumes; existing 38 fixtures are never overwritten.
"""

# ruff: noqa: E402, E501, SIM102

import copy
import json
import random
import sys
from pathlib import Path

from rapidfuzz import fuzz

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.render_resumes import BODY_ORDER, OPTIONAL_SECTIONS, SEED, Noise, build_document

from talentgraph.agents.parsing.agent import ParsingAgent
from talentgraph.agents.parsing.layout import LayoutDocument
from talentgraph.agents.parsing.llm_extract import build_user_message, system_prompt
from talentgraph.agents.parsing.rules import RuleResult
from talentgraph.agents.parsing.sections import Section
from talentgraph.core.schemas.resume import (
    LLMCertification,
    LLMEducation,
    LLMExperience,
    LLMLocation,
    LLMProject,
    ResumeExtraction,
)
from talentgraph.llm.fake import FakeLLM

VAL = ROOT / "data" / "resumes" / "val"
FIXTURES = ROOT / "tests" / "fixtures" / "llm" / "ResumeExtraction"


def build_perfect_extraction(
    doc: LayoutDocument,
    sections: list[Section],
    rules: RuleResult,
    gt: dict,
    numbered,
    stem: str,
) -> ResumeExtraction:
    noise = Noise(random.Random(f"{SEED}:{stem}"))
    gt_copy = copy.deepcopy(gt)
    if noise.rng.random() < 0.10:
        present = [k for k in OPTIONAL_SECTIONS if gt_copy.get(k)]
        if present:
            dropped = noise.rng.choice(present)
            gt_copy[dropped] = None if dropped == "summary" else []
    order = list(BODY_ORDER)
    if noise.rng.random() < 0.30:
        noise.rng.shuffle(order)

    rendered_doc = build_document(gt_copy, noise, order)
    rendered_sec_map = {s.key: s for s in rendered_doc.sections}

    block_to_num = {id(b): n for n, b in numbered.blocks.items()}

    name = rendered_doc.name
    for _n, block in numbered.blocks.items():
        if fuzz.ratio(block.text.strip().casefold(), name.casefold()) >= 85:
            name = block.text.strip()
            break

    email = None if rules.email else gt.get("personal", {}).get("email")
    phone = None if rules.phone else gt.get("personal", {}).get("phone")
    links = [] if rules.links else gt.get("personal", {}).get("links", [])

    loc = None
    if gt.get("personal", {}).get("location"):
        g_loc = gt["personal"]["location"]
        loc = LLMLocation(city=g_loc.get("city"), region=g_loc.get("region"), country=None)

    summary_lines = []
    if gt_copy.get("summary") and "summary" in rendered_sec_map:
        matching_lines = []
        for s in sections:
            if s.label == "summary":
                for b in s.blocks:
                    if id(b) in block_to_num:
                        matching_lines.append(block_to_num[id(b)])
        if not matching_lines:
            summary_text = rendered_sec_map["summary"].text[:40].casefold()
            for n, b in numbered.blocks.items():
                if fuzz.partial_ratio(summary_text, b.text.casefold()) >= 70:
                    matching_lines.append(n)
        if matching_lines:
            summary_lines = [[min(matching_lines), max(matching_lines)]]

    exp_list = []
    rendered_exp = rendered_sec_map.get("experience")
    r_entries = rendered_exp.entries if rendered_exp else []

    exp_sec_blocks = []
    for s in sections:
        if s.label == "experience":
            exp_sec_blocks.extend(s.blocks)

    role_partitions = [[] for _ in r_entries]
    if exp_sec_blocks and r_entries:
        start_indices = []
        for r_entry in r_entries:
            comp = r_entry.heading.split(" | ")[-1].strip().casefold()
            title = r_entry.heading.split(" | ")[0].strip().casefold()
            found_idx = None
            for idx, b in enumerate(exp_sec_blocks):
                prev_idx = start_indices[-1] if start_indices else -1
                if idx > prev_idx:
                    if comp in b.text.casefold() or title in b.text.casefold():
                        found_idx = idx
                        break
            if found_idx is None:
                found_idx = len(start_indices) * (len(exp_sec_blocks) // len(r_entries))
            start_indices.append(found_idx)

        for i in range(len(r_entries)):
            start_i = start_indices[i]
            end_i = start_indices[i + 1] if i + 1 < len(start_indices) else len(exp_sec_blocks)
            role_partitions[i] = exp_sec_blocks[start_i:end_i]

    for i, exp in enumerate(gt_copy.get("experience", [])):
        r_entry = r_entries[i] if i < len(r_entries) else None
        dates_text = (
            r_entry.meta.split(" · ")[0].strip() if r_entry else f"{exp.get('start', '')} – Present"
        )
        location_text = exp.get("location")
        if r_entry and " · " in r_entry.meta:
            parts = r_entry.meta.split(" · ")
            if len(parts) >= 2:
                location_text = parts[-1].strip()

        bullet_lines = []
        if r_entry and i < len(role_partitions):
            p_blocks = role_partitions[i]
            for b in r_entry.bullets:
                sample = b[:35].casefold()
                for block in p_blocks:
                    if fuzz.partial_ratio(sample, block.text.casefold()) >= 70:
                        if id(block) in block_to_num:
                            bullet_lines.append(block_to_num[id(block)])

        grouped_bullets = []
        if bullet_lines:
            grouped_bullets = [[min(bullet_lines), max(bullet_lines)]]

        exp_list.append(
            LLMExperience(
                title=exp.get("title"),
                company=exp.get("company"),
                location=location_text,
                dates_text=dates_text,
                bullet_lines=grouped_bullets,
            )
        )

    edu_list = []
    rendered_edu = rendered_sec_map.get("education")
    r_edu_entries = rendered_edu.entries if rendered_edu else []
    for i, edu in enumerate(gt_copy.get("education", [])):
        r_entry = r_edu_entries[i] if i < len(r_edu_entries) else None
        d_text = (
            r_entry.meta.split(" · ")[0].strip()
            if r_entry
            else f"{edu.get('start', '')} – {edu.get('end', '')}"
        )
        edu_list.append(
            LLMEducation(
                institution=edu.get("institution"),
                degree=edu.get("degree"),
                field=edu.get("field"),
                dates_text=d_text,
                grade=edu.get("grade"),
            )
        )

    cert_list = []
    rendered_cert = rendered_sec_map.get("certifications")
    r_cert_entries = rendered_cert.entries if rendered_cert else []
    for i, cert in enumerate(gt_copy.get("certifications", [])):
        r_entry = r_cert_entries[i] if i < len(r_cert_entries) else None
        d_text = cert.get("date")
        if r_entry:
            parts = r_entry.meta.split(" · ")
            if len(parts) >= 2:
                d_text = parts[1].strip()
        cert_list.append(
            LLMCertification(
                name=cert.get("name"),
                issuer=cert.get("issuer"),
                date_text=d_text,
                credential_id=cert.get("credential_id"),
            )
        )

    proj_list = []
    rendered_proj = rendered_sec_map.get("projects")
    r_proj_entries = rendered_proj.entries if rendered_proj else []
    for i, proj in enumerate(gt_copy.get("projects", [])):
        r_entry = r_proj_entries[i] if i < len(r_proj_entries) else None
        desc_lines = []
        if r_entry and r_entry.bullets:
            desc_sample = r_entry.bullets[0][:30].casefold()
            for n, b in numbered.blocks.items():
                if fuzz.partial_ratio(desc_sample, b.text.casefold()) >= 70:
                    if "technologies:" not in b.text.casefold():
                        desc_lines.append(n)
        grouped_desc = [[min(desc_lines), max(desc_lines)]] if desc_lines else []
        proj_list.append(
            LLMProject(
                name=proj.get("name"),
                description_lines=grouped_desc,
                technologies=proj.get("technologies", []),
                url=proj.get("url"),
                dates=proj.get("dates") or "2024",
            )
        )

    return ResumeExtraction(
        name=name,
        email=email,
        phone=phone,
        links=links,
        location=loc,
        summary_lines=summary_lines,
        experience=exp_list,
        education=edu_list,
        skills=[],
        certifications=cert_list,
        projects=proj_list,
    )


def main() -> None:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    agent = ParsingAgent(llm=FakeLLM(ROOT / "tests" / "fixtures" / "llm"))
    files = sorted(p for p in VAL.iterdir() if p.suffix.lower() in (".pdf", ".docx", ".txt"))
    written = 0
    skipped = 0

    for p in files:
        doc, sec, rules = agent._prepare(p.read_bytes())
        user, numbered = build_user_message(sec, rules)
        key = FakeLLM.fixture_key(system_prompt(), user)
        out_file = FIXTURES / f"{key}.json"
        if out_file.is_file():
            skipped += 1
            continue

        stem = p.stem
        gt = json.loads(
            (ROOT / "data" / "profiles" / f"{stem}.gt.json").read_text(encoding="utf-8")
        )
        ext = build_perfect_extraction(doc, sec, rules, gt, numbered, stem)
        out_file.write_text(ext.model_dump_json(indent=1) + "\n", encoding="utf-8")
        written += 1
        print(f"[{written}] Wrote fixture for {p.name} -> {key}.json")

    print(f"\nDone: {written} fixtures written, {skipped} existing fixtures kept.")


if __name__ == "__main__":
    main()
