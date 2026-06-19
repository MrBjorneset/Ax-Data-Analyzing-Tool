# streamlit_app.py — entry point for the combined Domino Ax toolkit.
#
# This is a Streamlit *multipage* app. Streamlit automatically builds a
# sidebar navigation from the files in the pages/ folder:
#
#   streamlit_app.py            -> this Home page
#   pages/1_Log_Analyzer.py     -> Uberlog CSV analyzer
#   pages/2_Settings_Inventory.py -> XML clean/_rt config comparison
#
# Run locally with:
#   pip install -r requirements.txt
#   streamlit run streamlit_app.py

import streamlit as st

st.set_page_config(
    page_title="Domino Ax Toolkit",
    page_icon="🛠️",
    layout="wide",
)

st.title("🛠️ Domino Ax Toolkit")
st.caption("A combined toolkit for Domino Ax-Series CIJ printers.")

st.divider()

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