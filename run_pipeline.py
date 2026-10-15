from src.parser import parse_statement, check_balance
from src.categorizer import load_labels, categorize
from src.analytics import prepare, monthly_summary, category_by_month, recurring, anomalies


df = parse_statement("data/private/statement.pdf")
print(len(df), "transactions")

bad = check_balance(df)
print(len(bad), "rows fail the balance check")

df = df.iloc[::-1].reset_index(drop=True)   # chronological order
df.to_csv("data/private/clean.csv", index=False)

labels = load_labels("data/private/payee_labels.csv")
df = categorize(df, labels)
df.to_csv("data/private/categorized.csv", index=False)

print(df["category"].value_counts())
print(df["cat_source"].value_counts())
other = df[(df.category == "Other") & (df.amount < 0)]
print("Spend still in Other: Rs", round(-other.amount.sum()))
print(other.groupby("payee_norm").amount.agg(["size", "sum"]).sort_values("sum").head(15))

spend = -df[(df.amount < 0) & (df.category != "Internal Transfer")].amount.sum()
print("Total spend: Rs", round(spend))

a = prepare(df)
spend = -a[a.amount < 0].amount.sum()
print("Total spend: Rs", round(spend))

pd_opts = {"display.width": 200, "display.max_columns": 20}
import pandas as pd
with pd.option_context(*[x for kv in pd_opts.items() for x in kv]):
    print(monthly_summary(a).round(2))
    print(recurring(a))
    print(anomalies(a)[["date", "payee_norm", "category", "spend"]].sort_values("spend", ascending=False).head(15))