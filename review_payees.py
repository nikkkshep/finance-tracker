import pandas as pd

df = pd.read_csv("data/private/categorized.csv", parse_dates=["date"])
p2p_names = set(df.loc[df["category"] == "Person-to-Person", "payee_norm"])

g = df.groupby("payee_norm")["amount"]
info = pd.DataFrame({
    "txns": g.size(),
    "sent": g.apply(lambda s: -s[s < 0].sum()),
    "received": g.apply(lambda s: s[s > 0].sum()),
    "typical_sent": g.apply(lambda s: -s[s < 0].median() if (s < 0).any() else 0),
    "round_share": g.apply(lambda s: (s.abs() % 10 == 0).mean()),
})
review = info[info.index.isin(p2p_names) & (info["sent"] > 0)]
review = review.sort_values("txns", ascending=False)
review.round(2).to_csv("data/private/review_payees.csv")

print(len(review), "Person-to-Person payees you have paid")
print(review.head(40).to_string())