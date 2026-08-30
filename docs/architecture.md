# Architecture: HDFC Mutual Fund FAQ Assistant (RAG Prototype)

| Field | Value |
| --- | --- |
| Status | Prototype |
| Source of truth | `docs/PRD.md` only |
| Date | 30 Aug 2026 |

This document describes a **local, single-process** RAG prototype. It does not add stacks, services, or corpus beyond the PRD.

---

## Repository layout

Artifacts live under `data/`. Pipeline and UI live under `src/`. Docs stay in `docs/`. No extra services.

```
ChatBot-NL/
├── docs/
│   ├── PRD.md
│   └── architecture.md
├── data/                          # generated artifacts only (not source)
│   ├── raw/                       # Phase 1 — page snapshots
│   ├── chunks/                    # Phase 2 — section chunks
│   ├── embeddings/                # Phase 3 — MiniLM vectors (sidecar)
│   └── vectordb/                  # Phase 4 — ChromaDB persist
└── src/                           # code only
    ├── loading/                   # Phase 1 — fetch 5 URLs → data/raw
    ├── chunking/                  # Phase 2 — raw → data/chunks
    ├── embedding/                 # Phase 3 — chunks → data/embeddings
    ├── store/                     # Phase 4 — embeddings → data/vectordb
    ├── retrieval/                 # Phase 5 — guardrails, k-NN, Mistral
    ├── ui/                        # Streamlit (PRD F9)
    └── retrieval_testing/         # Phase 6 — PRD §10 / §11
```

| Path | Phase | Contents |
| --- | --- | --- |
| `data/raw/` | 1 | One snapshot per allowlisted URL: `text`, `source_url`, `fund_name`, `ingest_ts`. No blogs, no factsheet bodies. |
| `data/chunks/` | 2 | Chunks with `chunk_id`, `text`, `source_url`, `fund_name`, `ingest_ts`. No cross-URL merge. |
| `data/embeddings/` | 3 | Vectors from `sentence-transformers/all-MiniLM-L6-v2` aligned to `chunk_id`. Query-time embeds are not stored. |
| `data/vectordb/` | 4 | ChromaDB collection (embedding + text + `source_url` + `fund_name` + `ingest_ts`). Rebuild on re-ingest (P1). |
| `src/loading/` | 1 | Load allowlist only. |
| `src/chunking/` | 2 | Section-sized chunks. |
| `src/embedding/` | 3 | Same MiniLM for ingest and query. |
| `src/store/` | 4 | ChromaDB read/write. |
| `src/retrieval/` | 5 | Guardrails before retrieve; F4 weak path; generate contract. |
| `src/ui/` | 5.3 | Welcome, 3 examples, “Facts-only. No investment advice.” |
| `src/retrieval_testing/` | 6 | Edge cases 1–10; citation / grounding / no PII writes. |

**Rules:** do not write user questions, PAN, Aadhaar, OTPs, emails, or phones into `data/`. Factsheet URLs are never files under `data/`.

---

## System view (PRD pipeline)

```
Ingest (once / on re-ingest P1)
  5 Groww URLs → fetch text → chunk → MiniLM embed → ChromaDB
                                                    (source_url, fund, ingest_ts)

Query
  Streamlit
       │
       ▼
  Guardrails (PII, advice, returns-compare, empty, out-of-corpus)
       │  refuse → 1 allowed URL + polite message (no retrieve / no store PII)
       ▼
  Query embed (same MiniLM) → k-NN ChromaDB
       │  empty / weak → say so + closest allowed page or refuse
       ▼
  Prompt (facts from chunks only, ≤3 sentences, 1 citation)
       ▼
  Mistral API → answer + citation URL + "Last updated from sources: <ingest_ts>"
```

**Runtime:** Streamlit UI + Python ingest/retrieve/generate. **LLM:** Mistral API key. **Embeddings:** `sentence-transformers/all-MiniLM-L6-v2`. **Store:** ChromaDB.

**Hard corpus (index these URLs only):**

| Fund | source_url |
| --- | --- |
| HDFC Large Cap Fund Direct Growth | https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth |
| HDFC Flexi Cap Fund Direct Growth | https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth |
| HDFC ELSS Tax Saver Fund Direct Plan Growth | https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth |
| HDFC Small Cap Fund Direct Growth | https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth |
| HDFC Balanced Advantage Fund Direct Growth | https://groww.in/mutual-funds/hdfc-balanced-advantage-fund-direct-growth |

