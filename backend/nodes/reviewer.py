import os
import re
import json
from groq import Groq
from typing import Any

def _get_groq_client():
    return Groq(api_key=os.getenv("GROQ_API_KEY"))


def reviewer(state: dict[str, Any]) -> dict[str, Any]:
    """
    Node C — Academic Reviewer
    Reviews the paper for academic quality using Groq LLM.
    Scores across 4 dimensions (total 40 points):
      - Novelty & Originality     (10 pts)
      - Methodology & Rigor       (10 pts)
      - Clarity & Presentation    (10 pts)
      - Contribution & Impact     (10 pts)
    """
    title = state.get("title", "")
    abstract = state.get("abstract", "")
    full_text = state.get("full_text", "")
    section_headings = state.get("section_headings", [])

    print(f"[Node C] Running academic review...")

    review = _llm_review(title, abstract, section_headings, full_text)

    total_score = (
        review.get("novelty_score", 0) +
        review.get("methodology_score", 0) +
        review.get("clarity_score", 0) +
        review.get("contribution_score", 0)
    )
    total_score = min(40, total_score)

    print(f"[Node C] Done — Score: {total_score}/40")
    print(f"[Node C]   Novelty: {review.get('novelty_score')}/10 | "
          f"Methodology: {review.get('methodology_score')}/10 | "
          f"Clarity: {review.get('clarity_score')}/10 | "
          f"Contribution: {review.get('contribution_score')}/10")

    return {
        **state,
        "review_results": {
            "score": total_score,
            "novelty_score": review.get("novelty_score", 0),
            "methodology_score": review.get("methodology_score", 0),
            "clarity_score": review.get("clarity_score", 0),
            "contribution_score": review.get("contribution_score", 0),
            "novelty_feedback": review.get("novelty_feedback", ""),
            "methodology_feedback": review.get("methodology_feedback", ""),
            "clarity_feedback": review.get("clarity_feedback", ""),
            "contribution_feedback": review.get("contribution_feedback", ""),
            "strengths": review.get("strengths", []),
            "weaknesses": review.get("weaknesses", []),
            "overall_comment": review.get("overall_comment", ""),
            "recommendation": review.get("recommendation", ""),
        },
    }


def _llm_review(  # noqa
    title: str,
    abstract: str,
    section_headings: list,
    full_text: str,
) -> dict:
    """Send paper to Groq for full academic review."""

    # Use full text but cap to avoid token limits
    paper_content = full_text[:8000]

    prompt = f"""You are a strict but fair IEEE peer reviewer with expertise in evaluating research papers.
Review this paper thoroughly and provide detailed academic feedback.

PAPER:
Title: {title}
Sections: {section_headings}
Abstract: {abstract}

Full content:
\"\"\"
{paper_content}
\"\"\"

Evaluate the paper on EXACTLY these 4 dimensions, each scored out of 10:

1. NOVELTY & ORIGINALITY (0-10)
   - Does the paper present new ideas, methods, or findings?
   - Is it sufficiently different from existing work?

2. METHODOLOGY & RIGOR (0-10)
   - Is the research methodology sound and well-described?
   - Are experiments/evaluations appropriate and reproducible?
   - Are results validated properly?

3. CLARITY & PRESENTATION (0-10)
   - Is the paper well-written and easy to follow?
   - Are figures, tables, and results clearly presented?
   - Is the structure logical?

4. CONTRIBUTION & IMPACT (0-10)
   - Does the paper make a meaningful contribution to the field?
   - Does it address a real problem?
   - Is the significance of results clearly argued?

Return ONLY a valid JSON object:
{{
  "novelty_score": <0-10>,
  "novelty_feedback": "specific feedback on novelty",
  "methodology_score": <0-10>,
  "methodology_feedback": "specific feedback on methodology",
  "clarity_score": <0-10>,
  "clarity_feedback": "specific feedback on clarity",
  "contribution_score": <0-10>,
  "contribution_feedback": "specific feedback on contribution",
  "strengths": ["strength 1", "strength 2", "strength 3"],
  "weaknesses": ["weakness 1", "weakness 2", "weakness 3"],
  "overall_comment": "2-3 sentence overall assessment",
  "recommendation": "Accept / Minor Revision / Major Revision / Reject"
}}

Rules:
- Be critical and specific — avoid generic praise
- Scores should reflect real quality (7-8 = good, 5-6 = average, 3-4 = weak)
- Return ONLY JSON, no backticks, no explanation
"""

    try:
        response = _get_groq_client().chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500,
            temperature=0.2,
        )
        raw = response.choices[0].message.content.strip()
        raw = re.sub(r'^```json\s*', '', raw)
        raw = re.sub(r'^```\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)
        return json.loads(raw)

    except Exception as e:
        print(f"[Node C] LLM review error: {e}")
        return {
            "novelty_score": 5, "novelty_feedback": "Review failed",
            "methodology_score": 5, "methodology_feedback": "Review failed",
            "clarity_score": 5, "clarity_feedback": "Review failed",
            "contribution_score": 5, "contribution_feedback": "Review failed",
            "strengths": [], "weaknesses": [],
            "overall_comment": "Automated review could not be completed.",
            "recommendation": "Manual Review Required",
        }