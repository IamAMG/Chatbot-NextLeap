# Groww SIP Behavioral Discovery Engine — AI Evidence Log & Golden Dataset

**Project:** ChatBot-NL / Groww SIP Discovery Engine  
**File:** `backend/app/golden_dataset.py`  
**Endpoint:** `GET /api/evidence-log`  
**Golden Test:** `POST /api/evidence-log/run-golden-test`

---

## Overview

The discovery engine pipeline: **ingest → triage → LLM tag → synthesis**

Every golden row has expected values for:
- `behavioral_trigger`
- `sentiment_label`
- `segment_proxy_ticket`
- `retention_dropoff_bucket`
- `opportunity score band`

Evidence categories:
- `data_gathering` — does the pipeline ingest + clean from multiple sources?
- `theme_identification` — are the 4 behavioral triggers correctly assigned?
- `insight_generation` — are opportunity scores + interventions produced?
- `insight_validation` — does the engine reproduce expected tags on golden rows?

---

## Behavioral Triggers (4)

| # | Trigger |
|---|---------|
| T1 | Anxiety on negative portfolio returns |
| T2 | Cash-flow crunch / salary date mismatch |
| T3 | Information overload / confusion about CAGR vs absolute returns |
| T4 | App friction / autodebit (NACH/UPI mandate) failures |

---

## Golden Dataset Rows (17)

| ID | Source | Title | Content | Trigger | Sentiment | Segment | Drop-off | Opportunity | Category | Noise |
|----|--------|-------|---------|---------|-----------|---------|----------|-------------|----------|-------|
| GD-001 | Reddit | Groww SIP negative returns anxiety | I started a Rs 3000 monthly SIP in Groww direct mutual fund 8 months ago but my portfolio is showing negative returns I am anxious should I pause my SIP or continue investing | Anxiety on negative portfolio returns | Negative | Rs.500 - Rs.2,000/mo | Months 6-8 | 70-95 | theme_identification | No |
| GD-002 | Reddit | Groww portfolio down worried | My Groww SIP portfolio is down 12 percent since I started I am worried about negative returns and thinking of stopping the mandate | Anxiety on negative portfolio returns | Critical | Rs.2,500 - Rs.10,000/mo | Months 1-3 | 75-98 | theme_identification | No |
| GD-003 | YouTube | Groww SIP review 2025 | I started my SIP on Groww but the portfolio is showing negative returns and I am anxious about losing money | Anxiety on negative portfolio returns | Negative | Rs.500 - Rs.2,000/mo | Months 10-12 | 65-90 | data_gathering | No |
| GD-004 | Reddit | SIP date vs salary date mismatch | My salary comes on the 5th but Groww SIP autopay deducts on the 1st causing cash-flow crunch and failed NACH mandate | Cash-flow crunch / salary date mismatch | Negative | Rs.2,500 - Rs.10,000/mo | Months 1-3 | 70-95 | theme_identification | No |
| GD-005 | Reddit | NACH failing salary after SIP | NACH mandate keeps failing because salary date is after SIP debit date on Groww I need to shift the date | Cash-flow crunch / salary date mismatch | Critical | Rs.500 - Rs.2,000/mo | Months 6-8 | 75-98 | theme_identification | No |
| GD-006 | YouTube | Groww SIP mandate problem | My salary comes after the SIP debit date so I face cash-flow crunch every month on Groww autopay | Cash-flow crunch / salary date mismatch | Negative | Rs.500 - Rs.2,000/mo | Months 10-12 | 65-90 | data_gathering | No |
| GD-007 | Reddit | CAGR vs absolute returns confused | I am confused about CAGR versus absolute returns on my Groww mutual fund SIP there is too much information overload | Information overload / confusion about CAGR vs absolute returns | Neutral | Rs.500 - Rs.2,000/mo | Months 10-12 | 60-85 | theme_identification | No |
| GD-008 | Reddit | XIRR CAGR information overload | Information overload about XIRR CAGR absolute returns I cannot tell if my mutual fund SIP is performing well | Information overload / confusion about CAGR vs absolute returns | Negative | Rs.2,500 - Rs.10,000/mo | Months 6-8 | 65-90 | theme_identification | No |
| GD-009 | YouTube | Mutual fund returns explained | I am confused whether CAGR or absolute return shows real profit on my Groww SIP there is information overload | Information overload / confusion about CAGR vs absolute returns | Neutral | Rs.500 - Rs.2,000/mo | Months 10-12 | 60-85 | data_gathering | No |
| GD-010 | Reddit | NACH mandate failing Groww | Groww app autodebit NACH mandate keeps failing and my SIP installment is not getting invested | App friction / autodebit (NACH/UPI mandate) failures | Critical | Rs.500 - Rs.2,000/mo | Months 1-3 | 75-98 | theme_identification | No |
| GD-011 | Reddit | UPI mandate failed SIP paused | UPI mandate failed multiple times on Groww my SIP is paused because autodebit is not working | App friction / autodebit (NACH/UPI mandate) failures | Critical | Rs.2,500 - Rs.10,000/mo | Months 6-8 | 75-98 | theme_identification | No |
| GD-012 | YouTube | Groww SIP autodebit problem | My Groww SIP autodebit keeps failing via NACH mandate and the app does not retry the installment | App friction / autodebit (NACH/UPI mandate) failures | Negative | Rs.500 - Rs.2,000/mo | Months 1-3 | 70-95 | data_gathering | No |
| GD-013 | Reddit | Hinglish SIP pause kya karun | Maine Groww par SIP shuru kiya hai but portfolio red hai kya main pause kar doon | Anxiety on negative portfolio returns | Negative | Rs.500 - Rs.2,000/mo | Months 1-3 | 70-95 | theme_identification | No |
| GD-014 | Reddit | Mera SIP negative returns anxiety | Mera SIP Rs 1000 per month hai Groww par returns negative de rahe hain anxiety ho rahi hai | Anxiety on negative portfolio returns | Critical | Rs.500 - Rs.2,000/mo | Months 6-8 | 75-98 | theme_identification | No |
| GD-015 | Google Play | Groww | Good app | None | None | None | None | 0-0 | insight_validation | Yes |
| GD-016 | TradingQ&A | Referral group | Join my Telegram group for referral code and earn cashback | None | None | None | None | 0-0 | insight_validation | Yes |
| GD-017 | App Store | Groww | OTP not coming | None | None | None | None | 0-0 | insight_validation | Yes |

