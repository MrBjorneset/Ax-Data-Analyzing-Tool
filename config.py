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

# =============== UI ===============
APP_TITLE = "Domino CIJ Ax Uberlog Analyzer"
APP_SUBTITLE = "Interactive log inspection & visualization"
APP_ICON = "📊"