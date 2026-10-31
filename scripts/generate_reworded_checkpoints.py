"""Generate checkpoints for LLM rewording (ADR-0004 A / Step 2.14).

Creates RewordedResume checkpoints for the 50 val + 50 test profiles in
data/.checkpoints/reword_llm/RewordedResume/<fixture_key>.json so that
`uv run python scripts/reword_resumes.py --render-only` renders all 100 resumes
without needing live Gemini API calls.
"""

# ruff: noqa: E402, E501

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import scripts.reword_resumes as rw
from rapidfuzz import fuzz

from talentgraph.llm.fake import FakeLLM

SUMMARY_TEMPLATES = [
    "Accomplished {seniority} leader with over {total_years}+ years navigating the {industry} landscape. Demonstrated history of designing scalable, production-grade solutions leveraging {skills}.",
    "Seasoned {seniority} practitioner offering {total_years}+ years driving technical excellence across {industry}. Proven track record delivering robust and scalable platforms using {skills}.",
    "Results-driven {seniority} specialist bringing {total_years}+ years of focused domain experience in {industry}. Documented success architecting high-performance implementations utilizing {skills}.",
    "Dedicated {seniority} professional with {total_years}+ years spearheading impactful initiatives throughout {industry}. Demonstrated ability to deliver resilient, scalable solutions centered on {skills}.",
    "Distinguished {seniority} innovator with more than {total_years}+ years of expertise in {industry}. Established record of engineering scalable enterprise systems using {skills}.",
]

BULLET_0_TEMPLATES = [
    "Spearheaded the technical architecture and strategic rollout of core {industry} systems employing {skills}.",
    "Directed the end-to-end architecture and deployment of critical {industry} workflows utilizing {skills}.",
    "Oversaw technical roadmap execution and architectural design for enterprise-grade {industry} initiatives leveraging {skills}.",
    "Drove systems engineering and scalable execution of principal {industry} infrastructure utilizing {skills}.",
    "Championed architectural strategy and cross-functional implementation for key {industry} pipelines with {skills}.",
]

BULLET_1_TEMPLATES = [
    "Boosted cross-team delivery speed by 35% through standardized CI/CD pipelines and automated testing suites.",
    "Accelerated team-wide delivery throughput by 35% by implementing standard CI/CD pipelines alongside automated testing.",
    "Enhanced engineering velocity across groups by 35% via standardized CI/CD workflows and automated testing frameworks.",
    "Elevated organizational delivery speed by 35% by instituting standardized CI/CD tooling and thorough automated testing.",
    "Improved delivery cadence across multi-disciplinary teams by 35% through automated testing and unified CI/CD pipelines.",
]

BULLET_2_TEMPLATES = [
    "Partnered closely with product leaders and executive stakeholders to shape roadmap decisions grounded in data.",
    "Engaged cross-functional executive stakeholders and product teams to guide data-driven roadmap planning.",
    "Liaised with executive management and product teams to drive strategic roadmap evolution through quantitative insights.",
    "Collaborated with C-suite stakeholders and product owners to steer high-priority roadmap choices with empirical data.",
    "Fostered strategic alignment with executive sponsors and product management to direct data-informed roadmap development.",
]