Do **not** crawl factsheets, blogs, or other funds into the store. A factsheet may appear as a **link in the answer** only (PRD F7).

---

## Phase 1 — Data loading

**Purpose:** Load public text for the five URLs into a structured document list. Nothing else enters the pipeline.

**In**

- Fixed allowlist of five Groww URLs (table above).
- Optional P1: Streamlit re-ingest that re-runs this phase and refreshes last-updated.

**Out (per page)**

| Field | Rule |
| --- | --- |
| `source_url` | Exact allowlisted URL |
| `fund_name` / `category` | From PRD corpus table |
| `text` | Visible page text used for FAQ facts (expense ratio, SIP, exit load, lock-in, riskometer, benchmark, capital-gains statement copy if present) |
| `ingest_ts` | Timestamp used later as “Last updated from sources:” |

**Rules**

- Fetch **only** those five pages. No linked pages, no third-party blogs, no app-backend screenshots.
- If a page fetch fails, that URL is missing from the corpus; do not substitute another site.
- PRD open question (JS-heavy Groww HTML): **ingest-time snapshot** of extracted text. Query path does not live-crawl. Re-ingest (P1) refreshes the snapshot and `ingest_ts`.
- Do not persist user messages, PAN, Aadhaar, accounts, OTPs, emails, or phones (none of that belongs in this phase).

**Done when:** five documents (or fewer if a fetch failed, with that failure visible) exist with URL + text + `ingest_ts`.

---

## Phase 2 — Chunking

**Purpose:** Split each loaded page so retrieval can hit typical fund-page **sections**, not an entire HTML dump.

**In:** documents from Phase 1.

**Out:** chunks with:

| Field | Rule |
| --- | --- |
| `chunk_id` | Stable id |
| `text` | One chunk |
| `source_url` | Parent page (citation candidate) |
| `fund_name` | Parent fund |
| `ingest_ts` | Copied from parent |

**Rules (PRD: “Fit typical fund-page sections”)**

- Prefer section-sized chunks around: expense ratio, minimum SIP, exit load, riskometer, benchmark, ELSS lock-in, capital-gains statement instructions.
- Keep `source_url` on every chunk so the answer path can emit **exactly one** citation URL (the page of the chosen chunk / majority of retrieved chunks).
- Do not merge text across different URLs.
- Do not add commentary or computed returns into chunks.

**Done when:** every loaded page has ≥1 chunk; every chunk traces to one allowlisted URL.

---

## Phase 3 — Embedding

**Purpose:** Turn chunk text (and later queries) into vectors with the **same** model.

**Model (fixed):** Hugging Face `sentence-transformers/all-MiniLM-L6-v2`.

**Ingest path:** embed each chunk’s `text`.

**Query path:** embed the user question with the **same** model (PRD F2, F3). No second embedding model.

**Rules**

- Do not embed PII; PII queries never reach this phase (guardrail before retrieve).
- Do not embed URLs outside the allowlist.

**Done when:** each chunk has a vector from MiniLM; query encoder is the same class of model/weights.

---

## Phase 4 — Vector store

**Purpose:** Persist chunk vectors + metadata for k-NN at query time.

**Store (fixed):** ChromaDB.

**Collection contents**

| Stored | Why (PRD) |
| --- | --- |
| Embedding | Retrieval |
| `text` | LLM context (facts from corpus only) |
| `source_url` | Single citation (F5) |
| `fund_name` | P1: show which fund matched |
| `ingest_ts` | “Last updated from sources:” |

**Rules**

- One collection for this prototype. Index **only** chunks from the five URLs.
- No user chat, no PII, no factsheet bodies, no blogs.
- Re-ingest (P1): replace or rebuild this collection so citations and timestamps stay consistent with the new snapshot.

**Done when:** ChromaDB holds the current chunk set and can return nearest neighbours with metadata.

---

## Phase 5 — Retrieval logic

**Purpose:** Given a question that passed guardrails, return grounded context or a controlled weak-retrieval outcome. Generation is specified here only as the PRD requires it after retrieve.

### 5.1 Pre-retrieve guardrails (do not retrieve)

Run **before** query embed. On match: **no ChromaDB write**, no PII logging.

