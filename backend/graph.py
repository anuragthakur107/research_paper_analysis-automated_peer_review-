"""
graph.py — LangGraph Pipeline for Automated Peer Review

Pipeline flow:
    ingestion
        ↓
    node_a   ← fact_checker (citation verification, ~2-3 min due to 20 ref lookups)
        ↓           ↑ natural delay here resets the Groq TPM window
    node_b   ← formatter   (IEEE formatting check)
        ↓
    node_c   ← reviewer    (academic review)
        ↓
    aggregator
        ↓
    scoring
        ↓
    report

Why sequential instead of parallel:
  Node A checks 20 references one by one against ArXiv + Scholar.
  This naturally takes 2-3 minutes, which is enough for the Groq
  60s TPM window to reset before Node B and C fire their LLM calls.
  No sleep hacks needed — Node A's ref lookup loop is the natural buffer.
"""

from __future__ import annotations

from typing import TypedDict, Any

from langgraph.graph import StateGraph, END

from nodes.ingestion    import extract_paper
from nodes.fact_checker import fact_checker
from nodes.formatter    import formatter
from nodes.reviewer     import reviewer
from nodes.aggregator   import aggregator
from nodes.scoring      import scoring
from nodes.report       import report


# ── State schema ──────────────────────────────────────────────────────────────
class PaperState(TypedDict, total=False):
    # Input
    pdf_path: str

    # Ingestion outputs
    full_text:        str
    title:            str
    abstract:         str
    references:       list
    section_headings: list
    page_count:       int
    references_raw:   str

    # Node outputs
    fact_check_results: dict   # Node A — citations  (0-30)
    format_results:     dict   # Node B — formatting (0-30)
    review_results:     dict   # Node C — academic   (0-40)

    # Aggregation / scoring
    scores:      dict
    decision:    str
    total_score: int
    margin:      int

    # Final output
    final_report: dict


# ── Build graph ───────────────────────────────────────────────────────────────
def build_graph():
    g = StateGraph(PaperState)

    g.add_node("ingestion",  extract_paper)
    g.add_node("node_a",     fact_checker)
    g.add_node("node_b",     formatter)
    g.add_node("node_c",     reviewer)
    g.add_node("aggregator", aggregator)
    g.add_node("scoring",    scoring)
    g.add_node("report",     report)

    g.set_entry_point("ingestion")

    g.add_edge("ingestion",  "node_a")
    g.add_edge("node_a",     "node_b")
    g.add_edge("node_b",     "node_c")
    g.add_edge("node_c",     "aggregator")
    g.add_edge("aggregator", "scoring")
    g.add_edge("scoring",    "report")
    g.add_edge("report",     END)

    return g.compile()


# Compiled singleton — imported by main.py
peer_review_graph = build_graph()


def run_pipeline(pdf_path: str) -> dict:
    """
    Entry point for the FastAPI server.
    Returns the final_report dict on success, raises on failure.
    """
    initial_state: PaperState = {"pdf_path": pdf_path}
    final_state = peer_review_graph.invoke(initial_state)
    return final_state["final_report"]