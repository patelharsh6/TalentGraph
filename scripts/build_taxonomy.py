"""Phase 1.2-1.3: build the 4-level skill tree (skills.csv) and its aliases (aliases.csv).

Domain -> Category -> Subcategory -> Skill, assembled from three layers:

1. the hand-curated tree in this file plus data/taxonomy/curated_tech.yaml;
2. O*NET 31.0 (software skills, knowledge areas, essential/transferable skills), downloaded by
   data/taxonomy/raw/download.py. Products already in the curated layer become aliases;
3. skills that only implications.yaml / relations.yaml reference.

Aliases are real surface forms only: curated abbreviations, O*NET product names, and derived
punctuation/spacing/vendor/acronym variants. Run data/taxonomy/raw/download.py first.
"""

from __future__ import annotations

import argparse
import csv
import html
import logging
import re
from collections import Counter, defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("build_taxonomy")

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data" / "taxonomy"
ONET_DIR = DATA_DIR / "raw" / "onet"

# Ambiguous alias lexicon
AMBIGUOUS_ALIASES = {
    "c",
    "r",
    "go",
    "rust",
    "swift",
    "spring",
    "excel",
    "word",
    "access",
    "git",
    "ruby",
    "sass",
    "pm",
    "cv",
    "de",
    "rest",
    "spark",
    "chef",
    "puppet",
    "flask",
    "unity",
    "unreal",
    "linear",
    "target",
    "strike",
    "base",
    "matrix",
    "pilot",
    "torch",
    # Common English words that are also product names (mostly vendor-stripped O*NET forms).
    "act",
    "animate",
    "audition",
    "blackboard",
    "box",
    "bridge",
    "calendar",
    "canvas",
    "compass",
    "connect",
    "docs",
    "drive",
    "dynamics",
    "edge",
    "explorer",
    "flow",
    "forms",
    "fusion",
    "inventor",
    "keynote",
    "logic",
    "mail",
    "maps",
    "maya",
    "motion",
    "notes",
    "numbers",
    "office",
    "outlook",
    "pages",
    "paint",
    "photos",
    "premiere",
    "project",
    "publisher",
    "reader",
    "sheets",
    "sketch",
    "slack",
    "slides",
    "stream",
    "studio",
    "teams",
    "zoom",
}


def normalize_alias_text(text: str) -> str:
    """Normalize alias for lookup (lowercase, stripped punctuation/spaces)."""
    s = text.lower().strip()
    s = re.sub(r"[\s\-_/.]+", " ", s).strip()
    return s


def slugify(text: str) -> str:
    """Turn text into a URL-safe lowercase slug."""
    s = text.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    return s.strip("-")


