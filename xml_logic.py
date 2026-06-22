# xml_logic.py — XML clean/_rt comparison logic.
# Pure data logic extracted from the old Compare_xml.py — no Streamlit imports.
# The page in pages/2_Settings_Inventory.py handles all rendering.

import pandas as pd


# ----------------------- important settings (label -> path) -----------------
# Order here is the order shown in the top table. Paths use the same notation
# as the full table; matching is namespace/root tolerant (see _norm).
IMPORTANT_SETTINGS = [
    # --- Printer identity & hardware ---
    ("Printer serial number",             "root/PrinterIdentity/SerialNumber"),
    ("Print head",                        "root/HardwareConfig/PrintheadName"),
    ("Throw distance",                    "root/HardwareConfig/NozzleThrowDistance_mm"),
    ("Print Height",                      "root/sectionAL/housekeeping:cfg:VectorControllerConfig/elem#18/housekeeping:cfg:ControllerConfig/PrintHeight_pc"),
    ("Air dryer",                         "root/HardwareConfig/AirDryerAvailable"),

    # --- Ink ---
    ("Current ink",                       "root/InkType/InkName"),
    ("Ink pressure target",               "root/sectionAL/housekeeping:cfg:VectorControllerConfig/elem#3/housekeeping:cfg:ControllerConfig/TargetPressureViaFeedMb"),

    # --- Encoder, speed & digital gearbox ---
    ("Encoder input",                     "root/DataRouting/ConfigVector/elem/DataRouting:Configuration/EncoderSource"),
    ("Encoder mode",                      "root/DataRouting/ConfigVector/elem/DataRouting:Configuration/EncoderMode"),
    ("Encoder direction",                 "root/DataRouting/ConfigVector/elem/DataRouting:Configuration/EncoderDirection"),
    ("Digital gearbox multiplier",        "root/DataRouting/ConfigVector/elem/DataRouting:Configuration/Multiplier"),
    ("Digital gearbox divider",           "root/DataRouting/ConfigVector/elem/DataRouting:Configuration/Divider"),
    ("Calibration distance",              "root/Encoder/ExternalEncoderCalibrationDistanceMM"),
    ("Calibration pulse count",           "root/Encoder/ExternalEncoderCalibrationPulseCount"),
    ("Internal print speed",              "root/Encoder/InternalVelocityGoal"),
    ("Encoder stroke resolution",         "root/Encoder/InternalStrokeResolutionPulsesPerStroke"),
    ("Internal distance interval",        "root/Encoder/InternalDistanceIntervalMM"),

    # --- Print trigger & product detect ---
    ("Trigger by 0=internal 1=external",  "root/DataRouting/ConfigVector/elem#2/DataRouting:Configuration/External"),
    ("Trigger level 0=low 1=high",        "root/DataRouting/ConfigVector/elem#2/DataRouting:Configuration/ActiveLevel"),
    ("Print delay",                       "root/ProductDetect/PrintDelayGoals/elem/pair/second/simple"),
    ("Stroke pitch",                      "root/printing/PrintingConfig/strokePitch"),
    ("Stroke release mode",               "root/ProductDetect/TofCalculationMode"),

    # --- Text appearance ---
    ("Bold text",                         "root/printsystem/GlobalBold"),
    ("Invert text",                       "root/printsystem/GlobalInvert"),
    ("Reverse text",                      "root/printsystem/GlobalReverse"),

    # --- EHT ---
    ("EHT trip mode",                     "root/sectionAL/housekeeping:cfg:VectorControllerConfig/elem#25/housekeeping:cfg:ControllerConfig/m_eEhtTripMode"),

    # --- Maintenance & inspection ---
    ("ITM life first warning",            "root/sectionAL/housekeeping:cfg:VectorControllerConfig/elem/housekeeping:cfg:ControllerConfig/RuntimeITMLifeFirstWarning_hrs"),
    ("ITM second warning",                "root/sectionAL/housekeeping:cfg:VectorControllerConfig/elem/housekeeping:cfg:ControllerConfig/RuntimeITMLifeSecondWarning_hrs"),
    ("Grace period",                      "root/sectionAL/housekeeping:cfg:VectorControllerConfig/elem/housekeeping:cfg:ControllerConfig/ITMGracePeriod_hrs"),
    ("Inspection mode",                   "root/syscfg:service:InspectionInterval/InspectionTimeMode"),
    ("Inspection date",                   "root/syscfg:service:InspectionInterval/NextInspectionDate"),

    # --- Network ---
    ("Enable DHCP",                       "root/CommunicationService/NetworkConfigurationParameters/elem#2/pair/second/NetworkAdapterDetails/isDHCPEnabled"),
    ("IP address",                        "root/CommunicationService/NetworkConfigurationParameters/elem/pair/second/NetworkAdapterDetails/ipAddress"),
    ("Subnet mask",                       "root/CommunicationService/NetworkConfigurationParameters/elem/pair/second/NetworkAdapterDetails/subnetMask"),
    ("Default gateway",                   "root/CommunicationService/NetworkConfigurationParameters/elem/pair/second/NetworkAdapterDetails/defaultGatewayAddress"),
    ("Domain name",                       "root/CommunicationService/NetworkConfigurationParameters/elem#3/pair/second/NetworkAdapterDetails/domainName"),
    ("DNS server",                        "root/CommunicationService/NetworkConfigurationParameters/elem#3/pair/second/NetworkAdapterDetails/primaryNameServerDNS"),
]


