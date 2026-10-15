"""
TRANSFORM (cleaning) step: fix formatting problems that do not make a row wrong.

Examples: "  RAHUL.SHARMA@GMAIL.COM " -> "rahul.sharma@gmail.com",
          "retail" -> "Retail", "delivered" -> "DELIVERED", "+91-98765-43210" -> "+919876543210".

Cleaning runs BEFORE validation, so a value is only rejected if it is still
wrong after these safe, rule-based fixes.
"""

import re

import pandas as pd

SEGMENTS = {"retail": "Retail", "smb": "SMB", "corporate": "Corporate"}


def _tidy_name(name: str) -> str:
    # Only re-case names typed in ALL lower or ALL upper case; keep "McKenzie" as it is.
    if name and (name.islower() or name.isupper()):
        return name.title()
    return name


def _tidy_phone(phone: str) -> str:
    # Keep a leading "+" and the digits; drop spaces, dashes and brackets.
    if not phone:
        return phone
    digits = re.sub(r"\D", "", phone)
    if phone.startswith("+"):
        return "+" + digits
    if len(digits) == 10:              # local Indian mobile number without country code
        return "+91" + digits
    return digits


def clean(df: pd.DataFrame, dataset: str) -> tuple[pd.DataFrame, int]:
    """Return the cleaned DataFrame and how many cell values were changed."""
    before = df.copy()
    text_columns = [c for c in df.columns if c != "source_row"]
    df[text_columns] = df[text_columns].apply(lambda col: col.str.strip())

    if dataset == "customers":
        df["email"] = df["email"].str.lower()
        df["first_name"] = df["first_name"].map(_tidy_name)
        df["last_name"] = df["last_name"].map(_tidy_name)
        df["segment"] = df["segment"].map(lambda s: SEGMENTS.get(s.lower(), s))
        df["phone"] = df["phone"].map(_tidy_phone)
    elif dataset == "products":
        df["sku"] = df["sku"].str.upper()
    elif dataset == "orders":
        df["status"] = df["status"].str.upper()
    elif dataset == "order_items":
        df["sku"] = df["sku"].str.upper()
    elif dataset == "payments":
        df["status"] = df["status"].str.upper()
        df["payment_method"] = df["payment_method"].str.upper()

    changed = int((before[text_columns] != df[text_columns]).sum().sum())
    return df, changed
