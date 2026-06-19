# logic.py — data loading, cleaning, filtering, stats, anomaly detection.
# No Streamlit or Plotly imports here — pure data logic only.
# For engineering limit checking, see limits.py.

import pandas as pd
import numpy as np
from io import StringIO

from config import (
    MAIN_KEYWORDS,
    SUB_KEYWORDS,
    TYPE_KEYWORDS,
    PRINTER_STATES,
    STEADY_STATE,
    STATUS_COLUMN_KEYWORD,
    TIMESTAMP_COLUMN_KEYWORD,
)


# =============== CSV PARSING ===============

def _find_row_with_keywords(lines: list[str], keywords: list[str]) -> int | None:
    for i, line in enumerate(lines):
        if all(k in line for k in keywords):
            return i
    return None


def _detect_header_rows(lines: list[str]) -> tuple[int, int, int]:
    r1 = _find_row_with_keywords(lines, MAIN_KEYWORDS)
    r2 = _find_row_with_keywords(lines, SUB_KEYWORDS)
    r3 = _find_row_with_keywords(lines, TYPE_KEYWORDS)
    if None in (r1, r2, r3):
        raise ValueError(
            "Could not detect header rows. "
            "Check that the CSV is a valid Domino Ax Uberlog file."
        )
    return r1, r2, r3


def _fill_forward(lst: list[str]) -> list[str]:
    """Forward-fill empty strings with the last non-empty value."""
    out, last = [], ""
    for v in lst:
        v = v.strip()
        out.append(v if v else last)
        if v:
            last = v
    return out


def _pad_equal(*lists: list) -> list[list]:
    """Pad all lists to the same length with empty strings."""
    m = max(len(l) for l in lists)
    return [l + [""] * (m - len(l)) for l in lists]


def _extract_metadata(lines: list[str], stop_row: int) -> dict[str, str]:
    """Parse key-value metadata rows above the header block."""
    info = {}
    for line in lines[:stop_row]:
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 2 and parts[0]:
            info[parts[0]] = parts[1]
    return info


def _build_column_names(h1: list, h2: list, h3: list) -> list[str]:
    """Combine the three header rows into unique, readable column names."""
    cols = []
    for g, s, t in zip(h1, h2, h3):
        name = g
        if s:
            name += f" - {s}"
        if t:
            name += f" ({t})"
        cols.append(name)
    return cols


def _build_param_map(h1: list, h2: list, cols: list) -> dict:
    """
    Build a nested dict: { main_group: { sub_label: column_name } }
    Used by the UI to render grouped multiselects.
    """
    param_map = {}
    for g, s, c in zip(h1, h2, cols):
        param_map.setdefault(g, {})
        param_map[g][s if s else "(None)"] = c
    return param_map


def load_and_clean_csv(uploaded_file) -> tuple[pd.DataFrame, dict, dict]:
    """
    Parse a Domino Ax Uberlog CSV file.

    Returns:
        df        : cleaned DataFrame with readable column names
        param_map : nested dict for grouped parameter selection in the UI
        metadata  : dict of key-value info rows from the file header
    """
    content = uploaded_file.read().decode("utf-8", errors="ignore")
    lines = content.splitlines()

    r1, r2, r3 = _detect_header_rows(lines)
    metadata = _extract_metadata(lines, r1)

    h1 = _fill_forward(lines[r1].split(","))
    h2 = _fill_forward(lines[r2].split(","))
    h3 = lines[r3].split(",")
    h1, h2, h3 = _pad_equal(h1, h2, h3)

    df = pd.read_csv(StringIO(content), skiprows=r3 + 1, header=None)
    df = df.iloc[:, :len(h1)]
    df.columns = _build_column_names(h1, h2, h3)

    param_map = _build_param_map(h1, h2, df.columns.tolist())
    return df, param_map, metadata


# =============== STATE FILTERING ===============

def find_status_column(df: pd.DataFrame) -> str | None:
    """Return the name of the system-status column, or None if not found."""
    for col in df.columns:
        if STATUS_COLUMN_KEYWORD.lower() in col.lower():
            return col
    return None


