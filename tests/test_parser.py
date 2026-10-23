import pandas as pd
from src.parser import _parse_block, check_balance


def test_debit_split_over_three_lines():
    row = _parse_block("14-Oct-26", [
        "UPI/111111111111/DR/TEST",
        "S12345678 Transfer 20.00 - 464.28",
        "(14-Oct-26) SHOP/BANK/Sent usin",
    ])
    assert row["amount"] == -20.0
    assert row["balance"] == 464.28
    assert row["payee"] == "TEST SHOP"


def test_credit_is_positive():
    row = _parse_block("12-Oct-26", [
        "UPI/222222222222/CR/FRIEND",
        "C98765432 Transfer - 200.00 858.00",
        "(12-Oct-26) NAME/BANK/Payment f",
    ])
    assert row["amount"] == 200.0


def test_indian_number_format_and_other_reference_prefix():
    row = _parse_block("05-Jan-26", [
        "TO TRF - RDP: 334904000007783-",
        "IB165424 Transfer 1,00,000.00 - 6,497.38",
        "(05-Jan-26) SOMEONE",
    ])
    assert row["amount"] == -100000.0
    assert row["balance"] == 6497.38


def test_block_without_amounts_is_skipped():
    assert _parse_block("14-Oct-26", ["just some text"]) is None


def test_balance_check_passes_on_a_consistent_statement():
    # newest first: 484.28 - 20 = 464.28
    df = pd.DataFrame({"amount": [-20.0, -10.0], "balance": [464.28, 484.28]})
    assert check_balance(df).empty


def test_balance_check_flags_a_broken_chain():
    df = pd.DataFrame({"amount": [-20.0, -10.0], "balance": [464.28, 999.0]})
    assert len(check_balance(df)) == 1