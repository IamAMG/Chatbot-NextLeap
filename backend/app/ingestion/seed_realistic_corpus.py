"""Baseline Indian SIP investor corpus (~40 high-signal posts) so the app works out-of-the-box.

Covers the 4 behavioral triggers plus noise rows (spam / generic) to exercise
Stage 2 cleaning. All rows are synthetic, first-person Hinglish/English narratives.
"""

from __future__ import annotations

from typing import List, Dict, Any

ROWS: List[Dict[str, Any]] = [
    # ---- Trigger 1: Anxiety on negative portfolio returns ----
    {
        "source": "Reddit", "title": "Groww SIP negative returns anxiety",
        "content": "I started a Rs 3000 monthly SIP in Groww direct mutual fund 8 months ago but my portfolio is showing negative returns I am anxious should I pause my SIP or continue investing",
        "author": "investor_in", "date": "2025-11-10", "votes": 45,
        "url": "https://www.reddit.com/r/MutualfundsIndia/comments/example1",
    },
    {
        "source": "Reddit", "title": "Groww portfolio down worried",
        "content": "My Groww SIP portfolio is down 12 percent since I started I am worried about negative returns and thinking of stopping the mandate",
        "author": "sip_user", "date": "2025-10-22", "votes": 32,
        "url": "https://www.reddit.com/r/IndiaInvestments/comments/example2",
    },
    {
        "source": "Reddit", "title": "ELSS losses anxious",
        "content": "I started SIP in ELSS fund via Groww but seeing losses in red I am anxious and scared to continue the autopay",
        "author": "mf_beginner", "date": "2025-09-15", "votes": 28,
        "url": "https://www.reddit.com/r/personalfinanceindia/comments/example3",
    },
    {
        "source": "Reddit", "title": "Negative returns panic redeem",
        "content": "Portfolio showing negative returns since I started my mutual fund SIP I am panicking should I redeem or stay invested",
        "author": "worried_investor", "date": "2025-11-01", "votes": 51,
        "url": "https://www.reddit.com/r/MutualfundsIndia/comments/example4",
    },
    {
        "source": "Reddit", "title": "SIP loss pause installment",
        "content": "My mutual fund SIP on Groww is in loss I am worried about negative returns and want to pause the installment",
        "author": "new_sip", "date": "2025-10-05", "votes": 19,
        "url": "https://www.reddit.com/r/IndiaInvestments/comments/example5",
    },
    {
        "source": "YouTube", "title": "Groww SIP review 2025",
        "content": "I started my SIP on Groww but the portfolio is showing negative returns and I am anxious about losing money",
        "author": "viewer_1", "date": "2025-10-12", "votes": 11,
        "url": "https://www.youtube.com/watch?v=abc1",
    },
    # ---- Trigger 2: Cash-flow crunch / salary date mismatch ----
    {
        "source": "Reddit", "title": "SIP date vs salary date mismatch",
        "content": "My salary comes on the 5th but Groww SIP autopay deducts on the 1st causing cash-flow crunch and failed NACH mandate",
        "author": "salaried", "date": "2025-11-05", "votes": 41,
        "url": "https://www.reddit.com/r/personalfinanceindia/comments/example6",
    },
    {
        "source": "Reddit", "title": "Change SIP date salary mismatch",
        "content": "I want to change my SIP date because salary date mismatch causes insufficient funds and UPI mandate failure on Groww",
        "author": "emp", "date": "2025-10-18", "votes": 33,
        "url": "https://www.reddit.com/r/MutualfundsIndia/comments/example7",
    },
    {
        "source": "Reddit", "title": "Cash crunch SIP debit before salary",
        "content": "Monthly SIP debit hits before my salary is credited causing cash crunch I want to pause the mandate temporarily",
        "author": "cash_strapped", "date": "2025-09-30", "votes": 27,
        "url": "https://www.reddit.com/r/IndiaInvestments/comments/example8",
    },
    {
        "source": "Reddit", "title": "NACH failing salary after SIP",
        "content": "NACH mandate keeps failing because salary date is after SIP debit date on Groww I need to shift the date",
        "author": "nach_user", "date": "2025-11-12", "votes": 22,
        "url": "https://www.reddit.com/r/personalfinanceindia/comments/example9",
    },
    {
        "source": "Reddit", "title": "Cash-flow crunch auto-debit date",
        "content": "Cash-flow crunch every month since my SIP auto-debit date does not match my salary credit date",
        "author": "monthly_sip", "date": "2025-10-02", "votes": 16,
        "url": "https://www.reddit.com/r/MutualfundsIndia/comments/example10",
    },
    {
        "source": "YouTube", "title": "Groww SIP mandate problem",
        "content": "My salary is credited after the SIP debit date so I face cash-flow crunch every month on Groww autopay",
        "author": "viewer_2", "date": "2025-09-25", "votes": 8,
        "url": "https://www.youtube.com/watch?v=abc2",
    },
    # ---- Trigger 3: Information overload / confusion about CAGR vs absolute returns ----
    {
        "source": "Reddit", "title": "CAGR vs absolute returns confused",
        "content": "I am confused about CAGR versus absolute returns on my Groww mutual fund SIP there is too much information overload",
        "author": "confused", "date": "2025-11-08", "votes": 38,
        "url": "https://www.reddit.com/r/MutualfundsIndia/comments/example11",
    },
    {
        "source": "Reddit", "title": "Which return metric matters",
        "content": "Does CAGR or absolute return matter more for my SIP I am overwhelmed by conflicting advice on Groww",
        "author": "learner", "date": "2025-10-11", "votes": 29,
        "url": "https://www.reddit.com/r/IndiaInvestments/comments/example12",
    },
    {
        "source": "Reddit", "title": "XIRR CAGR information overload",
        "content": "Information overload about XIRR CAGR absolute returns I cannot tell if my mutual fund SIP is performing well",
        "author": "metrics", "date": "2025-09-20", "votes": 24,
        "url": "https://www.reddit.com/r/personalfinanceindia/comments/example13",
    },
    {
        "source": "Reddit", "title": "CAGR vs absolute which to track",
        "content": "I am confused by CAGR vs absolute returns shown on Groww SIP dashboard which one should I track",
        "author": "tracker", "date": "2025-10-25", "votes": 17,
        "url": "https://www.reddit.com/r/MutualfundsIndia/comments/example14",
    },
    {
        "source": "Reddit", "title": "Too many return metrics confused",
        "content": "Too many metrics XIRR CAGR absolute return annualized return I am confused about my SIP performance",
        "author": "metrics2", "date": "2025-11-03", "votes": 21,
        "url": "https://www.reddit.com/r/IndiaInvestments/comments/example15",
    },
    {
        "source": "YouTube", "title": "Mutual fund returns explained",
        "content": "I am confused whether CAGR or absolute return shows real profit on my Groww SIP there is information overload",
        "author": "viewer_3", "date": "2025-10-08", "votes": 9,
        "url": "https://www.youtube.com/watch?v=abc3",
    },
    # ---- Trigger 4: App friction / autodebit (NACH/UPI mandate) failures ----
    {
        "source": "Reddit", "title": "NACH mandate failing Groww",
        "content": "Groww app autodebit NACH mandate keeps failing and my SIP installment is not getting invested",
        "author": "nach_fail", "date": "2025-11-06", "votes": 44,
        "url": "https://www.reddit.com/r/MutualfundsIndia/comments/example16",
    },
    {
        "source": "Reddit", "title": "UPI mandate failed SIP paused",
        "content": "UPI mandate failed multiple times on Groww my SIP is paused because autodebit is not working",
        "author": "upi_user", "date": "2025-10-14", "votes": 36,
        "url": "https://www.reddit.com/r/IndiaInvestments/comments/example17",
    },
    {
        "source": "Reddit", "title": "App friction autodebit not working",
        "content": "App friction the Groww app keeps failing to deduct my SIP amount via NACH and autopay",
        "author": "app_issue", "date": "2025-09-28", "votes": 30,
        "url": "https://www.reddit.com/r/personalfinanceindia/comments/example18",
    },
    {
        "source": "Reddit", "title": "Mandate not active unable to invest",
        "content": "My Groww SIP mandate is not active autodebit keeps failing I am unable to invest monthly",
        "author": "invest", "date": "2025-10-30", "votes": 25,
        "url": "https://www.reddit.com/r/IndiaInvestments/comments/example19",
    },
    {
        "source": "Reddit", "title": "NACH UPI mandate failure installment skipped",
        "content": "NACH UPI mandate failure on Groww app my SIP installment got skipped due to app friction",
        "author": "skip", "date": "2025-11-09", "votes": 18,
        "url": "https://www.reddit.com/r/MutualfundsIndia/comments/example20",
    },
    {
        "source": "YouTube", "title": "Groww SIP autodebit problem",
        "content": "My Groww SIP autodebit keeps failing via NACH mandate and the app does not retry the installment",
        "author": "viewer_4", "date": "2025-10-03", "votes": 7,
        "url": "https://www.youtube.com/watch?v=abc4",
    },
    # ---- Additional clean narratives (mix of triggers, incl. Hinglish) ----
    {
        "source": "Reddit", "title": "First SIP nervous volatility",
        "content": "I started my first SIP of Rs 500 per month in Groww direct mutual fund and I am nervous about market volatility",
        "author": "first_timer", "date": "2025-10-20", "votes": 14,
        "url": "https://www.reddit.com/r/MutualfundsIndia/comments/example21",
    },
    {
        "source": "Reddit", "title": "Hinglish SIP pause kya karun",
        "content": "Maine Groww par SIP shuru kiya hai but portfolio red hai kya main pause kar doon",
        "author": "hinglish_user", "date": "2025-11-02", "votes": 33,
        "url": "https://www.reddit.com/r/personalfinanceindia/comments/example22",
    },
    {
        "source": "Reddit", "title": "Mera SIP negative returns anxiety",
        "content": "Mera SIP Rs 1000 per month hai Groww par returns negative de rahe hain anxiety ho rahi hai",
        "author": "hinglish2", "date": "2025-09-18", "votes": 26,
        "url": "https://www.reddit.com/r/IndiaInvestments/comments/example23",
    },
    {
        "source": "Reddit", "title": "Direct vs regular plan confused",
        "content": "I want to start SIP but confused whether to choose direct or regular plan on Groww app",
        "author": "planner", "date": "2025-10-07", "votes": 12,
        "url": "https://www.reddit.com/r/MutualfundsIndia/comments/example24",
    },
    {
        "source": "Reddit", "title": "Autodebit failed installment skipped no retry",
        "content": "My SIP installment of Rs 2000 was skipped because Groww app autodebit failed and no retry",
        "author": "skipped", "date": "2025-11-11", "votes": 20,
        "url": "https://www.reddit.com/r/IndiaInvestments/comments/example25",
    },
    {
        "source": "Reddit", "title": "Salary 7th SIP 1st cash crunch NACH",
        "content": "Salary comes on 7th SIP deducts on 1st cash crunch every month Groww NACH mandate issue",
        "author": "salary7", "date": "2025-09-25", "votes": 31,
        "url": "https://www.reddit.com/r/personalfinanceindia/comments/example26",
    },
    {
        "source": "Reddit", "title": "CAGR vs absolute return real profit",
        "content": "CAGR vs absolute return which one shows real profit on my Groww mutual fund SIP I am confused",
        "author": "realprofit", "date": "2025-10-16", "votes": 23,
        "url": "https://www.reddit.com/r/MutualfundsIndia/comments/example27",
    },
    {
        "source": "Reddit", "title": "Paused SIP negative returns restart",
        "content": "I paused my SIP due to negative returns but now market is up should I restart the mandate",
        "author": "pauser", "date": "2025-11-04", "votes": 19,
        "url": "https://www.reddit.com/r/IndiaInvestments/comments/example28",
    },
    {
        "source": "Reddit", "title": "UPI mandate expired investment stuck",
        "content": "Groww SIP UPI mandate expired I am unable to renew and my monthly investment is stuck",
        "author": "expired", "date": "2025-09-10", "votes": 15,
        "url": "https://www.reddit.com/r/MutualfundsIndia/comments/example29",
    },
    {
        "source": "Reddit", "title": "Information overload options cannot decide",
        "content": "Information overload too many mutual fund options on Groww I cannot decide which SIP to start",
        "author": "options", "date": "2025-10-28", "votes": 11,
        "url": "https://www.reddit.com/r/personalfinanceindia/comments/example30",
    },
    # ---- Noise rows (to exercise Stage 2 filtering) ----
    {
        "source": "Google Play", "title": "Groww",
        "content": "Good app", "author": "user_a", "date": "2025-10-01", "votes": 2,
        "url": "https://play.google.com/store/apps/details?id=com.nextbillion.groww",
    },
    {
        "source": "App Store", "title": "Groww",
        "content": "OTP not coming", "author": "user_b", "date": "2025-10-02", "votes": 1,
        "url": "https://apps.apple.com/in/app/groww",
    },
    {
        "source": "YouTube", "title": "Groww SIP full video",
        "content": "Nice video Radhe Radhe", "author": "viewer_5", "date": "2025-09-30", "votes": 0,
        "url": "https://www.youtube.com/watch?v=abc5",
    },
    {
        "source": "TradingQ&A", "title": "Referral group",
        "content": "Join my Telegram group for referral code and earn cashback",
        "author": "spammer", "date": "2025-10-05", "votes": 0,
        "url": "https://tradingqna.com/t/example-spam/1",
    },
    {
        "source": "TradingQ&A", "title": "Promo",
        "content": "Use promo code GROWW50 for discount", "author": "promo_bot", "date": "2025-10-06", "votes": 0,
        "url": "https://tradingqna.com/t/example-promo/2",
    },
    {
        "source": "Google Play", "title": "Groww",
        "content": "Great app superb best", "author": "user_c", "date": "2025-10-07", "votes": 3,
        "url": "https://play.google.com/store/apps/details?id=com.nextbillion.groww",
    },
    {
        "source": "TradingQ&A", "title": "Free tips",
        "content": "WhatsApp me for free tips", "author": "tips_bot", "date": "2025-10-08", "votes": 0,
        "url": "https://tradingqna.com/t/example-tips/3",
    },
    {
        "source": "App Store", "title": "Groww",
        "content": "Login issue not working", "author": "user_d", "date": "2025-10-09", "votes": 0,
        "url": "https://apps.apple.com/in/app/groww",
    },
    {
        "source": "Google Play", "title": "Groww",
        "content": "Bad app worst", "author": "user_e", "date": "2025-10-10", "votes": 0,
        "url": "https://play.google.com/store/apps/details?id=com.nextbillion.groww",
    },
    {
        "source": "TradingQ&A", "title": "Coupon",
        "content": "Download app now coupon code", "author": "coupon_bot", "date": "2025-10-11", "votes": 0,
        "url": "https://tradingqna.com/t/example-coupon/4",
    },
]
