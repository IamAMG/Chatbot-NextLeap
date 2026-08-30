# ChatBot-NL — HDFC Mutual Fund FAQ Assistant (RAG Prototype)

A **facts-only FAQ chatbot** over five HDFC Direct Growth mutual-fund pages on
Groww, built to test a full RAG pipeline: ingest → chunk → embed → vector
store → retrieve → generate.

> Educational RAG prototype. **Not investment advice.**

## Scope

Answers only factual queries about these five funds (one allowlisted URL each):

| Category | Scheme |
| --- | --- |
| Large-cap | HDFC Large Cap Fund Direct Growth |
| Flexi-cap | HDFC Flexi Cap Fund Direct Growth |
| ELSS | HDFC ELSS Tax Saver Fund Direct Plan Growth |
| Small-cap | HDFC Small Cap Fund Direct Growth |
| Hybrid | HDFC Balanced Advantage Fund Direct Growth |

See `docs/PRD.md` and `docs/architecture.md` for full requirements.

## Pipeline

```
[5 Groww URLs] -> fetch -> chunk -> MiniLM embeddings -> ChromaDB (data/vectordb)
                                                                     ^
User question -> guardrails -> embed (same MiniLM) -> k-NN retrieve -|
                                                                     v
                                       Mistral API -> answer + citation
```

| Stage | Module | Choice |
| --- | --- | --- |
| Data loading | `src/loading/` | 5 allowlisted Groww URLs → `data/raw/` |
| Chunking | `src/chunking/` | facts block + prose sections → `data/chunks/` |
| Embedding | `src/embedding/` | `sentence-transformers/all-MiniLM-L6-v2` → `data/embeddings/` |
| Vector store | `src/store/` | ChromaDB → `data/vectordb/` |
| Retrieval | `src/retrieval/` | guardrails, k-NN, Mistral prompt |
| UI | `src/ui/app.py` | Streamlit (Groww palette) |
| Testing | `src/retrieval_testing/` | edge cases (PRD §10) via pytest |

## Requirements

- Python 3.10+
- A **Mistral API key** for answer generation
- (Optional) Hugging Face token to avoid hub download rate limits

Install:

```bash
pip install -r requirements.txt
```

Create `.env` (copy from `.env.example`) and set your key:

```
MISTRAL_API_KEY=your_key_here
```

## Run

**1. Ingest (one-time or re-ingest to refresh):**

```bash
python -m src.loading
python -m src.chunking
python -m src.embedding
python -m src.store
```

**2. Backend CLI:**

```bash
python -m src.retrieval "What is the expense ratio of HDFC Large Cap?"
```

**3. Frontend UI:**

```bash
streamlit run src/ui/app.py
# open http://localhost:8501
```

## Guardrails

- **Facts only** – no investment advice, no buy/sell recommendations.
- **No returns** – never computes, compares, or ranks returns; links to the
  fund factsheet instead.
- **No PII** – rejects PAN, Aadhaar, account, OTP, email, phone numbers and
  stores nothing.
- **Hard corpus** – only indexes the five allowlisted URLs.
- Answers are ≤3 sentences with one citation and a last-updated line.

## Tests

```bash
python -m pytest src/retrieval_testing -q
```

## Project status

Prototype / hobby RAG test. See `docs/PRD.md` for non-goals and edge cases.
