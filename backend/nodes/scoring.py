from typing import Any

PASS_THRESHOLD = 70


def scoring(state: dict[str, Any]) -> dict[str, Any]:
    """
    Scoring Node — Applies PASS/FAIL threshold.
    Score >= 70 → PASS
    Score <  70 → FAIL
    """
    scores = state.get("scores", {})
    total  = scores.get("total", 0)

    decision = "PASS" if total >= PASS_THRESHOLD else "FAIL"
    margin   = total - PASS_THRESHOLD

    print(f"[Scoring] Total: {total}/100 → {decision} "
          f"({'above' if margin >= 0 else 'below'} threshold by {abs(margin)} pts)")

    return {
        **state,
        "decision":  decision,
        "total_score": total,
        "margin":    margin,
    }