**Summary:** 14 signal rows (11 English + 3 Hinglish) + 3 noise rows.

---

## AI Evidence Log Questions (Mentor-Testable, Q-01 → Q-10)

### Category: Data Gathering & Analysis

**Q-01** — Does the discovery engine gather SIP investor feedback from at least 4 distinct sources (Reddit, YouTube, Play Store, App Store, TradingQ&A)?
- **Expected:** Yes — ingest endpoint pulls from 8 connectors; rows carry source, title, author, date, votes, url.
- **Test:** Call `GET /api/sync_status` and confirm `clean_count > 0` across multiple sources; call `GET /api/rows` grouped by source.

**Q-02** — Are raw rows cleaned (HTML/URL/emoji stripped), language-filtered (en/hinglish/hi), and near-duplicate deduplicated before analysis?
- **Expected:** Yes — refinement pipeline normalizes text, allows only en/hinglish/hi, dedupes cross-source.
- **Test:** Call `POST /api/ingest` and check refinement counts (in/out/dropped_dup/dropped_language).

### Category: Theme Identification

**Q-03** — Are the 4 behavioral triggers correctly identified (Anxiety on negative returns, Cash-flow crunch, Information overload, App friction/NACH failures)?
- **Expected:** Yes — every clean row is tagged with exactly one of the 4 triggers via LLM or deterministic fallback.
- **Test:** Run golden test `POST /api/evidence-log/run-golden-test`; verify trigger match rate >= 80%.

