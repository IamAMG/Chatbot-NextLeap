"""Phase 5.3 — Streamlit UI (Groww-inspired palette, facts-only FAQ).

Run with:
    streamlit run src/ui/app.py
or (from repo root):
    python -m streamlit run src/ui/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import streamlit as st

from src.retrieval.retrieve import Retriever

# Groww-inspired palette
GREEN = "#00D09C"
DARK = "#120B26"
WHITE = "#FFFFFF"
MUTED = "#5B5B5B"

EXAMPLE_QUESTIONS = [
    "What is the expense ratio of HDFC Large Cap Fund Direct Growth?",
    "What is the ELSS lock-in for HDFC ELSS Tax Saver Fund Direct Plan Growth?",
    "What is the minimum SIP for HDFC Small Cap Fund Direct Growth?",
]


def _css() -> str:
    return f"""
    <style>
      .block-container {{ padding-top: 2rem; max-width: 860px; }}
      .app-title {{ color: {DARK}; font-size: 1.9rem; font-weight: 700; }}
      .app-sub {{ color: {MUTED}; margin-top: -0.4rem; }}
      .banner {{ background: {GREEN}; color: {DARK}; border-radius: 12px;
                 padding: 0.4rem 0.9rem; display: inline-block; font-weight: 600; }}
      .answer-box {{ background: #ffffff; border: 1px solid #e3e3e3; border-left: 4px solid {GREEN};
                    border-radius: 8px; padding: 1rem 1.2rem; margin-top: 0.6rem; }}
      .meta {{ color: {MUTED}; font-size: 0.85rem; }}
      .refuse-box {{ background: #fff5f5; border-left: 4px solid #e11d48;
                     border-radius: 8px; padding: 1rem 1.2rem; margin-top: 0.6rem; }}
    </style>
    """


def _render_answer(answer) -> None:
    if answer.action == "answered":
        st.markdown('<div class="answer-box">', unsafe_allow_html=True)
        st.write(answer.answer)
        if answer.fund_name:
            st.markdown(f"<div class='meta'>Matched fund: {answer.fund_name}</div>", unsafe_allow_html=True)
        if answer.url:
            st.markdown(f"<div class='meta'>Source: [{answer.url}]({answer.url})</div>", unsafe_allow_html=True)
        if answer.ingest_ts:
            st.markdown(f"<div class='meta'>Last updated from sources: {answer.ingest_ts}</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    elif answer.action in ("refused", "weak"):
        st.markdown('<div class="refuse-box">', unsafe_allow_html=True)
        st.write(answer.answer)
        if answer.url:
            st.markdown(f"<div class='meta'>Learn more: [{answer.url}]({answer.url})</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    elif answer.action == "error":
        st.error(answer.answer)


@st.cache_resource
def _retriever():
    return Retriever()


def main() -> None:
    st.markdown(_css(), unsafe_allow_html=True)

    st.markdown(
        '<div class="app-title">HDFC Fund Facts Assistant</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="app-sub">Answers factual questions about five HDFC Direct Growth funds on Groww.</div>', unsafe_allow_html=True)
    st.markdown('<div class="banner">Facts-only. No investment advice.</div>', unsafe_allow_html=True)

    if "history" not in st.session_state:
        st.session_state.history = []

    picked = st.radio("Try an example:", [""] + EXAMPLE_QUESTIONS, label_visibility="collapsed")

    with st.form("ask", clear_on_submit=False):
        q = st.text_input("Ask a question", value=picked or "", placeholder="e.g. What is the exit load of HDFC Flexi Cap?")
        submitted = st.form_submit_button("Ask")

    if submitted and q.strip():
        retriever = _retriever()
        with st.spinner("Looking it up…"):
            answer = retriever.answer(q.strip())
        st.session_state.history.append((q.strip(), answer))
        _render_answer(answer)
    else:
        st.caption("Examples cover expense ratio, ELSS lock-in, and minimum SIP.")

    if st.session_state.history:
        st.markdown("### History")
        for old_q, old_a in reversed(st.session_state.history):
            st.markdown("---")
            st.markdown(f"**Q:** {old_q}")
            _render_answer(old_a)


if __name__ == "__main__":
    main()
