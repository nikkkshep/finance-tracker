# prep_labels.py (project root, run once)
import os
import pandas as pd

OUT = "data/private/payee_labels.csv"
if os.path.exists(OUT):
    raise SystemExit("payee_labels.csv already exists, not overwriting your labels")

p = pd.read_csv("data/private/payees_to_label.csv")
p["total"] = p["spent"] + p["received"]

top_txns = set(p.nlargest(100, "txns").payee_norm)
top_money = set(p.nlargest(40, "total").payee_norm)
p["priority"] = p.payee_norm.isin(top_txns | top_money)
p = p.sort_values(["priority", "total"], ascending=[False, False])

pr = p[p.priority]
print(len(pr), "payees to label first")
print("covering", round(pr.txns.sum() / p.txns.sum() * 100), "% of txns and",
      round(pr.total.sum() / p.total.sum() * 100), "% of money")
p.to_csv(OUT, index=False)