# src/analytics.py
import pandas as pd
ONE_OFF = 20000
def prepare(df):
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.to_period("M")
    return df[df["category"] != "Internal Transfer"]

def monthly_summary(df, one_off=ONE_OFF):
    d = df.copy()
    credit = d["amount"].where(d["amount"] > 0, 0)
    debit = (-d["amount"]).where(d["amount"] < 0, 0)
    is_allow = d["category"] == "Allowance"

    d["allowance"] = credit.where(is_allow & (credit < one_off), 0)
    d["allowance_oneoff"] = credit.where(is_allow & (credit >= one_off), 0)
    d["received_other"] = credit.where(~is_allow, 0)
    d["spend_regular"] = debit.where(debit < one_off, 0)
    d["spend_oneoff"] = debit.where(debit >= one_off, 0)

    cols = ["allowance", "allowance_oneoff", "received_other",
            "spend_regular", "spend_oneoff"]
    m = d.groupby("month")[cols].sum()
    m["used_pct"] = (m["spend_regular"]
                     / m["allowance"].where(m["allowance"] > 0) * 100).round(0)
    m["txns"] = d.groupby("month").size()

    first, last = d["date"].min(), d["date"].max()
    m["partial"] = False
    m.loc[m.index[0], "partial"] = first.day > 1
    if last.day < last.days_in_month:
        m.loc[m.index[-1], "partial"] = True
    return m.round(0)

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