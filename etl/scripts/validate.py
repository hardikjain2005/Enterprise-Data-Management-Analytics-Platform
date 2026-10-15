"""
VALIDATE step: row-level data-quality rules, written once and driven by RULES.

Every rule produces "issues". A row with at least one issue is REJECTED: it is
not loaded, but it is recorded in data_quality_issues (and in a rejected CSV),
so nothing disappears silently.

Checks that need the database (does this customer exist? is this email used
by another customer?) are done later in SQL - see load.py.
"""

from datetime import datetime

import pandas as pd

EMAIL_PATTERN = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"

# One entry per dataset. Reading this dict tells you every rule applied to a file.
RULES = {
    "customers": {
        "columns": ["customer_code", "first_name", "last_name", "email", "phone", "city",
                    "state", "country", "segment", "signup_date"],
        "required": ["customer_code", "first_name", "last_name", "email", "city", "country",
                     "segment", "signup_date"],
        "key": ["customer_code"],                       # identifies a record
        "unique": ["email"],                            # must not repeat across records
        "emails": ["email"],
        "dates": {"signup_date": "%Y-%m-%d"},
        "no_future_dates": ["signup_date"],
        "allowed": {"segment": ["Retail", "SMB", "Corporate"]},
        "numbers": {},
    },
    "products": {
        "columns": ["sku", "product_name", "category", "unit_price", "stock_quantity"],
        "required": ["sku", "product_name", "category", "unit_price", "stock_quantity"],
        "key": ["sku"],
        "numbers": {"unit_price": {"min": 0}, "stock_quantity": {"min": 0, "integer": True}},
    },
    "orders": {
        "columns": ["order_number", "customer_code", "employee_code", "order_date", "status"],
        "required": ["order_number", "customer_code", "order_date", "status"],
        "key": ["order_number"],
        "dates": {"order_date": "%Y-%m-%d %H:%M:%S"},
        "no_future_dates": ["order_date"],
        "allowed": {"status": ["PENDING", "PROCESSING", "SHIPPED", "DELIVERED", "CANCELLED"]},
        "numbers": {},
    },
    "order_items": {
        "columns": ["order_number", "sku", "quantity", "unit_price", "discount_pct"],
        "required": ["order_number", "sku", "quantity", "unit_price", "discount_pct"],
        "key": ["order_number", "sku"],
        "numbers": {"quantity": {"min": 1, "integer": True},
                    "unit_price": {"min": 0},
                    "discount_pct": {"min": 0, "max": 100}},
    },
    "payments": {
        "columns": ["payment_reference", "order_number", "payment_date", "amount",
                    "payment_method", "status"],
        "required": ["payment_reference", "order_number", "payment_date", "amount",
                     "payment_method", "status"],
        "key": ["payment_reference"],
        "dates": {"payment_date": "%Y-%m-%d %H:%M:%S"},
        "no_future_dates": ["payment_date"],
        "numbers": {"amount": {"min": 0.01}},
        "allowed": {"payment_method": ["CARD", "UPI", "NET_BANKING", "BANK_TRANSFER", "WALLET"],
                    "status": ["PENDING", "COMPLETED", "FAILED", "REFUNDED"]},
    },
}


def missing_columns(df: pd.DataFrame, dataset: str) -> list[str]:
    """Schema check: which expected columns are absent from the file?"""
    return [c for c in RULES[dataset]["columns"] if c not in df.columns]


class IssueCollector:
    """Collects issues and remembers which rows are bad."""

    def __init__(self, df: pd.DataFrame, dataset: str):
        self.df = df
        self.key = RULES[dataset]["key"]
        self.issues: list[dict] = []
        self.bad = pd.Series(False, index=df.index)

    def record_id(self, row) -> str:
        value = "|".join(str(row[k]) for k in self.key)
        return value if value.strip("|") else f"row {row['source_row']}"

    def add(self, mask, column, rule, issue_type, severity, message):
        """mask = True for every bad row; message(row) builds the description."""
        for idx in self.df.index[mask]:
            row = self.df.loc[idx]
            self.issues.append({
                "source_row": int(row["source_row"]),
                "record_identifier": self.record_id(row),
                "column_name": column,
                "rule_name": rule,
                "issue_type": issue_type,
                "severity": severity,
                "description": f"Row {row['source_row']}: {message(row)}",
            })
        self.bad |= pd.Series(mask, index=self.df.index)


