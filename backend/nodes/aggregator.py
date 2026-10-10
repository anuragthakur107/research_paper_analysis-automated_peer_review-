from typing import Any


def aggregator(state: dict[str, Any]) -> dict[str, Any]:
    """
    Aggregator Node — Collects scores from all 3 nodes.
    
    Node A (fact_checker)  → citations score  (0-30)
    Node B (formatter)     → formatting score (0-30)
    Node C (reviewer)      → review score     (0-40)
    Total                                      (0-100)
    """
    citation_score  = state.get("fact_check_results", {}).get("score", 0)
    formatting_score = state.get("format_results", {}).get("score", 0)
    review_score    = state.get("review_results", {}).get("score", 0)

    total = citation_score + formatting_score + review_score

    print(f"[Aggregator] Citations: {citation_score}/30 | "
          f"Formatting: {formatting_score}/30 | "
          f"Review: {review_score}/40 | "
          f"Total: {total}/100")

    return {
        **state,
        "scores": {
            "citations":   citation_score,
            "formatting":  formatting_score,
            "review":      review_score,
            "total":       total,
        },
    }