def generate_rich_domain_skills() -> list[dict[str, Any]]:
    """Build the full 4-level tree (curated + curated_tech.yaml + O*NET + rule-referenced)."""
    skills_records: list[dict[str, Any]] = []
    seen_slugs: set[str] = set()

    def add_skill(
        slug: str,
        name: str,
        type_: str,
        level: int,
        parent_slug: str,
        desc: str,
        aliases: list[Any] | None = None,
    ) -> None:
        if not slug or slug in seen_slugs:
            return
        raw = aliases if aliases is not None else [name.lower(), slug.replace("-", " ")]
        skills_records.append(
            {
                "slug": slug,
                "name": name,
                "type": type_,
                "level": level,
                "parent_slug": parent_slug,
                "description": desc,
                # (alias, source) pairs; bare strings are hand-curated.
                "aliases": [(a, "curated") if isinstance(a, str) else tuple(a) for a in raw],
                "name_source": "curated",
            }
        )
        seen_slugs.add(slug)

    # -------------------------------------------------------------
    # 1. Level 0 Root Domains
    # -------------------------------------------------------------
    root_domains = [
        (
            "technical-skills",
            "Technical Skills",
            "technical",
            "Core technical proficiencies across software, hardware, data, and systems engineering",
        ),
        (
            "business-skills",
            "Business Skills",
            "business",
            "Commercial, strategic, operational, financial, and product capabilities",
        ),
        (
            "soft-skills",
            "Soft Skills",
            "soft",
            "Interpersonal, leadership, cognitive, and collaborative human capabilities",
        ),
        (
            "domain-knowledge",
            "Domain Knowledge",
            "domain",
            "Industry-specific, regulatory, and specialized vertical expertise",
        ),
    ]

    for slug, name, type_, desc in root_domains:
        add_skill(slug, name, type_, 0, "", desc)

    # -------------------------------------------------------------
    # 2. Level 1 Categories & Level 2 Subcategories
    # -------------------------------------------------------------
    taxonomy_structure = [
        # Technical Domain
        (
            "technical-skills",
            "technical",
            "programming-languages",
            "Programming Languages",
            [
                ("system-and-compiled-languages", "System & Compiled Languages"),
                ("jvm-languages", "JVM Languages & Ecosystem"),
                ("dynamic-and-scripting-languages", "Dynamic & Scripting Languages"),
                ("functional-programming", "Functional Programming"),
            ],
        ),
        (
            "technical-skills",
            "technical",
            "web-development",
            "Web Development",
            [
                ("frontend-frameworks", "Frontend Frameworks & Libraries"),
                ("backend-frameworks", "Backend Frameworks & Runtimes"),
                ("api-technologies", "API Technologies & Protocols"),
                ("css-and-styling", "CSS & Styling Architectures"),
            ],
        ),
        (
            "technical-skills",
            "technical",
            "data-and-ai",
            "Data Science, AI & Machine Learning",
            [
                ("machine-learning-frameworks", "Machine Learning & Deep Learning"),
                ("generative-ai-and-llms", "Generative AI & LLMs"),
                ("natural-language-and-vision", "NLP & Computer Vision"),
                ("data-engineering-and-analytics", "Data Engineering & Analytics"),
                ("vector-and-search-databases", "Vector & Search Databases"),
            ],
        ),
        (
            "technical-skills",
            "technical",
            "cloud-and-infrastructure",
            "Cloud, DevOps & Infrastructure",
            [
                ("cloud-platforms", "Cloud Platforms & Serverless"),
                ("container-and-orchestration", "Containers & Orchestration"),
                ("ci-cd-and-automation", "CI/CD & Infrastructure as Code"),
                ("observability-and-sre", "Observability, Monitoring & SRE"),
            ],
        ),
        (
            "technical-skills",
            "technical",
            "databases-and-storage",
            "Databases & Storage",
            [
                ("relational-databases", "Relational Database Management Systems"),
                ("nosql-and-document-databases", "NoSQL & Document Databases"),
                ("distributed-and-streaming-storage", "Distributed & Streaming Storage"),
            ],
        ),
        (
            "technical-skills",
            "technical",
            "cybersecurity-and-networking",
            "Cybersecurity & Networking",
            [
                ("application-security", "Application Security & DevSecOps"),
                ("network-and-cloud-security", "Network & Cloud Security"),
                ("identity-and-access", "Identity, Authentication & Access"),
            ],
        ),
        (
            "technical-skills",
            "technical",
            "mobile-and-embedded",
            "Mobile & Embedded Systems",
            [
                ("mobile-platforms", "iOS & Android Mobile Development"),
                ("embedded-and-iot", "Embedded Systems & IoT"),
            ],
        ),
        # Business Domain
        (
            "business-skills",
            "business",
            "product-and-design",
            "Product Management & Design",
            [
                ("product-strategy-and-execution", "Product Strategy & Execution"),
                ("user-experience-and-ui", "UX/UI Design & Research"),
                ("agile-and-project-management", "Agile Methodologies & Delivery"),
            ],
        ),
        (
            "business-skills",
            "business",
            "finance-and-accounting",
            "Finance & Accounting",
            [
                ("corporate-finance-and-valuation", "Corporate Finance & Valuation"),
                ("accounting-and-audit", "Accounting, Audit & Financial Reporting"),
                ("risk-and-capital-markets", "Risk Management & Capital Markets"),
            ],
        ),
        (
            "business-skills",
            "business",
            "marketing-and-sales",
            "Marketing, Sales & Growth",
            [
                ("digital-marketing-and-seo", "Digital Marketing & SEO"),
                ("sales-and-business-development", "B2B Sales & Revenue Operations"),
                ("customer-success-and-crm", "Customer Success & CRM"),
            ],
        ),
        (
            "business-skills",
            "business",
            "operations-and-hr",
            "Operations, People & HR",
            [
                ("talent-acquisition-and-people", "Talent Acquisition & People Operations"),
                ("supply-chain-and-procurement", "Supply Chain & Procurement"),
            ],
        ),
        # Soft Skills Domain
        (
            "soft-skills",
            "soft",
            "interpersonal-skills",
            "Interpersonal Communication & Teamwork",
            [
                ("communication-and-presentation", "Communication & Presentation"),
                ("collaboration-and-stakeholder", "Collaboration & Stakeholder Management"),
            ],
        ),
        (
            "soft-skills",
            "soft",
            "leadership-and-strategy",
            "Leadership & Strategic Thinking",
            [
                ("leadership-and-people-development", "Leadership & People Development"),
                ("strategic-decision-making", "Strategic Thinking & Decision Making"),
                ("problem-solving-and-adaptability", "Problem Solving & Adaptability"),
            ],
        ),
        # Domain Knowledge Domain
        (
            "domain-knowledge",
            "domain",
            "healthcare-and-biotech",
            "Healthcare & Life Sciences",
            [
                ("clinical-systems-and-ehr", "Clinical Systems & Health Informatics"),
                ("biomedical-and-genomics", "Biomedical Engineering & Genomics"),
                ("healthcare-regulations", "Healthcare Regulatory & Compliance"),
            ],
        ),
        (
            "domain-knowledge",
            "domain",
            "fintech-and-banking",
            "FinTech & Financial Systems",
            [
                ("banking-systems-and-payments", "Banking Systems & Digital Payments"),
                ("financial-regulations-compliance", "Financial Regulations & AML/KYC"),
            ],
        ),
        (
            "domain-knowledge",
            "domain",
            "manufacturing-and-energy",
            "Manufacturing, Hardware & Energy",
            [
                ("industrial-automation-scada", "Industrial Automation & SCADA"),
                ("clean-energy-and-utilities", "Clean Energy & Smart Utilities"),
            ],
        ),
        (
            "domain-knowledge",
            "domain",
            "legal-and-governance",
            "Legal, Governance & Risk",
            [
                ("corporate-law-and-contracts", "Corporate Law & Contracts"),
                ("privacy-and-data-governance", "Privacy & Data Governance"),
            ],
        ),
    ]

    for d_slug, d_type, c_slug, c_name, subcats in taxonomy_structure:
        add_skill(
            c_slug,
            c_name,
            d_type,
            1,
            d_slug,
            f"{c_name} category under {d_slug.replace('-', ' ').title()}",
        )
        for s_slug, s_name in subcats:
            add_skill(
                s_slug,
                s_name,
                d_type,
                2,
                c_slug,
                f"{s_name} subcategory under {c_name}",
            )

    # -------------------------------------------------------------
    # 3. Core Curated Skills (Level 3)
    # -------------------------------------------------------------
    curated_level3_skills = [
        # System Languages
        (
            "system-and-compiled-languages",
            "c-language",
            "C",
            "Low-level compiled systems programming language",
            ["c programming", "ansi c", "c99", "c11"],
        ),
        (
            "system-and-compiled-languages",
            "c-plus-plus",
            "C++",
            "High-performance object-oriented and generic systems language",
            ["cpp", "c plus plus", "c++17", "c++20"],
        ),
        (
            "system-and-compiled-languages",
            "rust-language",
            "Rust",
            "Memory-safe systems programming language without garbage collection",
            ["rust", "rustlang"],
        ),
        (
            "system-and-compiled-languages",
            "golang",
            "Go",
            "Statically typed compiled language designed for scalable concurrency",
            ["go", "go lang", "golang programming"],
        ),
        (
            "system-and-compiled-languages",
            "zig",
            "Zig",
            "General-purpose systems programming language and toolchain",
            ["ziglang"],
        ),
        (
            "system-and-compiled-languages",
            "assembly-language",
            "Assembly Language",
            "Low-level machine instruction language",
            ["x86 assembly", "arm assembly"],
        ),
        # JVM Languages
        (
            "jvm-languages",
            "java",
            "Java",
            "Object-oriented class-based language running on the Java Virtual Machine",
            ["core java", "java 11", "java 17", "java 21", "jvm"],
        ),
        (
            "jvm-languages",
            "kotlin",
            "Kotlin",
            "Modern concise multiplatform language interoperable with Java",
            ["kotlinlang", "kotlin jvm", "kotlin multiplatform"],
        ),
        (
            "jvm-languages",
            "scala",
            "Scala",
            "Language combining object-oriented and functional programming on JVM",
            ["scalalang", "scala 3"],
        ),
        (
            "jvm-languages",
            "clojure",
            "Clojure",
            "Dynamic functional Lisp dialect targeting the JVM",
            ["clojure jvm", "clojurescript"],
        ),
        # Scripting & Dynamic
        (
            "dynamic-and-scripting-languages",
            "python",
            "Python",
            "Interpreted high-level general-purpose programming language",
            ["python3", "python 3", "cpython", "py"],
        ),
        (
            "dynamic-and-scripting-languages",
            "javascript",
            "JavaScript",
            "Dynamic high-level scripting language for client and server web applications",
            ["js", "ecmascript", "es6", "esnext"],
        ),
        (
            "dynamic-and-scripting-languages",
            "typescript",
            "TypeScript",
            "Typed superset of JavaScript compiling to plain JavaScript",
            ["ts", "typed javascript"],
        ),
        (
            "dynamic-and-scripting-languages",
            "c-sharp",
            "C#",
            "Modern general-purpose object-oriented language for .NET",
            ["csharp", "c sharp", "c#.net", "dotnet c#"],
        ),
        (
            "dynamic-and-scripting-languages",
            "ruby-language",
            "Ruby",
            "Dynamic interpreted object-oriented language",
            ["ruby", "ruby programming"],
        ),
        (
            "dynamic-and-scripting-languages",
            "php",
            "PHP",
            "Popular general-purpose server-side scripting language",
            ["php 8", "php scripting"],
        ),
        (
            "dynamic-and-scripting-languages",
            "r-language",
            "R",
            "Language and environment for statistical computing and graphics",
            ["r", "r programming", "rstats"],
        ),
        (
            "dynamic-and-scripting-languages",
            "julia",
            "Julia",
            "High-performance dynamic language for technical computing",
            ["julialang"],
        ),
        (
            "dynamic-and-scripting-languages",
            "elixir",
            "Elixir",
            "Functional concurrent language built on Erlang BEAM virtual machine",
            ["elixirlang"],
        ),
        (
            "dynamic-and-scripting-languages",
            "dart",
            "Dart",
            "Client-optimized programming language for multiplatform apps",
            ["dartlang"],
        ),
        (
            "dynamic-and-scripting-languages",
            "sql",
            "SQL",
            "Structured Query Language for managing data in relational databases",
            ["structured query language", "ansi sql", "sql queries"],
        ),
        (
            "dynamic-and-scripting-languages",
            "solidity",
            "Solidity",
            "Object-oriented language for Ethereum smart contracts",
            ["solidity smart contracts"],
        ),
        (
            "dynamic-and-scripting-languages",
            "shell-scripting",
            "Shell Scripting",
            "Scripting for Unix shells including Bash and Zsh",
            ["bash", "zsh", "bash scripting"],
        ),
        # Frontend
        (
            "frontend-frameworks",
            "react",
            "React",
            "Declarative component-based UI library for web interfaces",
            ["react.js", "reactjs", "react js"],
        ),
        (
            "frontend-frameworks",
            "vue-js",
            "Vue.js",
            "Progressive approachable framework for building web interfaces",
            ["vue", "vue.js", "vuejs", "vue 3"],
        ),
        (
            "frontend-frameworks",
            "angular",
            "Angular",
            "Comprehensive TypeScript-based web application platform",
            ["angular.js", "angularjs", "angular 2+"],
        ),
        (
            "frontend-frameworks",
            "svelte",
            "Svelte",
            "Compile-time component framework for reactive web user interfaces",
            ["sveltejs", "svelte 4", "svelte 5"],
        ),
        (
            "frontend-frameworks",
            "next-js",
            "Next.js",
            "React framework for full-stack web applications with server components",
            ["nextjs", "next.js", "next js"],
        ),
        (
            "frontend-frameworks",
            "nuxt-js",
            "Nuxt.js",
            "Intuitive Vue framework for universal and SSR applications",
            ["nuxtjs", "nuxt.js"],
        ),
        (
            "frontend-frameworks",
            "remix",
            "Remix",
            "Full-stack React framework focused on web standards",
            ["remix.run", "remix js"],
        ),
        (
            "frontend-frameworks",
            "astro",
            "Astro",
            "Content-focused web framework with islands architecture",
            ["astro.build"],
        ),
        (
            "frontend-frameworks",
            "solidjs",
            "SolidJS",
            "High-performance declarative UI library with fine-grained reactivity",
            ["solid.js"],
        ),
        (
            "frontend-frameworks",
            "redux",
            "Redux",
            "Predictable state container for JavaScript apps",
            ["redux toolkit", "rtk", "react-redux"],
        ),
        (
            "frontend-frameworks",
            "zustand",
            "Zustand",
            "Small, fast state-management solution for React",
            ["zustand state management"],
        ),
        (
            "frontend-frameworks",
            "html5",
            "HTML5",
            "Standard markup language for structuring web documents",
            ["html", "semantic html"],
        ),
        (
            "frontend-frameworks",
            "css3",
            "CSS3",
            "Style sheet language for web presentation",
            ["css", "cascading style sheets"],
        ),
        (
            "frontend-frameworks",
            "tailwindcss",
            "Tailwind CSS",
            "Utility-first CSS framework for custom user interfaces",
            ["tailwind", "tailwind css"],
        ),
        (
            "frontend-frameworks",
            "sass-css",
            "Sass",
            "Preprocessor scripting language compiled into CSS",
            ["sass", "scss"],
        ),
        (
            "frontend-frameworks",
            "bootstrap",
            "Bootstrap",
            "HTML, CSS, and JS framework for responsive web apps",
            ["bootstrap 5"],
        ),
        (
            "frontend-frameworks",
            "webassembly",
            "WebAssembly",
            "Binary instruction format for high performance in browsers",
            ["wasm", "web assembly"],
        ),
        # Backend
        (
            "backend-frameworks",
            "node-js",
            "Node.js",
            "Asynchronous event-driven JavaScript runtime environment",
            ["nodejs", "node.js", "node js"],
        ),
        (
            "backend-frameworks",
            "express-js",
            "Express.js",
            "Fast, unopinionated minimalist web framework for Node.js",
            ["express", "expressjs"],
        ),
        (
            "backend-frameworks",
            "nest-js",
            "NestJS",
            "Progressive TypeScript Node.js server-side framework",
            ["nestjs", "nest.js"],
        ),
        (
            "backend-frameworks",
            "fastify",
            "Fastify",
            "High-throughput and low overhead web framework for Node.js",
            ["fastify js"],
        ),
        (
            "backend-frameworks",
            "fastapi",
            "FastAPI",
            "Modern high-performance Python web API framework with type hints",
            ["fast api", "fastapi python"],
        ),
        (
            "backend-frameworks",
            "django",
            "Django",
            "High-level Python web framework with built-in ORM and admin",
            ["django framework", "django rest framework", "drf"],
        ),
        (
            "backend-frameworks",
            "flask",
            "Flask",
            "Lightweight WSGI Python micro web framework",
            ["flask framework", "flask python"],
        ),
        (
            "backend-frameworks",
            "spring-boot",
            "Spring Boot",
            "Opinionated Java framework for production-grade microservices",
            ["springboot", "spring boot 3"],
        ),
        (
            "backend-frameworks",
            "spring-framework",
            "Spring Framework",
            "Comprehensive enterprise Java application framework",
            ["spring mvc", "spring security"],
        ),
        (
            "backend-frameworks",
            "aspnet-core",
            "ASP.NET Core",
            "Cross-platform open-source web framework for modern .NET apps",
            ["asp.net core", "dotnet core", ".net core"],
        ),
        (
            "backend-frameworks",
            "ruby-on-rails",
            "Ruby on Rails",
            "Server-side web application framework in Ruby",
            ["rails", "ror", "ruby rails"],
        ),
        (
            "backend-frameworks",
            "laravel",
            "Laravel",
            "PHP web framework with expressive syntax and broad ecosystem",
            ["laravel framework"],
        ),
        (
            "backend-frameworks",
            "gin-gonic",
            "Gin",
            "HTTP web framework written in Go featuring martini-like API",
            ["gin", "gin-gonic"],
        ),
        (
            "backend-frameworks",
            "actix-web",
            "Actix Web",
            "Blazing fast actor-based web framework for Rust",
            ["actix", "actix rust"],
        ),
        (
            "backend-frameworks",
            "axum",
            "Axum",
            "Ergonomic modular web application framework in Rust",
            ["axum rust"],
        ),
        (
            "backend-frameworks",
            "phoenix-framework",
            "Phoenix",
            "High-productivity web framework for Elixir",
            ["phoenix elixir"],
        ),
        # ML & AI
        (
            "machine-learning-frameworks",
            "machine-learning",
            "Machine Learning",
            "Algorithms building mathematical models from training data",
            ["ml", "statistical machine learning"],
        ),
        (
            "machine-learning-frameworks",
            "deep-learning",
            "Deep Learning",
            "Neural network architectures with multi-layer representation learning",
            ["dl", "neural networks", "deep neural networks"],
        ),
        (
            "machine-learning-frameworks",
            "artificial-intelligence",
            "Artificial Intelligence",
            "Theory and development of intelligent computer systems",
            ["ai", "applied ai"],
        ),
        (
            "machine-learning-frameworks",
            "pytorch",
            "PyTorch",
            "Open source machine learning framework with dynamic computation graphs",
            ["torch", "pytorch dl"],
        ),
        (
            "machine-learning-frameworks",
            "tensorflow",
            "TensorFlow",
            "End-to-end open source machine learning platform by Google",
            ["tf", "tensorflow 2"],
        ),
        (
            "machine-learning-frameworks",
            "keras",
            "Keras",
            "High-level deep learning API running atop TensorFlow and PyTorch",
            ["keras deep learning"],
        ),
        (
            "machine-learning-frameworks",
            "scikit-learn",
            "Scikit-Learn",
            "Machine learning tools in Python for classification and regression",
            ["sklearn", "scikit learn"],
        ),
        (
            "machine-learning-frameworks",
            "jax",
            "JAX",
            "Composable transformations of Python+NumPy with GPU acceleration",
            ["google jax", "flax"],
        ),
        (
            "machine-learning-frameworks",
            "xgboost",
            "XGBoost",
            "Scalable distributed gradient-boosted decision tree library",
            ["extreme gradient boosting"],
        ),
        (
            "machine-learning-frameworks",
            "lightgbm",
            "LightGBM",
            "Fast distributed gradient boosting framework by Microsoft",
            ["lgbm"],
        ),
        (
            "machine-learning-frameworks",
            "catboost",
            "CatBoost",
            "Fast gradient boosting on decision trees",
            ["catboost ml"],
        ),
        (
            "machine-learning-frameworks",
            "mlflow",
            "MLflow",
            "Open source platform to manage the ML lifecycle",
            ["mlflow tracking"],
        ),
        (
            "machine-learning-frameworks",
            "weights-and-biases",
            "Weights & Biases",
            "Platform for tracking ML experiments and dataset versioning",
            ["wandb", "w&b"],
        ),
        (
            "machine-learning-frameworks",
            "machine-learning-operations",
            "MLOps",
            "Practices and systems for automated ML operations",
            ["mlops", "ml operations"],
        ),
        (
            "machine-learning-frameworks",
            "machine-learning-engineering",
            "Machine Learning Engineering",
            "Engineering scalable ML models in production",
            ["ml engineering", "mle", "ml engineer"],
        ),
        # GenAI & LLMs
        (
            "generative-ai-and-llms",
            "large-language-models",
            "Large Language Models",
            "Massive transformer models for complex text comprehension",
            ["llm", "llms", "foundation models"],
        ),
        (
            "generative-ai-and-llms",
            "generative-ai",
            "Generative AI",
            "AI systems generating novel text, code, images, and audio",
            ["genai", "gen ai", "generative ai"],
        ),
        (
            "generative-ai-and-llms",
            "retrieval-augmented-generation",
            "Retrieval-Augmented Generation",
            "Framework augmenting LLMs with document retrieval",
            ["rag", "rag systems", "semantic retrieval"],
        ),
        (
            "generative-ai-and-llms",
            "huggingface-transformers",
            "Transformers",
            "State-of-the-art transformer architectures by Hugging Face",
            ["huggingface", "hugging face", "hf transformers"],
        ),
        (
            "generative-ai-and-llms",
            "langchain",
            "LangChain",
            "Framework for building context-aware reasoning applications with LLMs",
            ["lang chain", "langchain python"],
        ),
        (
            "generative-ai-and-llms",
            "llamaindex",
            "LlamaIndex",
            "Data framework for ingesting and searching private data with LLMs",
            ["llama-index", "gpt-index"],
        ),
        (
            "generative-ai-and-llms",
            "prompt-engineering",
            "Prompt Engineering",
            "Techniques for structuring instructions to optimize LLM outputs",
            ["prompt design", "in-context prompting"],
        ),
        (
            "generative-ai-and-llms",
            "fine-tuning",
            "Fine-Tuning",
            "Adapting pre-trained model weights to specialized domains",
            ["model fine-tuning", "supervised fine-tuning", "sft"],
        ),
        (
            "generative-ai-and-llms",
            "lora",
            "LoRA",
            "Low-Rank Adaptation parameter-efficient fine-tuning technique",
            ["qlora", "peft", "low rank adaptation"],
        ),
        (
            "generative-ai-and-llms",
            "vllm",
            "vLLM",
            "High-throughput and memory-efficient LLM inference serving engine",
            ["vllm serving"],
        ),
        (
            "generative-ai-and-llms",
            "deepspeed",
            "DeepSpeed",
            "Deep learning optimization library for distributed training",
            ["microsoft deepspeed"],
        ),
        (
            "generative-ai-and-llms",
            "triton-inference-server",
            "Triton Inference Server",
            "Enterprise multi-framework AI model serving platform",
            ["nvidia triton", "triton server"],
        ),
        # NLP & Vision
        (
            "natural-language-and-vision",
            "natural-language-processing",
            "Natural Language Processing",
            "Techniques for analyzing and generating human language",
            ["nlp", "computational linguistics"],
        ),
        (
            "natural-language-and-vision",
            "computer-vision",
            "Computer Vision",
            "Interpreting and understanding digital visual data",
            ["cv", "visual recognition", "image processing"],
        ),
        (
            "natural-language-and-vision",
            "opencv",
            "OpenCV",
            "Open source computer vision and image analysis library",
            ["cv2", "open-cv"],
        ),
        # Data Engineering
        (
            "data-engineering-and-analytics",
            "pandas",
            "Pandas",
            "Python data analysis library providing DataFrame structures",
            ["pandas dataframe", "py-pandas"],
        ),
        (
            "data-engineering-and-analytics",
            "numpy",
            "NumPy",
            "Scientific computing package for array manipulation in Python",
            ["numpy arrays", "py-numpy"],
        ),
        (
            "data-engineering-and-analytics",
            "polars",
            "Polars",
            "Fast multi-threaded DataFrame library implemented in Rust",
            ["polars dataframe", "py-polars"],
        ),
        (
            "data-engineering-and-analytics",
            "scipy",
            "SciPy",
            "Scientific algorithms and mathematical tools for Python",
            ["scipy computing"],
        ),
        (
            "data-engineering-and-analytics",
            "apache-spark",
            "Apache Spark",
            "Unified distributed engine for large-scale data analytics",
            ["spark", "spark sql", "spark streaming"],
        ),
        (
            "data-engineering-and-analytics",
            "pyspark",
            "PySpark",
            "Python API for Apache Spark distributed computing",
            ["pyspark dataframe"],
        ),
        (
            "data-engineering-and-analytics",
            "databricks",
            "Databricks",
            "Unified data analytics platform powered by Apache Spark",
            ["databricks lakehouse"],
        ),
        (
            "data-engineering-and-analytics",
            "dbt",
            "dbt",
            "Data build tool for analytics engineering in the warehouse",
            ["dbt-core", "dbt cloud", "data build tool"],
        ),
        (
            "data-engineering-and-analytics",
            "apache-kafka",
            "Apache Kafka",
            "Distributed event streaming platform for real-time pipelines",
            ["kafka", "kafka streams", "kafka connect"],
        ),
        (
            "data-engineering-and-analytics",
            "apache-airflow",
            "Apache Airflow",
            "Workflow orchestration platform to schedule pipelines",
            ["airflow", "airflow dags"],
        ),
        (
            "data-engineering-and-analytics",
            "snowflake",
            "Snowflake",
            "Cloud data warehouse and analytical processing platform",
            ["snowflake data warehouse"],
        ),
        (
            "data-engineering-and-analytics",
            "bigquery",
            "Google BigQuery",
            "Serverless highly scalable cloud data warehouse",
            ["bigquery", "gcp bigquery"],
        ),
        (
            "data-engineering-and-analytics",
            "data-engineering",
            "Data Engineering",
            "Designing and building systems for data processing",
            ["de", "data infrastructure"],
        ),
        (
            "data-engineering-and-analytics",
            "business-intelligence",
            "Business Intelligence",
            "Architectures for converting data into business insight",
            ["bi", "bi reporting"],
        ),
        (
            "data-engineering-and-analytics",
            "extract-transform-load",
            "ETL",
            "Extract, Transform, and Load structured and raw data",
            ["etl", "data ingestion"],
        ),
        (
            "data-engineering-and-analytics",
            "extract-load-transform",
            "ELT",
            "Transforming data inside the analytical data warehouse",
            ["elt"],
        ),
        # Vector Databases
        (
            "vector-and-search-databases",
            "pinecone",
            "Pinecone",
            "Managed vector database for high-speed similarity search",
            ["pinecone vector db"],
        ),
        (
            "vector-and-search-databases",
            "chromadb",
            "ChromaDB",
            "AI-native open-source embedding database for LLMs",
            ["chroma", "chroma db"],
        ),
        (
            "vector-and-search-databases",
            "weaviate",
            "Weaviate",
            "Open-source vector search engine and database",
            ["weaviate vector db"],
        ),
        (
            "vector-and-search-databases",
            "qdrant",
            "Qdrant",
            "Vector similarity search engine with payload filtering",
            ["qdrant vector db"],
        ),
        (
            "vector-and-search-databases",
            "vector-databases",
            "Vector Databases",
            "Specialized databases for vector embeddings",
            ["vector db", "vector stores"],
        ),
        (
            "vector-and-search-databases",
            "elasticsearch",
            "Elasticsearch",
            "Distributed search and analytics engine on Lucene",
            ["elastic search", "elastic stack"],
        ),
        # Cloud Platforms
        (
            "cloud-platforms",
            "amazon-web-services",
            "Amazon Web Services (AWS)",
            "Comprehensive hyperscale cloud computing platform",
            ["aws", "amazon cloud", "aws cloud"],
        ),
        (
            "cloud-platforms",
            "google-cloud-platform",
            "Google Cloud Platform (GCP)",
            "Hyperscale cloud platform infrastructure by Google",
            ["gcp", "google cloud"],
        ),
        (
            "cloud-platforms",
            "microsoft-azure",
            "Microsoft Azure",
            "Enterprise cloud computing service platform by Microsoft",
            ["azure", "azure cloud", "ms azure"],
        ),
        (
            "cloud-platforms",
            "cloudflare",
            "Cloudflare",
            "Global cloud security and serverless edge network",
            ["cloudflare workers", "cloudflare cdn"],
        ),
        (
            "cloud-platforms",
            "vercel",
            "Vercel",
            "Frontend cloud platform for serverless and Next.js",
            ["vercel cloud"],
        ),
        (
            "cloud-platforms",
            "aws-lambda",
            "AWS Lambda",
            "Serverless compute service running code on events",
            ["lambda", "aws serverless"],
        ),
        (
            "cloud-platforms",
            "aws-s3",
            "AWS S3",
            "Scalable cloud object storage service on AWS",
            ["s3", "simple storage service", "amazon s3"],
        ),
        (
            "cloud-platforms",
            "aws-ec2",
            "AWS EC2",
            "Scalable compute cloud virtual machines on AWS",
            ["ec2", "amazon ec2"],
        ),
        (
            "cloud-platforms",
            "aws-eks",
            "AWS EKS",
            "Managed Kubernetes service on Amazon Web Services",
            ["eks", "amazon eks"],
        ),
        (
            "cloud-platforms",
            "aws-ecs",
            "AWS ECS",
            "Container management and orchestration service on AWS",
            ["ecs", "amazon ecs"],
        ),
        # Containers & DevOps
        (
            "container-and-orchestration",
            "docker",
            "Docker",
            "Containerization platform to package and run software",
            ["docker container", "dockerfile", "docker-compose"],
        ),
        (
            "container-and-orchestration",
            "kubernetes",
            "Kubernetes",
            "Container orchestration system for automating deployment",
            ["k8s", "k8", "kube"],
        ),
        (
            "container-and-orchestration",
            "helm",
            "Helm",
            "The package manager for Kubernetes applications",
            ["helm charts", "helm v3"],
        ),
        (
            "container-and-orchestration",
            "container-orchestration",
            "Container Orchestration",
            "Automating management of containerized workloads",
            ["container orchestration engine"],
        ),
        # CI/CD & IaC
        (
            "ci-cd-and-automation",
            "terraform",
            "Terraform",
            "Infrastructure as Code tool to build and version cloud",
            ["hashicorp terraform", "terraform iac"],
        ),
        (
            "ci-cd-and-automation",
            "ansible",
            "Ansible",
            "Open source IT automation tool for configuration management",
            ["ansible playbooks"],
        ),
        (
            "ci-cd-and-automation",
            "continuous-integration-and-continuous-delivery",
            "CI/CD",
            "Automated pipeline for building, testing, and deploying",
            ["ci/cd", "cicd", "ci cd", "continuous integration", "continuous deployment"],
        ),
        (
            "ci-cd-and-automation",
            "github-actions",
            "GitHub Actions",
            "CI/CD automation workflows in GitHub",
            ["gha", "github ci"],
        ),
        (
            "ci-cd-and-automation",
            "gitlab-ci",
            "GitLab CI",
            "Continuous integration and deployment in GitLab",
            ["gitlab ci/cd", "gitlab pipelines"],
        ),
        (
            "ci-cd-and-automation",
            "jenkins",
            "Jenkins",
            "Extensible open-source automation server for CI/CD",
            ["jenkins ci", "jenkins pipeline"],
        ),
        (
            "ci-cd-and-automation",
            "infrastructure-as-code",
            "Infrastructure as Code",
            "Managing infrastructure through code definitions",
            ["iac", "infrastructure automation"],
        ),
        # Observability & SRE
        (
            "observability-and-sre",
            "prometheus",
            "Prometheus",
            "Open-source monitoring system with time-series data",
            ["prometheus monitoring", "promql"],
        ),
        (
            "observability-and-sre",
            "grafana",
            "Grafana",
            "Visualization platform for metrics and logs",
            ["grafana dashboards"],
        ),
        (
            "observability-and-sre",
            "jaeger",
            "Jaeger",
            "Distributed tracing platform for microservices",
            ["jaeger tracing"],
        ),
        (
            "observability-and-sre",
            "opentelemetry",
            "OpenTelemetry",
            "Vendor-neutral telemetry framework for traces and metrics",
            ["otel", "open telemetry"],
        ),
        (
            "observability-and-sre",
            "site-reliability-engineering",
            "Site Reliability Engineering",
            "Applying software engineering to operations",
            ["sre", "reliability engineering"],
        ),
        (
            "observability-and-sre",
            "devops",
            "DevOps",
            "Integration of development and operations",
            ["dev ops", "devops engineering"],
        ),
        (
            "observability-and-sre",
            "linux",
            "Linux",
            "Unix-like open-source operating system kernel",
            ["linux os", "ubuntu", "debian", "redhat", "centos"],
        ),
        (
            "observability-and-sre",
            "nginx",
            "Nginx",
            "High-performance web server, reverse proxy, and load balancer",
            ["nginx server", "nginx reverse proxy"],
        ),
        # Databases
        (
            "relational-databases",
            "postgresql",
            "PostgreSQL",
            "Enterprise-grade open-source object-relational database",
            ["postgres", "psql", "postgresql db"],
        ),
        (
            "relational-databases",
            "mysql",
            "MySQL",
            "Open-source relational database management system",
            ["mysql db", "mysql 8"],
        ),
        (
            "relational-databases",
            "sqlite",
            "SQLite",
            "Lightweight serverless in-process SQL database engine",
            ["sqlite3", "sqlite db"],
        ),
        (
            "relational-databases",
            "oracle-db",
            "Oracle Database",
            "Multi-model database management system by Oracle",
            ["oracle sql", "pl/sql"],
        ),
        (
            "relational-databases",
            "sql-server",
            "Microsoft SQL Server",
            "Relational database management system by Microsoft",
            ["mssql", "ms sql server"],
        ),
        (
            "relational-databases",
            "relational-database-management-system",
            "RDBMS",
            "Relational database management system architecture",
            ["rdbms", "relational database"],
        ),
        # NoSQL
        (
            "nosql-and-document-databases",
            "mongodb",
            "MongoDB",
            "Document-oriented NoSQL database for JSON-like documents",
            ["mongo", "mongodb atlas"],
        ),
        (
            "nosql-and-document-databases",
            "redis",
            "Redis",
            "In-memory data structure store used as cache and broker",
            ["redis cache", "redis db"],
        ),
        (
            "nosql-and-document-databases",
            "cassandra",
            "Apache Cassandra",
            "Distributed wide-column NoSQL database",
            ["cassandra db", "cql"],
        ),
        (
            "nosql-and-document-databases",
            "dynamodb",
            "Amazon DynamoDB",
            "Managed serverless key-value NoSQL database on AWS",
            ["dynamo", "aws dynamodb"],
        ),
        (
            "nosql-and-document-databases",
            "nosql-databases",
            "NoSQL Databases",
            "Non-relational distributed database systems",
            ["nosql"],
        ),
        # Security
        (
            "identity-and-access",
            "oauth2",
            "OAuth 2.0",
            "Industry-standard authorization protocol for web apps",
            ["oauth", "oauth2"],
        ),
        (
            "identity-and-access",
            "openid-connect",
            "OpenID Connect",
            "Simple identity layer on top of OAuth 2.0 protocol",
            ["oidc"],
        ),
        (
            "identity-and-access",
            "jwt",
            "JSON Web Tokens",
            "Compact URL-safe means of representing claims",
            ["jwt tokens", "json web token"],
        ),
        (
            "identity-and-access",
            "single-sign-on",
            "Single Sign-On (SSO)",
            "Authentication scheme allowing single login for multiple apps",
            ["sso", "saml sso"],
        ),
        (
            "identity-and-access",
            "identity-and-access-management",
            "Identity and Access Management",
            "Framework of policies and technologies for digital identities",
            ["iam"],
        ),
        (
            "identity-and-access",
            "role-based-access-control",
            "Role-Based Access Control",
            "Restricting system access to authorized users based on roles",
            ["rbac"],
        ),
        # Mobile
        (
            "mobile-platforms",
            "react-native",
            "React Native",
            "Cross-platform mobile framework using React",
            ["reactnative", "react native"],
        ),
        (
            "mobile-platforms",
            "flutter",
            "Flutter",
            "Google UI toolkit for multiplatform compiled apps",
            ["flutter framework", "flutter sdk"],
        ),
        (
            "mobile-platforms",
            "swiftui",
            "SwiftUI",
            "Modern declarative UI framework for Apple platforms",
            ["swiftui ios"],
        ),
        (
            "mobile-platforms",
            "uikit",
            "UIKit",
            "Classic imperative UI framework for iOS apps",
            ["uikit ios", "ios uikit"],
        ),
        (
            "mobile-platforms",
            "jetpack-compose",
            "Jetpack Compose",
            "Android modern declarative UI toolkit",
            ["compose android", "android compose"],
        ),
        (
            "mobile-platforms",
            "android-sdk",
            "Android SDK",
            "Development kit for building Android applications",
            ["android development", "android studio"],
        ),
        (
            "mobile-platforms",
            "ios-development",
            "iOS Development",
            "Native mobile development for Apple devices",
            ["ios app development", "apple ios"],
        ),
        # Product & Agile
        (
            "product-strategy-and-execution",
            "product-management",
            "Product Management",
            "Leading end-to-end product strategy and execution",
            ["pm", "product lead", "product ownership"],
        ),
        (
            "product-strategy-and-execution",
            "product-roadmapping",
            "Product Roadmapping",
            "Defining strategic feature timelines for products",
            ["product roadmap", "roadmap planning"],
        ),
        (
            "product-strategy-and-execution",
            "user-stories",
            "User Stories",
            "Formulating user requirements in agile development",
            ["user story mapping", "acceptance criteria"],
        ),
        (
            "product-strategy-and-execution",
            "product-discovery",
            "Product Discovery",
            "Validating market needs and user pain points",
            ["customer discovery"],
        ),
        (
            "product-strategy-and-execution",
            "competitive-analysis",
            "Competitive Analysis",
            "Evaluating competitor strengths and market positioning",
            ["market analysis"],
        ),
        (
            "agile-and-project-management",
            "project-management",
            "Project Management",
            "Planning and executing projects across cross-functional teams",
            ["pmp", "project delivery"],
        ),
        (
            "agile-and-project-management",
            "agile-methodology",
            "Agile Methodology",
            "Iterative and flexible approach to software delivery",
            ["agile", "agile development"],
        ),
        (
            "agile-and-project-management",
            "scrum",
            "Scrum",
            "Agile framework with sprints and standups",
            ["scrum framework"],
        ),
        (
            "agile-and-project-management",
            "kanban",
            "Kanban",
            "Visual workflow management method with WIP limits",
            ["kanban boards"],
        ),
        (
            "agile-and-project-management",
            "jira",
            "Jira",
            "Issue and project tracking software for agile teams",
            ["atlassian jira", "jira software"],
        ),
        (
            "agile-and-project-management",
            "confluence",
            "Confluence",
            "Collaborative workspace for documentation",
            ["atlassian confluence"],
        ),
        (
            "agile-and-project-management",
            "linear",
            "Linear",
            "Issue tracking and project management tool",
            ["linear app"],
        ),
        (
            "agile-and-project-management",
            "notion",
            "Notion",
            "All-in-one collaborative workspace",
            ["notion workspace"],
        ),
        (
            "agile-and-project-management",
            "asana",
            "Asana",
            "Work management platform to track team initiatives",
            ["asana project management"],
        ),
        (
            "user-experience-and-ui",
            "user-experience-design",
            "User Experience (UX) Design",
            "Designing intuitive digital experiences",
            ["ux", "ux design", "ui/ux", "ui ux"],
        ),
        (
            "user-experience-and-ui",
            "user-interface-design",
            "User Interface (UI) Design",
            "Visual and interactive interface design",
            ["ui", "ui design"],
        ),
        (
            "user-experience-and-ui",
            "figma",
            "Figma",
            "Collaborative interface design and prototyping tool",
            ["figma design", "figma ui"],
        ),
        (
            "user-experience-and-ui",
            "adobe-xd",
            "Adobe XD",
            "Vector-based user experience design tool",
            ["xd"],
        ),
        (
            "user-experience-and-ui",
            "sketch",
            "Sketch",
            "Digital design and prototyping platform",
            ["sketch app"],
        ),
        (
            "user-experience-and-ui",
            "wireframing",
            "Wireframing",
            "Creating structural blueprints for web and mobile layouts",
            ["wireframes"],
        ),
        (
            "user-experience-and-ui",
            "prototyping",
            "Prototyping",
            "Building interactive mockups for usability testing",
            ["prototype"],
        ),
        (
            "user-experience-and-ui",
            "user-research",
            "User Research",
            "Gathering qualitative insights from users",
            ["usability research"],
        ),
        (
            "user-experience-and-ui",
            "design-systems",
            "Design Systems",
            "Standardized components and guidelines for UI design",
            ["component libraries"],
        ),
        # Finance
        (
            "corporate-finance-and-valuation",
            "financial-modeling",
            "Financial Modeling",
            "Building spreadsheet models to forecast financial outcomes",
            ["three statement modeling", "financial forecasting"],
        ),
        (
            "corporate-finance-and-valuation",
            "dcf-valuation",
            "DCF Valuation",
            "Discounted Cash Flow method for estimating intrinsic value",
            ["discounted cash flow", "wacc"],
        ),
        (
            "corporate-finance-and-valuation",
            "lbo-modeling",
            "LBO Modeling",
            "Leveraged Buyout modeling and debt structuring",
            ["leveraged buyout"],
        ),
        (
            "corporate-finance-and-valuation",
            "corporate-finance",
            "Corporate Finance",
            "Managing financial decisions and capital allocation",
            ["capital budgeting"],
        ),
        (
            "corporate-finance-and-valuation",
            "financial-analysis",
            "Financial Analysis",
            "Evaluating financial health, profitability, and cost",
            ["ratio analysis"],
        ),
        (
            "corporate-finance-and-valuation",
            "financial-accounting",
            "Financial Accounting",
            "Preparing financial statements in compliance with standards",
            ["statutory reporting", "general ledger"],
        ),
        (
            "corporate-finance-and-valuation",
            "gaap",
            "GAAP",
            "Generally Accepted Accounting Principles",
            ["us gaap"],
        ),
        (
            "corporate-finance-and-valuation",
            "ifrs",
            "IFRS",
            "International Financial Reporting Standards",
            ["international accounting standards"],
        ),
        (
            "corporate-finance-and-valuation",
            "bloomberg-terminal",
            "Bloomberg Terminal",
            "Financial market data and analytics platform",
            ["bloomberg"],
        ),
        # Marketing & Sales
        (
            "digital-marketing-and-seo",
            "digital-marketing",
            "Digital Marketing",
            "Promoting products through online and digital channels",
            ["online marketing"],
        ),
        (
            "digital-marketing-and-seo",
            "search-engine-optimization",
            "Search Engine Optimization (SEO)",
            "Optimizing website content for organic search traffic",
            ["seo", "technical seo"],
        ),
        (
            "digital-marketing-and-seo",
            "search-engine-marketing",
            "Search Engine Marketing (SEM)",
            "Paid search advertising strategies",
            ["sem", "paid search", "google ads"],
        ),
        (
            "digital-marketing-and-seo",
            "google-analytics",
            "Google Analytics",
            "Web analytics service tracking website traffic and metrics",
            ["ga4", "google analytics 4"],
        ),
        (
            "digital-marketing-and-seo",
            "growth-marketing",
            "Growth Marketing",
            "Data-driven marketing for user acquisition and retention",
            ["growth hacking"],
        ),
        (
            "digital-marketing-and-seo",
            "conversion-rate-optimization",
            "Conversion Rate Optimization (CRO)",
            "Increasing percentage of visitors converting to actions",
            ["cro", "ab testing", "a/b testing"],
        ),
        (
            "sales-and-business-development",
            "salesforce",
            "Salesforce",
            "Enterprise CRM platform for sales and customer support",
            ["salesforce crm", "sfdc"],
        ),
        (
            "sales-and-business-development",
            "hubspot",
            "HubSpot",
            "Inbound marketing, sales, and service CRM",
            ["hubspot crm", "hubspot marketing"],
        ),
        (
            "sales-and-business-development",
            "b2b-sales",
            "B2B Sales",
            "Business-to-business sales and deal closing",
            ["enterprise sales", "account executive"],
        ),
        (
            "sales-and-business-development",
            "customer-relationship-management",
            "CRM",
            "Customer relationship management systems",
            ["crm", "customer management"],
        ),
        # Soft Skills
        (
            "communication-and-presentation",
            "effective-communication",
            "Effective Communication",
            "Conveying information clearly across teams",
            ["verbal communication", "written communication"],
        ),
        (
            "communication-and-presentation",
            "stakeholder-communication",
            "Stakeholder Communication",
            "Communicating project status to executive leadership",
            ["stakeholder management"],
        ),
        (
            "communication-and-presentation",
            "technical-writing",
            "Technical Writing",
            "Authoring clear documentation and architecture records",
            ["documentation", "api documentation"],
        ),
        (
            "communication-and-presentation",
            "public-speaking",
            "Public Speaking",
            "Presenting ideas and technical talks to audiences",
            ["presentation skills"],
        ),
        (
            "leadership-and-people-development",
            "team-leadership",
            "Team Leadership",
            "Guiding and motivating teams toward shared goals",
            ["leading teams", "team lead"],
        ),
        (
            "leadership-and-people-development",
            "people-management",
            "People Management",
            "Overseeing career development and performance reviews",
            ["engineering management", "direct reports"],
        ),
        (
            "leadership-and-people-development",
            "mentoring",
            "Mentoring",
            "Advising and supporting colleagues in technical growth",
            ["coaching", "technical mentoring"],
        ),
        (
            "problem-solving-and-adaptability",
            "problem-solving",
            "Problem Solving",
            "Identifying challenges and implementing sustainable solutions",
            ["analytical problem solving"],
        ),
        (
            "problem-solving-and-adaptability",
            "root-cause-analysis",
            "Root Cause Analysis",
            "Structured method of identifying system breakdowns",
            ["rca", "5 whys"],
        ),
        (
            "problem-solving-and-adaptability",
            "critical-thinking",
            "Critical Thinking",
            "Objective analysis and evaluation to form sound judgments",
            ["logical reasoning"],
        ),
        (
            "problem-solving-and-adaptability",
            "adaptability",
            "Adaptability",
            "Adjusting rapidly to new requirements and environments",
            ["flexibility", "resilience"],
        ),
        (
            "problem-solving-and-adaptability",
            "time-management",
            "Time Management",
            "Organizing and prioritizing tasks effectively",
            ["prioritization"],
        ),
        # Healthcare Domain
        (
            "clinical-systems-and-ehr",
            "electronic-health-records",
            "Electronic Health Records (EHR)",
            "Digital patient medical records across clinical networks",
            ["ehr", "emr"],
        ),
        (
            "clinical-systems-and-ehr",
            "epic-systems",
            "Epic Systems",
            "Enterprise healthcare software for hospital records",
            ["epic ehr"],
        ),
        (
            "clinical-systems-and-ehr",
            "cerner",
            "Cerner",
            "Health information technology and records platform",
            ["oracle cerner"],
        ),
        (
            "clinical-systems-and-ehr",
            "hl7-fhir",
            "HL7 / FHIR",
            "Standards for exchanging clinical health data",
            ["fhir", "hl7 v2"],
        ),
        (
            "healthcare-regulations",
            "hipaa-compliance",
            "HIPAA Compliance",
            "Adhering to US healthcare data privacy regulations",
            ["hipaa regulations"],
        ),
        (
            "healthcare-regulations",
            "clinical-trials",
            "Clinical Trials",
            "Research studies testing medical treatments on humans",
            ["clinical study management"],
        ),
        (
            "biomedical-and-genomics",
            "bioinformatics",
            "Bioinformatics",
            "Applying computational tools to molecular biology",
            ["computational biology", "genomics"],
        ),
        # FinTech Domain
        (
            "banking-systems-and-payments",
            "payment-gateways",
            "Payment Gateways",
            "Technology processing credit cards and electronic payments",
            ["stripe", "adyen", "paypal integration"],
        ),
        (
            "financial-regulations-compliance",
            "pci-dss",
            "PCI DSS",
            "Payment Card Industry Data Security Standard",
            ["pci compliance"],
        ),
        (
            "financial-regulations-compliance",
            "anti-money-laundering",
            "Anti-Money Laundering (AML)",
            "Regulations preventing disguising illegally obtained funds",
            ["aml", "kyc aml"],
        ),
        (
            "financial-regulations-compliance",
            "know-your-customer",
            "Know Your Customer (KYC)",
            "Identity verification and customer due diligence",
            ["kyc", "customer onboarding"],
        ),
        (
            "banking-systems-and-payments",
            "algorithmic-trading",
            "Algorithmic Trading",
            "Automated computer execution of financial market orders",
            ["algo trading", "quantitative trading"],
        ),
        (
            "banking-systems-and-payments",
            "credit-risk-modeling",
            "Credit Risk Modeling",
            "Statistical models predicting borrower default probability",
            ["credit risk"],
        ),
        # Manufacturing & Logistics
        (
            "industrial-automation-scada",
            "supply-chain-management",
            "Supply Chain Management",
            "Managing the flow of goods, services, and raw materials",
            ["supply chain optimization", "logistics"],
        ),
        (
            "industrial-automation-scada",
            "internet-of-things",
            "Internet of Things (IoT)",
            "Network of physical devices connected to internet",
            ["iot", "connected devices"],
        ),
        (
            "industrial-automation-scada",
            "embedded-c",
            "Embedded C",
            "C programming tailored to embedded microcontrollers",
            ["embedded systems"],
        ),
        (
            "industrial-automation-scada",
            "scada",
            "SCADA",
            "Supervisory Control and Data Acquisition industrial automation",
            ["scada systems"],
        ),
        (
            "industrial-automation-scada",
            "plc-programming",
            "PLC Programming",
            "Programming Programmable Logic Controllers for automated factory systems",
            ["plc ladder logic"],
        ),
        (
            "industrial-automation-scada",
            "six-sigma",
            "Six Sigma",
            "Methodology for process improvement and defect reduction",
            ["lean six sigma"],
        ),
        # Legal & Governance
        (
            "privacy-and-data-governance",
            "gdpr",
            "GDPR",
            "General Data Protection Regulation standards for European data privacy",
            ["eu gdpr"],
        ),
        (
            "privacy-and-data-governance",
            "soc2",
            "SOC 2",
            "Security, availability, and confidentiality audit compliance",
            ["soc 2 type ii"],
        ),
        (
            "privacy-and-data-governance",
            "iso-27001",
            "ISO/IEC 27001",
            "Information security management systems standard",
            ["iso 27001"],
        ),
        (
            "corporate-law-and-contracts",
            "contract-drafting",
            "Contract Drafting",
            "Preparing legally binding commercial agreements and NDAs",
            ["commercial contracts"],
        ),
        (
            "corporate-law-and-contracts",
            "intellectual-property",
            "Intellectual Property (IP)",
            "Protecting patents, trademarks, and copyrights",
            ["patent prosecution"],
        ),
    ]

    for parent_subcat, s_slug, s_name, s_desc, s_aliases in curated_level3_skills:
        parent_record = next((r for r in skills_records if r["slug"] == parent_subcat), None)
        d_type = parent_record["type"] if parent_record else "technical"
        add_skill(s_slug, s_name, d_type, 3, parent_subcat, s_desc, s_aliases)

    # Real skills referenced by the generators and curated aliases that the tree above lacks.
    for parent_subcat, s_slug, s_name, s_desc, s_aliases in EXTRA_CURATED_SKILLS:
        parent_record = next((r for r in skills_records if r["slug"] == parent_subcat), None)
        d_type = parent_record["type"] if parent_record else "technical"
        add_skill(s_slug, s_name, d_type, 3, parent_subcat, s_desc, s_aliases)

    merge_curated_tech_yaml(skills_records, add_skill)

    referenced_slugs = load_rule_referenced_slugs()
    add_onet_layer(skills_records, add_skill, seen_slugs, referenced_slugs)
    register_rule_referenced_slugs(skills_records, add_skill, seen_slugs, referenced_slugs)
    return skills_records


