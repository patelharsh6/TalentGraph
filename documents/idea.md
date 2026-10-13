Multi-Agent AI System for Intelligent Resume Parsing, Skill-Set Matching, and
API-Ready Talent Intelligence
Description:
Recruitment and talent acquisition teams process thousands of resumes daily across diverse formats
(PDF, DOCX, LinkedIn exports, plain text), each with inconsistent layouts, terminology, and skill
representations. A candidate might list 'React.js' while a job description requires 'ReactJS' or 'React';
one resume uses 'ML Engineering' while the skill database categorizes it as 'Machine Learning
Engineering.' Current ATS (Applicant Tracking Systems) rely on rigid keyword matching that misses
qualified candidates and surfaces irrelevant ones, leading to poor hiring outcomes and wasted
recruiter time.
Your challenge is to build a Multi-Agent AI system that intelligently parses resumes from multiple
formats, extracts and normalizes skills against a structured skill-set taxonomy, performs semantic
matching against job descriptions and role requirements, and exposes the entire pipeline through welldocumented REST APIs for seamless third-party integration by HR platforms, job boards, and
enterprise systems.
Challenge Requirements:
1. Multi-Format Resume Parsing Agent: Build a specialized parsing agent that extracts
structured information from resumes in PDF, DOCX, and plain text formats. The agent must handle
diverse resume layouts (single-column, multi-column, creative designs, tabular formats) and
extract: personal information (name, contact, location), work experience (company, role, duration,
responsibilities), education (institution, degree, field, year), skills (technical and soft), certifications,
projects, and publications. Use a combination of layout analysis (for PDFs), NLP-based section
detection, and LLM-powered extraction to handle edge cases and ambiguous formatting.
2. Skill Taxonomy and Normalization Agent: Build a skill normalization agent that maintains a
hierarchical skill-set database (e.g., 'Python' -> 'Programming Languages' -> 'Technical Skills')
and maps extracted resume skills to canonical entries. The agent must handle: synonyms and
abbreviations ('JS' = 'JavaScript', 'K8s' = 'Kubernetes'), skill hierarchy inference (someone with
'TensorFlow' and 'PyTorch' experience implies 'Deep Learning' proficiency), proficiency level
estimation based on context (5 years of Python experience vs. 'familiar with Python'), and
emerging skill detection (flagging skills not yet in the taxonomy for human review and addition).
3. Semantic Skill-to-Job Matching Agent: Build a matching agent that goes beyond keyword
matching to perform semantic similarity between candidate skill profiles and job requirements.
Implement: vector embedding-based skill matching (using sentence transformers or domainspecific embeddings), weighted scoring that considers skill importance (required vs. nice-to-have),
experience depth weighting (years of experience, project complexity), gap analysis that identifies
missing skills and suggests upskilling paths, and a configurable matching threshold that balances
precision vs. recall based on hiring manager preferences.
4. Multi-Agent Orchestration Layer: Design and implement an orchestration framework where
the parsing, normalization, and matching agents collaborate through a shared message protocol.
The orchestrator should: manage agent lifecycle and task delegation, handle concurrent resume
processing (batch mode for bulk uploads), implement retry logic and graceful degradation (if one
agent fails, partial results are still returned), and provide observability with per-agent execution
traces, latency metrics, and quality scores. Use a framework such as LangGraph, CrewAI,
AutoGen, or a custom orchestrator.
5. API Layer for Third-Party Consumption: Expose the entire pipeline through a productiongrade REST API (OpenAPI/Swagger documented) with endpoints for: single resume parsing
(POST /api/v1/parse with file upload), batch resume processing (POST /api/v1/parse/batch with
async job tracking), skill profile retrieval (GET /api/v1/candidates/{id}/skills), job matching (POST
/api/v1/match with candidate ID and job description), skill taxonomy browsing and search (GET
/api/v1/skills/taxonomy), and webhook callbacks for async processing completion. Implement API
key authentication, rate limiting, request validation, and comprehensive error responses. Provide
SDKs or code examples in Python and JavaScript for easy integration.
Suggested Datasets:
A synthetic resume dataset (500+ resumes across 10+ industries in PDF and DOCX formats with
varying layouts), a structured skill taxonomy database (5,000+ skills organized hierarchically
across technology, business, and domain categories), sample job descriptions (100+ across
engineering, data science, product management, and design roles), and a ground-truth matching
dataset for evaluation (expert-labeled candidate-job compatibility scores).
Technology Requirements:
Python (LangChain/LangGraph or CrewAI for multi-agent orchestration, sentence-transformers for
embeddings, pdfplumber/PyMuPDF for PDF parsing, python-docx for DOCX parsing), a vector
database (ChromaDB, Pinecone, or Weaviate) for skill embeddings, PostgreSQL for structured
data, FastAPI for the API layer with OpenAPI documentation, Redis for job queuing and caching,
and Docker/Docker Compose for deployment.
Evaluation Criteria:
Resume parsing accuracy (field-level F1-score on ground-truth labeled resumes), skill
normalization precision (correct canonical mapping rate), matching quality (NDCG and correlation
with expert rankings), API completeness (endpoint coverage, documentation quality, error
handling), multi-agent orchestration reliability (success rate under concurrent load), and end-toend latency (single resume processing time < 10 seconds).
Domain:
Multi-Agent AI & Talent Intelligence