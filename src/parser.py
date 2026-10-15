import re
import pdfplumber
import pandas as pd

DATE_START = re.compile(r"^(\d{2}-[A-Za-z]{3}-\d{2})\s*(.*)$")
VALUE_DATE = re.compile(r"\(\d{2}-[A-Za-z]{3}-\d{2}\)")
FOOTER = re.compile(r"^Page \d+ of \d+")
AMOUNTS = re.compile(
    r"(?P<ref>(?<![A-Za-z0-9])[A-Z]{1,2}\d{5,})\s+(?P<type>[A-Za-z ]+?)\s+"
    r"(?P<debit>[\d,]+\.\d{2}|-)\s+(?P<credit>[\d,]+\.\d{2}|-)\s+(?P<balance>[\d,]+\.\d{2})"
)
def _num(s):
    return 0.0 if s == "-" else float(s.replace(",", ""))

def _parse_block(date, lines):
    text = " ".join(lines)
    m = AMOUNTS.search(text)
    if not m:
        return None
    desc = text[:m.start()] + " " + text[m.end():]
    desc = re.sub(r"\s+", " ", VALUE_DATE.sub("", desc)).strip()
    parts = [p.strip() for p in desc.split("/")]
    payee = parts[3] if parts[0] == "UPI" and len(parts) > 3 else desc
    return {
        "date": date,
        "description": desc,
        "payee": payee,
        "amount": _num(m["credit"]) - _num(m["debit"]),
        "balance": _num(m["balance"]),
        "ref": m["ref"],
    }

def parse_statement(path, password=None):
    blocks = []
    with pdfplumber.open(path, password=password) as pdf:
        for page in pdf.pages:
            current = None
            for line in (page.extract_text() or "").split("\n"):
                line = line.strip()
                if not line or FOOTER.match(line):
                    continue
                d = DATE_START.match(line)
                if d:
                    if current:
                        blocks.append(current)
                    current = (d.group(1), [d.group(2)])
                elif current:
                    current[1].append(line)
            if current:
                blocks.append(current)

    rows = []
    for date, lines in blocks:
        row = _parse_block(date, lines)
        if row:
            rows.append(row)
        else:
            print("UNPARSED:", date, lines)
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"], format="%d-%b-%y")
    return df

def check_balance(df):
    """df in original statement order (newest first).
    Each row's balance must equal the next (older) row's balance + this row's amount."""
    expected = df["balance"].shift(-1) + df["amount"]
    return df[(expected - df["balance"]).abs() > 0.01]