# -------------------------------------------------------------------------------------------------
# Extra curated skills, curated_tech.yaml, O*NET layer
# -------------------------------------------------------------------------------------------------

EXTRA_CURATED_SKILLS: list[tuple[str, str, str, str, list[str]]] = [
    (
        "user-experience-and-ui",
        "information-architecture",
        "Information Architecture",
        "Structuring and labeling content so users can find and understand it",
        ["ia design", "content architecture"],
    ),
    (
        "user-experience-and-ui",
        "design-thinking",
        "Design Thinking",
        "Human-centred, iterative approach to framing and solving problems",
        ["human centered design", "human-centred design"],
    ),
    (
        "talent-acquisition-and-people",
        "instructional-design",
        "Instructional Design",
        "Designing learning experiences and training materials from learning objectives",
        ["learning design", "learning experience design"],
    ),
    (
        "talent-acquisition-and-people",
        "curriculum-development",
        "Curriculum Development",
        "Planning course sequences, learning outcomes and teaching materials",
        ["curriculum design", "course design"],
    ),
    (
        "talent-acquisition-and-people",
        "assessment-design",
        "Assessment Design",
        "Designing tests, rubrics and evaluations that measure learning outcomes",
        ["learning assessment", "rubric design"],
    ),
    (
        "talent-acquisition-and-people",
        "lms-platforms",
        "Learning Management Systems (LMS)",
        "Administering and building courses in LMS platforms such as Canvas or Moodle",
        ["learning management systems", "lms administration"],
    ),
    (
        "talent-acquisition-and-people",
        "edtech-solutions",
        "Educational Technology (EdTech)",
        "Applying digital tools and platforms to teaching and learning",
        ["educational technology", "edtech"],
    ),
    (
        "sales-and-business-development",
        "sales-prospecting",
        "Sales Prospecting",
        "Identifying and qualifying potential customers to build a sales pipeline",
        ["lead prospecting", "lead generation outreach"],
    ),
    (
        "corporate-law-and-contracts",
        "ma-due-diligence",
        "M&A Due Diligence",
        "Legal and financial investigation of a target company before a merger or acquisition",
        ["mergers and acquisitions due diligence", "m&a diligence"],
    ),
    (
        "supply-chain-and-procurement",
        "operations-management",
        "Operations Management",
        "Planning and controlling business operations to deliver goods and services efficiently",
        ["business operations management"],
    ),
    (
        "supply-chain-and-procurement",
        "process-optimization",
        "Process Optimization",
        "Analysing and redesigning workflows to reduce cost, time and errors",
        ["process improvement", "business process improvement"],
    ),
    (
        "collaboration-and-stakeholder",
        "cross-functional-collaboration",
        "Cross-Functional Collaboration",
        "Working across teams and disciplines toward shared goals",
        ["cross functional teamwork", "cross-team collaboration"],
    ),
    (
        "product-strategy-and-execution",
        "key-performance-indicators",
        "Key Performance Indicators (KPIs)",
        "Defining and tracking quantitative measures of performance",
        ["kpi tracking", "kpi reporting"],
    ),
    (
        "product-strategy-and-execution",
        "objectives-and-key-results",
        "Objectives and Key Results (OKRs)",
        "Goal-setting framework that pairs objectives with measurable key results",
        ["okr planning"],
    ),
    (
        "product-strategy-and-execution",
        "go-to-market-strategy",
        "Go-to-Market Strategy",
        "Planning how a product reaches and wins its target customers",
        ["gtm strategy", "go to market planning"],
    ),
    (
        "product-strategy-and-execution",
        "research-and-development",
        "Research and Development (R&D)",
        "Systematic work to create new products, processes or knowledge",
        ["r&d management"],
    ),
    (
        "talent-acquisition-and-people",
        "talent-acquisition",
        "Talent Acquisition",
        "Sourcing, screening and hiring candidates",
        ["recruiting", "recruitment"],
    ),
    (
        "banking-systems-and-payments",
        "swift-network",
        "SWIFT Interbank Messaging",
        "Using the SWIFT network for international payments and settlement messages",
        ["swift payments", "swift messaging", "swift mt103"],
    ),
    (
        "industrial-automation-scada",
        "preventive-maintenance",
        "Preventive Maintenance",
        "Scheduled inspection and servicing of equipment to prevent failures",
        ["planned maintenance", "preventative maintenance"],
    ),
    (
        "industrial-automation-scada",
        "predictive-maintenance",
        "Predictive Maintenance",
        "Using sensor data and models to service equipment before it fails",
        ["condition based maintenance"],
    ),
    (
        "ci-cd-and-automation",
        "git-version-control",
        "Git",
        "Distributed version control system for tracking source code changes",
        ["git scm", "git version control"],
    ),
    (
        "backend-frameworks",
        "full-stack-development",
        "Full-Stack Development",
        "Building both the frontend and backend of web applications",
        ["full stack engineering"],
    ),
    (
        "application-security",
        "devsecops",
        "DevSecOps",
        "Integrating security practices into DevOps pipelines",
        ["secure devops"],
    ),
    (
        "api-technologies",
        "application-programming-interface",
        "Application Programming Interfaces (APIs)",
        "Designing and consuming interfaces between software components",
        ["api design", "api development"],
    ),
    (
        "api-technologies",
        "representational-state-transfer",
        "REST Architecture",
        "Architectural style for stateless resource-oriented web APIs",
        ["restful architecture"],
    ),
    (
        "ci-cd-and-automation",
        "behavior-driven-development",
        "Behavior-Driven Development (BDD)",
        "Specifying software behaviour through shared, executable examples",
        ["behaviour driven development"],
    ),
    (
        "cloud-platforms",
        "infrastructure-as-a-service",
        "Infrastructure as a Service (IaaS)",
        "Cloud model that provides virtualised compute, storage and networking",
        ["iaas cloud"],
    ),
    (
        "cloud-platforms",
        "platform-as-a-service",
        "Platform as a Service (PaaS)",
        "Cloud model that provides a managed application runtime platform",
        ["paas cloud"],
    ),
    (
        "cloud-platforms",
        "software-as-a-service",
        "Software as a Service (SaaS)",
        "Cloud model that delivers applications over the internet on subscription",
        ["saas applications"],
    ),
    (
        "communication-and-presentation",
        "executive-communication",
        "Executive Communication",
        "Briefing and aligning C-level stakeholders",
        ["c-level communication", "executive stakeholder alignment"],
    ),
    (
        "privacy-and-data-governance",
        "workplace-compliance",
        "Workplace Compliance",
        "Applying labour regulations such as working-time and rest-period rules",
        ["labor law compliance", "employment law compliance"],
    ),
]


