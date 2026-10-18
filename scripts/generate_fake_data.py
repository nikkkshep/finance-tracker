import random
from datetime import date, timedelta
from pathlib import Path
import pandas as pd

random.seed(42)
START, END = date(2025, 10, 15), date(2026, 10, 14)

MERCHANTS = {   # category -> (merchant, min amount, max amount)
    "Food": [("ZOMATO", 150, 450), ("SWIGGY", 120, 400), ("CAMPUS CANTEEN", 20, 120),
             ("CHAI POINT", 15, 60), ("DOMINOS PIZZA", 200, 600), ("SHARMA SWEETS", 40, 250)],
    "Groceries": [("BLINKIT", 150, 700), ("ZEPTO", 150, 800), ("CITY MART", 100, 600)],
    "Travel": [("UBER", 80, 400), ("OLA", 70, 350), ("DELHI METRO", 30, 80), ("RAPIDO", 40, 200)],
    "Shopping": [("AMAZON", 300, 3000), ("MYNTRA", 500, 2500), ("FLIPKART", 300, 2500)],
    "Personal Care": [("STYLE HAIR STUDIO", 100, 400)],
    "Health": [("APOLLO PHARMACY", 100, 900)],
    "Entertainment & Sports": [("BOOKMYSHOW", 200, 800), ("TURF ARENA", 300, 1200)],
}
WEIGHTS = {"Food": 38, "Groceries": 14, "Travel": 12, "Shopping": 3,
           "Personal Care": 2, "Health": 1, "Entertainment & Sports": 3}
FRIENDS = ["AARAV MEHTA", "RIYA SINGH", "KABIR VERMA", "ISHITA ROY",
           "ROHAN GUPTA", "ANANYA SHAH", "VIHAAN JOSHI", "MEERA NAIR"]
SUBSCRIPTIONS = [("NETFLIX", 199, 5), ("SPOTIFY", 119, 12), ("JIO PREPAID", 349, 20)]

rows = []

def add(d, payee, amount, category):
    rows.append({"date": d, "payee": payee, "amount": amount, "category": category})

d = START
while d <= END:
    for _ in range(random.choice([1, 2, 2, 3, 3])):          # transactions today
        if random.random() < 0.8:                            # shop / food / travel
            cat = random.choices(list(WEIGHTS), weights=list(WEIGHTS.values()))[0]
            name, lo, hi = random.choice(MERCHANTS[cat])
            add(d, name, -round(random.uniform(lo, hi)), cat)
        else:                                                # UPI with a friend
            friend = random.choice(FRIENDS)
            if random.random() < 0.7:
                add(d, friend, -random.choice([20, 30, 40, 50, 80, 100, 150, 200, 300, 500]), "Person-to-Person")
            else:
                add(d, friend, random.choice([50, 100, 200, 300, 500]), "Person-to-Person")
    if d.day == 1:
        add(d, "FAMILY ALLOWANCE", random.choice([12000, 15000, 18000]), "Allowance")
    if d.day == 5:
        add(d, "OWN ACCOUNT TRANSFER", -2000, "Internal Transfer")
    for name, amt, day in SUBSCRIPTIONS:
        if d.day == day:
            add(d, name, -amt, "Bills & Subscriptions")
    d += timedelta(days=1)

# one big one-off: a fee paid from a matching transfer
add(date(2026, 8, 18), "FAMILY ALLOWANCE", 120000, "Allowance")
add(date(2026, 8, 20), "COLLEGE FEES", -120000, "Education")

# running balance (top up from "allowance" if it would go negative)
rows.sort(key=lambda r: r["date"])
final, bal = [], 3000
for r in rows:
    if bal + r["amount"] < 0:
        need = -(bal + r["amount"])
        top = (need // 5000 + 1) * 5000
        bal += top
        final.append({"date": r["date"], "payee": "FAMILY ALLOWANCE",
                      "amount": top, "category": "Allowance", "balance": bal})
    bal += r["amount"]
    final.append({**r, "balance": bal})

df = pd.DataFrame(final)
df["date"] = pd.to_datetime(df["date"])
df["payee_norm"] = df["payee"].str.upper()
df["ref"] = ["S" + str(random.randint(10**7, 10**8 - 1)) for _ in range(len(df))]
df["description"] = ["UPI/" + str(random.randint(10**11, 10**12 - 1)) + "/"
                     + ("DR" if a < 0 else "CR") + "/" + p
                     for a, p in zip(df["amount"], df["payee"])]
df["cat_source"] = "synthetic"

Path("data/sample").mkdir(parents=True, exist_ok=True)
df[["date", "description", "payee", "amount", "balance", "ref",
    "payee_norm", "category", "cat_source"]].to_csv("data/sample/transactions.csv", index=False)
print(len(df), "rows written")