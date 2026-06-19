# pages/2_Settings_Inventory.py — XML clean/_rt comparison page.
# Rendering only; comparison logic lives in xml_logic.py.

import os
import glob
import io
import xml.etree.ElementTree as ET

import streamlit as st

from xml_logic import pair_base, build_dataframe, build_important_table

st.set_page_config(page_title="Machine Settings Inventory", page_icon="🔧", layout="wide")


def show_results(df, machine_name="machine", key_prefix="default"):
    if df.empty:
        st.warning("No paired settings found.")
        return

    n_changed = int((df["Status"] == "changed").sum())
    n_only = int(df["Status"].isin(["only in clean", "only in real-time"]).sum())
    c1, c2, c3 = st.columns(3)
    c1.metric("Total settings", len(df))
    c2.metric("Changed", n_changed)
    c3.metric("Only in one file", n_only)

    # --- Important settings (fixed labels) ---
    st.subheader("Important settings")
    imp = build_important_table(df)
    n_missing = int((imp["Status"] == "not found").sum())
    if n_missing:
        st.caption(f"{n_missing} of {len(imp)} not located in the files "
                   "(absent in this machine's config, or the path notation differs).")
    st.dataframe(
        imp.style.set_properties(
            subset=["Real-time"],
            **{"color": "#d4a017", "font-weight": "bold"},
        ),
        use_container_width=True, hide_index=True,
    )
    st.download_button(
        "Download important settings (CSV)",
        data=imp.to_csv(index=False).encode("utf-8"),
        file_name=f"{machine_name}_important.csv",
        mime="text/csv", key=f"dl_imp_{key_prefix}",
    )

    # --- Full table ---
    st.subheader("All settings")
    view = st.radio("Show", ["Only differences", "All settings (incl. defaults)"],
                    horizontal=True, key=f"view_{key_prefix}")
    shown = df if view.startswith("All") else df[df["Status"] != "unchanged"]
    st.dataframe(shown, use_container_width=True, hide_index=True)
    st.download_button(
        "Download full table (CSV)",
        data=shown.to_csv(index=False).encode("utf-8"),
        file_name=f"{machine_name}_settings.csv",
        mime="text/csv", key=f"dl_full_{key_prefix}",
    )


def pairs_from_bytes(xmls):
    """Build (label, clean_root, rt_root) pairs from a list of (name, bytes)."""
    groups = {}
    for name, data in xmls:
        base, kind = pair_base(name)
        groups.setdefault(base, {})[kind] = data
    pairs, unmatched = [], []
    for base in sorted(groups):
        g = groups[base]
        if "base" in g and "rt" in g:
            try:
                pairs.append((base,
                              ET.parse(io.BytesIO(g["base"])).getroot(),
                              ET.parse(io.BytesIO(g["rt"])).getroot()))
            except ET.ParseError as e:
                st.error(f"{base}: could not parse - {e}")
        else:
            unmatched.append(base)
    return pairs, unmatched


# ----------------------------------- UI ------------------------------------

st.title("Machine Settings Inventory")
st.caption("Compare one machine's clean-install config files against its real-time files.")

backup_xmls = st.session_state.get("backup_xmls", [])

tab_backup, tab_upload, tab_folder = st.tabs(
    ["From service backup", "Upload backup files", "Local folder path"]
)

with tab_backup:
    if not backup_xmls:
        st.info("No service backup loaded. Upload one on the Home page, then return here.")
    else:
        st.write(f"Using **{len(backup_xmls)} XML file(s)** from the service backup "
                 "uploaded on the Home page.")
        machine_name_b = st.text_input("Machine name (for the export filename)",
                                       value="machine", key="mn_backup")
        pairs, unmatched = pairs_from_bytes(backup_xmls)
        if unmatched:
            st.warning("No clean/_rt partner for: " + ", ".join(unmatched))
        if pairs:
            show_results(build_dataframe(pairs), machine_name_b or "machine", key_prefix="backup")
        else:
            st.warning("No clean/_rt pairs found in the backup.")


with tab_upload:
    st.write("Upload all the `.xml` files from **one machine's** backup "
             "(select the folder contents, Ctrl+A in the file dialog).")
    machine_name = st.text_input("Machine name (for the export filename)", value="machine")
    uploads = st.file_uploader("XML files", type=["xml"],
                               accept_multiple_files=True, key="uploads")
    if uploads:
        groups = {}
        for f in uploads:
            base, kind = pair_base(f.name)
            groups.setdefault(base, {})[kind] = f
        pairs, unmatched = [], []
        for base in sorted(groups):
            g = groups[base]
            if "base" in g and "rt" in g:
                try:
                    pairs.append((base, ET.parse(g["base"]).getroot(),
                                  ET.parse(g["rt"]).getroot()))
                except ET.ParseError as e:
                    st.error(f"{base}: could not parse - {e}")
            else:
                unmatched.append(base)
        if unmatched:
            st.warning("No clean/_rt partner for: " + ", ".join(unmatched))
        if pairs:
            show_results(build_dataframe(pairs), machine_name or "machine", key_prefix="upload")

with tab_folder:
    st.write("If you run this app locally, point it at one machine's backup folder.")
    folder = st.text_input("Folder path", value="Config")
    if st.button("Scan folder"):
        if not os.path.isdir(folder):
            st.error(f"Not a folder: {folder}")
        else:
            pairs = []
            for path in sorted(glob.glob(os.path.join(folder, "*.xml"))):
                stem = path[:-4]
                if stem.endswith("_rt"):
                    continue
                partner = stem + "_rt.xml"
                if os.path.exists(partner):
                    label = os.path.basename(path)[:-4]
                    try:
                        pairs.append((label, ET.parse(path).getroot(),
                                      ET.parse(partner).getroot()))
                    except ET.ParseError as e:
                        st.error(f"{label}: could not parse - {e}")
            if not pairs:
                st.warning(f"No  X.xml / X_rt.xml  pairs found in {folder}")
            else:
                show_results(build_dataframe(pairs),
                             os.path.basename(os.path.abspath(folder)), key_prefix="folder")