def merge_curated_tech_yaml(
    skills_records: list[dict[str, Any]], add_skill: Callable[..., None]
) -> None:
    """Merge data/taxonomy/curated_tech.yaml into the tree (new nodes added, aliases merged)."""
    path = DATA_DIR / "curated_tech.yaml"
    if not path.exists():
        return
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    by_slug = {r["slug"]: r for r in skills_records}
    for domain in data.get("domains", []):
        d_slug, d_type = domain["slug"], domain.get("type", "technical")
        for cat in domain.get("categories", []):
            add_skill(cat["slug"], cat["name"], d_type, 1, d_slug, f"{cat['name']} category")
            for sub in cat.get("subcategories", []):
                add_skill(sub["slug"], sub["name"], d_type, 2, cat["slug"], f"{sub['name']}")
                for sk in sub.get("skills", []):
                    aliases = [(str(a), "curated") for a in sk.get("aliases", [])]
                    existing = by_slug.get(sk["slug"])
                    if existing is not None:
                        existing["aliases"].extend(aliases)
                        continue
                    add_skill(
                        sk["slug"],
                        sk["name"],
                        d_type,
                        3,
                        sub["slug"],
                        sk.get("description") or sk["name"],
                        [(sk["name"].lower(), "curated"), *aliases],
                    )
        by_slug = {r["slug"]: r for r in skills_records}


