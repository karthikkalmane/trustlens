"""
TrustLens – Universal Product Scraper
Supports: Flipkart, Amazon, Meesho, Snapdeal, Myntra, Ajio,
          Tata CLiQ, Nykaa, FirstCry, Pepperfry, JioMart,
          IndiaMART, TradeIndia + any generic URL
"""

import re
import json
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from config import Config


# ─── Platform Detection ────────────────────────────────────────────────
PLATFORM_MAP = {
    "flipkart.com":   "flipkart",
    "amazon.in":      "amazon",
    "amazon.com":     "amazon",
    "meesho.com":     "meesho",
    "snapdeal.com":   "snapdeal",
    "myntra.com":     "myntra",
    "ajio.com":       "ajio",
    "tatacliq.com":   "tatacliq",
    "nykaa.com":      "nykaa",
    "firstcry.com":   "firstcry",
    "pepperfry.com":  "pepperfry",
    "jiomart.com":    "jiomart",
    "indiamart.com":  "indiamart",
    "tradeindia.com": "tradeindia",
}

def detect_platform(url):
    domain = urlparse(url).netloc.lower().replace("www.", "")
    for key, plat in PLATFORM_MAP.items():
        if key in domain:
            return plat
    return "generic"

def validate_url(url):
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False, "Invalid URL format."
        if parsed.scheme not in ("http", "https"):
            return False, "Only HTTP/HTTPS URLs are supported."
        return True, detect_platform(url)
    except Exception:
        return False, "Could not parse the URL."


# ─── HTTP Fetch ────────────────────────────────────────────────────────
def fetch_page(url, retries=2):
    for attempt in range(retries + 1):
        try:
            session = requests.Session()
            session.headers.update(Config.HEADERS)
            resp = session.get(url, timeout=Config.REQUEST_TIMEOUT, allow_redirects=True)
            resp.raise_for_status()
            return resp.text
        except requests.exceptions.Timeout:
            if attempt == retries:
                raise Exception("Page load timed out. The server took too long to respond.")
            time.sleep(1)
        except requests.exceptions.HTTPError as e:
            raise Exception(f"HTTP {e.response.status_code}: Could not access the product page.")
        except requests.exceptions.ConnectionError:
            raise Exception("Could not connect. Check your internet connection.")
    return None


# ─── JSON-LD Extractor (works across ALL platforms) ────────────────────
def extract_jsonld(soup):
    """Extract Product schema.org data embedded in the page."""
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
            items = data if isinstance(data, list) else [data]
            for item in items:
                # Handle @graph arrays
                if item.get("@type") == "ItemList":
                    continue
                if "@graph" in item:
                    for node in item["@graph"]:
                        if node.get("@type") in ("Product", "product"):
                            return node
                if item.get("@type") in ("Product", "product"):
                    return item
        except Exception:
            continue
    return {}

def parse_price_from_jsonld(ld):
    """Pull price from JSON-LD offers."""
    offers = ld.get("offers", ld.get("Offers", {}))
    if isinstance(offers, list):
        offers = offers[0] if offers else {}
    price = offers.get("price", offers.get("Price", 0))
    try:
        return float(str(price).replace(",", "").replace("₹", "").strip())
    except Exception:
        return 0


# ─── Generic Price Extractor (regex on raw HTML) ──────────────────────
PRICE_PATTERNS = [
    r'[\"\']?price[\"\']?\s*:\s*[\"\']?([\d,]+(?:\.\d+)?)[\"\']?',
    r'₹\s*([\d,]+(?:\.\d+)?)',
    r'Rs\.?\s*([\d,]+(?:\.\d+)?)',
    r'INR\s*([\d,]+(?:\.\d+)?)',
    r'selling[_\s-]?price[\"\']\s*:\s*[\"\']?([\d,]+)',
    r'discounted[_\s-]?price[\"\']\s*:\s*[\"\']?([\d,]+)',
]

def extract_price_from_html(html):
    for pattern in PRICE_PATTERNS:
        matches = re.findall(pattern, html, re.IGNORECASE)
        if matches:
            try:
                return float(matches[0].replace(",", ""))
            except Exception:
                continue
    return 0

def extract_rating_from_html(html):
    patterns = [
        r'"ratingValue"\s*:\s*"?([\d.]+)"?',
        r'"averageRating"\s*:\s*"?([\d.]+)"?',
        r'rating[\"\']\s*:\s*[\"\']?([\d.]+)',
    ]
    for p in patterns:
        m = re.search(p, html, re.IGNORECASE)
        if m:
            try:
                val = float(m.group(1))
                if 0 < val <= 5:
                    return val
            except Exception:
                continue
    return 0

