from typing import Any
from datetime import datetime


def report(state: dict[str, Any]) -> dict[str, Any]:
    """
    Report Node — Assembles final JSON report for the frontend.
    This is the last node in the pipeline.
    """
    scores   = state.get("scores", {})
    decision = state.get("decision", "FAIL")
    margin   = state.get("margin", 0)

    fact_check = state.get("fact_check_results", {})
    format_res = state.get("format_results", {})
    review_res = state.get("review_results", {})

    final_report = {
        # ── Paper Info ───────────────────────────────────────────
        "title":     state.get("title", "Unknown"),
        "abstract":  state.get("abstract", ""),
        "sections":  state.get("section_headings", []),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),

        # ── Overall Result ───────────────────────────────────────
        "decision":    decision,
        "total_score": scores.get("total", 0),
        "margin":      margin,
        "threshold":   70,

        # ── Score Breakdown ──────────────────────────────────────
        "scores": {
            "citations":  {"score": scores.get("citations", 0),  "max": 30},
            "formatting": {"score": scores.get("formatting", 0), "max": 30},
            "review":     {"score": scores.get("review", 0),     "max": 40},
        },

        # ── Citation Details (Node A) ────────────────────────────
        "citations": {
            "verified":           fact_check.get("verified", 0),
            "unverified":         fact_check.get("unverified", 0),
            "total_checked":      fact_check.get("total", 0),
            "verification_rate":  fact_check.get("verification_rate", 0),
            "summary":            fact_check.get("summary", ""),
            "details":            fact_check.get("details", []),
        },

        # ── Formatting Details (Node B) ──────────────────────────
        "formatting": {
            "passed":          format_res.get("passed", []),
            "issues":          format_res.get("issues", []),
            "summary":         format_res.get("summary", ""),
            "overall_comment": format_res.get("llm_details", {}).get("overall_comment", ""),
        },

        # ── Review Details (Node C) ──────────────────────────────
        "review": {
            "novelty_score":        review_res.get("novelty_score", 0),
            "methodology_score":    review_res.get("methodology_score", 0),
            "clarity_score":        review_res.get("clarity_score", 0),
            "contribution_score":   review_res.get("contribution_score", 0),
            "novelty_feedback":     review_res.get("novelty_feedback", ""),
            "methodology_feedback": review_res.get("methodology_feedback", ""),
            "clarity_feedback":     review_res.get("clarity_feedback", ""),
            "contribution_feedback":review_res.get("contribution_feedback", ""),
            "strengths":            review_res.get("strengths", []),
            "weaknesses":           review_res.get("weaknesses", []),
            "overall_comment":      review_res.get("overall_comment", ""),
            "recommendation":       review_res.get("recommendation", ""),
        },
    }

    print(f"[Report] ✅ Final report generated — {decision} ({scores.get('total', 0)}/100)")

    return {**state, "final_report": final_report}