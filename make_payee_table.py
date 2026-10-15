import pandas as pd

print("reading clean.csv...")
df = pd.read_csv("data/private/clean.csv", parse_dates=["date"])
print(len(df), "transactions loaded")

df["payee_norm"] = (
    df["payee"].str.upper().str.replace(r"\s+", " ", regex=True).str.strip()
)

payees = (
    df.groupby("payee_norm")
      .agg(
          txns=("amount", "size"),
          spent=("amount", lambda s: -s[s < 0].sum()),
          received=("amount", lambda s: s[s > 0].sum()),
      )
      .sort_values("txns", ascending=False)
)
payees["category"] = ""

payees.to_csv("data/private/payees_to_label.csv")
print(len(payees), "unique payees")
print("saved to data/private/payees_to_label.csv")