def extract_review_count_from_html(html):
    patterns = [
        r'"reviewCount"\s*:\s*"?([\d,]+)"?',
        r'"ratingCount"\s*:\s*"?([\d,]+)"?',
        r'([\d,]+)\s+(?:ratings?|reviews?)',
    ]
    for p in patterns:
        m = re.search(p, html, re.IGNORECASE)
        if m:
            try:
                return int(m.group(1).replace(",", ""))
            except Exception:
                continue
    return 0


# ─── Meta Tag Helpers ─────────────────────────────────────────────────
def get_meta(soup, *names):
    for name in names:
        tag = (soup.find("meta", property=name)
               or soup.find("meta", attrs={"name": name}))
        if tag and tag.get("content"):
            return tag["content"].strip()
    return ""

def get_title(soup):
    for sel in ["h1", "h2", '[class*="title"]', '[class*="name"]', '[id*="title"]']:
        tag = soup.select_one(sel)
        if tag:
            t = tag.get_text(strip=True)
            if len(t) > 5:
                return t
    og = get_meta(soup, "og:title", "twitter:title")
    if og:
        return og
    title = soup.find("title")
    return title.get_text(strip=True) if title else "Unknown Product"


# ─── Review Extractors ────────────────────────────────────────────────
REVIEW_SELECTORS = [
    '[class*="review-text"]', '[class*="reviewText"]',
    '[class*="review_text"]', '[class*="review-body"]',
    '[class*="comment-body"]', '[class*="user-review"]',
    '[class*="t-ZTKy"]', '[class*="_2-N8zT"]',  # Flipkart
    '[class*="review-content"]', '[class*="reviewContent"]',
    '[class*="review"]', 'p.review', '.review p',
    '[itemprop="reviewBody"]', '[itemprop="description"]',
]

def extract_reviews(soup):
    reviews = []
    for sel in REVIEW_SELECTORS:
        tags = soup.select(sel)
        for tag in tags[:Config.MAX_REVIEWS]:
            text = tag.get_text(separator=" ", strip=True)
            if len(text) > 15 and text not in reviews:
                reviews.append(text)
        if len(reviews) >= 5:
            break
    return reviews[:Config.MAX_REVIEWS]


# ─── Platform-Specific Scrapers ───────────────────────────────────────

def scrape_flipkart(url, soup, html):
    data = {"platform": "flipkart", "url": url}

    # Product name — multiple fallbacks
    name = ""
    for sel in ['span.B_NuCI', 'span[class*="B_NuCI"]', 'h1[class*="yhB1nd"]',
                'h1', 'span[class*="title"]']:
        el = soup.select_one(sel)
        if el:
            name = el.get_text(strip=True)
            if len(name) > 5:
                break
    data["product_name"] = name or get_title(soup)

    # Price — JSON-LD first, then CSS, then regex
    ld = extract_jsonld(soup)
    price = parse_price_from_jsonld(ld)
    if not price:
        for sel in ['div._30jeq3', 'div[class*="_30jeq3"]', 'div[class*="price"]',
                    '._16Jk6d', 'span[class*="price"]']:
            el = soup.select_one(sel)
            if el:
                raw = re.sub(r"[^\d.]", "", el.get_text().replace(",", ""))
                if raw:
                    try:
                        price = float(raw)
                        break
                    except Exception:
                        pass
    if not price:
        price = extract_price_from_html(html)
    data["price"] = price

    # MRP
    mrp = 0
    for sel in ['div._3I9_wc', 'div[class*="_3I9_wc"]', 'div[class*="mrp"]',
                'span[class*="strike"]', 'del']:
        el = soup.select_one(sel)
        if el:
            raw = re.sub(r"[^\d.]", "", el.get_text().replace(",", ""))
            if raw:
                try:
                    mrp = float(raw)
                    break
                except Exception:
                    pass
    data["mrp"] = mrp or price

    # Discount
    discount = 0
    for sel in ['div._3Ay6Sb', 'div[class*="discount"]', 'span[class*="discount"]']:
        el = soup.select_one(sel)
        if el:
            nums = re.findall(r"\d+", el.get_text())
            if nums:
                discount = int(nums[0])
                break
    if not discount and data["mrp"] > 0 and price > 0:
        discount = max(0, round(((data["mrp"] - price) / data["mrp"]) * 100))
    data["discount_percent"] = discount

    # Rating
    rating = 0
    for sel in ['div._3LWZlK', 'div[class*="_3LWZlK"]', 'span[class*="rating"]',
                '[id*="productRating"]', 'div[class*="rate"]']:
        el = soup.select_one(sel)
        if el:
            nums = re.findall(r"[\d.]+", el.get_text())
            for n in nums:
                try:
                    v = float(n)
                    if 0 < v <= 5:
                        rating = v
                        break
                except Exception:
                    pass
            if rating:
                break
    if not rating:
        rating = extract_rating_from_html(html) or float(ld.get("aggregateRating", {}).get("ratingValue", 0))
    data["avg_rating"] = round(rating, 1)

    # Review count
    rcount = 0
    for sel in ['span._2_R_DZ', 'span[class*="_2_R_DZ"]', 'span[class*="count"]']:
        el = soup.select_one(sel)
        if el:
            nums = re.findall(r"[\d,]+", el.get_text())
            if nums:
                rcount = int(nums[0].replace(",", ""))
                break
    if not rcount:
        rcount = extract_review_count_from_html(html)
    data["review_count"] = rcount

    # Seller
    seller_name = ""
    seller_rating = 0
    for sel in ['div._3zxWtP', 'div[class*="seller"]', '[id*="seller"]']:
        el = soup.select_one(sel)
        if el:
            seller_name = el.get_text(strip=True)[:80]
            break
    data["seller_name"] = seller_name or "Flipkart Seller"
    data["seller_rating"] = seller_rating

    data["reviews"] = extract_reviews(soup)
    return data


