# src/analytics.py
import pandas as pd

def prepare(df):
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.to_period("M")
    return df[df["category"] != "Internal Transfer"]

def monthly_summary(df):
    g = df.groupby("month")["amount"]
    out = pd.DataFrame({
        "income": g.apply(lambda s: s[s > 0].sum()),
        "spend": g.apply(lambda s: -s[s < 0].sum()),
    })
    out["net"] = out["income"] - out["spend"]
    out["savings_rate"] = (out["net"] / out["income"]).where(out["income"] > 0)
    return out

def category_by_month(df):
    sp = df[df["amount"] < 0].assign(spend=lambda d: -d["amount"])
    return sp.pivot_table(index="month", columns="category",
                          values="spend", aggfunc="sum", fill_value=0)

def recurring(df, min_count=3):
    """Payees you pay about monthly, for a similar amount each time."""
    sp = df[df["amount"] < 0].sort_values("date")
    rows = []
    for payee, g in sp.groupby("payee_norm"):
        if len(g) < min_count:
            continue
        gaps = g["date"].diff().dt.days.dropna()
        amt = -g["amount"]
        if 25 <= gaps.median() <= 35 and amt.std() / amt.mean() < 0.1:
            rows.append({"payee": payee, "times": len(g),
                         "typical_amount": round(amt.median(), 2),
                         "category": g["category"].iloc[0]})
    return pd.DataFrame(rows)

def anomalies(df, k=3.0, min_rows=15):
    """Unusually large payments within their own category (IQR rule)."""
    sp = df[df["amount"] < 0].assign(spend=lambda d: -d["amount"])
    flagged = []
    for cat, g in sp.groupby("category"):
        if len(g) < min_rows:
            continue
        q1, q3 = g["spend"].quantile([0.25, 0.75])
        flagged.append(g[g["spend"] > q3 + k * (q3 - q1)])
    return pd.concat(flagged) if flagged else sp.iloc[0:0]