**Q-04** — Does the engine correctly handle Hinglish (code-mixed Hindi/English) investor narratives?
- **Expected:** Yes — language detector allows hinglish; deterministic tagger and LLM tag Hinglish rows into correct triggers.
- **Test:** Golden rows GD-013/GD-014 must map to 'Anxiety on negative portfolio returns'.

### Category: Insight Generation

**Q-05** — Are opportunity scores (0-100) generated per behavioral cluster using frequency, emotional intensity, and early drop-off?
- **Expected:** Yes — synthesis.py computes composite score = 0.35*freq + 0.35*intensity + 0.30*early_dropoff.
- **Test:** Call `GET /api/opportunity`; each cluster must have `opportunity_score` between 0 and 100.

**Q-06** — Does each cluster produce a recommended product intervention and verbatim investor quotes?
- **Expected:** Yes — synthesis returns `recommended_intervention` + `quotes` per cluster.
- **Test:** Call `GET /api/opportunity`; verify every cluster has non-empty `recommended_intervention` and `quotes` array.

### Category: Insight Validation

**Q-07** — Does the golden dataset test reproduce expected behavioral triggers on known SIP investor posts?
- **Expected:** Yes — running the pipeline on golden rows yields tags matching expected values for >= 80% of rows.
- **Test:** `POST /api/evidence-log/run-golden-test`; check `pass_rate >= 0.80`.

**Q-08** — Are noise/spam rows (generic app reviews, referral promos) correctly filtered out and never tagged as behavioral triggers?
- **Expected:** Yes — Stage 2 triage marks them as `FILTERED_SPAM_PROMO` / `FILTERED_NON_SIP`; they are excluded from synthesis.
- **Test:** Golden rows GD-015/GD-016/GD-017 must have `cleaning_status != CLEAN_SIP_SIGNAL`.

**Q-09** — Is the 12-month retention drop-off distribution (Months 1-3 / 6-8 / 10-12) computed per cluster?
- **Expected:** Yes — synthesis aggregates `retention_dropoff_bucket` into 3 windows with percentages summing to ~100.
- **Test:** Call `GET /api/opportunity`; verify `months_1_to_3_pct + months_6_to_8_pct + months_10_to_12_pct ≈ 100` for each cluster.

**Q-10** — Is the pipeline deterministic and reproducible (zero-token fallback when no LLM keys are configured)?
- **Expected:** Yes — `deterministic_tag` runs without any LLM API keys and produces consistent tags.
- **Test:** Run `POST /api/pipeline/analyze` with no LLM keys; rows must still be tagged via deterministic fallback.

---

## Categories

| ID | Name | Description |
|----|------|-------------|
| data_gathering | Data Gathering & Analysis | How the workflow gathers raw SIP investor feedback and analyzes/cleans it before tagging. |
| theme_identification | Theme Identification | How the 4 behavioral triggers are identified from cleaned investor narratives. |
| insight_generation | Insight Generation | How opportunity scores, interventions, quotes, and drop-off distributions are generated per theme. |
| insight_validation | Insight Validation | How insight quality is validated against the golden dataset (expected vs actual tags). |

---

## Running the Golden Test

```bash
curl -X POST http://localhost:8000/api/evidence-log/run-golden-test
```

Returns per-row pass/fail results plus aggregate pass rate by category. Threshold: `pass_rate >= 0.80`.

---

## Source Location

- `backend/app/golden_dataset.py` — dataset + questions
- `backend/app/main.py:457` — `/api/evidence-log` endpoint
- `backend/app/main.py:467` — `/api/evidence-log/run-golden-test` endpoint
- `backend/app/db/models.py:8` — `discovery_engine.db` (evidence DB)
- `backend/app/ingestion/` — 8 source connectors (Reddit, YouTube, Play Store, App Store, TradingQ&A + more)
- `backend/app/refinement/` — cleaning + dedup pipeline
- `backend/app/triage/` — Stage 2 signal vs noise filter
- `backend/app/llm/` — deterministic + LLM tagging
- `backend/app/synthesis.py` — opportunity scoring + interventions
