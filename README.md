# Automated Peer Review System — Research Analysis & Discovery Graph

An AI-powered research paper analysis system that automates academic review, evaluates research claims, verifies citations, and explores relationships between findings using knowledge graphs.

## Overview

Research papers contain valuable claims, evidence, and insights, but discovering connections across multiple papers can be challenging. This project combines multi-agent AI workflows and graph-based knowledge representation to support systematic research analysis.

The system analyses research papers, evaluates their claims, checks citations and formatting, and generates structured review reports. Its discovery-oriented approach focuses on connecting related claims across papers to identify potential research directions, supporting evidence, and possible contradictions.

## Key Features

- **Automated Peer Review:** Evaluates research papers using specialized AI review components.
- **Research Claim Analysis:** Extracts and analyses claims to understand their context and relevance.
- **Citation Verification:** Cross-checks references using scholarly sources such as arXiv and Google Scholar, where configured.
- **Formatting Compliance:** Checks research paper formatting against configured academic standards.
- **Multi-Agent Workflow:** Uses LangGraph to coordinate separate review components.
- **Parallel Processing:** Executes independent review tasks concurrently to improve processing efficiency.
- **Knowledge Graph Exploration:** Uses Neo4j to represent research papers, claims, concepts, and their relationships, where configured.
- **Potential Discovery Identification:** Helps explore connections, conflicting claims, research gaps, and hypotheses that may deserve further investigation.
- **Structured Reports:** Combines analysis results into an organised review report with scores and findings.

## How It Works

1. **Paper Ingestion:** A research paper is submitted for analysis.
2. **Claim and Content Analysis:** The system processes the paper and identifies relevant claims.
3. **Citation Verification:** References are checked against available scholarly metadata.
4. **Academic Review:** The paper is evaluated for research quality and supporting evidence.
5. **Formatting Validation:** The system checks formatting compliance.
6. **Parallel Execution:** Independent review components can run concurrently.
7. **Result Aggregation:** Outputs from the review components are combined.
8. **Graph-Based Exploration:** Related claims and concepts can be connected in a Neo4j knowledge graph.
9. **Report Generation:** The system produces a structured summary of review findings.

## Research Discovery Through Knowledge Graphs

The goal of graph-based analysis is to move beyond reviewing papers individually and help researchers explore relationships across the literature.

A conceptual graph may represent:

- **Paper nodes:** Research papers and their metadata.
- **Claim nodes:** Findings, hypotheses, and statements extracted from papers.
- **Concept nodes:** Topics, methods, and scientific concepts.
- **Evidence relationships:** Links between claims and their supporting sources.
- **Cross-paper relationships:** Connections between similar, supporting, or potentially conflicting claims.

By exploring paths through connected claims, researchers can investigate:

- Whether different papers support similar conclusions.
- Which findings appear to conflict or require further verification.
- How ideas and methods connect across research areas.
- Which relationships may suggest new research questions or experiments.

These connections are intended to support further investigation. A graph relationship alone does not establish scientific validity or prove that a discovery is novel.

## Technology Stack

- **Language:** Python
- **AI Workflow Orchestration:** LangGraph, LangChain
- **Backend:** FastAPI
- **LLM:** Groq API
- **Research Sources:** arXiv API, Google Scholar integration where configured
- **Knowledge Graph:** Neo4j
- **Semantic Retrieval:** Vector database, depending on configuration
- **Frontend:** HTML, CSS, JavaScript

## Project Structure

```text
automated peer review/
├── backend/
│   ├── main.py
│   ├── graph.py
│   ├── requirements.txt
│   ├── README.MD
│   └── nodes/
│       ├── ingestion.py
│       ├── reviewer.py
│       ├── fact_checker.py
│       ├── scoring.py
│       ├── aggregator.py
│       ├── formatter.py
│       └── report.py
├── frontend/
│   └── index.html
├── docs/
│   └── images/
└── .gitignore
```

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/anuragthakur107/research_paper_analysis-automated_peer_review-.git
cd research_paper_analysis-automated_peer_review-
```

### 2. Create a Virtual Environment

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```powershell
pip install -r backend/requirements.txt
```

### 4. Configure Environment Variables

Create a `backend/.env` file containing the API credentials and configuration required by the application.

Never commit API keys, passwords, or private credentials to GitHub.

### 5. Start the Backend

From the project root, try:

```powershell
uvicorn main:app --app-dir backend --reload
```

If your FastAPI application uses a different entry point or startup command, follow the instructions in `backend/README.MD`.

### 6. Open the Frontend

Open `frontend/index.html` in your browser. If the frontend communicates with the backend, ensure its API URL and the backend CORS settings are configured correctly.

## Screenshots

Add screenshots to `docs/images/` to demonstrate the application's interface.

Suggested screenshots:

- `dashboard.png` — Main application interface
- `claim-analysis.png` — Research claim analysis
- `knowledge-graph.png` — Graph of papers, claims, and relationships
- `review-report.png` — Generated review report

Once the images are added, embed them using Markdown:

```markdown
![Application Dashboard](docs/images/dashboard.png)

![Research Knowledge Graph](docs/images/knowledge-graph.png)
```

## Responsible Use

- Verify important findings against original research papers.
- Treat AI-generated claims and relationships as suggestions that require validation.
- Preserve source references so claims can be traced back to the literature.
- Do not describe a finding as a novel scientific discovery without checking relevant prior work.
- Keep API keys, private documents, and confidential research data out of the public repository.

##