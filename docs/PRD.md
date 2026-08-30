# PRD: HDFC Mutual Fund FAQ Assistant (RAG Prototype)

| Field | Value |
| --- | --- |
| Product | Facts-only FAQ chatbot for 5 HDFC Direct Growth funds on Groww |
| Status | Prototype / hobby (RAG test) |
| Owner | PM (this document) |
| Source | `Problem Statement.txt` |
| Date | 30 Aug 2026 |

---

## 1. Problem

Investors looking at HDFC funds on [Groww](https://groww.in/) have to hunt across long fund pages for basic facts (expense ratio, SIP minimum, exit load, lock-in, riskometer, how to get a capital-gains statement). They also get pulled into advice-shaped questions the product must not answer.

We need a **small, citable, facts-only assistant** over a **fixed public corpus** so we can test a RAG pipeline without building a full product.

## 2. Goal

Ship a working Streamlit prototype that:

1. Ingests **only** the five Groww fund URLs below.
2. Answers **factual** questions from retrieved chunks.
3. Always shows **one citation URL**.
4. **Refuses** advice / portfolio / performance-comparison questions.
5. Lets us validate ingest → embed → retrieve → generate end to end.

**Success for this prototype:** a reviewer can ask the example questions, get a short sourced answer, see a refusal on advice, and we have a short edge-case test list that passes.

## 3. Non-goals (explicit)

- Not a production chatbot, not Groww-branded for launch.
- No login, accounts, or personalization.
- No funds, AMCs, or pages beyond the five URLs.
- No third-party blogs, screenshots of app backends, or unofficial sources.
- No computed or compared returns; no “best fund” ranking.
- No PII collection or storage.
- No multi-turn memory beyond the current chat session needed to answer one question.

## 4. Users

| Who | What they do |
| --- | --- |
| Internal tester / builder | Validates RAG quality and guardrails |
| Mock “Groww visitor” | Asks factual questions about the five HDFC Direct Growth schemes |

No real customer launch. Treat answers as **educational facts from public pages**, not advice.

## 5. Corpus (hard scope)

AMC: **HDFC**. Website: **groww.in**. Ingest **only** these pages:

| Category | Scheme | URL |
| --- | --- | --- |
| Large-cap | HDFC Large Cap Fund Direct Growth | https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth |
| Flexi-cap | HDFC Flexi Cap Fund Direct Growth | https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth |
| ELSS | HDFC ELSS Tax Saver Fund Direct Plan Growth | https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth |
| Small-cap | HDFC Small Cap Fund Direct Growth | https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth |
| Hybrid | HDFC Balanced Advantage Fund Direct Growth | https://groww.in/mutual-funds/hdfc-balanced-advantage-fund-direct-growth |

Note: Flexi-cap still uses Groww’s legacy `hdfc-equity-fund-direct-growth` slug. Do not crawl linked factsheets, blogs, or other funds unless a **link-only** response is required (see constraints).

## 6. User experience

**Surface:** Streamlit, simple layout, Groww-inspired palette (green / white / dark text).

**First screen:**

- Welcome line (one sentence: this bot answers facts on the five HDFC funds above).
- Three clickable example questions, e.g.:
  - What is the expense ratio of HDFC Large Cap Fund Direct Growth?
  - What is the ELSS lock-in for HDFC ELSS Tax Saver?
  - What is the minimum SIP for HDFC Small Cap Fund Direct Growth?
- Persistent note: **“Facts-only. No investment advice.”**

**Each answer must:**

- Be **≤ 3 sentences**.
- Include **exactly one** citation link (the Groww page used).
- Include **“Last updated from sources: &lt;date&gt;”** (ingest / scrape timestamp).
- Stay factual; no recommendations.

## 7. Functional requirements

### Must have (P0)

| ID | Requirement |
| --- | --- |
| F1 | Ingest the 5 URLs, chunk text, embed, store in ChromaDB. |
| F2 | Embeddings: `sentence-transformers/all-MiniLM-L6-v2` (Hugging Face). |
| F3 | On question: embed query → retrieve relevant chunks → prompt LLM (Mistral API) → answer. |
| F4 | Answers only from retrieved corpus; if retrieval is weak / empty, say so and cite the closest allowed page (or refuse). |
| F5 | One citation URL per answer. |
| F6 | Refuse buy/sell/“should I…”/portfolio allocation with a polite facts-only message + one relevant **educational** link from the allowed pages (or the matching fund page). |
| F7 | Do not compute or compare returns; if asked, do not invent numbers — point the user to the official factsheet **as a link**, without scraping extra pages into the vector store. |
| F8 | Reject / do not store PAN, Aadhaar, account numbers, OTPs, emails, phone numbers. |
| F9 | Streamlit UI as in §6. |
| F10 | Edge-case tests (see §10). |

### Nice to have (P1)

- Show which fund the retrieval matched.
- Re-ingest button for the five URLs (refresh “Last updated”).
- Chat history in-session only.

## 8. RAG pipeline (build spec)

```
[5 Groww URLs] → fetch HTML/text → chunk → MiniLM embeddings → ChromaDB
                                                                      ↑
User question → refuse PII / advice? → embed question → k-NN retrieve -┘
                                                                      ↓
                         prompt (facts-only, ≤3 sentences, cite one URL)
                                                                      ↓
                              Mistral API → Streamlit reply + citation + timestamp
```

| Stage | Choice |
| --- | --- |
| Ingestion | Only the 5 URLs |
| Chunking | Fit typical fund-page sections (expense ratio, SIP, exit load, riskometer, lock-in) |
| Embedding | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector store | ChromaDB |
| LLM | Mistral (API key) |
| UI | Streamlit |

System prompt rules: facts from context only; no advice; no performance math; no PII echo; ≤3 sentences; one source URL; last-updated line.

## 9. Constraints (compliance / product)

- **Public sources only.** Groww fund pages in §5. No app-backend screenshots. No third-party blogs in the index.
- **No PII.** Detect and refuse; do not log those fields.
- **No performance claims.** Do not calculate or compare returns.
- **Clarity.** Short answers + citation + last-updated line.
- **Advice boundary.** Opinion / “should I invest” → refusal, not a hedged recommendation.

## 10. Edge cases to test

| # | Input | Expected |
| --- | --- | --- |
| 1 | Expense ratio for a named fund in corpus | Fact + that fund’s Groww URL + last-updated |
| 2 | ELSS lock-in | 3-year lock-in fact (from page) + ELSS URL |
| 3 | Minimum SIP / exit load / riskometer / benchmark | Fact from page + citation |
| 4 | How to download capital-gains statement | Factual steps if on page; else honest “not on this page” + citation |
| 5 | “Should I buy / sell / switch?” | Refusal + educational / fund page link; no allocation advice |
| 6 | “Which fund is best / compare 3Y returns?” | No computed comparison; link-only to factsheet / refuse ranking |
| 7 | Fund **not** in the five URLs | Out of scope; do not invent |
| 8 | PAN / phone / OTP in the message | Refuse; do not store |
| 9 | Empty / gibberish query | Ask to rephrase; no hallucinated fund data |
| 10 | Ambiguous “expense ratio?” with no fund name | Ask which of the five funds, or retrieve only if clearly unique |

## 11. Success metrics (prototype-scale)

- **Grounding:** ≥ 80% of P0 factual questions get a correct number/fact matching the live page (spot-check).
- **Citation:** 100% of answers include one allowed URL.
- **Guardrails:** 100% of advice and PII cases refuse as specified.
- **Length:** Answers stay ≤ 3 sentences (excluding citation + last-updated line).
- **Latency:** Good enough for a local demo (no SLA).

## 12. Open questions

1. If Groww HTML is JS-heavy, do we snapshot static text at ingest time vs live fetch each run?
2. “Official factsheet” links: allow **citing** a factsheet URL without indexing it?
3. Which Mistral model (e.g. small vs larger) for cost vs quality?

---

*This PRD is for a RAG learning prototype, not a regulated investment-advice product.*
