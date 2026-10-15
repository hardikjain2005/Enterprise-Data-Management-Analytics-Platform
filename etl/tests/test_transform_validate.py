"""Unit tests for the ETL cleaning and validation rules (no database needed)."""

import pandas as pd

from transform import clean
from validate import missing_columns, validate

CUSTOMER_COLUMNS = ["customer_code", "first_name", "last_name", "email", "phone", "city", "state",
                    "country", "segment", "signup_date"]


def customers_df(rows):
    df = pd.DataFrame(rows, columns=CUSTOMER_COLUMNS).astype(str)
    df.insert(0, "source_row", range(2, len(df) + 2))
    return df


def good_customer(code="CUST-1", email="a.b@gmail.com", **overrides):
    row = dict(customer_code=code, first_name="Asha", last_name="Rao", email=email, phone="+919800000000",
               city="Pune", state="Maharashtra", country="India", segment="Retail", signup_date="2025-03-01")
    row.update(overrides)
    return [row[c] for c in CUSTOMER_COLUMNS]


def rules_hit(issues):
    return sorted(i["rule_name"] for i in issues)


def test_cleaning_fixes_formatting():
    df = customers_df([good_customer(first_name="  asha ", email=" A.B@GMAIL.COM ", segment="retail",
                                     phone="98765 43210")])
    cleaned, changed = clean(df, "customers")
    row = cleaned.iloc[0]
    assert (row.first_name, row.email, row.segment, row.phone) == ("Asha", "a.b@gmail.com", "Retail", "+919876543210")
    assert changed == 4


def test_valid_rows_pass_and_are_typed():
    valid, rejected, issues = validate(customers_df([good_customer()]), "customers")
    assert len(valid) == 1 and rejected.empty and issues == []
    assert str(valid.iloc[0].signup_date) == "2025-03-01"
    assert valid.iloc[0].state == "Maharashtra"


def test_each_customer_rule():
    df = customers_df([
        good_customer("C1", email=""),                        # missing value
        good_customer("C2", email="not-an-email"),            # bad format
        good_customer("C3", email="c3@x.com", signup_date="2025-02-30"),   # impossible date
        good_customer("C4", email="c4@x.com", signup_date="2099-01-01"),   # future date
        good_customer("C5", email="c5@x.com", segment="Enterprise"),       # not allowed
    ])
    valid, rejected, issues = validate(df, "customers")
    assert valid.empty and len(rejected) == 5
    assert rules_hit(issues) == ["allowed_values", "email_format", "no_future_date", "required_value", "valid_date"]


def test_duplicates_keep_first_and_grade_severity():
    df = customers_df([
        good_customer("C1", email="one@x.com"),
        good_customer("C1", email="one@x.com"),               # exact copy -> MEDIUM
        good_customer("C1", email="other@x.com"),             # same key, different data -> HIGH
        good_customer("C2", email="one@x.com"),               # email used by C1 -> HIGH
    ])
    valid, rejected, issues = validate(df, "customers")
    assert list(valid.customer_code) == ["C1"]
    assert [(i["rule_name"], i["severity"]) for i in issues] == [
        ("unique_key", "MEDIUM"), ("unique_key", "HIGH"), ("unique_email", "HIGH")]


def test_bad_first_copy_does_not_reject_good_second_copy():
    df = customers_df([good_customer("C1", email="broken"), good_customer("C1", email="ok@x.com")])
    valid, _, issues = validate(df, "customers")
    assert list(valid.email) == ["ok@x.com"]
    assert rules_hit(issues) == ["email_format"]


def test_numeric_rules_on_order_items():
    df = pd.DataFrame({
        "order_number": ["O1", "O2", "O3", "O4", "O5"],
        "sku": ["S1"] * 5,
        "quantity": ["2", "0", "-1", "1.5", "3"],
        "unit_price": ["10", "10", "10", "10", "abc"],
        "discount_pct": ["0", "0", "0", "0", "0"],
    })
    df.insert(0, "source_row", range(2, 7))
    valid, _, issues = validate(df, "order_items")
    assert list(valid.order_number) == ["O1"]
    assert rules_hit(issues) == ["integer_value", "min_value", "non_negative", "numeric_value"]


def test_missing_column_is_detected():
    df = customers_df([good_customer()]).drop(columns=["email"])
    assert missing_columns(df, "customers") == ["email"]
