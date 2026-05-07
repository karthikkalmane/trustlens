# TrustLens — AI-Powered Product Authenticity Risk Analyzer
**Student:** Karthik Ganapati Hegde (1MS24MC041)  
**Guide:** Ms. Komal SK | **Dept:** MCA, MSRIT Bengaluru | **Year:** 2025–26

---

## Project Overview
TrustLens is a full-stack Flask web application that analyzes any e-commerce product URL
and generates a **Fake Risk Probability Score** using:
- Web Scraping (JSON-LD + platform-specific parsers)
- NLP Sentiment Analysis (VADER)
- Review Bot / Spam Detection
- ML Classification (Random Forest)
- Explainable AI (XAI) — human-readable verdict
- Price History Chart (Chart.js + local tracking + CamelCamelCamel for Amazon)
- User Authentication (Login / Signup)
- SQLite Database (history, users, price tracking)

### Supported Platforms
Flipkart, Amazon, Meesho, Snapdeal, Myntra, Ajio, Tata CLiQ, Nykaa, FirstCry,
Pepperfry, JioMart, IndiaMART, TradeIndia + **any generic product website URL**

---

## Project Structure
```
trustlens/
├── app.py                     # Flask app — all routes, auth, logic
├── config.py                  # Settings (paths, headers, platforms)
├── train_model.py             # Train Random Forest ML model (run once)
├── requirements.txt           # Python dependencies
│
├── modules/
│   ├── scraper.py             # Universal product scraper (13+ platforms)
│   ├── sentiment_analyzer.py  # VADER NLP sentiment analysis
│   ├── bot_detector.py        # Review bot / spam detection
│   ├── price_analyzer.py      # Price deviation & seller risk
│   ├── risk_evaluator.py      # ML model inference & scoring
│   ├── price_history.py       # Price history tracking & CamelCamelCamel
│   └── xai.py                 # Explainable AI — human verdict
│
├── database/
│   └── db.py                  # SQLite: users, history, price_history
│
├── models/                    # Auto-created after train_model.py
│   ├── risk_model.pkl
│   └── scaler.pkl
│
├── templates/
│   ├── base.html              # Navbar, auth, flash messages
│   ├── index.html             # Home page with URL form
│   ├── result.html            # Full analysis dashboard
│   ├── history.html           # User analysis history
│   ├── login.html             # Login page
│   └── signup.html            # Signup page
│
└── static/
    ├── css/style.css          # Dark analytical theme
    └── js/main.js             # Loading overlay, URL hints, bar animations
```

---

## COMPLETE SETUP GUIDE

### PREREQUISITES — Install These First
1. **Python 3.9 or above**
   - Download: https://www.python.org/downloads/
   - During install → ✅ Check **"Add Python to PATH"**
   - Verify: open Terminal/CMD → type `python --version`

2. **VS Code** (recommended)
   - Download: https://code.visualstudio.com/
   - Install the **Python extension** by Microsoft

3. **Git** (optional, for version control)
   - Download: https://git-scm.com/

---

### STEP 1 — Extract the Project
1. Download the `trustlens_project.zip` file
2. Right-click → **Extract All** → choose a folder (e.g., `Desktop/trustlens`)
3. Open **VS Code** → **File → Open Folder** → select the `trustlens` folder

---

### STEP 2 — Open Terminal in VS Code
Press `` Ctrl + ` `` (backtick key, below Esc)
OR go to **Terminal → New Terminal**

---

### STEP 3 — Create Virtual Environment
```bash
python -m venv venv
```
Then **activate** it:
```bash
# Windows:
venv\Scripts\activate