def scrape_amazon(url, soup, html):
    data = {"platform": "amazon", "url": url}

    # Name
    name_tag = soup.find("span", id="productTitle")
    data["product_name"] = name_tag.get_text(strip=True) if name_tag else get_title(soup)

    # Price — try multiple Amazon price selectors
    price = 0
    for sel in ['span.a-price-whole', '#priceblock_ourprice',
                '#priceblock_dealprice', '.a-price .a-offscreen',
                'span[class*="price"]', '#apex_offerDisplay_desktop']:
        el = soup.select_one(sel)
        if el:
            raw = re.sub(r"[^\d.]", "", el.get_text().replace(",", ""))
            if raw:
                try:
                    price = float(raw)
                    break
                except Exception:
                    pass
    if not price:
        price = extract_price_from_html(html)
    data["price"] = price

    # MRP
    mrp = 0
    for sel in ['span.a-text-strike', 'span[data-a-strike="true"]',
                '.basisPrice .a-offscreen', 'span[class*="strike"]']:
        el = soup.select_one(sel)
        if el:
            raw = re.sub(r"[^\d.]", "", el.get_text().replace(",", ""))
            if raw:
                try:
                    mrp = float(raw)
                    break
                except Exception:
                    pass
    data["mrp"] = mrp or price

    discount = 0
    if data["mrp"] > 0 and price > 0 and data["mrp"] > price:
        discount = round(((data["mrp"] - price) / data["mrp"]) * 100)
    data["discount_percent"] = discount

    # Rating
    rating = 0
    for sel in ['span#acrPopover', 'i[data-hook="average-star-rating"]',
                'span[data-hook="rating-out-of-text"]']:
        el = soup.select_one(sel)
        if el:
            raw = el.get("title", el.get_text())
            nums = re.findall(r"[\d.]+", raw)
            for n in nums:
                try:
                    v = float(n)
                    if 0 < v <= 5:
                        rating = v
                        break
                except Exception:
                    pass
            if rating:
                break
    if not rating:
        rating = extract_rating_from_html(html)
    data["avg_rating"] = round(rating, 1)

    # Review count
    rcount = 0
    for sel in ['#acrCustomerReviewText', 'span[data-hook="total-review-count"]']:
        el = soup.select_one(sel)
        if el:
            nums = re.findall(r"[\d,]+", el.get_text())
            if nums:
                rcount = int(nums[0].replace(",", ""))
                break
    data["review_count"] = rcount or extract_review_count_from_html(html)

    # Seller
    seller = soup.find("a", id="sellerProfileTriggerId")
    data["seller_name"] = seller.get_text(strip=True) if seller else "Amazon"
    data["seller_rating"] = 0
    data["reviews"] = extract_reviews(soup)
    return data