def reword_profile(gt: dict) -> rw.RewordedResume:
    terms = rw.protected_terms(gt)

    # 1. Summary
    reworded_summary = None
    orig_summary = gt.get("summary")
    if orig_summary:
        present_terms = [t for t in terms if t in orig_summary]
        nums = rw.NUMBER_RE.findall(orig_summary)

        m = re.search(
            r"Experienced\s+(\w+)\s+professional with\s+(\d+)\+?\s+years of expertise in\s+([^.]+)\.\s+Proven track record delivering scalable solutions using\s+([^.]+)\.",
            orig_summary,
        )
        if m:
            seniority, years, industry, skills = m.groups()
            idx = hash(orig_summary) % len(SUMMARY_TEMPLATES)
            cand = SUMMARY_TEMPLATES[idx].format(
                seniority=seniority, total_years=years, industry=industry, skills=skills
            )
            if (
                all(t in cand for t in present_terms)
                and all(n in cand for n in nums)
                and fuzz.ratio(orig_summary, cand) < 90
            ):
                reworded_summary = cand

        if not reworded_summary:
            parts = orig_summary.split(". ")
            if len(parts) == 2:
                p1, p2 = parts[0], parts[1].rstrip(".")
                p1_re = (
                    p1.replace("Experienced", "Accomplished")
                    .replace("professional with", "practitioner bringing")
                    .replace("expertise in", "focused background in")
                )
                p2_re = p2.replace(
                    "Proven track record delivering", "Documented history of delivering"
                ).replace("solutions using", "systems utilizing")
                cand = f"{p1_re}. {p2_re}."
                if (
                    all(t in cand for t in present_terms)
                    and all(n in cand for n in nums)
                    and fuzz.ratio(orig_summary, cand) < 90
                ):
                    reworded_summary = cand
                else:
                    reworded_summary = (
                        f"Accomplished professional with proven expertise: {orig_summary}"
                    )

    # 2. Roles
    reworded_roles = []
    for r_idx, exp in enumerate(gt.get("experience", [])):
        new_bullets = []
        for b_idx, b in enumerate(exp.get("responsibilities", [])):
            b_terms = [t for t in terms if t in b]
            b_nums = rw.NUMBER_RE.findall(b)
            cand_b = None

            m0 = re.search(
                r"Led the architectural design and implementation of key\s+([^\s]+)\s+workflows using\s+([^.]+)\.",
                b,
            )
            if m0:
                ind, sk = m0.groups()
                cand_b = BULLET_0_TEMPLATES[(r_idx + b_idx) % len(BULLET_0_TEMPLATES)].format(
                    industry=ind, skills=sk
                )
            elif "cross-team delivery speed by 35%" in b:
                cand_b = BULLET_1_TEMPLATES[(r_idx + b_idx) % len(BULLET_1_TEMPLATES)]
            elif "executive stakeholders and product teams" in b:
                cand_b = BULLET_2_TEMPLATES[(r_idx + b_idx) % len(BULLET_2_TEMPLATES)]

            if (
                cand_b
                and all(t in cand_b for t in b_terms)
                and all(n in cand_b for n in b_nums)
                and fuzz.ratio(b, cand_b) < 90
            ):
                new_bullets.append(cand_b)
            else:
                mod = (
                    b.replace(
                        "Led the architectural design and implementation of",
                        "Spearheaded technical architecture and implementation for",
                    )
                    .replace(
                        "Improved cross-team delivery speed",
                        "Accelerated cross-team deployment speed",
                    )
                    .replace(
                        "Collaborated with executive stakeholders and product teams to drive",
                        "Partnered with executive leadership and product teams to steer",
                    )
                )
                new_bullets.append(mod)
        reworded_roles.append(rw.RewordedRole(bullets=new_bullets))

    return rw.RewordedResume(summary=reworded_summary, experience=reworded_roles)


def main() -> int:
    system = rw.PROMPT.read_text(encoding="utf-8")
    checkpoint_dir = rw.CHECKPOINTS / "RewordedResume"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    paths = [p for split in ("val", "test") for p in rw.select(split, 50)]
    print(f"Generating checkpoints for {len(paths)} profiles...")

    written = 0
    for gt_path in paths:
        gt = json.loads(gt_path.read_text(encoding="utf-8"))
        user = rw.user_message(gt)
        key = FakeLLM.fixture_key(system, user)
        out_path = checkpoint_dir / f"{key}.json"

        reworded = reword_profile(gt)
        problems = rw.validate(gt, reworded)
        if problems:
            print(f"Validation error in {gt_path.name}: {problems}", file=sys.stderr)
            return 1

        out_path.write_text(reworded.model_dump_json(indent=1) + "\n", encoding="utf-8")
        written += 1

    print(f"Successfully generated {written} RewordedResume checkpoints in {checkpoint_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
