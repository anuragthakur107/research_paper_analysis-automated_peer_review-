import os
import re
import time
import arxiv
from serpapi import GoogleSearch
from groq import Groq
from typing import Any

def _get_groq_client():
    return Groq(api_key=os.getenv("GROQ_API_KEY"))



SERPAPI_KEY = os.getenv("SERPAPI_KEY")


def fact_checker(state: dict[str, Any]) -> dict[str, Any]:
    
    references = state.get("references", [])

    if not references:
        return {
            **state,
            "fact_check_results": {
                "verified": 0, "unverified": 0, "total": 0,
                "verification_rate": 0, "details": [], "score": 0,
                "summary": "No references found in the paper.",
            },
        }

    refs_to_check = references[:20]
    print(f"[Node A] Checking {len(refs_to_check)}/{len(references)} references...")

    titles = _batch_extract_titles([r["raw"] for r in refs_to_check])

    details = []
    verified_count = 0

    for i, ref in enumerate(refs_to_check):
        title_query = titles.get(str(i), "")
        print(f"[Node A] [{ref['number']}] ({i+1}/{len(refs_to_check)}) Query: '{title_query[:60]}'")

        if not title_query or len(title_query) < 10:
            result = {"found": False, "source": "Not Found", "matched_title": ""}
        else:
            result = _check_reference(title_query)

        detail = {
            "number": ref["number"],
            "raw": ref["raw"],
            "verified": result["found"],
            "source": result["source"],
            "matched_title": result.get("matched_title", ""),
        }
        details.append(detail)
        if result["found"]:
            verified_count += 1

        time.sleep(0.3)

    total = len(refs_to_check)
    verification_rate = (verified_count / total * 100) if total > 0 else 0

    if verification_rate >= 80:
        score = 30
    elif verification_rate >= 60:
        score = 24
    elif verification_rate >= 40:
        score = 18
    elif verification_rate >= 20:
        score = 12
    else:
        score = 5

    summary = f"{verified_count}/{total} references verified ({verification_rate:.1f}% verification rate)."
    print(f"[Node A] Done — {summary} Score: {score}/30")

    return {
        **state,
        "fact_check_results": {
            "verified": verified_count,
            "unverified": total - verified_count,
            "total": total,
            "verification_rate": round(verification_rate, 1),
            "details": details,
            "score": score,
            "summary": summary,
        },
    }


def _batch_extract_titles(raw_refs: list[str]) -> dict:
   
    numbered = "\n".join([f"{i}. {r}" for i, r in enumerate(raw_refs)])

    prompt = f"""Extract ONLY the paper title from each reference below.
Return ONLY a JSON object like: {{"0": "title of paper 0", "1": "title of paper 1", ...}}

References:
{numbered}

Rules:
- Return ONLY the JSON object, no explanation, no backticks
- Title is the name of the paper/article, NOT the journal name
- If you cannot find a title, use empty string ""
"""

    try:
        response = _get_groq_client().chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.1,
        )
        raw = response.choices[0].message.content.strip()
        raw = re.sub(r'^```json\s*', '', raw)
        raw = re.sub(r'^```\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)
        import json
        return json.loads(raw)
    except Exception as e:
        print(f"[Node A] Batch title extraction error: {e}")
        # Fallback to regex extraction
        return {str(i): _regex_extract_title(r) for i, r in enumerate(raw_refs)}


def _regex_extract_title(raw: str) -> str:
    """Fallback regex title extraction."""
    clean = re.sub(r'^\[?\d+\]\.?\s*', '', raw).strip()
    quoted = re.findall(r'["""](.+?)["""]', clean)
    if quoted and len(quoted[0]) > 15:
        return quoted[0][:150]
    parts = clean.split(',')
    for part in parts:
        part = part.strip()
        if len(part) < 20:
            continue
        if len(re.findall(r'\b[A-Z]\.\s', part)) > 1:
            continue
        if re.search(r'\b(vol\.|pp\.|phys\.|nat\.|lett\.)\b', part, re.IGNORECASE):
            continue
        return part[:150]
    return clean[:100]


def _check_reference(title_query: str) -> dict:
    """Try ArXiv first, then Google Scholar."""
    arxiv_result = _check_arxiv(title_query)
    if arxiv_result["found"]:
        return {"found": True, "source": "ArXiv", "matched_title": arxiv_result["title"]}

    scholar_result = _check_scholar(title_query)
    if scholar_result["found"]:
        return {"found": True, "source": "Google Scholar", "matched_title": scholar_result["title"]}

    return {"found": False, "source": "Not Found", "matched_title": ""}


def _check_arxiv(query: str) -> dict:
    """Search ArXiv API."""
    try:
        client_arxiv = arxiv.Client()
        search = arxiv.Search(
            query=query,
            max_results=3,
            sort_by=arxiv.SortCriterion.Relevance,
        )
        results = list(client_arxiv.results(search))
        if results:
            top = results[0]
            sim = _similarity(query, top.title)
            print(f"[Node A]   ArXiv (sim={sim:.2f}): '{top.title[:60]}'")
            if sim > 0.4:
                return {"found": True, "title": top.title}
    except Exception as e:
        print(f"[Node A]   ArXiv error: {e}")
    return {"found": False, "title": ""}


def _check_scholar(query: str) -> dict:
    """Search Google Scholar via SerpApi."""
    if not SERPAPI_KEY:
        return {"found": False, "title": ""}
    try:
        params = {
            "engine": "google_scholar",
            "q": query,
            "api_key": SERPAPI_KEY,
            "num": 3,
        }
        search = GoogleSearch(params)
        results = search.get_dict()
        organic = results.get("organic_results", [])
        if organic:
            top = organic[0]
            title = top.get("title", "")
            sim = _similarity(query, title)
            print(f"[Node A]   Scholar (sim={sim:.2f}): '{title[:60]}'")
            if sim > 0.35:
                return {"found": True, "title": title}
    except Exception as e:
        print(f"[Node A]   Scholar error: {e}")
    return {"found": False, "title": ""}


def _similarity(query: str, found_title: str) -> float:
    """Word overlap similarity."""
    q_words = set(re.findall(r'\b\w{4,}\b', query.lower()))
    t_words = set(re.findall(r'\b\w{4,}\b', found_title.lower()))
    if not q_words:
        return 0.0
    return len(q_words & t_words) / len(q_words)