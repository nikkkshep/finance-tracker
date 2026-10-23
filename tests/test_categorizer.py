import pandas as pd
import pytest
from src.categorizer import categorize, load_labels


def make_df(rows):
    return pd.DataFrame(rows, columns=["payee", "description", "amount"])


def result(df, labels=None):
    out = categorize(df, labels or {})
    return list(zip(out["category"], out["cat_source"]))


def test_manual_label_wins_over_keyword():
    df = make_df([("ZOMATO", "UPI/1/DR/ZOMATO", -100)])
    assert result(df, {"ZOMATO": "Groceries"}) == [("Groceries", "label")]


def test_keyword_rule():
    df = make_df([("ZOMATO", "UPI/1/DR/ZOMATO", -100)])
    assert result(df) == [("Food", "keyword")]


def test_keywords_match_whole_words_only():
    df = make_df([("OLAF", "UPI/1/DR/OLAF", -10)])
    assert result(df) == [("Other", "none")]


def test_payee_who_sent_money_is_a_person():
    df = make_df([("RIYA", "UPI/1/DR/RIYA", -50), ("RIYA", "UPI/2/CR/RIYA", 100)])
    assert result(df) == [("Person-to-Person", "received-rule")] * 2


def test_unknown_label_is_rejected(tmp_path):
    f = tmp_path / "labels.csv"
    pd.DataFrame({"payee_norm": ["X"], "category": ["Foodd"]}).to_csv(f, index=False)
    with pytest.raises(ValueError):
        load_labels(f)