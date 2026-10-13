# Candidate-to-Job Semantic Match Evaluation Rubric

This rubric defines the standardized 5-point relevance grading scale (0–4) used for scoring candidate-to-job compatibility in TalentGraph.

---

## Relevance Grading Scale (0 – 4)

### Grade 4: Strong / Ideal Match (Excellent Fit)
- **Skill Overlap:** Candidate possesses **>= 90%** of required skills with canonical or direct descendant equivalents.
- **Experience Depth:** Meets or exceeds the required years of experience for the seniority level (e.g. Senior = 5+ years).
- **Domain & Role Alignment:** Role title and career progression directly match the job family (e.g. Senior Backend Engineer for a Backend role).
- **Nice-to-Haves:** Covers multiple preferred/nice-to-have technologies.

### Grade 3: Solid Match (Qualified Fit)
- **Skill Overlap:** Candidate possesses **70% – 89%** of required core skills. Missing skills are easily learnable adjacent tools.
- **Experience Depth:** Meets minimum required total experience, with solid tenure in relevant roles.
- **Domain & Role Alignment:** Directly related title or adjacent discipline (e.g. Full Stack Engineer applying for Frontend/Backend).
- **Nice-to-Haves:** Covers at least one preferred technology.

### Grade 2: Partial / Transferable Match (Upskilling Candidate)
- **Skill Overlap:** Candidate possesses **40% – 69%** of required core skills, or demonstrates strong ancestor/sibling competency (e.g. PyTorch experience for a TensorFlow requirement, or Docker experience for a Kubernetes requirement).
- **Experience Depth:** Moderate experience (may be slightly junior for a senior role, or broad generalist).
- **Upskilling Potential:** High capability to ramp up within 30–60 days based on graph relation edges.

### Grade 1: Weak / Marginal Match (Underqualified)
- **Skill Overlap:** Candidate possesses **10% – 39%** of required skills (e.g. only matches generic tools like Git or SQL, while missing core domain/framework skills).
- **Experience Depth:** Insufficient depth or mismatched seniority level.
- **Domain Mismatch:** Experience in largely distinct domain without strong transferable bridges.

### Grade 0: Irrelevant Match (Disqualified)
- **Skill Overlap:** Candidate possesses **< 10%** of required skills (no relevant technical or domain overlap).
- **Domain Mismatch:** Completely disparate professional field (e.g. Healthcare Clinical Nurse applying for Principal Distributed Systems Architect).

---

## Ground-Truth Dataset Distribution Goals
To prevent skew and ensure valid evaluation for metric **M3 (NDCG@10 >= 0.80, Spearman rho >= 0.60)**:
- 20 candidate pairs per job (5 strong, 5 partial, 5 weak, 5 random).
- No single grade class (0, 1, 2, 3, 4) exceeds **40%** of total dataset pairs.
- Stratified 70/15/15 split by job (train/val/test).
- Sample of >= 200 pairs exported to `human_labeling.csv` for inter-annotator agreement tracking.