def load_rule_referenced_slugs() -> set[str]:
    """Slugs that implications.yaml / relations.yaml reference (they must exist in the tree)."""
    referenced: set[str] = set()
    implications_path = DATA_DIR / "implications.yaml"
    relations_path = DATA_DIR / "relations.yaml"
    if implications_path.exists():
        with open(implications_path, encoding="utf-8") as f:
            for imp in (yaml.safe_load(f) or {}).get("implications", []):
                referenced.add(imp.get("consequent_slug", ""))
                referenced.update(imp.get("antecedent_slugs", []))
    if relations_path.exists():
        with open(relations_path, encoding="utf-8") as f:
            for rel in (yaml.safe_load(f) or {}).get("relations", []):
                referenced.add(rel.get("skill_slug", ""))
                referenced.add(rel.get("related_slug", ""))
    referenced.discard("")
    return referenced


# Vendor prefixes stripped from O*NET product names to derive short aliases
# ("Autodesk AutoCAD" -> "autocad"). Multi-word prefixes are matched first.
VENDOR_PREFIXES = sorted(
    {
        "abb",
        "accelrys",
        "adobe",
        "adp",
        "allscripts",
        "alteryx",
        "amazon",
        "amazon web services",
        "apache",
        "apple",
        "atlassian",
        "autodesk",
        "avid",
        "avid technology",
        "bentley",
        "cadence",
        "cerner",
        "cisco",
        "cisco systems",
        "corel",
        "dassault systemes",
        "elite software",
        "emc",
        "esri",
        "experian",
        "fanuc",
        "fanuc robotics",
        "ge",
        "ge healthcare",
        "google",
        "hashicorp",
        "henry schein",
        "hewlett packard",
        "hewlett packard hp",
        "hp",
        "ibm",
        "infor",
        "intergraph",
        "intuit",
        "lexisnexis",
        "mckesson",
        "meditech",
        "mentor graphics",
        "microsoft",
        "mozilla",
        "national instruments",
        "oracle",
        "proquest",
        "ptc",
        "red hat",
        "rockware",
        "sage",
        "scientific software",
        "sun microsystems",
        "sungard",
        "symantec",
        "synopsys",
        "teradata",
        "thomson reuters",
        "vero software",
        "salesforce",
        "sap",
        "siemens",
        "the mathworks",
        "trimble",
        "vmware",
    },
    key=len,
    reverse=True,
)
VENDOR_SHORT_FORMS = {"microsoft": "ms"}  # "Microsoft Excel" -> "ms excel"
COMPANY_CONTINUATIONS = {
    "associates",
    "corp",
    "corporation",
    "energy",
    "group",
    "healthcare",
    "hearing",
    "inc",
    "intelligent",
    "international",
    "labs",
    "solutions",
    "systems",
    "technologies",
    "technology",
}
# Normalized derived aliases that are plain words; filled while building, read by _is_ambiguous.
AMBIGUOUS_DERIVED: set[str] = set()