def scrape_meesho(url, soup, html):
    data = {"platform": "meesho", "url": url}
    ld = extract_jsonld(soup)
    data["product_name"] = ld.get("name") or get_title(soup)
    price = parse_price_from_jsonld(ld) or extract_price_from_html(html)
    data["price"] = price
    data["mrp"] = price
    data["discount_percent"] = 0

    # Meesho specific
    for sel in ['h4[class*="price"]', 'p[class*="price"]', 'span[class*="price"]']:
        el = soup.select_one(sel)
        if el:
            raw = re.sub(r"[^\d.]", "", el.get_text().replace(",", ""))
            if raw:
                try:
                    data["price"] = float(raw)
                    break
                except Exception:
                    pass

    rating = float(ld.get("aggregateRating", {}).get("ratingValue", 0))
    if not rating:
        rating = extract_rating_from_html(html)
    data["avg_rating"] = round(rating, 1)
    data["review_count"] = int(ld.get("aggregateRating", {}).get("reviewCount", 0)) or extract_review_count_from_html(html)
    data["seller_name"] = "Meesho Seller"
    data["seller_rating"] = 0
    data["reviews"] = extract_reviews(soup)
    return data


def scrape_snapdeal(url, soup, html):
    data = {"platform": "snapdeal", "url": url}
    ld = extract_jsonld(soup)
    data["product_name"] = ld.get("name") or get_title(soup)

    price = 0
    for sel in ['span#selling-price-id', '.payBlkBig', 'span[class*="price"]',
                '.product-price']:
        el = soup.select_one(sel)
        if el:
            raw = re.sub(r"[^\d.]", "", el.get_text().replace(",", ""))
            if raw:
                try:
                    price = float(raw)
                    break
                except Exception:
                    pass
    if not price:
        price = parse_price_from_jsonld(ld) or extract_price_from_html(html)
    data["price"] = price

    mrp = 0
    for sel in ['.pdp-mrp', 'span[class*="mrp"]', 'del']:
        el = soup.select_one(sel)
        if el:
            raw = re.sub(r"[^\d.]", "", el.get_text().replace(",", ""))
            if raw:
                try:
                    mrp = float(raw)
                    break
                except Exception:
                    pass
    data["mrp"] = mrp or price
    if mrp and price and mrp > price:
        data["discount_percent"] = round(((mrp - price) / mrp) * 100)
    else:
        data["discount_percent"] = 0

    rating = extract_rating_from_html(html)
    data["avg_rating"] = round(rating, 1)
    data["review_count"] = extract_review_count_from_html(html)
    data["seller_name"] = "Snapdeal Seller"
    data["seller_rating"] = 0
    data["reviews"] = extract_reviews(soup)
    return data


def scrape_myntra(url, soup, html):
    data = {"platform": "myntra", "url": url}
    # Myntra is JS-heavy; try JSON-LD and meta
    ld = extract_jsonld(soup)
    data["product_name"] = ld.get("name") or get_meta(soup, "og:title") or get_title(soup)
    price = parse_price_from_jsonld(ld) or extract_price_from_html(html)
    data["price"] = price
    data["mrp"] = price
    data["discount_percent"] = 0

    # Myntra embeds data in __NEXT_DATA__ or window.__myx
    m = re.search(r'"discountedPrice"\s*:\s*(\d+)', html)
    if m:
        data["price"] = float(m.group(1))
    m2 = re.search(r'"mrp"\s*:\s*(\d+)', html)
    if m2:
        data["mrp"] = float(m2.group(1))
    if data["mrp"] and data["price"] and data["mrp"] > data["price"]:
        data["discount_percent"] = round(((data["mrp"] - data["price"]) / data["mrp"]) * 100)

    m3 = re.search(r'"overallRating"\s*:\s*"?([\d.]+)"?', html)
    data["avg_rating"] = float(m3.group(1)) if m3 else extract_rating_from_html(html)
    m4 = re.search(r'"totalCount"\s*:\s*(\d+)', html)
    data["review_count"] = int(m4.group(1)) if m4 else extract_review_count_from_html(html)
    data["seller_name"] = "Myntra"
    data["seller_rating"] = 0
    data["reviews"] = extract_reviews(soup)
    return data


