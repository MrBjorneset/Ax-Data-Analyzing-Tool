# config.py — all constants and configuration for the AX Log Analyzer

# =============== CSV HEADER DETECTION ===============
MAIN_KEYWORDS = [
    "General",
    "Solenoid valves",
    "Gear pump status",
    "Gutter pump status",
    "Peltier",
    "Viscosity control",
]

SUB_KEYWORDS = [
    "Gutter Data Sync No",
    "Ink",
    "Feed",
    "Control voltage",
    "gutter vacuum",
    "Ink temperature",
]

TYPE_KEYWORDS = ["Int8", "Int16", "Int32", "Float", "Bool"]

# =============== PRINTER STATE MACHINE ===============
# States in lifecycle order. Used for state filter ordering.
PRINTER_STATES = [
    "STANDBY",
    "SEQUENCING_ON",
    "JETS_RUNNING",
    "READY_TO_PRINT",
    "SEQUENCING_OFF",
]

# The state considered "steady-state" — default for anomaly analysis.
STEADY_STATE = "READY_TO_PRINT"

# Substring matched (case-insensitive) to find the status column in the DataFrame.
STATUS_COLUMN_KEYWORD = "system status"

# Substring matched (case-insensitive) to find the timestamp column.
TIMESTAMP_COLUMN_KEYWORD = "timestamp"

# =============== ANOMALY DETECTION DEFAULTS ===============
ZSCORE_DEFAULT_THRESHOLD = 3.0
ZSCORE_MIN = 1.0
ZSCORE_MAX = 6.0
ZSCORE_STEP = 0.1

# =============== PLOT PRESETS ===============
# A preset is a named list of plots. Each plot has a title and a list of
# parameter-name substrings (matched case-insensitively against the log's
# columns). Plots whose substrings match no columns are skipped automatically,
# so a preset can safely list more than any single log contains.
#
# Add or edit presets here — the Log Analyzer picks them up automatically.
PLOT_PRESETS = {
    "Full dashboard (17 plots)": [
        {"title": "Ink Pressure Pump (mBar / RPM)", "vars": ["ink system pressure", "speedrpm"]},
        {"title": "Gutter Pump Speed (RPM)",         "vars": ["gutter pump speed"]},
        {"title": "Printhead Temperature (°C)",      "vars": ["target temp", "actual temp"]},
        {"title": "Jet Hours (Seconds)",             "vars": ["jet hours"]},
        {"title": "CPU1 Printing / CPU2 UI (%)",     "vars": ["cpu1 load", "cpu2 load"]},
        {"title": "Viscosity (cP)",                  "vars": ["actual cp", "target cp"]},
        {"title": "Gutter Vacuum (- mBar)",          "vars": ["gutter vacuum"]},
        {"title": "Modulation Voltage (V)",          "vars": ["modulation voltage"]},
        {"title": "Products Coded",                  "vars": ["products coded"]},
        {"title": "Free Memory (kB)",                "vars": ["free memory"]},
        {"title": "Ink Temperature (°C)",            "vars": ["ink temperature"]},
        {"title": "Phase Position 0",                "vars": ["phase position"]},
        {"title": "Line Speed (mm/s)",               "vars": ["line speed"]},
        {"title": "Main PCB Zinc Temperature (°C)",  "vars": ["zinc temperature"]},
        {"title": "ITM Ink & MUM Makeup Levels (%)", "vars": ["itm level", "mum level"]},
        {"title": "Charge Electrode Offset",         "vars": ["charge electrode offset"]},
        {"title": "Jet ON = 1 & Jet OFF = 0",        "vars": ["jet on", "jet running"]},
    ],
    "Key parameters (6 plots)": [
        {"title": "Ink system pressure",     "vars": ["ink system pressure", "pressure set point"]},
        {"title": "Viscosity",               "vars": ["actual cp", "target cp"]},
        {"title": "Ink temperature",         "vars": ["ink temperature"]},
        {"title": "Gutter vacuum",           "vars": ["gutter vacuum"]},
        {"title": "EHT %",                   "vars": ["eht %"]},
        {"title": "Charge electrode offset", "vars": ["charge electrode offset"]},
    ],
}

# Which preset is selected when a log first loads.
DEFAULT_PRESET = "Full dashboard (17 plots)"

# =============== UI ===============
APP_TITLE = "Domino CIJ Ax Uberlog Analyzer"
APP_SUBTITLE = "Interactive log inspection & visualization"
APP_ICON = "📊"