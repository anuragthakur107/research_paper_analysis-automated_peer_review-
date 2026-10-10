import pymupdf4llm
import os
import json
import re
from groq import Groq
from typing import Any
from pathlib import Path

def _get_groq_client():
    return Groq(api_key=os.getenv("GROQ_API_KEY"))




CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)


def extract_paper(state: dict[str, Any]) -> dict[str, Any]:
    
    pdf_path = state["pdf_path"]

    cached = _load_cache(pdf_path)
    if cached:
        print(f"[Ingestion] ✅ Loaded from cache!")
        print(f"[Ingestion] Title: {cached.get('title', '')[:80]}")
        print(f"[Ingestion] References: {len(cached.get('references', []))} | Sections: {len(cached.get('section_headings', []))}")
        md_text = pymupdf4llm.to_markdown(pdf_path)
        return {**state, "full_text": md_text, **cached}

    print(f"[Ingestion] Reading PDF: {pdf_path}")
    md_text = pymupdf4llm.to_markdown(pdf_path)
    print(f"[Ingestion] Converted — {len(md_text)} chars (~{len(md_text)//4} tokens)")

    structured = _llm_extract(md_text)

    print(f"[Ingestion] Pages: {structured.get('page_count', 0)} | "
          f"References: {len(structured.get('references', []))} | "
          f"Sections: {len(structured.get('section_headings', []))}")
    print(f"[Ingestion] Title: {structured.get('title', '')[:80]}")
    print(f"[Ingestion] Abstract preview: {structured.get('abstract', '')[:100]}")

    result = {
        "title": structured.get("title", "Unknown Title"),
        "abstract": structured.get("abstract", ""),
        "references": structured.get("references", []),
        "section_headings": structured.get("section_headings", []),
        "page_count": structured.get("page_count", 0),
        "references_raw": "",
    }

    _save_cache(pdf_path, result)

    return {**state, "full_text": md_text, **result}


def _llm_extract(md_text: str) -> dict:
    """
    Send ENTIRE markdown to Groq in ONE call.
    Groq Pro handles large context easily.
    """
    prompt = f"""You are a research paper parser. Extract structured data from this IEEE research paper (markdown format).

FULL paper:
\"\"\"
{md_text}
\"\"\"

Return ONLY a valid JSON object with exactly these fields:
{{
  "title": "full paper title",
  "abstract": "complete abstract text",
  "section_headings": ["I. INTRODUCTION", "II. METHODOLOGY", ...],
  "page_count": <number>,
  "references": [
    {{
      "number": "1",
      "raw": "full reference text — authors, title, journal, year",
      "verified_arxiv": false,
      "verified_scholar": false
    }}
  ]
}}

Rules:
- Extract ALL references from the references section at the END of the paper
- Do NOT confuse in-text citations like [1] with the actual references list
- References list is at the very end of the paper
- Keep each reference's complete text in "raw"
- Section headings use IEEE Roman numeral format (I, II, III...)
- Return ONLY the JSON, no explanation, no markdown backticks
"""

    try:
        response = _get_groq_client().chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000,
            temperature=0.1,
        )
        raw = _clean_json(response.choices[0].message.content)
        return json.loads(raw)

    except Exception as e:
        print(f"[Ingestion] LLM error: {e}")
        return {
            "title": "Unknown Title",
            "abstract": "",
            "section_headings": [],
            "page_count": 0,
            "references": []
        }


def _load_cache(pdf_path: str) -> dict | None:
    cache_path = CACHE_DIR / f"{Path(pdf_path).stem}.json"
    if cache_path.exists():
        print(f"[Ingestion] Cache found: {cache_path}")
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def _save_cache(pdf_path: str, data: dict) -> None:
    cache_path = CACHE_DIR / f"{Path(pdf_path).stem}.json"
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"[Ingestion] ✅ Cached → {cache_path}")


def _clean_json(text: str) -> str:
    text = text.strip()
    text = re.sub(r'^```json\s*', '', text)
    text = re.sub(r'^```\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    return text.strip()