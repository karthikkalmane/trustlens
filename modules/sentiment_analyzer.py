"""
Sentiment Analysis Module — works without external NLP models
Uses pattern-based scoring as fallback if VADER is unavailable.
"""

import re
from collections import Counter

# Try VADER; fall back to simple lexicon
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    _vader = SentimentIntensityAnalyzer()
    USE_VADER = True
except ImportError:
    USE_VADER = False

# ─── Lexicons ─────────────────────────────────────────────────────────
POS_WORDS = [
    "excellent", "amazing", "great", "good", "wonderful", "fantastic",
    "perfect", "awesome", "love", "happy", "satisfied", "recommend",
    "quality", "original", "genuine", "authentic", "best", "superb",
    "brilliant", "nice", "beautiful", "fast", "quick", "worth",
    "value", "helpful", "pleased", "impressed", "outstanding"
]

NEG_WORDS = [
    "bad", "terrible", "horrible", "worst", "poor", "awful", "fake",
    "fraud", "scam", "cheat", "duplicate", "copy", "replica", "low quality",
    "disappointed", "waste", "broken", "damaged", "not original", "defective",
    "refund", "return", "lost", "missing", "wrong", "pathetic", "useless",
    "never", "don't buy", "avoid", "beware", "regret", "misleading"
]

SUSPICIOUS_KEYWORDS = [
    "fake", "duplicate", "copy", "replica", "not original", "not genuine",
    "low quality", "poor quality", "waste of money", "fraud", "cheated",
    "scam", "damaged", "broken", "not as described", "misleading",
    "counterfeit", "disappointed", "terrible", "horrible", "very bad",
    "worst product", "pathetic", "beware", "don't buy", "avoid",
    "refund denied", "no refund", "lost money", "stop selling"
]

AUTHENTIC_KEYWORDS = [
    "original", "genuine", "authentic", "best quality", "excellent quality",
    "highly recommend", "great value", "worth it", "totally satisfied",
    "amazing product", "perfect condition", "superb", "fantastic",
    "quick delivery", "well packed", "as described", "good build"
]


def clean_text(text):
    text = re.sub(r"http\S+|www\.\S+", "", text)
    text = re.sub(r"[^a-zA-Z\s'.,!?]", " ", text)
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


def simple_sentiment(text):
    """Lexicon-based compound score -1 to 1."""
    pos = sum(1 for w in POS_WORDS if w in text)
    neg = sum(1 for w in NEG_WORDS if w in text)
    total = pos + neg
    if total == 0:
        return 0.0
    return round((pos - neg) / total, 3)


def analyze_reviews(reviews):
    if not reviews:
        return {
            "sentiment_score": 0.0,
            "positive_ratio": 0.0,
            "negative_ratio": 0.0,
            "neutral_ratio": 0.0,
            "suspicious_keyword_count": 0,
            "authentic_keyword_count": 0,
            "avg_review_length": 0,
            "review_count_analyzed": 0,
            "keyword_risk_score": 0.0,
            "sentiment_details": [],
        }

    scores = []
    suspicious_count = 0
    authentic_count = 0
    lengths = []
    details = []

    for review in reviews:
        cleaned = clean_text(review)
        lengths.append(len(review.split()))

        if USE_VADER:
            vs = _vader.polarity_scores(cleaned)
            compound = vs["compound"]
        else:
            compound = simple_sentiment(cleaned)

        scores.append(compound)

        label = ("positive" if compound >= 0.05
                 else "negative" if compound <= -0.05
                 else "neutral")

        s_hits = [kw for kw in SUSPICIOUS_KEYWORDS if kw in cleaned]
        a_hits = [kw for kw in AUTHENTIC_KEYWORDS if kw in cleaned]
        suspicious_count += len(s_hits)
        authentic_count += len(a_hits)

        details.append({
            "text": review[:150] + ("…" if len(review) > 150 else ""),
            "compound": round(compound, 3),
            "label": label,
            "suspicious_words": s_hits[:3],
        })

    avg = sum(scores) / len(scores) if scores else 0
    pos_r = sum(1 for s in scores if s >= 0.05) / len(scores)
    neg_r = sum(1 for s in scores if s <= -0.05) / len(scores)
    neu_r = 1 - pos_r - neg_r

    kw_risk = min(1.0, suspicious_count / (len(reviews) * 2 + 1))

    return {
        "sentiment_score": round(avg, 4),
        "positive_ratio": round(pos_r, 4),
        "negative_ratio": round(neg_r, 4),
        "neutral_ratio": round(max(0, neu_r), 4),
        "suspicious_keyword_count": suspicious_count,
        "authentic_keyword_count": authentic_count,
        "avg_review_length": round(sum(lengths) / len(lengths), 1) if lengths else 0,
        "review_count_analyzed": len(reviews),
        "keyword_risk_score": round(kw_risk, 4),
        "sentiment_details": details[:10],
    }
