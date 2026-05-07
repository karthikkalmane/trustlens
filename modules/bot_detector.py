"""
Review Bot / Spam Detection Module
Detects:
- Repeated phrases across reviews
- Suspiciously short reviews
- Duplicate reviews
- Burst patterns
- Generic/template review patterns
"""

import re
from collections import Counter


# Phrases that bots/incentivised reviewers often use
BOT_PHRASE_PATTERNS = [
    r"good product",
    r"nice product",
    r"very good",
    r"best product",
    r"5 star",
    r"fast delivery",
    r"on time delivery",
    r"as expected",
    r"as described",
    r"highly recommend",
    r"value for money",
    r"worth (it|the price|buying)",
    r"(good|great) quality",
    r"(happy|satisfied) with (the |this )?(purchase|product|order)",
]


def _normalize(text):
    """Lowercase, remove punctuation, collapse spaces."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def detect_spam(reviews):
    """
    Analyzes a list of review strings and returns spam indicators.
    """
    if not reviews or len(reviews) < 2:
        return {
            "spam_score": 0.0,
            "duplicate_ratio": 0.0,
            "short_review_ratio": 0.0,
            "repeated_phrase_ratio": 0.0,
            "bot_phrase_count": 0,
            "avg_word_count": 0,
            "flags": [],
            "label": "Insufficient Data",
        }

    normalized = [_normalize(r) for r in reviews]
    flags = []
    score = 0.0

    # ── 1. Duplicate / near-duplicate detection ────────────────────────
    seen = Counter(normalized)
    duplicates = sum(v - 1 for v in seen.values() if v > 1)
    dup_ratio = round(duplicates / len(reviews), 3)
    if dup_ratio > 0.2:
        flags.append(f"High duplicate reviews ({int(dup_ratio*100)}%)")
        score += 0.3

    # ── 2. Short review ratio ──────────────────────────────────────────
    word_counts = [len(r.split()) for r in reviews]
    avg_wc = round(sum(word_counts) / len(word_counts), 1)
    short = sum(1 for wc in word_counts if wc <= 4)
    short_ratio = round(short / len(reviews), 3)
    if short_ratio > 0.4:
        flags.append(f"Many very short reviews ({int(short_ratio*100)}%)")
        score += 0.25
    elif avg_wc < 8:
        flags.append("Average review length is suspiciously short")
        score += 0.15

    # ── 3. Repeated phrases ────────────────────────────────────────────
    phrase_counts = Counter()
    for norm in normalized:
        # Extract 3-gram phrases
        words = norm.split()
        for i in range(len(words) - 2):
            phrase = " ".join(words[i:i+3])
            phrase_counts[phrase] += 1

    repeated_phrases = {p: c for p, c in phrase_counts.items() if c >= max(2, len(reviews) * 0.25)}
    rep_ratio = round(len(repeated_phrases) / max(len(phrase_counts), 1), 3)
    if repeated_phrases:
        top = sorted(repeated_phrases, key=lambda x: -repeated_phrases[x])[:3]
        flags.append(f"Repeated phrases detected: {', '.join(repr(p) for p in top)}")
        score += min(0.3, rep_ratio * 2)

    # ── 4. Bot template phrases ────────────────────────────────────────
    bot_hits = 0
    for norm in normalized:
        for pattern in BOT_PHRASE_PATTERNS:
            if re.search(pattern, norm):
                bot_hits += 1
                break  # count once per review

    bot_ratio = round(bot_hits / len(reviews), 3)
    if bot_ratio > 0.5:
        flags.append(f"High frequency of generic template phrases ({int(bot_ratio*100)}%)")
        score += 0.2
    elif bot_ratio > 0.3:
        flags.append(f"Moderate template phrases detected ({int(bot_ratio*100)}%)")
        score += 0.1

    # ── 5. Uniform rating burst ────────────────────────────────────────
    # If all reviews are suspiciously positive without detail
    very_positive = sum(1 for n in normalized
                        if any(w in n for w in ["excellent", "amazing", "perfect", "fantastic", "superb"]))
    if very_positive / len(reviews) > 0.7 and avg_wc < 12:
        flags.append("Excessive praise with low detail — possible review manipulation")
        score += 0.2

    score = min(1.0, score)

    if score < 0.25:
        label = "Likely Genuine"
    elif score < 0.5:
        label = "Possibly Manipulated"
    elif score < 0.75:
        label = "Likely Bot/Spam"
    else:
        label = "High Bot Activity"

    return {
        "spam_score": round(score, 3),
        "duplicate_ratio": dup_ratio,
        "short_review_ratio": short_ratio,
        "repeated_phrase_ratio": rep_ratio,
        "bot_phrase_count": bot_hits,
        "avg_word_count": avg_wc,
        "flags": flags,
        "label": label,
        "total_reviews": len(reviews),
    }
