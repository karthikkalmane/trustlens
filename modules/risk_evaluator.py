import os, numpy as np
try:
    import joblib
    JOBLIB_OK = True
except ImportError:
    JOBLIB_OK = False
from config import Config

FEATURES = [
    "price_deviation","discount_risk","seller_risk","review_count_risk",
    "rating_risk","sentiment_score","positive_ratio","negative_ratio",
    "keyword_risk_score","suspicious_keyword_count","avg_review_length",
    "discount_percent","avg_rating","seller_rating",
]

WEIGHTS = {
    "price_deviation":0.12,"discount_risk":0.12,"seller_risk":0.10,
    "review_count_risk":0.08,"rating_risk":0.08,"keyword_risk_score":0.15,
    "negative_ratio":0.10,"suspicious_keyword_count":0.10,"sentiment_score":0.15,
}

def _load_model():
    if not JOBLIB_OK: return None, None
    if os.path.exists(Config.MODEL_PATH) and os.path.exists(Config.SCALER_PATH):
        try:
            return joblib.load(Config.MODEL_PATH), joblib.load(Config.SCALER_PATH)
        except Exception: pass
    return None, None

MODEL, SCALER = _load_model()

def _rule_score(f):
    s = 0.0
    s += f.get("price_deviation",0)   * 0.12
    s += f.get("discount_risk",0)     * 0.12
    s += f.get("seller_risk",0)       * 0.10
    s += f.get("review_count_risk",0) * 0.08
    s += f.get("rating_risk",0)       * 0.08
    s += f.get("keyword_risk_score",0)* 0.15
    s += f.get("negative_ratio",0)    * 0.10
    s += min(f.get("suspicious_keyword_count",0),10)/10 * 0.10
    sent = f.get("sentiment_score",0)
    s += max(0, (-sent+1)/2)*0.5 * 0.15
    return min(1.0, max(0.0, s))

def evaluate_risk(features, bot_score=0.0):
    model, scaler = MODEL, SCALER
    if model and scaler:
        try:
            vec = np.array([[features.get(c,0) for c in FEATURES]])
            risk = float(model.predict_proba(scaler.transform(vec))[0][1])
            method = "ML Model (Random Forest)"
        except Exception:
            risk = _rule_score(features); method = "Rule-Based"
    else:
        risk = _rule_score(features); method = "Rule-Based (Weighted)"

    # Blend bot detection signal
    if bot_score > 0:
        risk = risk * 0.85 + bot_score * 0.15
        risk = min(1.0, risk)

    if risk < 0.35:   label, color = "Low Risk",      "#22c55e"
    elif risk < 0.65: label, color = "Moderate Risk", "#f59e0b"
    else:             label, color = "High Risk",     "#ef4444"

    indicators = {
        "Price Anomaly":      round((features.get("price_deviation",0)*0.6 + features.get("discount_risk",0)*0.4)*100),
        "Seller Credibility": round((1-features.get("seller_risk",0))*100),
        "Review Sentiment":   round((1-features.get("negative_ratio",0)-features.get("keyword_risk_score",0)*0.5)*100),
        "Review Volume":      round((1-features.get("review_count_risk",0))*100),
        "Rating Auth.":       round((1-features.get("rating_risk",0))*100),
    }
    indicators = {k: max(0, min(100, v)) for k,v in indicators.items()}

    return {
        "risk_score":  round(risk, 4),
        "risk_percent":round(risk*100, 1),
        "risk_label":  label,
        "risk_color":  color,
        "method":      method,
        "indicator_scores": indicators,
    }