# ----------------------------- core extraction -----------------------------

def build_map(elem, path="", acc=None):
    """Map a readable path -> text value for every element, keyed by `name`."""
    if acc is None:
        acc = {}

    tag = elem.tag.split("}")[-1]               # drop namespace prefix
    name = elem.get("name", tag)                # prefer the 'name' attribute
    here = f"{path}/{name}" if path else name

    text = (elem.text or "").strip()
    if text:
        acc[here] = text

    seen = {}
    for child in elem:
        child_tag = child.tag.split("}")[-1]
        child_name = child.get("name", child_tag)
        key = f"{here}/{child_name}"
        seen[key] = seen.get(key, 0) + 1
        if seen[key] > 1:                       # repeated name -> index it
            child.set("name", f"{child_name}#{seen[key]}")
        build_map(child, here, acc)

    return acc


def merge_pair(file_label, root_clean, root_rt):
    """Return one row per setting across a clean/_rt pair."""
    map_c = build_map(root_clean)
    map_r = build_map(root_rt)

    rows = []
    for key in sorted(set(map_c) | set(map_r)):
        in_c, in_r = key in map_c, key in map_r
        vc = map_c.get(key, "")
        vr = map_r.get(key, "")
        if in_c and in_r:
            status = "changed" if vc != vr else "unchanged"
        elif in_c:
            status = "only in clean"
        else:
            status = "only in real-time"
        rows.append({"File": file_label, "Setting": key,
                     "Clean": vc, "Real-time": vr, "Status": status})
    return rows


# ----------------------------- pairing helpers -----------------------------

def pair_base(filename):
    stem = filename[:-4] if filename.lower().endswith(".xml") else filename
    if stem.endswith("_rt"):
        return stem[:-3], "rt"
    return stem, "base"


STATUS_ORDER = {"changed": 0, "only in clean": 1, "only in real-time": 2, "unchanged": 3}


def build_dataframe(pairs):
    all_rows = []
    for label, root_c, root_r in pairs:
        all_rows.extend(merge_pair(label, root_c, root_r))
    df = pd.DataFrame(all_rows, columns=["File", "Setting", "Clean", "Real-time", "Status"])
    if not df.empty:
        df["_o"] = df["Status"].map(STATUS_ORDER)
        df = df.sort_values(["_o", "File", "Setting"]).drop(columns="_o").reset_index(drop=True)
    return df


# ----------------------- important-settings matching ------------------------

def _norm(path, drop_root=False):
    """Normalize a path: reduce each segment to the text after the last ':',
    lowercased. Optionally drop the leading (root) segment."""
    segs = [s.split(":")[-1] for s in path.strip().split("/") if s]
    if drop_root and len(segs) > 1:
        segs = segs[1:]
    return "/".join(segs).lower()


def build_important_table(df):
    """One row per IMPORTANT_SETTINGS entry, in the given order.
    Matches namespace/root-tolerantly; unmatched entries -> 'not found'."""
    by_full, by_noroot = {}, {}
    for _, r in df.iterrows():
        by_full.setdefault(_norm(r["Setting"]), r)
        by_noroot.setdefault(_norm(r["Setting"], drop_root=True), r)

    rows = []
    for label, path in IMPORTANT_SETTINGS:
        r = by_full.get(_norm(path))
        if r is None:
            r = by_noroot.get(_norm(path, drop_root=True))
        if r is not None:
            rows.append({"Setting": label, "Clean": r["Clean"],
                         "Real-time": r["Real-time"], "Status": r["Status"]})
        else:
            rows.append({"Setting": label, "Clean": "", "Real-time": "",
                         "Status": "not found"})
    return pd.DataFrame(rows, columns=["Setting", "Clean", "Real-time", "Status"])
