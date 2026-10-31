# External Data Attribution

In accordance with [ADR-0004](file:///docs/decisions/ADR-0004-external-and-real-world-data.md), TalentGraph incorporates external benchmarks for supplementary evaluation (reporting only, never for tuning).

---

## 1. TechWolf Skill Extraction Benchmarks

- **Datasets:**
  - `TechWolf/skill-extraction-techwolf`
  - `TechWolf/skill-extraction-tech`
  - `TechWolf/skill-extraction-house`
- **Citation:** Decorte, J., Van Renterghem, J., & Demeester, T. (2023). Design Choices for Skill Extraction from Job Postings. *arXiv:2307.10778*.
- **License:** Creative Commons Attribution 4.0 International ([CC BY 4.0](https://creativecommons.org/licenses/by/4.0/))
- **Usage:** External check of normalization precision/recall (M2) and fine-tuning gain (M9) via ESCO v1.1.0 to taxonomy slug crosswalk.

---

## 2. Luke Barousse Data Jobs Dataset

- **Dataset:** `lukebarousse/data_jobs`
- **Source:** [Hugging Face](https://huggingface.co/datasets/lukebarousse/data_jobs)
- **License:** [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0)
- **Usage:** Evaluation of unrecognized skill rate on real-world job posting skill strings.

---

## 3. USAJOBS Postings

- **Source:** [USAJOBS API](https://developer.usajobs.gov/) (U.S. Office of Personnel Management)
- **Terms:** Used under OPM API terms of service for testing and evaluation purposes.

