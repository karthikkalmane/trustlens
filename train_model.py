"""
TrustLens – ML Model Training Script
Run once: python train_model.py
"""
import os, numpy as np, pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score, roc_auc_score
import joblib
from config import Config

SEED = 42; np.random.seed(SEED)

FEATURES = [
    "price_deviation","discount_risk","seller_risk","review_count_risk",
    "rating_risk","sentiment_score","positive_ratio","negative_ratio",
    "keyword_risk_score","suspicious_keyword_count","avg_review_length",
    "discount_percent","avg_rating","seller_rating",
]

def gen_authentic(n=700):
    return pd.DataFrame({
        "price_deviation":np.random.beta(1.5,8,n),"discount_risk":np.random.beta(1,6,n),
        "seller_risk":np.random.beta(1,6,n),"review_count_risk":np.random.beta(1,5,n),
        "rating_risk":np.random.beta(1,6,n),"sentiment_score":np.clip(np.random.normal(0.35,0.25,n),-1,1),
        "positive_ratio":np.clip(np.random.normal(0.65,0.15,n),0,1),
        "negative_ratio":np.clip(np.random.normal(0.10,0.08,n),0,1),
        "keyword_risk_score":np.random.beta(1,8,n),"suspicious_keyword_count":np.random.poisson(0.5,n),
        "avg_review_length":np.clip(np.random.normal(40,20,n),5,200),
        "discount_percent":np.clip(np.random.normal(20,15,n),0,70),
        "avg_rating":np.clip(np.random.normal(4.1,0.5,n),1,5),
        "seller_rating":np.clip(np.random.normal(4.2,0.4,n),1,5),"label":0})

def gen_fake(n=700):
    return pd.DataFrame({
        "price_deviation":np.random.beta(5,3,n),"discount_risk":np.random.beta(5,2,n),
        "seller_risk":np.random.beta(4,3,n),"review_count_risk":np.random.beta(4,3,n),
        "rating_risk":np.random.beta(4,3,n),"sentiment_score":np.clip(np.random.normal(-0.15,0.3,n),-1,1),
        "positive_ratio":np.clip(np.random.normal(0.30,0.2,n),0,1),
        "negative_ratio":np.clip(np.random.normal(0.45,0.2,n),0,1),
        "keyword_risk_score":np.random.beta(5,3,n),"suspicious_keyword_count":np.random.poisson(3,n),
        "avg_review_length":np.clip(np.random.normal(15,10,n),2,100),
        "discount_percent":np.clip(np.random.normal(72,15,n),30,99),
        "avg_rating":np.clip(np.random.normal(3.0,0.8,n),1,5),
        "seller_rating":np.clip(np.random.normal(2.8,0.9,n),1,5),"label":1})

def train():
    print("="*55)
    print("  TrustLens – ML Model Training")
    print("="*55)
    df = pd.concat([gen_authentic(),gen_fake()],ignore_index=True).sample(frac=1,random_state=SEED)
    X = df[FEATURES]; y = df["label"]
    print(f"\n  Samples: {len(df)} | Authentic: {(y==0).sum()} | Fake: {(y==1).sum()}")
    X_tr,X_te,y_tr,y_te = train_test_split(X,y,test_size=0.2,random_state=SEED,stratify=y)
    scaler = StandardScaler()
    X_tr_s = scaler.fit_transform(X_tr); X_te_s = scaler.transform(X_te)
    model = RandomForestClassifier(n_estimators=200,max_depth=12,min_samples_split=4,random_state=SEED,class_weight="balanced")
    model.fit(X_tr_s,y_tr)
    y_pred = model.predict(X_te_s); y_proba = model.predict_proba(X_te_s)[:,1]
    print(f"\n  Accuracy : {accuracy_score(y_te,y_pred)*100:.2f}%")
    print(f"  ROC-AUC  : {roc_auc_score(y_te,y_proba):.4f}")
    print(classification_report(y_te,y_pred,target_names=["Authentic","Fake"]))
    os.makedirs(os.path.dirname(Config.MODEL_PATH),exist_ok=True)
    joblib.dump(model,Config.MODEL_PATH); joblib.dump(scaler,Config.SCALER_PATH)
    print(f"  ✔ Model → {Config.MODEL_PATH}")
    print(f"  ✔ Scaler→ {Config.SCALER_PATH}\n")

if __name__=="__main__":
    train()
