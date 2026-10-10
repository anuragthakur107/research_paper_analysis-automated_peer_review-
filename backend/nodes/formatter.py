import os
import re
import json
from groq import Groq
from typing import Any

def _get_groq_client():
    return Groq(api_key=os.getenv("GROQ_API_KEY"))





def formatter(state: dict[str, Any]) -> dict[str, Any]:
    """
    Node B — IEEE Formatter
    Checks the paper against IEEE formatting rules using LLM.
    Returns formatting score (0-30) + detailed feedback.

    IEEE Rules Checked:
    1. Abstract present and proper length (150-250 words)
    2. Keywords present
    3. Section headings use Roman numerals (I, II, III...)
    4. References section exists and follows IEEE citation format
    5. Introduction section present
    6. Conclusion section present
    7. Paper structure completeness
    """
    full_text = state.get("full_text", "")
    title = state.get("title", "")
    abstract = state.get("abstract", "")
    section_headings = state.get("section_headings", [])
    references = state.get("references", [])

    print(f"[Node B] Checking IEEE formatting rules...")

    # Run rule-based checks (no LLM tokens needed)
    rule_results = _rule_based_checks(abstract, section_headings, references, full_text)

    # Run LLM-based deep check (catches things rules miss)
    llm_results = _llm_format_check(title, abstract, section_headings, references, full_text)

    # Merge both results
    all_issues = rule_results["issues"] + llm_results["issues"]
    all_passed = rule_results["passed"] + llm_results["passed"]

    # Calculate score out of 30
    score = _calculate_score(rule_results, llm_results)

    summary = f"IEEE formatting check: {len(all_passed)} rules passed, {len(all_issues)} issues found."
    print(f"[Node B] Done — Score: {score}/30 | Issues: {len(all_issues)}")

    return {
        **state,
        "format_results": {
            "score": score,
            "issues": all_issues,
            "passed": all_passed,
            "summary": summary,
            "rule_details": rule_results,
            "llm_details": llm_results,
        },
    }


def _rule_based_checks(
    abstract: str,
    section_headings: list,
    references: list,
    full_text: str,
) -> dict:
    """Fast rule-based IEEE checks — no LLM needed."""
    issues = []
    passed = []

    # 1. Abstract present
    if abstract and len(abstract.strip()) > 50:
        passed.append("Abstract is present")
    else:
        issues.append("Abstract is missing or too short")

    # 2. Abstract word count (IEEE: 150-250 words)
    if abstract:
        word_count = len(abstract.split())
        if 150 <= word_count <= 250:
            passed.append(f"Abstract length is good ({word_count} words)")
        elif word_count < 150:
            issues.append(f"Abstract too short ({word_count} words, IEEE requires 150-250)")
        else:
            issues.append(f"Abstract too long ({word_count} words, IEEE requires 150-250)")

    # 3. Keywords present
    if re.search(r'\b(keywords|index terms)\b', full_text, re.IGNORECASE):
        passed.append("Keywords/Index Terms section present")
    else:
        issues.append("Keywords or Index Terms section missing")

    # 4. Roman numeral section headings
    roman_pattern = re.compile(r'^(I|II|III|IV|V|VI|VII|VIII|IX|X)[\.\s]', re.IGNORECASE)
    if section_headings:
        roman_count = sum(1 for h in section_headings if roman_pattern.match(h.strip()))
        if roman_count >= 2:
            passed.append(f"Section headings use IEEE Roman numeral format ({roman_count} sections)")
        else:
            issues.append("Section headings do not follow IEEE Roman numeral format (I, II, III...)")
    else:
        issues.append("No section headings detected")

    # 5. Introduction present
    has_intro = any(re.search(r'introduction', h, re.IGNORECASE) for h in section_headings)
    if has_intro:
        passed.append("Introduction section present")
    else:
        issues.append("Introduction section missing")

    # 6. Conclusion present
    has_conclusion = any(re.search(r'conclusion', h, re.IGNORECASE) for h in section_headings)
    if has_conclusion:
        passed.append("Conclusion section present")
    else:
        issues.append("Conclusion section missing")

    # 7. References present
    if references and len(references) > 0:
        passed.append(f"References section present ({len(references)} references)")
    else:
        issues.append("References section missing")

    # 8. Minimum references count (IEEE expects at least 5)
    if len(references) >= 5:
        passed.append(f"Sufficient references ({len(references)} references)")
    else:
        issues.append(f"Too few references ({len(references)}, IEEE papers typically have 5+)")

    return {"issues": issues, "passed": passed}


def _llm_format_check(
    title: str,
    abstract: str,
    section_headings: list,
    references: list,
    full_text: str,
) -> dict:
    """LLM-based deep IEEE format check."""

    # Send top portion of paper only to save tokens
    paper_sample = full_text[:6000]

    # Format references sample
    refs_sample = "\n".join([f"[{r['number']}] {r['raw'][:100]}" for r in references[:5]])

    prompt = f"""You are an IEEE paper format reviewer. Check this paper for IEEE formatting compliance.

PAPER DETAILS:
Title: {title}
Abstract: {abstract[:500]}
Section headings: {section_headings}
First 5 references:
{refs_sample}

Paper content (first portion):
\"\"\"
{paper_sample}
\"\"\"

Check these IEEE rules:
1. References use correct IEEE citation format: [N] Author(s), "Title," Journal, vol., pp., year
2. In-text citations use numbered format [1], [2] etc.
3. Paper has a clear research contribution stated
4. Abstract mentions methodology and results
5. Technical content appears rigorous

Return ONLY a valid JSON object:
{{
  "passed": ["rule that passed", "another rule passed"],
  "issues": ["specific issue found", "another issue"],
  "overall_comment": "Brief overall assessment of IEEE formatting compliance"
}}

Rules:
- Be specific about issues found
- Return ONLY JSON, no backticks, no explanation
"""

    try:
        response = _get_groq_client().chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.1,
        )
        raw = response.choices[0].message.content.strip()
        raw = re.sub(r'^```json\s*', '', raw)
        raw = re.sub(r'^```\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)
        result = json.loads(raw)
        return {
            "passed": result.get("passed", []),
            "issues": result.get("issues", []),
            "overall_comment": result.get("overall_comment", ""),
        }
    except Exception as e:
        print(f"[Node B] LLM check error: {e}")
        return {"passed": [], "issues": [], "overall_comment": "LLM check failed"}


def _calculate_score(rule_results: dict, llm_results: dict) -> int:
    """
    Score out of 30 based on issues found.
    Rule-based: 20 points max
    LLM-based:  10 points max
    """
    # Rule-based score (20 pts)
    total_rules = len(rule_results["passed"]) + len(rule_results["issues"])
    if total_rules > 0:
        rule_pass_rate = len(rule_results["passed"]) / total_rules
    else:
        rule_pass_rate = 0
    rule_score = round(rule_pass_rate * 20)

    # LLM-based score (10 pts)
    total_llm = len(llm_results["passed"]) + len(llm_results["issues"])
    if total_llm > 0:
        llm_pass_rate = len(llm_results["passed"]) / total_llm
    else:
        llm_pass_rate = 0.5  # neutral if LLM failed
    llm_score = round(llm_pass_rate * 10)

    return min(30, rule_score + llm_score)