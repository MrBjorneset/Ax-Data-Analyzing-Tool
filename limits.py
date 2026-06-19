# limits.py — Engineering parameter limits for the Domino Ax-Series CIJ printer.
#
# Sources:
#   - Domino Ax-Series Engineer's Reference Guide EPT026795 Issue 32 (Jan 2026)
#   - Observed steady-state values from field logs (READY_TO_PRINT state)
#
# HOW LIMITS WORK
# ---------------
# Each entry in PARAMETER_LIMITS is keyed on a substring of the DataFrame column name
# (matched case-insensitively). The value is a dict with:
#   min       : lower bound — values below this are flagged (None = no lower bound)
#   max       : upper bound — values above this are flagged (None = no upper bound)
#   unit      : display unit string
#   source    : where the limit comes from
#   note      : extra context for the engineer
#
# PARAMETERS INTENTIONALLY EXCLUDED
# ----------------------------------
# Viscosity (target cp, actual cp): ink-type dependent. The target is stored in the
#   log itself ("target cp @ 25 degC"). Use that to derive limits at runtime rather
#   than hardcoding here — see compute_viscosity_limits() below.
#
# System pressure set point: nozzle-size dependent. Use check_pressure_limits()
#   below which reads the set point and nozzle size from the log itself.
#
# Gutter pump speed: automatically controlled by the printer firmware based on
#   conduit length and nozzle size. No fixed engineering limit applies.

from __future__ import annotations
import pandas as pd


# ---------------------------------------------------------------------------
# STATIC LIMITS
# Fixed bounds that apply regardless of ink type or nozzle size.
# ---------------------------------------------------------------------------

PARAMETER_LIMITS: dict[str, dict] = {

    # --- Ink system pressure (actual, mBar) ---
    # The window of usable pressure is ~300 mBar wide (EPT026795 p.23-6).
    # Set point for 75µm nozzle = 2700 mBar; for 60µm = 3000 mBar.
    # We flag anything more than 200 mBar from the set point as a warning.
    # Use check_pressure_limits() for a log-aware version.
    "ink system pressure": {
        "min": 2300,   # well below any nozzle's set point — likely pump fault
        "max": 3500,   # well above any nozzle's set point — likely blockage
        "unit": "mBar",
        "source": "EPT026795 p.23-5 to 23-6",
        "note": "Actual limit is set-point ±150 mBar. Use check_pressure_limits() for "
                "a nozzle-aware check.",
    },

    # --- Gutter vacuum (mBar, negative values) ---
    # At max gutter pump speed with 60µm nozzle: ~-120 mBar (EPT026795 p.18-68).
    # Alert 564 fires when vacuum cannot be generated (too close to 0).
    # Alert 561 fires on vacuum loss but recovery.
    # With gutter blocked, value goes more negative (towards -600 mBar).
    # Steady-state in this log: mean ~-358 mBar, std ~43 mBar.
    "gutter vacuum": {
        "min": -600,   # more negative than this → gutter likely blocked/restricted
        "max": -50,    # less negative than this → vacuum loss, possible pump fault
        "unit": "mBar",
        "source": "EPT026795 p.18-68, alert 561/564",
        "note": "Value should be negative. -120 is typical at max pump speed for 60µm. "
                "Greater than -180 mBar suggests gutter pipe blockage.",
    },

    # --- Ink temperature (raw sensor units, = °C × 1000) ---
    # Printer operating environment: 5–45°C (EPT026795 p.30-6, p.2-19).
    # Below 15°C the printer requires 30 min warm-up (EPT026795 p.2-21).
    # Ink temperature tracks ambient closely; typical steady-state ~20–25°C.
    # Stored in the log as millidegrees (e.g. 21000 = 21.0°C).
    "ink temperature": {
        "min": 5000,    # 5°C — below operating range
        "max": 45000,   # 45°C — above operating range
        "unit": "m°C (÷1000 for °C)",
        "source": "EPT026795 p.30-6, p.2-19",
        "note": "Divide by 1000 for °C. Below 15000 (15°C) requires warm-up. "
                "Above 35000 (35°C) requires daily wash-down.",
    },

    # --- Feed pump current (mA) ---
    # No explicit spec in the manual but observed steady-state in this log:
    # mean ~1863 mA, std ~48 mA during READY_TO_PRINT.
    # Very low current = pump not running / stalled.
    # Very high current = pump working against a blockage or over-pressured.
    "Feed Pump Current": {
        "min": 500,     # well below idle current — pump likely stalled or disconnected
        "max": 3000,    # high sustained current suggests mechanical issue
        "unit": "mA",
        "source": "Field observation (this log: mean 1863 mA, std 48 mA)",
        "note": "No formal spec in EPT026795. Limits derived from observed steady-state. "
                "Refine after collecting more logs.",
    },

    # --- EHT % (deflection high voltage, % of nominal 4.2 kV) ---
    # Nominal EHT plate voltage: ±4.2 kV (EPT026795 p.35-36).
    # EHT % in the log represents this as a percentage.
    # Normal operating range is 85–100%. Trips indicate electrical fault.
    "EHT %": {
        "min": 80,
        "max": 105,
        "unit": "%",
        "source": "EPT026795 p.35-36, p.4-68",
        "note": "Nominal ±4.2 kV deflection plates. Below 80% may indicate contamination "
                "or plate misalignment. Trip events are logged separately.",
    },

    # --- Charge electrode offset (mV or raw units) ---
    # Used for drop charging. Significant drift from zero may indicate
    # contamination on the charge electrode or jet misalignment.
    "Charge electrode Offset": {
        "min": -500,
        "max": 500,
        "unit": "raw",
        "source": "EPT026795 p.12-38 (charge electrode alignment)",
        "note": "Large offset suggests ink on charge electrode or jet misalignment. "
                "Clean print head if offset grows.",
    },

    # --- System fan speed ---
    # Electronics cooling. Should be non-zero when printer is running.
    "System Fan Speed": {
        "min": 500,
        "max": None,    # no upper limit — faster is fine
        "unit": "rpm",
        "source": "Engineering judgement",
        "note": "Fan stopping while printer is running risks electronics overheating.",
    },
}


