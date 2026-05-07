import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "trustlens-super-secret-2025")
    DATABASE_PATH = os.path.join(BASE_DIR, "database", "trustlens.db")
    MODEL_PATH = os.path.join(BASE_DIR, "models", "risk_model.pkl")
    SCALER_PATH = os.path.join(BASE_DIR, "models", "scaler.pkl")
    DEBUG = True
    MAX_REVIEWS = 30
    REQUEST_TIMEOUT = 20

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Connection": "keep-alive",
        "DNT": "1",
    }

    # Supported platforms
    SUPPORTED_PLATFORMS = [
        "flipkart", "amazon", "meesho", "snapdeal", "myntra",
        "ajio", "tatacliq", "nykaa", "firstcry", "pepperfry",
        "jiomart", "indiamart", "tradeindia"
    ]
