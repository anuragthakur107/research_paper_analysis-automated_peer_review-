# 🔬 Automated Peer Review System

An AI-powered academic paper review pipeline built with **LangGraph**, **Groq LLM**, and **FastAPI**. Upload an IEEE-formatted research paper (PDF) and receive a structured, scored review report in seconds — covering citation verification, formatting compliance, and academic quality.

---

## 📁 Project Structure

```
automatedpeerreviewzipfile/
├── backend/
│   ├── main.py              # FastAPI server & job management
│   ├── graph.py             # LangGraph pipeline definition
│   ├── nodes/
│   │   ├── ingestion.py     # Node: PDF parsing & metadata extraction
│   │   ├── fact_checker.py  # Node A: Citation verification (ArXiv + Scholar)
│   │   ├── formatter.py     # Node B: IEEE formatting compliance check
│   │   ├── reviewer.py      # Node C: Academic quality review
│   │   ├── aggregator.py    # Node: Score aggregation
│   │   ├── scoring.py       # Node: PASS/FAIL decision
│   │   └── report.py        # Node: Final report assembly
│   ├── cache/               # JSON cache for processed papers
│   ├── uploads/             # Temporary PDF upload storage
│   ├── requirements.txt
│   └── .env
└── frontend/
    └── index.html           # Single-page frontend UI
```

---

## 🧠 LangGraph Pipeline

The system is built as a **directed acyclic graph (DAG)** using LangGraph's `StateGraph`. All nodes share a single typed state object (`PaperState`) that is mutated and passed forward as the graph executes.

### Graph Flow

```
ingestion
    ↓
parallel_review  ←── runs Node A, B, C concurrently (ThreadPoolExecutor)
    ↓
aggregator
    ↓
scoring
    ↓
report
    ↓
END
```

### Why ThreadPoolExecutor Instead of Native LangGraph Fan-Out?

LangGraph 0.2.x's native fan-in (multiple edges converging on one node) requires `Annotated` reducer types on state fields and is fragile across minor versions. Using `ThreadPoolExecutor` inside a single `parallel_review` node is simpler, equally fast (all three sub-nodes are I/O-bound LLM calls), and significantly more stable.

---

## 🗂️ State Schema (`PaperState`)

Defined as a `TypedDict` in `graph.py`, the shared state carries all data through the pipeline:

| Field | Type | Set By | Description |
|---|---|---|---|
| `pdf_path` | `str` | API | Path to the uploaded PDF |
| `full_text` | `str` | Ingestion | Full paper as markdown text |
| `title` | `str` | Ingestion | Extracted paper title |
| `abstract` | `str` | Ingestion | Extracted abstract |
| `references` | `list` | Ingestion | Parsed reference list |
| `section_headings` | `list` | Ingestion | Extracted section headings |
| `page_count` | `int` | Ingestion | Total page count |
| `fact_check_results` | `dict` | Node A | Citation verification results & score (0–30) |
| `format_results` | `dict` | Node B | IEEE formatting issues & score (0–30) |
| `review_results` | `dict` | Node C | Academic review feedback & score (0–40) |
| `scores` | `dict` | Aggregator | Combined score breakdown |
| `decision` | `str` | Scoring | `"PASS"` or `"FAIL"` |
| `total_score` | `int` | Scoring | Final score out of 100 |
| `margin` | `int` | Scoring | Points above/below the 70-point threshold |
| `final_report` | `dict` | Report | Complete structured report for the frontend |

---

## 🔵 Node Details

### 1. `ingestion` — PDF Parser
**File:** `nodes/ingestion.py`  
**Entry point of the graph.**

- Converts the PDF to clean markdown using **pymupdf4llm**
- Sends the full markdown to **Groq (llama-3.3-70b-versatile)** in a single LLM call
- Extracts: title, abstract, section headings, page count, and full reference list
- Implements a **JSON file cache** (keyed by PDF filename stem in `cache/`) to skip LLM calls for previously processed papers

**Output added to state:** `full_text`, `title`, `abstract`, `references`, `section_headings`, `page_count`

---

### 2. `parallel_review` — Concurrent Fan-Out
**File:** `graph.py` (inline function)

A wrapper node that fires **Node A**, **Node B**, and **Node C** simultaneously using a `ThreadPoolExecutor(max_workers=3)`. Results from all three are merged back into the state before passing to the aggregator. Typical speedup: ~3× vs. sequential execution.

---

### 3. Node A — `fact_checker` — Citation Verifier
**File:** `nodes/fact_checker.py`  
**Score: 0–30 points**

- Caps verification at the first 20 references to conserve API quota
- Sends all reference strings to Groq in **one batch LLM call** to extract paper titles
- For each title, tries **ArXiv API** first, then **Google Scholar via SerpAPI**
- Uses word-overlap similarity (≥ 0.4 for ArXiv, ≥ 0.35 for Scholar) to confirm a match
- Scoring tiers:

| Verification Rate | Score |
|---|---|
| ≥ 80% | 30 |
| ≥ 60% | 24 |
| ≥ 40% | 18 |
| ≥ 20% | 12 |
| < 20% | 5 |

**Output added to state:** `fact_check_results` (verified count, unverified count, per-reference details, score)

---

### 4. Node B — `formatter` — IEEE Compliance Checker
**File:** `nodes/formatter.py`  
**Score: 0–30 points**

Runs two independent checks in sequence and merges results:

**Rule-based checks (20 pts max)** — no LLM required:
- Abstract present and 150–250 words
- Keywords / Index Terms section present
- Section headings follow IEEE Roman numeral format (I, II, III…)
- Introduction and Conclusion sections present
- References section exists with ≥ 5 entries

