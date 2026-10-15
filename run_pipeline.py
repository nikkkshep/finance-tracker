from src.parser import parse_statement, check_balance

df = parse_statement("data/private/statement.pdf")
print(len(df), "transactions")
print(df.head(10))

bad = check_balance(df)
print(len(bad), "rows fail the balance check")
print(bad)

df = df.iloc[::-1].reset_index(drop=True)   # chronological order
df.to_csv("data/private/clean.csv", index=False)