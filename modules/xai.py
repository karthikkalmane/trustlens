"""
Explainable AI (XAI) Module
Generates a human-readable product brief explaining the risk assessment.
"""


def generate_explanation(result):
    """
    Takes the full analysis result dict and returns:
    - verdict: one-line verdict
    - summary: 2-3 sentence explanation
    - key_factors: list of main risk/trust drivers
    - recommendation: actionable advice
    """
    risk_pct = result.get("risk_percent", 0)
    risk_label = result.get("risk_label", "Unknown")
    features = result.get("features", {})
    sentiment = result.get("sentiment_score", 0)
    pos_r = result.get("positive_ratio", 0)
    neg_r = result.get("negative_ratio", 0)
    discount = result.get("discount_percent", 0)
    review_count = result.get("review_count", 0)
    avg_rating = result.get("avg_rating", 0)
    seller_name = result.get("seller_name", "")
    bot_data = result.get("bot_detection", {})
    spam_score = bot_data.get("spam_score", 0)
    product_name = result.get("product_name", "This product")

    key_factors = []
    positives = []
    negatives = []

    # ── Price Analysis ───────────────────────────────────────────────
    price_dev = features.get("price_deviation", 0)
    disc_risk = features.get("discount_risk", 0)

    if discount > 80:
        negatives.append(f"The discount of {discount}% is unusually high and raises authenticity concerns.")
    elif discount > 50:
        negatives.append(f"A {discount}% discount is higher than typical for this category — worth verifying.")
    elif 10 <= discount <= 50:
        positives.append(f"The discount of {discount}% is within a reasonable range.")

    if price_dev > 0.5:
        negatives.append("The selling price appears significantly below typical market levels.")
    elif price_dev < 0.2:
        positives.append("The pricing appears consistent with market norms.")

    # ── Review Analysis ──────────────────────────────────────────────
    if review_count >= 500:
        positives.append(f"Strong review volume ({review_count:,} reviews) provides good data reliability.")
    elif review_count >= 50:
        positives.append(f"Moderate review count ({review_count:,}) available for analysis.")
    elif review_count < 10:
        negatives.append(f"Very few reviews ({review_count}) — authenticity is harder to verify.")

    if avg_rating >= 4.3:
        positives.append(f"Average rating of {avg_rating}/5 is strong.")
    elif avg_rating >= 4.9 and review_count > 200:
        negatives.append("A perfect 5.0 rating across many reviews can be a red flag for manipulation.")
    elif avg_rating < 3.0 and avg_rating > 0:
        negatives.append(f"Below-average rating of {avg_rating}/5 suggests customer dissatisfaction.")

    # ── Sentiment Analysis ───────────────────────────────────────────
    if pos_r > 0.6:
        positives.append("Review sentiment is predominantly positive.")
    elif neg_r > 0.4:
        negatives.append(f"A significant portion of reviews ({int(neg_r*100)}%) express negative sentiment.")
    elif neg_r > 0.25:
        negatives.append("Noticeable negative sentiment detected in customer reviews.")

    suspicious_kw = features.get("suspicious_keyword_count", 0)
    if suspicious_kw > 3:
        negatives.append(f"Multiple red-flag keywords (e.g., 'fake', 'duplicate', 'fraud') found in reviews.")
    elif suspicious_kw == 0:
        positives.append("No suspicious keywords detected in customer reviews.")

    # ── Bot Detection ────────────────────────────────────────────────
    if spam_score > 0.5:
        negatives.append(f"Review bot analysis suggests possible review manipulation ({bot_data.get('label', '')}).")
    elif spam_score < 0.25:
        positives.append("Reviews appear genuine with no major manipulation patterns.")

    # ── Seller Analysis ──────────────────────────────────────────────
    seller_risk = features.get("seller_risk", 0)
    if seller_risk < 0.2:
        positives.append("Seller credibility indicators look acceptable.")
    elif seller_risk > 0.5:
        negatives.append("Seller credibility indicators raise concerns.")

    # ── Compile summary ──────────────────────────────────────────────
    if risk_label == "Low Risk":
        verdict = f"✅ {product_name[:50]} appears to be a legitimate listing."
        summary_parts = ["The overall analysis indicates this is likely a genuine product."]
        if positives:
            summary_parts.append(positives[0])
        if len(positives) > 1:
            summary_parts.append(positives[1])
        recommendation = "This product shows low risk indicators. You can proceed with reasonable confidence, but always verify the seller and check return policies before purchasing."
    elif risk_label == "Moderate Risk":
        verdict = f"⚠️ {product_name[:50]} shows some risk indicators — proceed with caution."
        summary_parts = ["The analysis flagged several moderate concerns about this listing."]
        if negatives:
            summary_parts.append(negatives[0])
        if positives:
            summary_parts.append(f"On the positive side: {positives[0].lower()}")
        recommendation = "Exercise caution. Check seller reviews independently, verify the brand's official website, and prefer cash-on-delivery or secure payment methods for this purchase."
    else:
        verdict = f"🚨 {product_name[:50]} shows HIGH risk of being fake or suspicious."
        summary_parts = ["Multiple strong risk signals were detected in this product listing."]
        if negatives:
            summary_parts.append(negatives[0])
        if len(negatives) > 1:
            summary_parts.append(negatives[1])
        recommendation = "We strongly advise against purchasing this product without further verification. Consider buying directly from the brand's official website or a trusted retailer. This listing shows multiple characteristics of counterfeit or fraudulent products."

    # Key factors
    all_factors = negatives[:3] + positives[:2]
    key_factors = all_factors[:4] if all_factors else ["Insufficient data for detailed analysis."]

    return {
        "verdict": verdict,
        "summary": " ".join(summary_parts),
        "key_factors": key_factors,
        "recommendation": recommendation,
        "positives": positives[:4],
        "negatives": negatives[:4],
    }
