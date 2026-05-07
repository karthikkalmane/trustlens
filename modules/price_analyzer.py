SUSPICIOUS_DISCOUNT = 70
HIGH_RISK_DISCOUNT = 85
MIN_SELLER_RATING = 3.5

def compute_price_deviation(price, mrp, product_name=""):
    if price <= 0:
        return 0.4
    if mrp > 0:
        ratio = price / mrp
        if ratio < 0.1:   return 1.0
        elif ratio < 0.3: return 0.7
        elif ratio < 0.5: return 0.3
    return 0.0

def compute_discount_risk(discount):
    if discount <= 30:   return 0.0
    elif discount <= 50: return 0.1
    elif discount <= SUSPICIOUS_DISCOUNT: return 0.3
    elif discount <= HIGH_RISK_DISCOUNT:  return 0.65
    else:                return 1.0

def compute_seller_risk(seller_rating):
    if seller_rating <= 0:   return 0.4
    if seller_rating >= 4.5: return 0.0
    elif seller_rating >= 4: return 0.1
    elif seller_rating >= MIN_SELLER_RATING: return 0.3
    elif seller_rating >= 3: return 0.6
    else:                    return 0.9

def compute_review_count_risk(review_count):
    if review_count >= 500: return 0.0
    elif review_count >= 100: return 0.1
    elif review_count >= 50:  return 0.2
    elif review_count >= 5:   return 0.4
    else:                     return 0.7

def compute_rating_risk(avg_rating, review_count):
    if avg_rating <= 0: return 0.3
    if avg_rating >= 4.9 and review_count > 100: return 0.4
    elif avg_rating < 2.5: return 0.8
    elif avg_rating < 3.0: return 0.5
    elif avg_rating < 3.5: return 0.2
    return 0.0

def analyze_price_seller(scraped, sentiment):
    price    = scraped.get("price", 0)
    mrp      = scraped.get("mrp", price)
    discount = scraped.get("discount_percent", 0)
    s_rating = scraped.get("seller_rating", 0)
    r_count  = scraped.get("review_count", 0)
    avg_r    = scraped.get("avg_rating", 0)

    return {
        "price": price,
        "mrp": mrp,
        "discount_percent": discount,
        "seller_rating": s_rating,
        "review_count": r_count,
        "avg_rating": avg_r,
        "price_deviation":    compute_price_deviation(price, mrp, scraped.get("product_name","")),
        "discount_risk":      compute_discount_risk(discount),
        "seller_risk":        compute_seller_risk(s_rating),
        "review_count_risk":  compute_review_count_risk(r_count),
        "rating_risk":        compute_rating_risk(avg_r, r_count),
        "sentiment_score":    sentiment.get("sentiment_score", 0),
        "positive_ratio":     sentiment.get("positive_ratio", 0),
        "negative_ratio":     sentiment.get("negative_ratio", 0),
        "keyword_risk_score": sentiment.get("keyword_risk_score", 0),
        "suspicious_keyword_count": sentiment.get("suspicious_keyword_count", 0),
        "avg_review_length":  sentiment.get("avg_review_length", 0),
    }
