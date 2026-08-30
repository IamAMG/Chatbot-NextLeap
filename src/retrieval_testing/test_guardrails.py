"""Guardrail edge cases (PRD §10 / architecture Phase 6). No vector store touched."""

from src.retrieval.guardrails import check


def _expect(input_text: str, category: str, action: str = "refuse") -> None:
    gr = check(input_text)
    assert gr.action == action, f"{input_text!r}: got action={gr.action}"
    if action == "refuse":
        assert gr.category == category, f"{input_text!r}: cat={gr.category} want {category}"
        assert gr.url, "refusal must carry an allowlisted URL"


# 1-4: factual questions pass guardrails (retrieval only, in Phase 5 tests).
def test_factual_questions_allow():
    for q in (
        "What is the expense ratio of HDFC Large Cap Fund Direct Growth?",
        "What is the ELSS lock-in?",
        "What is the minimum SIP for HDFC Small Cap Fund Direct Growth?",
        "What is the benchmark for HDFC Large Cap?",
        "How do I download my capital-gains statement?",
        "What is the expense ratio?",
    ):
        gr = check(q)
        assert gr.action == "allow", f"{q!r} not allowed: {gr.category}"


# 5: advice / opinion -> refusal.
def test_advice_refused():
    _expect("Should I buy HDFC Small Cap?", "advice")
    _expect("Is HDFC Large Cap worth investing in?", "advice")


# 6: returns / compare / rank -> refusal, no computed comparison.
def test_returns_compare_refused():
    _expect("Which fund is best, small cap or large cap?", "returns")
    _expect("Compare 3Y returns of HDFC Large Cap vs HDFC Small Cap?", "returns")
    _expect("How much would 10000 grow to in HDFC Large Cap in 10 years?", "returns")


# 7: fund outside the five URLs -> out of scope.
def test_out_of_scope_refused():
    _expect("Tell me about HDFC Thematic Fund (not in corpus)", "out-of-scope")


# 8: PII never accepted / stored.
def test_pii_refused():
    _expect("My PAN is BFGPM2456K and phone 9876543210", "pii")
    _expect("Email me at user@example.com", "pii")


# 9: empty / gibberish -> ask to rephrase.
def test_empty_gibberish_refused():
    _expect("12345", "empty")
    _expect("   ", "empty")
    _expect("asdfjkl", "empty")


# 10: ambiguous "expense ratio?" with no fund -> allowed (edge 10: resolve or
# ask). Guardrail allows; retrieval decides. Documented here.
def test_ambiguous_allows():
    assert check("What is the expense ratio?").action == "allow"
