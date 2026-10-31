export interface SampleCandidate {
  id: string;
  name: string;
  title: string;
  summary: string;
  skills: string[];
  rawText: string;
}

export interface SampleJob {
  id: string;
  title: string;
  company: string;
  seniority: string;
  minYears: number;
  description: string;
  requiredSkills: string[];
  preferredSkills: string[];
}

export const SAMPLE_CANDIDATES: SampleCandidate[] = [
  {
    id: "sample-cand-1",
    name: "Allison Hill",
    title: "Software Engineer",
    summary:
      "Experienced professional with expertise in scalable cloud architectures, CI/CD pipelines, TypeScript, Node.js, and React.",
    skills: ["TypeScript", "AWS", "CI/CD Pipelines", "Node.js", "React.js", "Docker", "PostgreSQL"],
    rawText: `Allison Hill
Email: allison.hill@example.com | Phone: (518) 519-6001 | Port Lindachester, MA
LinkedIn: linkedin.com/in/allison-hill | GitHub: github.com/allisonhill

SUMMARY
Experienced Junior professional with 2+ years of expertise in software engineering. Proven track record delivering scalable solutions using CI/CD Pipelines, Node.js, React.js, and AWS cloud infrastructure.

EXPERIENCE
Software Engineer | Cole LLC | 2024-06 – Present
• Led the architectural design and implementation of key backend microservices using TypeScript, Node.js, and AWS.
• Improved cross-team delivery speed by 35% through standardized CI/CD pipelines and automated Dockerized testing.
• Collaborated with executive stakeholders and product teams to drive data-informed roadmap decisions.

EDUCATION
Bachelor of Science in Computer Science | Ericmouth State University | 2020 – 2024
GPA: 3.8 / 4.0

SKILLS
TypeScript, JavaScript (ES6+), Node.js, React.js, AWS, Docker, PostgreSQL, CI/CD, Git, RESTful APIs`,
  },
  {
    id: "sample-cand-2",
    name: "Marcus Vance",
    title: "Senior Backend Engineer",
    summary:
      "Senior engineer with 7+ years building distributed backends with Python, FastAPI, PostgreSQL, Kubernetes, and Redis.",
    skills: ["Python", "FastAPI", "PostgreSQL", "Docker", "Kubernetes", "Redis", "Distributed Systems"],
    rawText: `Marcus Vance
Email: marcus.vance@example.com | San Francisco, CA

SUMMARY
Senior Backend Engineer with 7+ years architecting high-concurrency microservices, data pipelines, and distributed event systems.

EXPERIENCE
Senior Backend Engineer | Apex Systems | 2021 – Present
• Designed distributed API gateway handling 40k req/sec using FastAPI and async PostgreSQL.
• Orchestrated multi-region Kubernetes deployments and Kafka event streams with zero downtime.
• Mentored 6 junior/mid engineers and established engineering RFC standards.

SKILLS
Python, FastAPI, Django, PostgreSQL, Redis, Kubernetes, Docker, Kafka, Terraform, AWS`,
  },
  {
    id: "sample-cand-3",
    name: "Elena Rostova",
    title: "Machine Learning Infrastructure Engineer",
    summary:
      "ML specialist with 5 years building scalable model training pipelines with PyTorch, Ray, and Vector Databases.",
    skills: ["Python", "PyTorch", "Machine Learning", "Deep Learning", "LLMs", "Vector Databases", "Docker"],
    rawText: `Elena Rostova
Email: elena.rostova@example.com | Seattle, WA

SUMMARY
Machine Learning Engineer specializing in distributed training pipelines, LLM fine-tuning, and semantic retrieval systems.

EXPERIENCE
ML Infrastructure Engineer | NeuroScale AI | 2022 – Present
• Built retrieval-augmented generation (RAG) pipelines using vector databases and PyTorch.
• Reduced model inference latency by 45% using TensorRT and vLLM acceleration.
• Maintained large-scale data ingestion workers processing 5TB/day of multimodal data.

SKILLS
Python, PyTorch, Hugging Face, Ray, ChromaDB, Docker, CUDA, Kubernetes, MLOps`,
  },
];

export const SAMPLE_JOBS: SampleJob[] = [
  {
    id: "sample-job-1",
    title: "Principal Backend Software Engineer (Python/FastAPI)",
    company: "Schaefer, Mckinney and Duncan",
    seniority: "Principal",
    minYears: 6,
    description: `JOB TITLE: Principal Backend Software Engineer
COMPANY: Schaefer, Mckinney and Duncan
LOCATION: Hybrid / Remote Available
SENIORITY LEVEL: Principal
MINIMUM RELEVANT EXPERIENCE: 6+ Years

--- ROLE OVERVIEW ---
We are seeking an exceptional Principal Backend Software Engineer to architect, build, and deploy mission-critical solutions that directly impact platform scale.

--- KEY RESPONSIBILITIES ---
• Design and maintain scalable, secure, and resilient microservices.
• Drive technical strategy and mentor team members in technical execution.
• Collaborate cross-functionally with product managers and designers.

--- REQUIRED QUALIFICATIONS ---
• Proven expertise in Python (3+ years experience)
• Proven expertise in FastAPI (2+ years experience)
• Proven expertise in PostgreSQL (3+ years experience)
• Proven expertise in Docker (2+ years experience)
• Minimum of 6+ years in software engineering.

--- PREFERRED QUALIFICATIONS ---
• Familiarity with Kubernetes, Redis, and AWS.`,
    requiredSkills: ["Python", "FastAPI", "PostgreSQL", "Docker"],
    preferredSkills: ["Kubernetes", "Redis", "AWS"],
  },
  {
    id: "sample-job-2",
    title: "Full Stack Engineer (TypeScript/React/Node)",
    company: "Vanguard Tech Labs",
    seniority: "Mid-Senior",
    minYears: 3,
    description: `JOB TITLE: Full Stack Engineer (TypeScript/React/Node)
COMPANY: Vanguard Tech Labs
LOCATION: Remote

--- ROLE OVERVIEW ---
Join our core product team building high-performance web applications and cloud integrations.

--- REQUIRED QUALIFICATIONS ---
• Strong proficiency in TypeScript, React, and Node.js.
• Experience with relational databases like PostgreSQL.
• Hands-on experience with modern CI/CD workflows and Docker.`,
    requiredSkills: ["TypeScript", "React.js", "Node.js", "Docker"],
    preferredSkills: ["AWS", "CI/CD Pipelines", "TailwindCSS"],
  },
];