def dedupe_key(text: str) -> str:
    """Loose identity key: normalized text with simple plural 's' stripped per token."""
    tokens = normalize_alias_text(text).split()
    return " ".join(t[:-1] if len(t) > 3 and t.endswith("s") else t for t in tokens)


def onet_surface_forms(name: str) -> list[tuple[str, str]]:
    """Real surface forms of an O*NET product name, as (alias, source) pairs."""
    forms: list[tuple[str, str]] = [(name, "onet")]
    tokens = name.split()
    # Trailing acronym that spells the preceding words: "Structured query language SQL".
    if len(tokens) >= 3 and tokens[-1].isupper() and 2 <= len(tokens[-1]) <= 6:
        initials = "".join(t[0] for t in tokens[:-1] if t[:1].isalpha()).upper()
        if initials.endswith(tokens[-1]):
            forms.append((" ".join(tokens[:-1]), "variant"))
            forms.append((tokens[-1], "variant"))
    norm = normalize_alias_text(name)
    if norm.endswith(" software") and len(norm.split()) > 2:
        forms.append((norm.removesuffix(" software"), "variant"))
    for vendor in VENDOR_PREFIXES:
        if not norm.startswith(vendor + " "):
            continue
        rest = norm[len(vendor) + 1 :]
        first = rest.split()[0]
        # "Scientific Software Group MT3D99", "Bentley Systems AutoPIPE", "Sage 50 Accounting":
        # the vendor name continues (or the product is a number), so stripping would leave a
        # fragment rather than a name.
        if first in COMPANY_CONTINUATIONS or first[0].isdigit() or rest == "software":
            break
        forms.append((rest, "variant"))
        if vendor in VENDOR_SHORT_FORMS:
            forms.append((f"{VENDOR_SHORT_FORMS[vendor]} {rest}", "variant"))
        if " " not in rest:
            original = name.split()[-1]
            # A single plain word ("Clinical", "Frontier") is too generic to stand alone;
            # coined names with inner capitals or digits ("AutoCAD", "MicroHedge") are not.
            if not any(c.isupper() or c.isdigit() for c in original[1:]):
                AMBIGUOUS_DERIVED.add(rest)
        break
    return forms


