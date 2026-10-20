import sys
from pathlib import Path

import json
import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import GroupKFold, KFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.categorizer import categorize

MIN_PER_CLASS = 15
EXCLUDE = {"Other", "Internal Transfer", "Allowance", "Cash"}
NUMERIC = ["log_amount", "log_txns", "log_median", "share_round", "ever_received"]

BINARY = False

def payee_stats(df):
    """How you behave with each payee, computed from all transactions (no labels used)."""
    g = df.groupby("payee_norm")["amount"]
    return pd.DataFrame({
        "log_txns": np.log1p(g.size()),
        "log_median": np.log1p(g.apply(lambda s: s.abs().median())),
        "share_round": g.apply(lambda s: (s.abs() % 10 == 0).mean()),
        "ever_received": g.apply(lambda s: float((s > 0).any())),
    })


def make_features(rows, stats):
    f = pd.DataFrame({"payee": rows["payee_norm"].fillna(""),
                      "log_amount": np.log1p(rows["amount"].abs())}, index=rows.index)
    s = stats.reindex(rows["payee_norm"].values)
    s.index = rows.index
    return pd.concat([f, s], axis=1)


def build_pipeline():
    features = ColumnTransformer([
        ("payee_text", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), min_df=2), "payee"),
        ("numbers", StandardScaler(), NUMERIC),
    ])
    return Pipeline([
        ("features", features),
        ("clf", LogisticRegression(max_iter=2000, class_weight="balanced")),
    ])


def training_data(df, stats):
    d = df[(df["amount"] < 0) & (~df["category"].isin(EXCLUDE))]
    counts = d["category"].value_counts()
    d = d[d["category"].isin(counts[counts >= MIN_PER_CLASS].index)]
    y = d["category"]
    if BINARY:
        y = y.where(y == "Person-to-Person", "Merchant")
    return make_features(d, stats), y, d["payee_norm"]


def evaluate(X, y, groups, df):
    folds = min(5, groups.nunique())
    honest = cross_val_predict(build_pipeline(), X, y, groups=groups,
                               cv=GroupKFold(n_splits=folds))
    naive = cross_val_predict(build_pipeline(), X, y,
                              cv=KFold(n_splits=folds, shuffle=True, random_state=0))

    majority_label = y.value_counts().index[0]
    majority = (y == majority_label).mean()
    rules = categorize(df.loc[y.index], {})["category"]
    if BINARY:
        rules = rules.where(rules == "Other", "Merchant")   # any keyword hit means merchant
    rules = rules.where(rules != "Other", majority_label)   # no hit: guess the common class   # rules, else guess the common class
    rules_acc = (rules.values == y.values).mean()
    person_rule = np.where(X["ever_received"] == 1, "Person-to-Person", "Merchant")

    print(f"\nAlways guess the most common class:       {majority:.1%}")
    print(f"Keyword rules (else most common class):   {rules_acc:.1%}")
    print(f"ML, random split (inflated):              {accuracy_score(y, naive):.1%}")
    print(f"ML, split by payee (honest):              {accuracy_score(y, honest):.1%}")
    print(f"Honest macro F1:                          {f1_score(y, honest, average='macro'):.2f}")
    print("\n", classification_report(y, honest, zero_division=0))
    labels = sorted(y.unique())
    print(pd.DataFrame(confusion_matrix(y, honest, labels=labels),
                       index=[f"true {l}" for l in labels],
                       columns=[f"pred {l[:8]}" for l in labels]))
    return {
        "labels": labels,
        "n_rows": int(len(y)),
        "n_payees": int(groups.nunique()),
        "baseline_acc": float(majority),
        "random_split_acc": float(accuracy_score(y, naive)),
        "payee_split_acc": float(accuracy_score(y, honest)),
        "macro_f1": float(f1_score(y, honest, average="macro")),
        "confusion": confusion_matrix(y, honest, labels=labels).tolist(),
    }

def main(data_path, out_path):
    df = pd.read_csv(data_path, parse_dates=["date"])
    stats = payee_stats(df)
    X, y, groups = training_data(df, stats)
    print(f"Training rows: {len(y)} | payees: {groups.nunique()} | classes: {y.nunique()}")
    print(y.value_counts().to_string())

    metrics = evaluate(X, y, groups, df)
    Path("results").mkdir(exist_ok=True)
    Path("results/metrics.json").write_text(json.dumps(metrics, indent=2))

    model = build_pipeline().fit(X, y)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, out_path)

    todo = df[(df["amount"] < 0) & (df["cat_source"] == "none")]
    if len(todo):
        proba = model.predict_proba(make_features(todo, stats))
        out = todo[["date", "payee_norm", "amount"]].copy()
        out["predicted"] = model.classes_[proba.argmax(axis=1)]
        out["confidence"] = proba.max(axis=1).round(2)
        out.to_csv(Path(out_path).with_name("predictions.csv"), index=False)
        print(f"\nUnlabeled rows: {len(todo)} | confidence >= 0.6: {(out.confidence >= 0.6).sum()}")
        print(out["predicted"].value_counts().to_string())


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])