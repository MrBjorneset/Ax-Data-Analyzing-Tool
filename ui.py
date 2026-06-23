# ui.py — reusable Streamlit UI components.
# All st.* calls live here or in app.py. No data logic here.

import streamlit as st
import pandas as pd
from config import APP_TITLE, APP_SUBTITLE


# =============== PAGE SETUP ===============

CSS = """
<style>
.title-text {
    font-size: 36px; font-weight: 600; margin-bottom: 0px;
}
.subtitle-text {
    font-size: 16px; color: #999; margin-top: -10px;
}
.banner {
    padding: 10px 16px; border-radius: 4px;
    font-size: 15px; margin-bottom: 8px;
    border-left: 5px solid;
}
.banner-warning  { background-color: #fff3cd; border-color: #ffc107; color: #856404; }
.banner-ok       { background-color: #d4edda; border-color: #28a745; color: #155724; }
.banner-info     { background-color: #e8f4fd; border-color: #2196F3; color: #0c4a6e; }
</style>
"""

def render_page_header() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(f'<div class="title-text">{APP_TITLE}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="subtitle-text">{APP_SUBTITLE}</div>', unsafe_allow_html=True)
    st.divider()


# =============== SIDEBAR ===============

def render_sidebar_controls() -> dict:
    """
    Render static sidebar controls (those that don't depend on loaded data).
    Returns a dict of control values for use in app.py.
    """
    st.sidebar.header("Controls")
    uploaded_file = st.sidebar.file_uploader("Upload CSV log", type=["csv"])

    st.sidebar.divider()
    st.sidebar.subheader("📈 Plot")
    plot_type  = st.sidebar.selectbox("Plot type", ["Line", "Scatter", "Histogram", "Bar"])
    x_axis     = st.sidebar.radio(
        "X-axis",
        ["Timestamp", "Row index"],
        help="Timestamp uses the log's time column. Row index is a plain sequence number.",
    )
    multi_plot = st.sidebar.checkbox("Separate plots per parameter", value=False)
    show_grid  = st.sidebar.checkbox("Show grid", value=True)
    show_stats = st.sidebar.checkbox("Show stats summary", value=True)

    return dict(
        uploaded_file=uploaded_file,
        plot_type=plot_type,
        x_axis=x_axis,
        multi_plot=multi_plot,
        show_grid=show_grid,
        show_stats=show_stats,
    )


# =============== BANNERS ===============

def _banner(css_class: str, html: str) -> None:
    st.markdown(
        f'<div class="banner {css_class}">{html}</div>',
        unsafe_allow_html=True,
    )

def banner_warning(message: str) -> None:
    _banner("banner-warning", f"⚠️ {message}")

def banner_ok(message: str) -> None:
    _banner("banner-ok", f"✅ {message}")

def banner_info(message: str) -> None:
    _banner("banner-info", f"🔎 {message}")


# =============== PANELS ===============

def render_metadata_panel(metadata: dict, date_range: dict | None = None) -> None:
    with st.expander("📄 Log Information", expanded=True):

        # Date/time summary at the top — most useful at a glance
        if date_range:
            st.markdown(
                f"### 📅 {date_range['date']}"
                f"&nbsp;&nbsp;&nbsp;`{date_range['start']} → {date_range['end']}`"
                f"&nbsp;&nbsp;&nbsp;⏱ {date_range['duration']}",
                unsafe_allow_html=False,
            )
            st.divider()

        if metadata:
            cols = st.columns(2)
            for i, (k, v) in enumerate(metadata.items()):
                cols[i % 2].markdown(f"**{k}**  \n{v}")
        else:
            st.info("No metadata found in log.")


def render_parameter_selector(
    param_map: dict,
    df_filtered: pd.DataFrame,
) -> list[str]:
    """
    Compact parameter picker: a single searchable multiselect over all columns
    (their names already include the group, e.g. "Peltier - Ink temperature").
    Returns the list of selected column names.
    """
    all_cols: list[str] = []
    for subs in param_map.values():
        for c in subs.values():
            if c not in all_cols:
                all_cols.append(c)

    selected_columns = st.multiselect(
        "Parameters to plot",
        options=all_cols,
        key="manual_params",
        help="Type to search. Names include their group prefix.",
    )

    if selected_columns:
        with st.expander("Preview selected data"):
            st.dataframe(df_filtered[selected_columns].head(10),
                         use_container_width=True, height=240)

    return selected_columns


def render_preset_controls(preset_names: list[str], default: str) -> tuple[str, int]:
    """Render the preset chooser and layout selector. Returns (preset_name, ncols)."""
    st.subheader("📈 Preset plots")
    c1, c2 = st.columns([3, 1])
    with c1:
        idx = preset_names.index(default) if default in preset_names else 0
        preset = st.selectbox("Preset", preset_names, index=idx, key="preset_choice")
    with c2:
        ncols = st.selectbox("Columns", [1, 2, 3], index=1, key="preset_cols")
    return preset, ncols


def render_preset_toggles(plots: list[dict]) -> dict[int, bool]:
    """
    Render a row of checkboxes — one per preset plot. Plots with no matching
    columns in the current log are shown disabled. If any plot is flagged
    "default": True, only those start ticked; otherwise all start ticked.

    plots : list of {"title": str, "cols": list[str], "default"?: bool}
    Returns {plot_index: enabled_bool}.
    """
    has_any_default = any(p.get("default") for p in plots)
    enabled: dict[int, bool] = {}
    columns = st.columns(4)
    for i, p in enumerate(plots):
        has_data = bool(p["cols"])
        default_on = p.get("default", False) if has_any_default else True
        with columns[i % 4]:
            enabled[i] = st.checkbox(
                p["title"],
                value=has_data and default_on,
                disabled=not has_data,
                key=f"preset_toggle_{i}",
                help=None if has_data else "No matching parameter in this log",
            )
    return enabled


def render_stats_panel(stats_df: pd.DataFrame | None) -> None:
    st.divider()
    st.subheader("📊 Stats Summary")
    if stats_df is not None:
        st.dataframe(stats_df, use_container_width=True)
    else:
        st.info("No numeric columns selected — stats not available.")