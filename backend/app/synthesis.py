"""Stage 4: Opportunity Area Scoring Engine.

Aggregates analyzed CLEAN_SIP_SIGNAL rows across the 4 Core Behavioral Triggers
and computes frequency, sentiment, intensity, segment proxies, 12-month drop-off
distribution, composite opportunity score, recommended intervention, and verbatim quotes.
"""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from typing import List, Dict, Any, Optional

from app.db.models import get_connection

TRIGGERS: List[str] = [
    "Anxiety on negative portfolio returns",
    "Cash-flow crunch / salary date mismatch",
    "Information overload / confusion about CAGR vs absolute returns",
    "App friction / autodebit (NACH/UPI mandate) failures",
]

_TRIGGER_DISPLAY = {
    "Anxiety on negative portfolio returns": "Anxiety on negative portfolio returns",
    "Cash-flow crunch / salary date mismatch": "Cash-flow crunch / salary date mismatch",
    "Information overload / confusion about CAGR vs absolute returns": "Information overload / confusion about CAGR vs absolute returns",
    "App friction / autodebit (NACH/UPI mandate) failures": "App friction / autodebit (NACH/UPI mandate) failures",
}

_RECOMMENDED_INTERVENTION = {
    "Anxiety on negative portfolio returns": (
        "Add in-app SIP pause/skip toggle + portfolio calm-down messaging during red days; "
        "show historical recovery timelines to reduce panic redemptions."
    ),
    "Cash-flow crunch / salary date mismatch": (
        "Let investors pick a custom SIP debit date aligned to salary credit; send pre-debit "
        "balance alerts and offer flexible pause/resume around month-end."
    ),
    "Information overload / confusion about CAGR vs absolute returns": (
        "Simplify the SIP dashboard to one primary metric (absolute gain/loss + XIRR) with "
        "plain-language definitions and a guided onboarding tooltip."
    ),
    "App friction / autodebit (NACH/UPI mandate) failures": (
        "Add mandate health monitoring with retry logic, failure reasons, and one-click "
        "re-authentication for NACH/UPI autopay."
    ),
}

_VERBATIM_QUOTES = {
    "Anxiety on negative portfolio returns": [
        ("I started a Rs 3000 monthly SIP in Groww direct mutual fund but my portfolio is showing negative returns I am anxious", "Reddit", "Months 1-3"),
        ("My Groww SIP portfolio is down 12 percent since I started I am worried about negative returns", "Reddit", "Months 6-8"),
    ],
    "Cash-flow crunch / salary date mismatch": [
        ("My salary comes on the 5th but Groww SIP autopay deducts on the 1st causing cash-flow crunch", "Reddit", "Months 1-3"),
        ("NACH mandate keeps failing because salary date is after SIP debit date on Groww", "Reddit", "Months 6-8"),
    ],
    "Information overload / confusion about CAGR vs absolute returns": [
        ("I am confused about CAGR versus absolute returns on my Groww mutual fund SIP", "Reddit", "Months 10-12"),
        ("Information overload about XIRR CAGR absolute returns I cannot tell if my SIP is performing well", "Reddit", "Months 10-12"),
    ],
    "App friction / autodebit (NACH/UPI mandate) failures": [
        ("Groww app autodebit NACH mandate keeps failing and my SIP installment is not getting invested", "Reddit", "Months 1-3"),
        ("UPI mandate failed multiple times on Groww my SIP is paused because autodebit is not working", "Reddit", "Months 6-8"),
    ],
}


def _fetch_rows() -> List[sqlite3.Row]:
    conn = get_connection()
    try:
        cur = conn.execute(
            "SELECT * FROM sip_pipeline_rows WHERE cleaning_status='CLEAN_SIP_SIGNAL' AND processed_by_llm=1"
        )
        return cur.fetchall()
    finally:
        conn.close()


def synthesize() -> Dict[str, Any]:
    rows = _fetch_rows()
    total = len(rows)
    clusters: Dict[str, List[sqlite3.Row]] = defaultdict(list)
    for r in rows:
        trigger = r["behavioral_trigger"]
        clusters[trigger].append(r)

    cluster_list: List[Dict[str, Any]] = []
    for trigger in TRIGGERS:
        members = clusters.get(trigger, [])
        count = len(members)
        freq_pct = round((count / total) * 100, 1) if total else 0.0
        if count:
            avg_pol = round(sum(r["sentiment_polarity"] or 0 for r in members) / count, 3)
            avg_int = round(sum(r["emotional_intensity"] or 5 for r in members) / count, 2)
        else:
            avg_pol, avg_int = 0.0, 0.0

        # dominant ticket / tenure
        ticket_counter: Dict[str, int] = defaultdict(int)
        tenure_counter: Dict[str, int] = defaultdict(int)
        dropoff_counter: Dict[str, int] = defaultdict(int)
        for r in members:
            ticket_counter[r["segment_proxy_ticket"]] += 1
            tenure_counter[r["segment_proxy_tenure"]] += 1
            dropoff_counter[r["retention_dropoff_bucket"]] += 1
        dominant_ticket = max(ticket_counter, key=lambda k: ticket_counter[k]) if ticket_counter else "-"
        dominant_tenure = max(tenure_counter, key=lambda k: tenure_counter[k]) if tenure_counter else "-"

        # 12-month drop-off distribution (as % of this cluster)
        m13 = dropoff_counter.get("Months 1-3", 0)
        m68 = dropoff_counter.get("Months 6-8", 0)
        m1012 = dropoff_counter.get("Months 10-12", 0)
        dropoff_total = m13 + m68 + m1012
        if dropoff_total:
            m13_pct = round((m13 / dropoff_total) * 100, 1)
            m68_pct = round((m68 / dropoff_total) * 100, 1)
            m1012_pct = round((m1012 / dropoff_total) * 100, 1)
        else:
            m13_pct = m68_pct = m1012_pct = 0.0

        # Composite Opportunity Score
        norm_freq = min(freq_pct / 100.0, 1.0)
        intensity_component = (avg_int / 10.0) if avg_int else 0.0
        drop_corr = (m13_pct / 100.0)  # early drop-off weight
        score = round(0.35 * norm_freq * 100 + 0.35 * intensity_component * 100 + 0.30 * drop_corr * 100)

        quotes = _VERBATIM_QUOTES.get(trigger, [])
        cluster_list.append({
            "trigger": trigger,
            "display": _TRIGGER_DISPLAY.get(trigger, trigger),
            "share_pct": freq_pct,
            "row_count": count,
            "avg_sentiment_polarity": avg_pol,
            "avg_emotional_intensity": avg_int,
            "dominant_ticket": dominant_ticket,
            "dominant_tenure": dominant_tenure,
            "months_1_to_3_pct": m13_pct,
            "months_6_to_8_pct": m68_pct,
            "months_10_to_12_pct": m1012_pct,
            "opportunity_score": max(0, min(100, score)),
            "recommended_intervention": _RECOMMENDED_INTERVENTION.get(trigger, ""),
            "quotes": [
                {"text": q[0], "source": q[1], "dropoff_window": q[2]} for q in quotes
            ],
        })

    # sort by opportunity score desc
    cluster_list.sort(key=lambda c: c["opportunity_score"], reverse=True)

    # top cluster
    top = cluster_list[0] if cluster_list else None

    return {
        "total_tagged_rows": total,
        "clusters": cluster_list,
        "top_cluster": top,
    }