def find_timestamp_column(df: pd.DataFrame) -> str | None:
    """Return the name of the timestamp column, or None if not found."""
    for col in df.columns:
        if TIMESTAMP_COLUMN_KEYWORD.lower() in col.lower():
            return col
    return None


def parse_timestamps(df: pd.DataFrame, timestamp_col: str) -> pd.Series:
    """
    Parse the timestamp column to datetime. Returns a Series of datetime values
    aligned to df's index. Unparseable values become NaT.
    """
    return pd.to_datetime(df[timestamp_col], errors="coerce")


def get_log_date_range(df: pd.DataFrame, timestamp_col: str) -> dict | None:
    """
    Return a dict with start, end, duration, and date of the log session,
    derived from the timestamp column. Returns None if timestamps can't be parsed.
    """
    ts = parse_timestamps(df, timestamp_col).dropna()
    if ts.empty:
        return None

    start    = ts.min()
    end      = ts.max()
    duration = end - start

    total_seconds = int(duration.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    duration_str = f"{hours}h {minutes}m {seconds}s" if hours else f"{minutes}m {seconds}s"

    return {
        "date":     start.strftime("%d %B %Y"),
        "start":    start.strftime("%H:%M:%S"),
        "end":      end.strftime("%H:%M:%S"),
        "duration": duration_str,
    }


def get_available_states(df: pd.DataFrame, status_col: str) -> list[str]:
    """
    Return states present in the log, ordered by the known lifecycle sequence.
    Unknown states are appended at the end.
    """
    present = df[status_col].dropna().unique().tolist()
    ordered = [s for s in PRINTER_STATES if s in present]
    extras  = [s for s in present if s not in PRINTER_STATES]
    return ordered + extras


def filter_by_states(
    df: pd.DataFrame,
    status_col: str,
    selected_states: list[str],
) -> pd.DataFrame:
    """
    Return a copy of df containing only rows whose status is in selected_states.
    Index is reset so downstream code can use positional indexing safely.
    """
    if not selected_states:
        return df.copy().reset_index(drop=True)
    mask = df[status_col].isin(selected_states)
    return df[mask].copy().reset_index(drop=True)


# =============== STATISTICS ===============

def compute_stats(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame | None:
    """
    Return min / max / mean / std for each selected numeric column.
    Non-numeric columns are silently skipped. Returns None if none are numeric.
    """
    numeric_cols = [c for c in columns if pd.api.types.is_numeric_dtype(df[c])]
    if not numeric_cols:
        return None

    stats = df[numeric_cols].agg(["min", "max", "mean", "std"]).T
    stats.columns = ["Min", "Max", "Mean", "Std Dev"]
    stats.index.name = "Parameter"
    return stats.round(4)


# =============== ANOMALY DETECTION ===============

def compute_zscore_anomalies(
    df: pd.DataFrame,
    columns: list[str],
    threshold: float = 3.0,
) -> tuple[pd.DataFrame | None, pd.DataFrame | None, pd.DataFrame | None]:
    """
    Z-score anomaly detection for numeric columns.

    Returns:
        anomaly_mask    : bool DataFrame — True where |z| > threshold
        zscore_df       : float DataFrame of z-score values
        summary         : per-column anomaly count, worst z-score, and status label
    All three are None if no numeric columns are found.
    """
    numeric_cols = [c for c in columns if pd.api.types.is_numeric_dtype(df[c])]
    if not numeric_cols:
        return None, None, None

    data = df[numeric_cols].copy()
    mean = data.mean()
    std  = data.std().replace(0, np.nan)   # avoid divide-by-zero on constant cols

    zscore_df    = (data - mean).div(std).fillna(0)
    anomaly_mask = zscore_df.abs() > threshold

    summary = pd.DataFrame([
        {
            "Parameter":          col,
            "Anomalies detected": int(anomaly_mask[col].sum()),
            "Worst Z-score":      round(float(zscore_df[col].abs().max()), 3),
            "Status":             "⚠️ Check" if anomaly_mask[col].any() else "✅ OK",
        }
        for col in numeric_cols
    ]).set_index("Parameter")

    return anomaly_mask, zscore_df, summary