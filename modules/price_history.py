"""
Price History Module
- Stores price in local DB every time a product is analyzed
- Attempts to fetch Amazon price history from camelcamelcamel
"""

import re
import sqlite3
import requests
from datetime import datetime, timedelta
from urllib.parse import urlparse, quote
from bs4 import BeautifulSoup
from config import Config


def get_db():
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def save_price_point(url, platform, product_name, price):
    """Store a price data point for this URL."""
    if not price or price <= 0:
        return
    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO price_history (url_hash, url, platform, product_name, price, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            hash(url) & 0xFFFFFFFF,
            url[:500],
            platform,
            product_name[:200],
            price,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ))
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()


def get_local_price_history(url, days=90):
    """Retrieve our own tracked price history for this URL."""
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT price, recorded_at FROM price_history
            WHERE url_hash = ?
            ORDER BY recorded_at ASC
            LIMIT 60
        """, (hash(url) & 0xFFFFFFFF,)).fetchall()
        return [{"price": r["price"], "date": r["recorded_at"][:10]} for r in rows]
    except Exception:
        return []
    finally:
        conn.close()


def fetch_camelcamelcamel(amazon_url):
    """
    Fetch price history from camelcamelcamel for Amazon products.
    Returns list of {date, price} dicts.
    """
    # Extract ASIN from Amazon URL
    asin_match = re.search(r'/(?:dp|gp/product|product)/([A-Z0-9]{10})', amazon_url)
    if not asin_match:
        return []

    asin = asin_match.group(1)
    camel_url = f"https://camelcamelcamel.com/product/{asin}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://camelcamelcamel.com/",
    }

    try:
        resp = requests.get(camel_url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        history = []

        # Try to find price history table
        table = soup.find("table", class_=re.compile(r"product_pane"))
        if not table:
            table = soup.find("table")

        if table:
            rows = table.find_all("tr")[1:]  # skip header
            for row in rows[:30]:
                cells = row.find_all("td")
                if len(cells) >= 2:
                    date_txt = cells[0].get_text(strip=True)
                    price_txt = cells[1].get_text(strip=True)
                    price_clean = re.sub(r"[^\d.]", "", price_txt.replace(",", ""))
                    if price_clean:
                        try:
                            history.append({
                                "date": date_txt,
                                "price": float(price_clean)
                            })
                        except Exception:
                            pass

        return history[:30]

    except Exception:
        return []


def get_price_history(url, platform, product_name, current_price):
    """
    Main function: returns price history data for charting.
    Combines local tracking + camelcamelcamel (for Amazon).
    """
    # Always save current price
    save_price_point(url, platform, product_name, current_price)

    # Get local history
    local = get_local_price_history(url)

    # For Amazon, also try camelcamelcamel
    external = []
    if platform == "amazon":
        external = fetch_camelcamelcamel(url)

    # Merge: prefer external if available (more history)
    if external:
        history = external
        source = "CamelCamelCamel + Local Tracking"
    elif local:
        history = local
        source = "Local Price Tracking"
    else:
        # Generate synthetic "today only" point
        history = [{"date": datetime.now().strftime("%Y-%m-%d"), "price": current_price}]
        source = "Current Price"

    # Add price statistics
    prices = [h["price"] for h in history if h["price"] > 0]
    stats = {}
    if prices:
        stats = {
            "min_price": min(prices),
            "max_price": max(prices),
            "avg_price": round(sum(prices) / len(prices), 2),
            "current_vs_avg": round(
                ((current_price - (sum(prices)/len(prices))) / (sum(prices)/len(prices)) * 100), 1
            ) if prices else 0,
        }

    return {
        "history": history,
        "source": source,
        "stats": stats,
    }