def scrape_generic(url, soup, html):
    """
    Generic scraper for any URL — also used for fake website detection.
    Uses JSON-LD, Open Graph, meta tags, and regex heuristics.
    """
    platform = detect_platform(url)
    data = {"platform": platform if platform != "generic" else "Website", "url": url}

    ld = extract_jsonld(soup)

    # Product name
    name = ld.get("name", "")
    if not name:
        name = get_meta(soup, "og:title", "twitter:title", "product:title")
    if not name:
        name = get_title(soup)
    data["product_name"] = name or "Product"

    # Check if this is actually a product page
    is_product_page = bool(
        ld.get("@type") in ("Product", "product")
        or soup.find(attrs={"itemprop": "price"})
        or soup.find(attrs={"itemprop": "offers"})
        or re.search(r'(?i)(add.to.cart|buy.now|add.to.bag|shop.now)', html)
        or re.search(r'(?i)(price|₹|inr|product)', html[:3000])
    )
    data["is_product_page"] = is_product_page

    # Price
    price = parse_price_from_jsonld(ld)
    if not price:
        el = soup.find(attrs={"itemprop": "price"})
        if el:
            raw = el.get("content", el.get_text())
            try:
                price = float(re.sub(r"[^\d.]", "", raw.replace(",", "")))
            except Exception:
                price = 0
    if not price:
        price = extract_price_from_html(html)
    data["price"] = price
    data["mrp"] = price
    data["discount_percent"] = 0

    # Rating
    rating = float(ld.get("aggregateRating", {}).get("ratingValue", 0))
    if not rating:
        el = soup.find(attrs={"itemprop": "ratingValue"})
        if el:
            try:
                rating = float(el.get("content", el.get_text()).strip())
            except Exception:
                rating = 0
    if not rating:
        rating = extract_rating_from_html(html)
    data["avg_rating"] = round(rating, 1)

    # Review count
    rcount = int(ld.get("aggregateRating", {}).get("reviewCount", 0))
    if not rcount:
        rcount = extract_review_count_from_html(html)
    data["review_count"] = rcount

    data["seller_name"] = urlparse(url).netloc.replace("www.", "")
    data["seller_rating"] = 0
    data["reviews"] = extract_reviews(soup)

    # ── Fake website detection signals ────────────────────────────────
    trust_signals = _detect_trust_signals(soup, html, url)
    data["trust_signals"] = trust_signals

    return data


def _detect_trust_signals(soup, html, url):
    """Heuristics to detect potentially fake / scam websites."""
    signals = {
        "has_https": urlparse(url).scheme == "https",
        "has_contact_page": bool(re.search(r'(?i)(contact\s*us|support|help)', html)),
        "has_privacy_policy": bool(re.search(r'(?i)(privacy\s*policy|terms\s*(of\s*)?service|refund\s*policy)', html)),
        "has_about_page": bool(re.search(r'(?i)(about\s*us|who\s*we\s*are)', html)),
        "has_return_policy": bool(re.search(r'(?i)(return|refund|exchange)', html)),
        "suspicious_price": False,
        "too_good_to_be_true": False,
        "fake_urgency": bool(re.search(r'(?i)(limited\s*time|only\s*\d+\s*left|hurry|expires\s*in|deal\s*ends)', html)),
    }

    # Check for suspiciously low prices
    prices = re.findall(r'₹\s*([\d,]+)', html)
    prices_int = []
    for p in prices:
        try:
            prices_int.append(int(p.replace(",", "")))
        except Exception:
            pass
    if prices_int:
        min_price = min(prices_int)
        if min_price < 10:
            signals["suspicious_price"] = True

    # Too-good-to-be-true: 90%+ off signals
    disc = re.findall(r'(\d+)%\s*(?:off|discount)', html, re.IGNORECASE)
    if any(int(d) >= 90 for d in disc if d.isdigit()):
        signals["too_good_to_be_true"] = True

    # Trust score 0-100
    trust_score = 0
    if signals["has_https"]:           trust_score += 25
    if signals["has_contact_page"]:    trust_score += 15
    if signals["has_privacy_policy"]:  trust_score += 20
    if signals["has_about_page"]:      trust_score += 15
    if signals["has_return_policy"]:   trust_score += 15
    if not signals["suspicious_price"]:trust_score += 5
    if not signals["too_good_to_be_true"]: trust_score += 5
    signals["website_trust_score"] = trust_score

    return signals


# ─── Nykaa, Ajio, Tata CLiQ, FirstCry, Pepperfry, JioMart ────────────