**LLM-based deep check (10 pts max)** — sends first 6,000 chars of paper to Groq:
- IEEE citation format compliance (`[N] Author, "Title," Journal, vol., pp., year`)
- In-text citations use `[N]` format
- Abstract mentions methodology and results
- Paper has a clear stated research contribution

**Output added to state:** `format_results` (passed rules list, issues list, overall comment, score)

---

### 5. Node C — `reviewer` — Academic Quality Reviewer
**File:** `nodes/reviewer.py`  
**Score: 0–40 points**

Sends the first 8,000 characters of the paper to Groq for a structured academic review across four dimensions (10 pts each):

| Dimension | What is Evaluated |
|---|---|
| **Novelty & Originality** | New ideas, differentiation from prior work |
| **Methodology & Rigor** | Soundness of approach, reproducibility, validation |
| **Clarity & Presentation** | Writing quality, figure/table clarity, logical structure |
| **Contribution & Impact** | Meaningfulness to the field, problem significance |

Also returns: strengths list, weaknesses list, overall comment, and a final recommendation (`Accept / Minor Revision / Major Revision / Reject`).

**Output added to state:** `review_results` (four sub-scores, four feedback strings, strengths, weaknesses, recommendation)

---

### 6. `aggregator` — Score Collector
**File:** `nodes/aggregator.py`

Simple node that reads the three sub-scores from state and combines them:

```
citations  (0–30) + formatting (0–30) + review (0–40) = total (0–100)
```

**Output added to state:** `scores` dict

---

### 7. `scoring` — PASS/FAIL Decision
**File:** `nodes/scoring.py`

Applies the pass threshold:

- **≥ 70** → `PASS`
- **< 70** → `FAIL`

Also calculates `margin` (how many points above or below the threshold).

**Output added to state:** `decision`, `total_score`, `margin`

---

### 8. `report` — Final Report Assembler
**File:** `nodes/report.py`  
**Terminal node before `END`.**

Assembles all state fields into a single structured JSON report object consumed by the frontend. Includes paper metadata, decision, full score breakdown, citation details per reference, formatting passed/failed rules, and the complete academic review.

**Output added to state:** `final_report`

---

## 🌐 API (FastAPI)

**File:** `main.py`

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/review` | Upload PDF → returns `job_id` immediately (async, non-blocking) |
| `POST` | `/review/sync` | Upload PDF → waits and returns full report (synchronous) |
| `GET` | `/report/{job_id}` | Poll for job status: `queued` → `processing` → `done` / `error` |
| `GET` | `/jobs` | List all submitted jobs (debug) |
| `GET` | `/health` | Health check + API key status |

Jobs are stored in an in-memory dictionary. Uploaded PDFs are deleted after processing.

---

## ⚙️ Setup & Installation

### 1. Clone & Install

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create or edit `backend/.env`:

```env
GROQ_API_KEY=your_groq_api_key_here
SERPAPI_KEY=your_serpapi_key_here   # Optional — enables Google Scholar fallback
```

- **GROQ_API_KEY**: Required. Get a free key at [console.groq.com](https://console.groq.com)
- **SERPAPI_KEY**: Optional. Get at [serpapi.com](https://serpapi.com). Without it, citation checking falls back to ArXiv only.

### 3. Run the Server

```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Open the Frontend

Open `frontend/index.html` in your browser. The UI connects to `http://localhost:8000`.

---

## 🔄 How a Review Works (End-to-End)

1. User uploads an IEEE PDF via the frontend
2. FastAPI saves the file, creates a `job_id`, and starts the pipeline in a background thread
3. LangGraph invokes the compiled graph with `{"pdf_path": "..."}` as the initial state
4. **Ingestion** parses the PDF → checks cache → extracts metadata via Groq LLM
5. **Parallel review** fires Nodes A, B, C concurrently:
   - Node A verifies each citation against ArXiv and Google Scholar
   - Node B checks IEEE formatting rules (rule-based + LLM)
   - Node C performs a full academic review via Groq LLM
6. **Aggregator** sums the three scores
7. **Scoring** applies the 70-point threshold for PASS/FAIL
8. **Report** assembles the final JSON
9. Frontend polls `/report/{job_id}` and renders the results

---

## 📊 Scoring Summary

| Category | Node | Max Points | Method |
|---|---|---|---|
| Citation Verification | A — fact_checker | 30 | ArXiv + Google Scholar lookup |
| IEEE Formatting | B — formatter | 30 | Rule-based + Groq LLM |
| Academic Quality | C — reviewer | 40 | Groq LLM (4 dimensions × 10 pts) |
| **Total** | | **100** | |
| **Pass Threshold** | | **70** | |

---

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| Graph orchestration | LangGraph 0.2.28 |
| LLM inference | Groq API (llama-3.3-70b-versatile) |
| PDF parsing | pymupdf4llm |
| Citation lookup | arxiv Python client + SerpAPI (Google Scholar) |
| API server | FastAPI + Uvicorn |
| Frontend | Vanilla HTML/JS (single file) |

---

## 📝 Notes & Limitations

- **Reference cap**: Only the first 20 references are checked to stay within API rate limits
- **Paper content cap**: Node B uses the first 6,000 characters; Node C uses the first 8,000 characters of the paper text for LLM prompts
- **In-memory jobs**: Job history is lost on server restart. For production, replace the `jobs` dict with a database
- **CORS**: Currently set to `allow_origins=["*"]` — restrict this in production
- **Cache**: Ingestion results are cached by PDF filename stem in `backend/cache/`. Delete cache files to force re-processing