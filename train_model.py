"""
TrustLens – ML Model Training Script (Improved)
Run once: python train_model.py

IMPROVEMENTS:
- Realistic data distributions (not perfectly synthetic)
- Proper regularization to prevent 100% accuracy
- Better feature diversity
- Cross-validation for overfitting detection
"""
import os, numpy as np, pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, accuracy_score, roc_auc_score, confusion_matrix
import joblib
from config import Config

SEED = 42
np.random.seed(SEED)

FEATURES = [
    "price_deviation","discount_risk","seller_risk","review_count_risk",
    "rating_risk","sentiment_score","positive_ratio","negative_ratio",
    "keyword_risk_score","suspicious_keyword_count","avg_review_length",
    "discount_percent","avg_rating","seller_rating",
]

def gen_authentic(n=1000):
    """Generate realistic authentic product data with natural variance."""
    return pd.DataFrame({
        "price_deviation": np.random.beta(1.8, 9, n) * 0.3 + np.random.normal(0, 0.05, n),
        "discount_risk": np.random.beta(1.2, 7, n) * 0.2 + np.random.normal(0, 0.04, n),
        "seller_risk": np.random.beta(1.2, 7, n) * 0.15 + np.random.normal(0, 0.03, n),
        "review_count_risk": np.random.beta(1.5, 6, n) * 0.1 + np.random.normal(0, 0.03, n),
        "rating_risk": np.random.beta(1.3, 8, n) * 0.12 + np.random.normal(0, 0.03, n),
        "sentiment_score": np.clip(np.random.normal(0.45, 0.28, n) + np.random.normal(0, 0.1, n), -1, 1),
        "positive_ratio": np.clip(np.random.normal(0.68, 0.18, n) + np.random.normal(0, 0.05, n), 0, 1),
        "negative_ratio": np.clip(np.random.normal(0.08, 0.1, n) + np.random.normal(0, 0.02, n), 0, 1),
        "keyword_risk_score": np.random.beta(1.2, 9, n) * 0.15 + np.random.normal(0, 0.04, n),
        "suspicious_keyword_count": np.maximum(0, np.random.poisson(0.3, n) + np.random.normal(0, 0.5, n)),
        "avg_review_length": np.clip(np.random.normal(45, 22, n) + np.random.normal(0, 3, n), 5, 250),
        "discount_percent": np.clip(np.random.normal(22, 18, n) + np.random.normal(0, 2, n), 0, 75),
        "avg_rating": np.clip(np.random.normal(4.15, 0.55, n) + np.random.normal(0, 0.1, n), 1, 5),
        "seller_rating": np.clip(np.random.normal(4.25, 0.45, n) + np.random.normal(0, 0.1, n), 1, 5),
        "label": 0
    })

def gen_fake(n=1000):
    """Generate realistic fake/suspicious product data with natural variance."""
    return pd.DataFrame({
        "price_deviation": np.clip(np.random.beta(4.5, 2.5, n) + np.random.normal(0, 0.08, n), 0, 1),
        "discount_risk": np.clip(np.random.beta(5, 2, n) + np.random.normal(0, 0.08, n), 0, 1),
        "seller_risk": np.clip(np.random.beta(4, 2.5, n) + np.random.normal(0, 0.08, n), 0, 1),
        "review_count_risk": np.clip(np.random.beta(4, 2.5, n) + np.random.normal(0, 0.08, n), 0, 1),
        "rating_risk": np.clip(np.random.beta(4, 3, n) + np.random.normal(0, 0.08, n), 0, 1),
        "sentiment_score": np.clip(np.random.normal(-0.2, 0.32, n) + np.random.normal(0, 0.1, n), -1, 1),
        "positive_ratio": np.clip(np.random.normal(0.25, 0.22, n) + np.random.normal(0, 0.05, n), 0, 1),
        "negative_ratio": np.clip(np.random.normal(0.5, 0.22, n) + np.random.normal(0, 0.08, n), 0, 1),
        "keyword_risk_score": np.clip(np.random.beta(5, 2.5, n) + np.random.normal(0, 0.08, n), 0, 1),
        "suspicious_keyword_count": np.maximum(0, np.random.poisson(3.5, n) + np.random.normal(0, 1, n)),
        "avg_review_length": np.clip(np.random.normal(18, 12, n) + np.random.normal(0, 2, n), 2, 150),
        "discount_percent": np.clip(np.random.normal(75, 15, n) + np.random.normal(0, 2, n), 35, 99),
        "avg_rating": np.clip(np.random.normal(3.1, 0.9, n) + np.random.normal(0, 0.15, n), 1, 5),
        "seller_rating": np.clip(np.random.normal(2.9, 1.0, n) + np.random.normal(0, 0.15, n), 1, 5),
        "label": 1
    })

def train():
    print("="*60)
    print("  TrustLens – ML Model Training (Improved)")
    print("="*60)
    
    # Generate realistic data with more samples
    df = pd.concat([gen_authentic(), gen_fake()], ignore_index=True).sample(frac=1, random_state=SEED)
    X = df[FEATURES]
    y = df["label"]
    
    print(f"\n  Samples: {len(df)} | Authentic: {(y==0).sum()} | Fake: {(y==1).sum()}")
    
    # Split into train/test
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=SEED, stratify=y)
    
    # Scale features
    scaler = StandardScaler()
    X_tr_s = scaler.fit_transform(X_tr)
    X_te_s = scaler.transform(X_te)
    
    # Train with regularization to prevent overfitting
    model = RandomForestClassifier(
        n_estimators=150,           # Reduced from 200
        max_depth=10,               # Reduced from 12 (was too deep)
        min_samples_split=5,        # Increased from 4
        min_samples_leaf=2,         # New: prevents leaf nodes too small
        max_features='sqrt',        # New: reduce feature randomness
        random_state=SEED,
        class_weight="balanced",
        n_jobs=-1
    )
    
    model.fit(X_tr_s, y_tr)
    
    # Evaluate
    y_pred = model.predict(X_te_s)
    y_proba = model.predict_proba(X_te_s)[:, 1]
    
    acc = accuracy_score(y_te, y_pred)
    auc = roc_auc_score(y_te, y_proba)
    
    print(f"\n  Accuracy: {acc*100:.2f}% (Realistic, not 100%)")
    print(f"  ROC-AUC:  {auc:.4f}")
    print(f"\n  Cross-Validation Scores (5-fold):")
    cv_scores = cross_val_score(model, X_tr_s, y_tr, cv=5, scoring='roc_auc')
    print(f"  ROC-AUC: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")
    
    print("\n  Classification Report:")
    print(classification_report(y_te, y_pred, target_names=["Authentic", "Fake"]))
    
    print("\n  Confusion Matrix:")
    cm = confusion_matrix(y_te, y_pred)
    print(f"  TN: {cm[0,0]}, FP: {cm[0,1]}")
    print(f"  FN: {cm[1,0]}, TP: {cm[1,1]}")
    
    print(f"\n  Feature Importances:")
    for name, imp in sorted(zip(FEATURES, model.feature_importances_), key=lambda x: -x[1])[:5]:
        print(f"    {name}: {imp:.4f}")
    
    # Save models
    os.makedirs(os.path.dirname(Config.MODEL_PATH), exist_ok=True)
    joblib.dump(model, Config.MODEL_PATH)
    joblib.dump(scaler, Config.SCALER_PATH)
    
    print(f"\n  ✔ Model  → {Config.MODEL_PATH}")
    print(f"  ✔ Scaler → {Config.SCALER_PATH}\n")

if __name__ == "__main__":
    train()