def _read_onet_csv(name: str) -> list[dict[str, str]]:
    path = ONET_DIR / name
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {path}. Run `uv run python data/taxonomy/raw/download.py` first."
        )
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def add_onet_layer(
    skills_records: list[dict[str, Any]],
    add_skill: Callable[..., None],
    seen_slugs: set[str],
    referenced_slugs: set[str],
) -> None:
    """Add O*NET software skills, knowledge areas and foundational/transferable skills.

    Products already present in the curated tree become aliases of the curated skill instead
    of new nodes. A product whose short form matches a rule-referenced slug ("autocad") takes
    that slug so implications/relations resolve to it.
    """
    model = {r["Element ID"]: r for r in _read_onet_csv("content_model_reference.csv")}
    software = _read_onet_csv("software_skills.csv")

    by_slug = {r["slug"]: r for r in skills_records}
    index: dict[str, str] = {}
    for rec in skills_records:
        if rec["level"] < 3:
            continue
        index.setdefault(dedupe_key(rec["name"]), rec["slug"])
        for alias, _source in rec["aliases"]:
            if normalize_alias_text(alias) not in AMBIGUOUS_ALIASES:
                index.setdefault(dedupe_key(alias), rec["slug"])

    def unique_slug(base: str) -> str:
        slug, n = base, 2
        while slug in seen_slugs:
            slug, n = f"{base}-{n}", n + 1
        return slug

    # --- Software skills: 2.E.<group>.<element> -> example products -----------------------
    occupations: dict[str, set[str]] = defaultdict(set)
    element_votes: dict[str, Counter[str]] = defaultdict(Counter)
    hot: set[str] = set()
    for row in software:
        example = html.unescape(row["Workplace Example"]).strip()
        if not example:
            continue
        occupations[example].add(row["Title"])
        element_votes[example][row["Element ID"]] += 1
        if row["Hot Technology"] == "Y":
            hot.add(example)

    element_slugs: dict[str, str] = {}
    for element_id in sorted({e for votes in element_votes.values() for e in votes}):
        group_id = element_id.rsplit(".", 1)[0]
        group, element = model[group_id], model[element_id]
        group_slug = slugify(group["Element Name"])
        if group_slug in by_slug and by_slug[group_slug]["level"] != 1:
            group_slug = f"{group_slug}-group"
        if group_slug not in by_slug:
            add_skill(
                group_slug,
                group["Element Name"],
                "technical",
                1,
                "technical-skills",
                group["Description"] or f"{group['Element Name']} (O*NET {group_id})",
                [],
            )
            by_slug[group_slug] = skills_records[-1]
        elem_slug = slugify(element["Element Name"])
        if elem_slug in seen_slugs and by_slug[elem_slug]["level"] != 2:
            elem_slug = unique_slug(f"{elem_slug}-category")
        if elem_slug not in by_slug:
            add_skill(
                elem_slug,
                element["Element Name"],
                "technical",
                2,
                group_slug,
                element["Description"] or f"{element['Element Name']} (O*NET {element_id})",
                [],
            )
            by_slug[elem_slug] = skills_records[-1]
        element_slugs[element_id] = elem_slug

    for example in sorted(element_votes):
        forms = onet_surface_forms(example)
        # Short or all-caps forms ("OMS") collide across unrelated products: never dedupe on them.
        keys = [dedupe_key(f) for f, _ in forms if len(f) >= 5 and not f.isupper()]
        match = next((index[k] for k in keys if k in index), None)
        if match is not None:
            by_slug[match]["aliases"].extend(forms)
            continue
        # Most frequent element wins; ties go to the lowest element ID (deterministic).
        element_id = min(element_votes[example].items(), key=lambda kv: (-kv[1], kv[0]))[0]
        parent = element_slugs[element_id]
        slug = next(
            (
                slugify(form)
                for form, _ in forms
                if slugify(form) in referenced_slugs and slugify(form) not in seen_slugs
            ),
            None,
        ) or unique_slug(slugify(example))
        titles = sorted(occupations[example])
        n_occ = len(titles)
        desc = (
            f"{model[element_id]['Element Name']}. Listed by O*NET for {n_occ} occupation"
            f"{'s' if n_occ != 1 else ''}, e.g. {', '.join(titles[:2])}."
            + (" O*NET hot technology." if example in hot else "")
        )
        add_skill(slug, example, "technical", 3, parent, desc, forms)
        skills_records[-1]["name_source"] = "onet"
        by_slug[slug] = skills_records[-1]
        for k in keys:
            index.setdefault(k, slug)

    # --- Knowledge areas (2.C) and foundational/transferable skills (2.A, 2.B) ------------
    def children(element_id: str) -> list[str]:
        depth = element_id.count(".") + 1
        kids = [k for k in model if k.startswith(element_id + ".") and k.count(".") == depth]
        return sorted(kids, key=_element_sort_key)

    def add_content_model_tree(
        group_ids: list[str],
        domain: str,
        d_type: str,
        cat_slug: str,
        cat_name: str,
        group_suffix: str,
        item_suffix: str,
    ) -> None:
        add_skill(cat_slug, cat_name, d_type, 1, domain, f"{cat_name} from the O*NET content model")
        for gid in group_ids:
            g = model[gid]
            g_slug = unique_slug(slugify(g["Element Name"]) + group_suffix)
            add_skill(g_slug, g["Element Name"], d_type, 2, cat_slug, g["Description"])
            # A group without children (e.g. 2.C.6) becomes its own single skill.
            items = children(gid) or [gid]
            for iid in items:
                item = model[iid]
                key = dedupe_key(item["Element Name"])
                if key in index and not item_suffix:
                    by_slug[index[key]]["aliases"].append((item["Element Name"], "onet"))
                    continue
                i_slug = unique_slug(slugify(item["Element Name"]) + item_suffix)
                add_skill(
                    i_slug,
                    item["Element Name"],
                    d_type,
                    3,
                    g_slug,
                    item["Description"],
                    [(item["Element Name"], "onet")],
                )
                skills_records[-1]["name_source"] = "onet"
                by_slug[i_slug] = skills_records[-1]
                index.setdefault(key, i_slug)

    add_content_model_tree(
        children("2.C"),
        "domain-knowledge",
        "domain",
        "knowledge-areas",
        "Knowledge Areas",
        "-knowledge-group",
        "-knowledge",
    )
    add_content_model_tree(
        children("2.A"),
        "soft-skills",
        "soft",
        "essential-skills",
        "Essential Skills",
        "-skills",
        "",
    )
    add_content_model_tree(
        [g for g in children("2.B") if g != "2.B.3"],
        "soft-skills",
        "soft",
        "transferable-skills",
        "Transferable Skills",
        "-skills",
        "",
    )
    add_content_model_tree(
        ["2.B.3"],
        "technical-skills",
        "technical",
        "equipment-and-systems-skills",
        "Equipment & Systems Skills",
        "-group",
        "",
    )


