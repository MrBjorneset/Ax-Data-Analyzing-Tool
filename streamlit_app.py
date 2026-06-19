# streamlit_app.py — entry point for the combined Domino Ax toolkit.
#
# Streamlit multipage app. The pages/ folder gives the sidebar navigation:
#   streamlit_app.py              -> this Home page (+ service-backup upload)
#   pages/1_Log_Analyzer.py       -> Uberlog CSV analyzer
#   pages/2_Settings_Inventory.py -> XML clean/_rt config comparison
#
# Files uploaded here as a "service backup" are sorted by type and stored in
# st.session_state, so each page can use them without a second upload.

import streamlit as st

from backup import classify

st.set_page_config(
    page_title="Domino Ax Toolkit",
    page_icon="🛠️",
    layout="wide",
)

st.title("🛠️ Domino Ax Toolkit")
st.caption("A combined toolkit for Domino Ax-Series CIJ printers.")

st.divider()

# =============== SERVICE BACKUP UPLOAD ===============
st.subheader("📦 Upload a service backup")
st.write(
    "Drop in a whole machine backup at once — loose files or a `.zip`. "
    "The Uberlog **CSV** goes to the Log Analyzer; the **XML** config files go "
    "to the Settings Inventory. Each tool will offer these files automatically."
)

backup_files = st.file_uploader(
    "Backup files (.csv, .xml, .zip)",
    type=["csv", "tsv", "xml", "zip"],
    accept_multiple_files=True,
    key="backup_uploader",
)

if backup_files:
    csvs, xmls = classify(backup_files)
    st.session_state["backup_csvs"] = csvs
    st.session_state["backup_xmls"] = xmls

backup_csvs = st.session_state.get("backup_csvs", [])
backup_xmls = st.session_state.get("backup_xmls", [])

if backup_csvs or backup_xmls:
    # Count XML clean/_rt pairs for a friendlier summary
    bases = {}
    for name, _ in backup_xmls:
        stem = name[:-4] if name.lower().endswith(".xml") else name
        kind = "rt" if stem.endswith("_rt") else "base"
        if kind == "rt":
            stem = stem[:-3]
        bases.setdefault(stem, set()).add(kind)
    n_pairs = sum(1 for v in bases.values() if {"base", "rt"} <= v)

    c1, c2, c3 = st.columns(3)
    c1.metric("CSV logs", len(backup_csvs))
    c2.metric("XML files", len(backup_xmls))
    c3.metric("XML pairs", n_pairs)

    if backup_csvs:
        st.success(
            f"Found {len(backup_csvs)} log(s): "
            + ", ".join(f"`{n}`" for n, _ in backup_csvs)
            + " — open **Log Analyzer** in the sidebar."
        )
    if backup_xmls:
        st.success(
            f"Found {len(backup_xmls)} XML file(s) ({n_pairs} clean/_rt pair(s)) "
            "— open **Settings Inventory** in the sidebar."
        )

    if st.button("Clear backup"):
        st.session_state.pop("backup_csvs", None)
        st.session_state.pop("backup_xmls", None)
        st.rerun()

st.divider()

# =============== TOOL OVERVIEW ===============
col1, col2 = st.columns(2)

with col1:
    st.subheader("📊 Log Analyzer")
    st.markdown(
        "Upload a Domino Ax **Uberlog CSV** to inspect parameters over time:\n\n"
        "- Grouped parameter selection and interactive plots\n"
        "- State filtering (e.g. analyse only `READY_TO_PRINT`)\n"
        "- Z-score anomaly detection\n"
        "- Engineering-limit checks from EPT026795"
    )

with col2:
    st.subheader("🔧 Settings Inventory")
    st.markdown(
        "Compare a machine's **clean-install** config files (`X.xml`) against "
        "its **real-time** files (`X_rt.xml`):\n\n"
        "- Fixed *Important settings* summary table\n"
        "- Full settings inventory with changed/only-in-one highlighting\n"
        "- CSV export of both tables"
    )

st.divider()
st.info("👈 Use the sidebar to switch between the two tools.")