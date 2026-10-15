import os
import re
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
OWN_NAME = os.environ.get("OWN_NAME", "").upper().strip()

CATEGORIES = [
    "Food", "Groceries", "Travel", "Shopping", "Bills & Subscriptions",
    "Education", "Personal Care", "Health", "Entertainment & Sports",
    "Government & Fees", "Person-to-Person", "Income",
    "Internal Transfer", "Cash", "Other",
]

KEYWORDS = {
    "Food": ["ZOMATO", "SWIGGY", "CANTEEN", "SWEET", "BAKER", "BAKERY", "CAFE", "PIZZA", "JUICE", "DHABA", "FOODS", "DOMINOS", "DOMINOSPIZZA"],
    "Groceries": ["ZEPTO", "BLINKIT", "INSTAMART", "BIGBASKET", "KIRYANA", "GROCERY"],
    "Travel": ["UBER", "OLA", "RAPIDO", "IRCTC", "REDBUS", "METRO"],
    "Bills & Subscriptions": ["NETFLIX", "SPOTIFY", "AIRTEL", "JIO", "RECHARGE", "FAMAPP"],
    "Personal Care": ["SALON", "HAIR"],
    "Cash": ["BY CASH", "ATM"],
    "Food": [..., "DOMINOSPIZZA"],
    "Health": ["DOCTOR", "NUTRITION", "PHARMACY", "MEDICAL", "CHEMIST", "HOSPITAL"],
    "Entertainment & Sports": ["MOVIE", "BOOKMYSHOW", "PVR"],
    "Government & Fees": ["PASSPORT"],
}

def _norm(s):
    return " ".join(str(s).upper().split())

def load_labels(path):
    lab = pd.read_csv(path)
    lab = lab[lab["category"].notna() & (lab["category"].astype(str).str.strip() != "")]
    lab["category"] = lab["category"].str.strip()
    bad = set(lab["category"]) - set(CATEGORIES)
    if bad:
        raise ValueError(f"Unknown categories in label file: {bad}")
    return dict(zip(lab["payee_norm"], lab["category"]))

def _row_category(payee_norm, desc, labels):
    if payee_norm in labels:
        return labels[payee_norm], "label"
    if OWN_NAME and OWN_NAME in desc:
        return "Internal Transfer", "own-name"
    for cat, words in KEYWORDS.items():
        if any(re.search(rf"\b{re.escape(w)}\b", desc) for w in words):
            return cat, "keyword"
    return "Other", "none"

def categorize(df, labels):
    df = df.copy()
    df["payee_norm"] = df["payee"].map(_norm)
    desc = df["description"].map(_norm)
    res = [_row_category(p, d, labels) for p, d in zip(df["payee_norm"], desc)]
    df["category"], df["cat_source"] = zip(*res)
    return df