def validate(df: pd.DataFrame, dataset: str):
    """
    Apply all rules for `dataset`.
    Returns (valid_rows, rejected_rows, issues).
    """
    rules = RULES[dataset]
    found = IssueCollector(df, dataset)
    empty = df[rules["columns"]] == ""

    # 1. Missing required values
    for col in rules["required"]:
        found.add(empty[col], col, "required_value", "MISSING_VALUE", "HIGH",
                  lambda r, c=col: f"'{c}' is required but empty")

    # 2. Email format
    for col in rules.get("emails", []):
        bad = ~empty[col] & ~df[col].str.match(EMAIL_PATTERN)
        found.add(bad, col, "email_format", "INVALID_FORMAT", "MEDIUM",
                  lambda r, c=col: f"'{r[c]}' is not a valid email address")

    # 3. Dates: must parse with the expected format, and must not be in the future
    now = pd.Timestamp(datetime.now())
    for col, fmt in rules.get("dates", {}).items():
        parsed = pd.to_datetime(df[col], format=fmt, errors="coerce")
        bad = ~empty[col] & parsed.isna()
        found.add(bad, col, "valid_date", "INVALID_DATE", "HIGH",
                  lambda r, c=col, f=fmt: f"'{r[c]}' is not a valid date (expected {f})")
        if col in rules.get("no_future_dates", []):
            found.add(parsed > now, col, "no_future_date", "INVALID_DATE", "MEDIUM",
                      lambda r, c=col: f"'{r[c]}' is in the future")

    # 4. Numbers: must be numeric, integer where required, inside min/max
    for col, limits in rules.get("numbers", {}).items():
        parsed = pd.to_numeric(df[col], errors="coerce")
        not_number = ~empty[col] & parsed.isna()
        found.add(not_number, col, "numeric_value", "INVALID_FORMAT", "HIGH",
                  lambda r, c=col: f"'{r[c]}' is not a number")
        if limits.get("integer"):
            found.add(parsed.notna() & (parsed % 1 != 0), col, "integer_value", "INVALID_FORMAT", "MEDIUM",
                      lambda r, c=col: f"'{r[c]}' must be a whole number")
        if "min" in limits:
            too_low = parsed < limits["min"]
            negative = too_low & (parsed < 0)
            found.add(negative, col, "non_negative", "NEGATIVE_VALUE", "HIGH",
                      lambda r, c=col: f"'{c}' is negative ({r[c]})")
            found.add(too_low & ~negative, col, "min_value", "INVALID_VALUE", "MEDIUM",
                      lambda r, c=col, m=limits["min"]: f"'{c}' must be at least {m} (got {r[c]})")
        if "max" in limits:
            found.add(parsed > limits["max"], col, "max_value", "INVALID_VALUE", "MEDIUM",
                      lambda r, c=col, m=limits["max"]: f"'{c}' must be at most {m} (got {r[c]})")

    # 5. Allowed values (code lists)
    for col, allowed in rules.get("allowed", {}).items():
        bad = ~empty[col] & ~df[col].isin(allowed)
        found.add(bad, col, "allowed_values", "INVALID_VALUE", "MEDIUM",
                  lambda r, c=col, a=allowed: f"'{r[c]}' is not one of {a}")

    # 6. Duplicates - checked only among rows that passed the rules above, so
    #    a broken first copy does not cause a good second copy to be dropped.
    #    The FIRST occurrence is kept; later copies are rejected.
    data_cols = rules["columns"]
    for cols, rule in [(rules["key"], "unique_key")] + [([c], f"unique_{c}") for c in rules.get("unique", [])]:
        candidates = df[~found.bad]
        for idx in candidates.index[candidates.duplicated(subset=cols, keep="first")]:
            row = df.loc[idx]
            original = candidates[(candidates[cols] == row[cols]).all(axis=1)].iloc[0]
            if rule == "unique_key" and (original[data_cols] == row[data_cols]).all():
                severity, text = "MEDIUM", f"exact duplicate of row {original['source_row']}"
            elif rule == "unique_key":
                severity, text = "HIGH", f"same key as row {original['source_row']} but different values"
            else:
                severity, text = "HIGH", (f"{cols[0]} '{row[cols[0]]}' is already used by "
                                          f"{found.record_id(original)} (row {original['source_row']})")
            found.add(df.index == idx, ",".join(cols), rule, "DUPLICATE_RECORD", severity, lambda r, t=text: t)

    valid = df[~found.bad].copy()
    rejected = df[found.bad].copy()
    return to_typed(valid, dataset), rejected, found.issues


def to_typed(df: pd.DataFrame, dataset: str) -> pd.DataFrame:
    """Convert validated text columns to real types; empty optional values -> None (NULL)."""
    rules = RULES[dataset]
    for col, fmt in rules.get("dates", {}).items():
        df[col] = pd.to_datetime(df[col], format=fmt)
        if fmt == "%Y-%m-%d":
            df[col] = df[col].dt.date
    for col, limits in rules.get("numbers", {}).items():
        df[col] = pd.to_numeric(df[col])
        if limits.get("integer"):
            df[col] = df[col].astype(int)
    optional = [c for c in rules["columns"] if c not in rules["required"]]
    for col in optional:
        df[col] = df[col].replace("", None)
    return df
