import os, json, secrets
from flask import (Flask, render_template, request, jsonify,
                   redirect, url_for, session, flash)
from werkzeug.security import check_password_hash
from functools import wraps

from config import Config
from database import db
from modules.scraper import validate_url, scrape_product
from modules.sentiment_analyzer import analyze_reviews
from modules.price_analyzer import analyze_price_seller
from modules.risk_evaluator import evaluate_risk
from modules.bot_detector import detect_spam
from modules.xai import generate_explanation
from modules.price_history import get_price_history

app = Flask(__name__)
app.config.from_object(Config)
GUEST_COUNT_CACHE = {}

with app.app_context():
    db.init_db()


# ─── Auth Helpers ─────────────────────────────────────────────────────
def current_user():
    uid = session.get("user_id")
    if uid:
        return db.get_user_by_id(uid)
    return None

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to access this page.", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def get_or_create_guest_key():
    if "guest_key" not in session:
        session["guest_key"] = secrets.token_hex(16)
    return session["guest_key"]


# ─── Context Processor ────────────────────────────────────────────────
@app.context_processor
def inject_user():
    return {"current_user": current_user()}


# ─── Auth Routes ──────────────────────────────────────────────────────
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if session.get("user_id"):
        return redirect(url_for("index"))
    if request.method == "POST":
        username = request.form.get("username","").strip()
        email    = request.form.get("email","").strip()
        password = request.form.get("password","").strip()
        confirm  = request.form.get("confirm","").strip()
        if not all([username, email, password, confirm]):
            flash("All fields are required.", "error")
        elif password != confirm:
            flash("Passwords do not match.", "error")
        elif len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
        else:
            ok, msg, user = db.create_user(username, email, password)
            if ok:
                session["user_id"] = user["id"]
                session["username"] = user["username"]
                flash(f"Welcome, {username}! Your account has been created.", "success")
                return redirect(url_for("index"))
            else:
                flash(msg, "error")
    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("index"))
    if request.method == "POST":
        email    = request.form.get("email","").strip()
        password = request.form.get("password","").strip()
        user = db.verify_password(email, password)
        if user:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            flash(f"Welcome back, {user['username']}!", "success")
            return redirect(url_for("index"))
        else:
            flash("Invalid email or password.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You've been logged out.", "info")
    return redirect(url_for("index"))


# ─── Main Routes ──────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    url = request.form.get("url","").strip()
    if not url:
        return render_template("index.html", error="Please enter a product URL.")

    # ── Access Control ───────────────────────────────────────────────
    user = current_user()
    guest_key = get_or_create_guest_key()

    if not user:
        count = GUEST_COUNT_CACHE.get(guest_key)
        if count is None:
            count = db.get_guest_count(guest_key)
            GUEST_COUNT_CACHE[guest_key] = count
        if count >= 1:
            return render_template("index.html",
                error="Guest users can only analyze 1 product. Please log in or sign up for unlimited access.",
                submitted_url=url,
                show_login_prompt=True)

    # ── Validate URL ─────────────────────────────────────────────────
    valid, msg = validate_url(url)
    if not valid:
        return render_template("index.html", error=msg, submitted_url=url)

    try:
        # Step 1: Scrape
        scraped = scrape_product(url)

        # Step 2: Sentiment
        sentiment = analyze_reviews(scraped.get("reviews", []))

        # Step 3: Features
        features = analyze_price_seller(scraped, sentiment)

        # Step 4: Bot Detection
        bot_data = detect_spam(scraped.get("reviews", []))

        # Step 5: Risk Score
        risk = evaluate_risk(features, bot_score=bot_data.get("spam_score", 0))

        # Step 6: Price History
        price_hist = get_price_history(
            url, scraped.get("platform",""),
            scraped.get("product_name",""),
            scraped.get("price", 0)
        )

        result = {
            "url": url,
            "product_name": scraped.get("product_name","Unknown"),
            "platform":     scraped.get("platform","").capitalize(),
            "price":        scraped.get("price",0),
            "mrp":          scraped.get("mrp",0),
            "discount_percent": scraped.get("discount_percent",0),
            "avg_rating":   scraped.get("avg_rating",0),
            "review_count": scraped.get("review_count",0),
            "seller_name":  scraped.get("seller_name","Unknown"),
            "seller_rating":scraped.get("seller_rating",0),
            "trust_signals":scraped.get("trust_signals",{}),

            "risk_score":   risk["risk_score"],
            "risk_percent": risk["risk_percent"],
            "risk_label":   risk["risk_label"],
            "risk_color":   risk["risk_color"],
            "method":       risk["method"],
            "indicator_scores": risk["indicator_scores"],

            "sentiment_score":  sentiment["sentiment_score"],
            "positive_ratio":   round(sentiment["positive_ratio"]*100,1),
            "negative_ratio":   round(sentiment["negative_ratio"]*100,1),
            "neutral_ratio":    round(sentiment["neutral_ratio"]*100,1),
            "suspicious_keyword_count": sentiment["suspicious_keyword_count"],
            "sentiment_details": sentiment["sentiment_details"],
            "review_count_analyzed": sentiment["review_count_analyzed"],

            "bot_detection": bot_data,
            "price_history": price_hist,
            "features":  features,
        }

        # Step 7: XAI explanation
        result["explanation"] = generate_explanation(result)

        # Save to DB
        uid = user["id"] if user else None
        result["record_id"] = db.save_analysis(url, result, uid)

        # Increment counters
        if user:
            db.increment_user_count(user["id"])
        else:
            db.increment_guest_count(guest_key)
            GUEST_COUNT_CACHE[guest_key] = GUEST_COUNT_CACHE.get(guest_key, 0) + 1

        # Logged-in users see full result; guests see limited
        result["is_guest"] = not bool(user)
        return render_template("result.html", result=result)

    except Exception as e:
        err = str(e)
        if "NOT_PRODUCT_PAGE" in err:
            msg = err.replace("NOT_PRODUCT_PAGE: ", "")
        else:
            msg = f"Analysis failed: {err}"
        return render_template("index.html", error=msg, submitted_url=url)


# ─── History ──────────────────────────────────────────────────────────
@app.route("/history")
@login_required
def history():
    user = current_user()
    records = db.get_user_history(user["id"])
    return render_template("history.html", records=records)


@app.route("/history/delete/<int:rid>", methods=["POST"])
@login_required
def delete_record(rid):
    user = current_user()
    db.delete_record(rid, user["id"])
    return redirect(url_for("history"))


# ─── API ──────────────────────────────────────────────────────────────
@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    data = request.get_json()
    url = (data or {}).get("url","").strip()
    if not url:
        return jsonify({"error":"URL required"}), 400
    valid, msg = validate_url(url)
    if not valid:
        return jsonify({"error":msg}), 400
    try:
        scraped  = scrape_product(url)
        sent     = analyze_reviews(scraped.get("reviews",[]))
        features = analyze_price_seller(scraped, sent)
        bot      = detect_spam(scraped.get("reviews",[]))
        risk     = evaluate_risk(features, bot.get("spam_score",0))
        return jsonify({"product": scraped.get("product_name"),
                        "risk_percent": risk["risk_percent"],
                        "risk_label":   risk["risk_label"]})
    except Exception as e:
        return jsonify({"error":str(e)}), 500


if __name__ == "__main__":
    app.run(debug=Config.DEBUG, port=5000)