# Mac / Linux:
source venv/bin/activate
```
✅ You will see `(venv)` at the start of your terminal prompt.

> ⚠️ **Always activate venv before running any command.**

---

### STEP 4 — Install All Dependencies
```bash
pip install -r requirements.txt
```
This installs: Flask, Flask-Login, requests, BeautifulSoup4, VADER Sentiment,
scikit-learn, pandas, numpy, joblib, werkzeug, and more.

Wait 2–3 minutes for all packages to download.

---

### STEP 5 — Database Setup (SQLite — No Server Needed!)
**No installation required.** SQLite is built into Python.

The database file (`database/trustlens.db`) is **automatically created** the first time
you run the app. It will contain 4 tables:
- `users` — stores login accounts
- `analysis_history` — stores all analysis results per user
- `price_history` — stores price tracking data
- `guest_sessions` — tracks guest (unregistered) usage

> ℹ️ If you prefer **MySQL** instead:
> 1. Install MySQL from https://dev.mysql.com/downloads/
> 2. Create a database: `CREATE DATABASE trustlens;`
> 3. Install connector: `pip install flask-mysqldb`
> 4. Update `database/db.py` to use MySQL connector instead of sqlite3
> 5. (Ask your guide for the MySQL migration — SQLite is identical in schema)

---

### STEP 6 — Train the ML Model (Run Once Only)
```bash
python train_model.py
```
You will see output like:
```
=======================================================
  TrustLens – ML Model Training
=======================================================
  Samples: 1400 | Authentic: 700 | Fake: 700
  Accuracy : 91.43%
  ROC-AUC  : 0.9718
  ✔ Model → models/risk_model.pkl
  ✔ Scaler→ models/scaler.pkl
```
This creates `models/risk_model.pkl` and `models/scaler.pkl`.

> ℹ️ If you skip this step, the app still works using the **rule-based fallback** scorer.

---

### STEP 7 — Run the Application
```bash
python app.py
```
You will see:
```
 * Running on http://127.0.0.1:5000
 * Debug mode: on
```

---

### STEP 8 — Open in Browser
Hold **Ctrl** and click the link in the terminal, OR open your browser and go to:
```
http://localhost:5000
```

---

## HOW TO USE

### Guest (Not Logged In)
- Can analyze **1 product** for free
- Sees only the **Risk Score**
- Full dashboard (indicators, sentiment, bot detection, price chart) is locked

### Registered User
- **Unlimited** product analyses
- Full dashboard access
- Personal history page
- Price history chart

### To Test
1. Go to Flipkart or Amazon
2. Open any product page
3. Copy the URL from the browser address bar
4. Paste it in TrustLens and click **Analyze**

---

## EVERY-TIME STARTUP (After First Setup)
```bash
# Step 1: Open VS Code terminal
# Step 2: Activate venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # Mac/Linux

# Step 3: Run app
python app.py

# Step 4: Open http://localhost:5000
```

---

## TROUBLESHOOTING

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError` | Make sure `(venv)` shows in terminal. Run `pip install -r requirements.txt` |
| `python not found` | Re-install Python with "Add to PATH" checked |
| Port 5000 in use | Change `port=5000` to `port=5001` in `app.py` |
| Page shows N/A values | The site may be blocking bots — try a different product URL |
| Sentiment all 0.0 | Install VADER: `pip install vaderSentiment` |
| Flask-Login error | `pip install flask-login` |

---

## API ENDPOINTS

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/` | GET | No | Home page |
| `/signup` | GET/POST | No | Create account |
| `/login` | GET/POST | No | Login |
| `/logout` | GET | Yes | Logout |
| `/analyze` | POST | Optional | Analyze product URL |
| `/history` | GET | Yes | User history |
| `/api/analyze` | POST (JSON) | No | JSON API |
| `/api/history` | GET | No | JSON history |

---

## TECH STACK

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.9+, Flask 3.0 |
| Auth | Flask-Login, Werkzeug (bcrypt hashing) |
| Scraping | Requests, BeautifulSoup4, lxml |
| NLP | VADER Sentiment, custom lexicons |
| Bot Detection | Pattern matching, n-gram analysis |
| ML | Scikit-learn (Random Forest, StandardScaler) |
| XAI | Rule-based explanation engine |
| Price History | Local SQLite tracking + CamelCamelCamel |
| Database | SQLite (built-in Python, no server needed) |
| Frontend | HTML5, CSS3, JavaScript, Chart.js |
| Fonts | Space Mono, DM Sans (Google Fonts) |

---

## SDG ALIGNMENT
- **SDG 12** — Responsible Consumption and Production
- **SDG 9** — Industry, Innovation and Infrastructure

---
*TrustLens © 2025–26 — Ramaiah Institute of Technology, Bengaluru*
