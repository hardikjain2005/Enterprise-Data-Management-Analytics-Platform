"""EXTRACT step: read a raw CSV file exactly as it is."""

from pathlib import Path

import pandas as pd


def read_csv(path: Path) -> pd.DataFrame:
    """
    Read every column as TEXT (dtype=str) and keep empty cells as "".

    Why: if pandas guessed the types itself, a value like "N/A" would silently
    become NaN and "00123" would become 123. We want to SEE bad values so the
    validation step can report them, so all type conversion happens later.
    """
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    # Line number in the file (header is line 1), so issues can point to the exact row.
    df.insert(0, "source_row", range(2, len(df) + 2))
    return df