# ---------------------------------------------------------------------------
# DYNAMIC LIMIT HELPERS
# Limits that depend on values read from the log itself.
# ---------------------------------------------------------------------------

def get_pressure_limits(df: pd.DataFrame) -> tuple[float, float] | None:
    """
    Return (min, max) ink pressure limits based on the pressure set point
    stored in the log (±150 mBar = half the 300 mBar usable window).

    Returns None if the set point column cannot be found.
    """
    setpoint_col = next(
        (c for c in df.columns if "pressure set point" in c.lower()),
        None
    )
    if setpoint_col is None:
        return None

    setpoint = pd.to_numeric(df[setpoint_col], errors="coerce").median()
    if pd.isna(setpoint):
        return None

    return (setpoint - 150, setpoint + 150)


def get_viscosity_limits(df: pd.DataFrame) -> tuple[float, float] | None:
    """
    Return (min, max) viscosity limits based on the target cP stored in the log.
    Allows ±20% of target as a reasonable operating band.

    Returns None if the target viscosity column cannot be found.
    """
    target_col = next(
        (c for c in df.columns if "target cp" in c.lower() and "25" in c),
        None
    )
    if target_col is None:
        return None

    target = pd.to_numeric(df[target_col], errors="coerce").median()
    if pd.isna(target) or target <= 0:
        return None

    return (target * 0.80, target * 1.20)


# ---------------------------------------------------------------------------
# LIMIT CHECKING
# ---------------------------------------------------------------------------

def check_limits(
    df: pd.DataFrame,
    columns: list[str],
    extra_limits: dict[str, tuple[float, float]] | None = None,
) -> pd.DataFrame | None:
    """
    Check selected columns against engineering limits.

    extra_limits: optional dict of { column_name: (min, max) } to supplement
                  PARAMETER_LIMITS (used for dynamic limits like pressure and viscosity).

    Returns a summary DataFrame with one row per matched column, or None if
    no columns matched any limit definition.
    """
    extra_limits = extra_limits or {}
    rows = []

    for col in columns:
        if not pd.api.types.is_numeric_dtype(df[col]):
            continue

        # Match column to a limit definition (substring, case-insensitive)
        limit_def = next(
            (v for k, v in PARAMETER_LIMITS.items() if k.lower() in col.lower()),
            None
        )

        # Also check extra_limits (exact column name match)
        dynamic = extra_limits.get(col)

        if limit_def is None and dynamic is None:
            continue

        lo = limit_def["min"] if limit_def else None
        hi = limit_def["max"] if limit_def else None
        unit = limit_def.get("unit", "") if limit_def else ""
        note = limit_def.get("note", "") if limit_def else ""

        # Dynamic limits override static ones if provided
        if dynamic:
            lo, hi = dynamic

        series = pd.to_numeric(df[col], errors="coerce").dropna()
        if series.empty:
            continue

        below = int((series < lo).sum()) if lo is not None else 0
        above = int((series > hi).sum()) if hi is not None else 0
        total_violations = below + above

        lo_str = f"{lo:.1f}" if lo is not None else "—"
        hi_str = f"{hi:.1f}" if hi is not None else "—"

        if total_violations > 0:
            status = "🔴 Out of spec"
        else:
            status = "✅ OK"

        rows.append({
            "Parameter":          col,
            "Min limit":          lo_str,
            "Max limit":          hi_str,
            "Unit":               unit,
            "Below min":          below,
            "Above max":          above,
            "Total violations":   total_violations,
            "Status":             status,
            "Note":               note,
        })

    if not rows:
        return None

    return pd.DataFrame(rows).set_index("Parameter")