def _element_sort_key(element_id: str) -> tuple[Any, ...]:
    return tuple(int(p) if p.isdigit() else p for p in element_id.split("."))


SLUG_NAME_TOKENS = {
    "ab": "A/B",
    "ai": "AI",
    "api": "API",
    "aws": "AWS",
    "cd": "CD",
    "ci": "CI",
    "css": "CSS",
    "gcp": "GCP",
    "gpu": "GPU",
    "iam": "IAM",
    "iot": "IoT",
    "iso": "ISO",
    "js": "JS",
    "kyc": "KYC",
    "aml": "AML",
    "llm": "LLM",
    "ml": "ML",
    "ocr": "OCR",
    "orm": "ORM",
    "owasp": "OWASP",
    "pwa": "PWA",
    "qa": "QA",
    "rag": "RAG",
    "rpc": "RPC",
    "sql": "SQL",
    "svg": "SVG",
    "ui": "UI",
    "ux": "UX",
    "vba": "VBA",
}


def slug_to_name(slug: str) -> str:
    """Readable display name for a slug that only appears in the rule files."""
    words = [SLUG_NAME_TOKENS.get(w, w.capitalize()) for w in slug.split("-")]
    name = " ".join(words)
    return name.replace(" JS", ".js") if name.endswith(" JS") else name


def register_rule_referenced_slugs(
    skills_records: list[dict[str, Any]],
    add_skill: Callable[..., None],
    seen_slugs: set[str],
    referenced_slugs: set[str],
) -> None:
    """Create any skill that implications.yaml/relations.yaml reference but nothing else defines.

    Parents are inferred from keywords in the slug; this keeps the rule files resolvable.
    """
    for ref_slug in sorted(referenced_slugs - seen_slugs):
        subcat, d_type = _infer_subcategory(ref_slug)
        name = slug_to_name(ref_slug)
        add_skill(
            ref_slug,
            name,
            d_type,
            3,
            subcat,
            f"{name} (referenced by the skill implication and relation rules).",
            [name.lower(), ref_slug.replace("-", " ")],
        )


def _infer_subcategory(ref_slug: str) -> tuple[str, str]:
    keyword_map: list[tuple[tuple[str, ...], str, str]] = [
        (("llm", "gen", "gpt", "rag", "prompt"), "generative-ai-and-llms", "technical"),
        (
            ("ai", "learn", "train", "vision", "nlp", "model", "neural", "torch", "tensor"),
            "machine-learning-frameworks",
            "technical",
        ),
        (
            ("data", "spark", "sql", "warehouse", "stream", "pipeline", "kafka"),
            "data-engineering-and-analytics",
            "technical",
        ),
        (("cloud", "aws", "gcp", "azure", "serverless", "vpc"), "cloud-platforms", "technical"),
        (
            ("docker", "kube", "k8s", "container", "helm", "mesh"),
            "container-and-orchestration",
            "technical",
        ),
        (
            ("ci", "cd", "test", "deploy", "action", "git", "build", "automation"),
            "ci-cd-and-automation",
            "technical",
        ),
        (
            ("db", "database", "postgres", "mongo", "redis", "elastic", "vector"),
            "relational-databases",
            "technical",
        ),
        (
            ("react", "vue", "angular", "css", "html", "web", "front", "ui", "ux", "js"),
            "frontend-frameworks",
            "technical",
        ),
        (
            ("security", "auth", "oauth", "jwt", "crypto", "hack", "penetration", "owasp"),
            "application-security",
            "technical",
        ),
        (
            ("finance", "account", "dcf", "valuation", "tax", "banking", "risk", "trading"),
            "corporate-finance-and-valuation",
            "business",
        ),
        (
            ("lead", "manage", "communicat", "think", "team", "present", "negotiat", "conflict"),
            "leadership-and-people-development",
            "soft",
        ),
        (
            ("health", "ehr", "clinical", "bio", "patient", "medical", "genom", "fda"),
            "clinical-systems-and-ehr",
            "domain",
        ),
    ]
    for keywords, subcat, d_type in keyword_map:
        if any(k in ref_slug for k in keywords):
            return subcat, d_type
    return "backend-frameworks", "technical"


# -------------------------------------------------------------------------------------------------
# Aliases
# -------------------------------------------------------------------------------------------------


GENERIC_PLURALS = {
    "algorithms": "algorithm",
    "applications": "application",
    "databases": "database",
    "frameworks": "framework",
    "languages": "language",
    "libraries": "library",
    "methods": "method",
    "models": "model",
    "networks": "network",
    "platforms": "platform",
    "programs": "program",
    "protocols": "protocol",
    "services": "service",
    "systems": "system",
    "techniques": "technique",
    "tools": "tool",
}


def _is_ambiguous(norm: str) -> bool:
    return norm in AMBIGUOUS_ALIASES or norm in AMBIGUOUS_DERIVED or len(norm) <= 2


def build_alias_records(skills_records: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Every real surface form of every skill, deduplicated on the normalized form.

    Sources: curated (hand-written), onet (O*NET product names), variant (derived punctuation,
    spacing, vendor-prefix and acronym forms). The first claim on a normalized form wins, with
    aliases_curated.yaml taking priority; level 0-2 nodes do not get derived variants.
    """
    alias_records: list[dict[str, str]] = []
    seen: set[str] = set()
    valid_slugs = {r["slug"] for r in skills_records}

    def add(slug: str, alias: str, source: str, ambiguous: bool | None = None) -> None:
        norm = normalize_alias_text(alias)
        if not norm or norm in seen:
            return
        if ambiguous is None and source != "curated" and alias.isupper() and len(norm) <= 3:
            ambiguous = True  # derived TLAs ("RMS") are heavily overloaded
        alias_records.append(
            {
                "slug": slug,
                "alias": alias,
                "alias_normalized": norm,
                "ambiguous": str(_is_ambiguous(norm) if ambiguous is None else ambiguous).lower(),
                "source": source,
            }
        )
        seen.add(norm)

    curated_path = DATA_DIR / "aliases_curated.yaml"
    if curated_path.exists():
        data = yaml.safe_load(curated_path.read_text(encoding="utf-8")) or {}
        for ca in data.get("aliases", []):
            if ca["slug"] not in valid_slugs:
                raise ValueError(f"aliases_curated.yaml: unknown slug {ca['slug']!r}")
            norm = normalize_alias_text(ca["alias"])
            add(
                ca["slug"],
                ca["alias"],
                ca.get("source", "curated"),
                bool(ca.get("ambiguous", False)) or norm in AMBIGUOUS_ALIASES,
            )

    # Wikidata alt-labels (CC0), snapshotted by scripts/fetch_wikidata_aliases.py.
    wikidata: dict[str, list[str]] = defaultdict(list)
    wikidata_path = DATA_DIR / "wikidata_aliases.csv"
    if wikidata_path.exists():
        with open(wikidata_path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row["slug"] in valid_slugs:
                    wikidata[row["slug"]].append(row["alias"])

    for skill in skills_records:
        slug, name = skill["slug"], skill["name"]
        add(slug, name, skill.get("name_source", "curated"))
        for alias, source in skill["aliases"]:
            add(slug, alias, source)
        for alias in wikidata.get(slug, []):
            add(slug, alias, "wikidata")
        if skill["level"] < 3:
            continue
        add(slug, slug.replace("-", " "), "variant")
        # Punctuation variants: "React.js" -> "reactjs", "ASP.NET Core" -> "aspnet core"
        # ("react js" already comes from normalization).
        if re.search(r"\w[.\-]\w", name):
            add(slug, " ".join(re.sub(r"[.\-]", "", w) for w in name.lower().split()), "variant")
        if name.lower().endswith(".js"):
            base = name[:-3]
            add(slug, f"{base}js", "variant")
            add(slug, f"{base} js", "variant")
        # "and" / "&" spellings: "Research and Development" <-> "Research & Development".
        if " and " in name:
            add(slug, name.replace(" and ", " & "), "variant")
        elif "&" in name:
            add(slug, re.sub(r"\s*&\s*", " and ", name), "variant")
        # Singular of a generic plural head noun: "Graph Databases" -> "graph database".
        words = name.split()
        if len(words) >= 2 and words[-1].lower() in GENERIC_PLURALS:
            add(slug, " ".join([*words[:-1], GENERIC_PLURALS[words[-1].lower()]]), "variant")
        # Parenthesised acronym: "Key Performance Indicators (KPIs)" -> "kpis", "kpi".
        m = re.search(r"\(([A-Za-z0-9&/+.#-]{2,10})\)\s*$", name)
        if m:
            add(slug, name[: m.start()].strip(), "variant")
            acronym = m.group(1)
            add(slug, acronym, "variant")
            if acronym.endswith("s") and acronym[:-1].isupper() and len(acronym) > 2:
                add(slug, acronym[:-1], "variant")

    return alias_records


def build_taxonomy_files() -> None:
    """Build skills.csv and aliases.csv."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    skills_records = generate_rich_domain_skills()
    logger.info("Total taxonomy skills generated: %d", len(skills_records))
    alias_records = build_alias_records(skills_records)

    skills_csv_path = DATA_DIR / "skills.csv"
    with open(skills_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["slug", "name", "type", "level", "parent_slug", "description"]
        )
        writer.writeheader()
        for s in skills_records:
            writer.writerow({k: s[k] for k in writer.fieldnames})

    aliases_csv_path = DATA_DIR / "aliases.csv"
    with open(aliases_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["slug", "alias", "alias_normalized", "ambiguous", "source"]
        )
        writer.writeheader()
        writer.writerows(alias_records)

    logger.info("Successfully written %s (%d skills)", skills_csv_path, len(skills_records))
    logger.info("Successfully written %s (%d aliases)", aliases_csv_path, len(alias_records))
    logger.info("Alias sources: %s", dict(Counter(a["source"] for a in alias_records)))


def main() -> None:
    parser = argparse.ArgumentParser(description="Build 4-level skill taxonomy and alias mappings")
    parser.parse_args()
    build_taxonomy_files()


if __name__ == "__main__":
    main()