| Check | Behaviour (PRD) |
| --- | --- |
| PAN / Aadhaar / account / OTP / email / phone | Refuse; do not store (F8, edge 8) |
| Empty / gibberish | Ask to rephrase; no fund facts invented (edge 9) |
| Buy / sell / switch / “should I” / portfolio allocation | Polite facts-only refusal + **one** educational or matching fund URL from the allowlist (F6, edge 5) |
| Best fund / compare / compute returns | Do not compute or rank; **link-only** to official factsheet **without** indexing it (F7, edge 6) |
| Fund not in the five URLs | Out of scope; do not invent (edge 7) |
| Ambiguous “expense ratio?” and no fund | Ask which of the five, **or** retrieve only if uniquely determined (edge 10) |

### 5.2 Retrieve

1. Embed question (Phase 3).
2. k-NN in ChromaDB (Phase 4).
3. **Empty or weak retrieval (F4):** say retrieval is insufficient; cite the **closest allowlisted page** if one exists, or refuse. Do not fill gaps from the LLM’s prior knowledge.
4. **Strong retrieval:** pass chunk `text` + `source_url` + `ingest_ts` to the prompt.

**Citation:** exactly **one** URL — the Groww page used (typically the top chunk’s `source_url`). Must be one of the five allowlisted URLs.

### 5.3 Generate (after retrieve)

- **LLM:** Mistral API.
- **Context:** retrieved chunks only.
- **Output contract:** ≤3 sentences; no advice; no performance math; no PII echo; one citation URL; line `Last updated from sources: <ingest_ts>`.
- Streamlit (F9): welcome + three example questions + persistent “Facts-only. No investment advice.” Groww-inspired green / white / dark text. P1: show matched fund; in-session chat only.

**Done when:** every allowed question path either (a) answers from chunks with one citation + timestamp, or (b) refuses / weak-retrieves per PRD.

---

## Phase 6 — Retrieval testing

**Purpose:** Prove ingest → retrieve (and guardrails) against PRD §10 and §11. This is **F10**, not a production eval platform.

### 6.1 What to test

| Layer | Assertion |
| --- | --- |
| Store | Only five `source_url` values exist in ChromaDB |
| Retrieve (facts) | Named-fund expense ratio / ELSS lock-in / SIP / exit load / riskometer / benchmark return chunks from the **correct** URL |
| Weak retrieve | Empty/weak path does not invent; closest allowed page or refuse |
| Citation | 100% of generated answers include **one** allowlisted URL |
| Guardrails | Advice, returns-compare, PII, unknown fund, empty/gibberish, ambiguous fund — as PRD §10 |
| Grounding (spot-check) | ≥80% of P0 factual asks match the ingested page |
| Length | ≤3 sentences excluding citation + last-updated |

### 6.2 Cases (map 1:1 to PRD §10)

1. Expense ratio of a named in-corpus fund → fact + that fund’s URL + last-updated.  
2. ELSS lock-in → lock-in fact from ELSS page + ELSS URL.  
3. Minimum SIP / exit load / riskometer / benchmark → fact + citation.  
4. How to download capital-gains statement → steps if in chunks; else “not on this page” + citation.  
5. Should I buy/sell/switch → refusal + one allowlisted educational/fund link; **no retrieve-to-advise**.  
6. Best fund / compare 3Y returns → no computed comparison; factsheet link only / refuse ranking.  
7. Fund outside the five URLs → out of scope.  
8. PAN / phone / OTP → refuse; store unchanged.  
9. Empty / gibberish → rephrase; no hallucinated data.  
10. “Expense ratio?” with no fund → clarify or retrieve only if unique.

### 6.3 How (prototype)

- Script or checklist over a frozen ingest snapshot so retrieve tests are repeatable.
- For retrieve-quality cases: assert top-k `source_url` / section, not only the LLM string.
- For guardrail cases: assert **no** ChromaDB mutation and no PII in logs.
- Latency: “good enough for a local demo”; no SLA.

**Done when:** the ten edge cases pass on the current snapshot and citation / refuse / grounding checks in PRD §11 hold for that run.

---

## Out of scope (do not architect)

Anything PRD §3 / non-goals: production hardening, auth, extra funds/pages, blogs in the index, return calculators, PII stores, multi-turn memory beyond one in-session question, extra embedding models, extra vector DBs.

P1 (matched fund label, re-ingest button, in-session history) may be added **inside** the phases above; they are not new systems.

---

*Architecture bound to `docs/PRD.md`. No requirements added.*