def scrape_nykaa(url, soup, html):
    data = _platform_base(url, soup, html, "nykaa")
    m = re.search(r'"discountedPrice"\s*:\s*(\d+)', html)
    if m:
        data["price"] = float(m.group(1))
    m2 = re.search(r'"mrp"\s*:\s*(\d+)', html)
    if m2:
        data["mrp"] = float(m2.group(1))
    return _finalize(data)

def scrape_ajio(url, soup, html):
    data = _platform_base(url, soup, html, "ajio")
    m = re.search(r'"price"\s*:\s*(\d+(?:\.\d+)?)', html)
    if m:
        data["price"] = float(m.group(1))
    return _finalize(data)

def scrape_tatacliq(url, soup, html):
    data = _platform_base(url, soup, html, "tatacliq")
    return _finalize(data)

def scrape_firstcry(url, soup, html):
    data = _platform_base(url, soup, html, "firstcry")
    return _finalize(data)

def scrape_pepperfry(url, soup, html):
    data = _platform_base(url, soup, html, "pepperfry")
    return _finalize(data)

def scrape_jiomart(url, soup, html):
    data = _platform_base(url, soup, html, "jiomart")
    return _finalize(data)

def scrape_indiamart(url, soup, html):
    data = _platform_base(url, soup, html, "indiamart")
    # IndiaMART shows price range
    m = re.search(r'([\d,]+)\s*/\s*(?:piece|kg|unit|set|pack)', html, re.IGNORECASE)
    if m:
        data["price"] = float(m.group(1).replace(",", ""))
    return _finalize(data)

def scrape_tradeindia(url, soup, html):
    data = _platform_base(url, soup, html, "tradeindia")
    return _finalize(data)

def _platform_base(url, soup, html, platform):
    """Shared base extraction using JSON-LD + meta + regex."""
    ld = extract_jsonld(soup)
    name = ld.get("name") or get_meta(soup, "og:title", "twitter:title") or get_title(soup)
    price = parse_price_from_jsonld(ld) or extract_price_from_html(html)
    rating = float(ld.get("aggregateRating", {}).get("ratingValue", 0)) or extract_rating_from_html(html)
    rcount = int(ld.get("aggregateRating", {}).get("reviewCount", 0)) or extract_review_count_from_html(html)
    return {
        "platform": platform,
        "url": url,
        "product_name": name or "Unknown Product",
        "price": price,
        "mrp": parse_price_from_jsonld(ld) or price,
        "discount_percent": 0,
        "avg_rating": round(rating, 1),
        "review_count": rcount,
        "seller_name": f"{platform.capitalize()} Seller",
        "seller_rating": 0,
        "reviews": extract_reviews(soup),
    }

def _finalize(data):
    if data["mrp"] > 0 and data["price"] > 0 and data["mrp"] > data["price"]:
        data["discount_percent"] = round(((data["mrp"] - data["price"]) / data["mrp"]) * 100)
    return data


# ─── Main Entry Point ─────────────────────────────────────────────────
SCRAPERS = {
    "flipkart":  scrape_flipkart,
    "amazon":    scrape_amazon,
    "meesho":    scrape_meesho,
    "snapdeal":  scrape_snapdeal,
    "myntra":    scrape_myntra,
    "ajio":      scrape_ajio,
    "tatacliq":  scrape_tatacliq,
    "nykaa":     scrape_nykaa,
    "firstcry":  scrape_firstcry,
    "pepperfry": scrape_pepperfry,
    "jiomart":   scrape_jiomart,
    "indiamart": scrape_indiamart,
    "tradeindia":scrape_tradeindia,
}

def scrape_product(url):
    platform = detect_platform(url)
    html = fetch_page(url)
    soup = BeautifulSoup(html, "lxml")

    if platform in SCRAPERS:
        data = SCRAPERS[platform](url, soup, html)
    else:
        # Generic scraper for unknown URLs
        data = scrape_generic(url, soup, html)
        if not data.get("is_product_page", True):
            raise Exception(
                "NOT_PRODUCT_PAGE: This URL does not appear to be a product listing. "
                "Please enter a direct product page URL."
            )

    # Ensure all required keys exist with defaults
    data.setdefault("product_name", "Unknown Product")
    data.setdefault("price", 0)
    data.setdefault("mrp", 0)
    data.setdefault("discount_percent", 0)
    data.setdefault("avg_rating", 0)
    data.setdefault("review_count", 0)
    data.setdefault("seller_name", "Unknown")
    data.setdefault("seller_rating", 0)
    data.setdefault("reviews", [])
    data.setdefault("trust_signals", {})

    return data
