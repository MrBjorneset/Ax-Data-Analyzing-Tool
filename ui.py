# ui.py — reusable Streamlit UI components.
# All st.* calls live here or in app.py. No data logic here.

import streamlit as st
import pandas as pd
from config import (
    APP_TITLE,
    APP_SUBTITLE,
    STEADY_STATE,
    ZSCORE_DEFAULT_THRESHOLD,
    ZSCORE_MIN,
    ZSCORE_MAX,
    ZSCORE_STEP,
)


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

    st.sidebar.divider()
    st.sidebar.subheader("🔍 Anomaly Detection")
    enable_anomaly    = st.sidebar.checkbox("Enable Z-score anomaly detection", value=True)
    zscore_threshold  = st.sidebar.slider(
        "Z-score threshold",
        min_value=ZSCORE_MIN,
        max_value=ZSCORE_MAX,
        value=ZSCORE_DEFAULT_THRESHOLD,
        step=ZSCORE_STEP,
        help="Flag points this many standard deviations from the mean. Lower = more sensitive.",
    )

    st.sidebar.divider()
    st.sidebar.subheader("📏 Engineering Limits")
    enable_limits = st.sidebar.checkbox(
        "Check engineering limits",
        value=True,
        help="Flag readings outside known safe operating ranges from the Domino Ax "
             "Engineer's Reference Guide (EPT026795 Issue 32).",
    )

    return dict(
        uploaded_file=uploaded_file,
        plot_type=plot_type,
        x_axis=x_axis,
        multi_plot=multi_plot,
        show_grid=show_grid,
        show_stats=show_stats,
        enable_anomaly=enable_anomaly,
        zscore_threshold=zscore_threshold,
        enable_limits=enable_limits,
    )


def render_state_filter_sidebar(available_states: list[str]) -> list[str]:
    """
    Render the state filter section in the sidebar (shown only when a log is loaded).
    Returns the list of selected states.
    """
    st.sidebar.divider()
    st.sidebar.subheader("⚙️ State Filter")
    st.sidebar.caption(
        "Select which printer states to include. "
        "Deselect startup/shutdown states to avoid false anomaly alerts."
    )
    default = [STEADY_STATE] if STEADY_STATE in available_states else available_states
    return st.sidebar.multiselect(
        "Include states",
        options=available_states,
        default=default,
        help="READY_TO_PRINT = steady-state. SEQUENCING_ON/OFF and STANDBY are transient phases.",
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


def render_state_filter_banner(
    total_rows: int,
    filtered_rows: int,
    selected_states: list[str],
    excluded_states: list[str],
) -> None:
    excluded = total_rows - filtered_rows
    if excluded > 0:
        banner_info(
            f"<strong>State filter active</strong> — "
            f"Analysing <strong>{filtered_rows:,} rows</strong> {selected_states}. "
            f"Excluded <strong>{excluded:,} rows</strong> from: {excluded_states}."
        )
    elif selected_states:
        banner_info(
            f"<strong>State filter active</strong> — "
            f"All {total_rows:,} rows match selected states."
        )


def render_parameter_selector(
    param_map: dict,
    df_filtered: pd.DataFrame,
) -> list[str]:
    """
    Render grouped parameter multiselects and a data preview.
    Returns the list of selected column names.
    """
    st.subheader("🔧 Parameters")
    selected_columns = []
    col_left, col_right = st.columns([3, 2])

    with col_left:
        for main, subs in param_map.items():
            selected_columns += st.multiselect(
                label=main,
                options=list(subs.values()),
                key=main,
            )

    with col_right:
        st.markdown("### Preview")
        preview = df_filtered[selected_columns] if selected_columns else df_filtered
        st.dataframe(preview.head(10), width="stretch", height=260)

    return selected_columns


def render_anomaly_banner(n_flagged: int, selected_states: list[str]) -> None:
    states_label = ", ".join(selected_states) if selected_states else "all states"
    if n_flagged > 0:
        banner_warning(
            f"<strong>Potential fault detected</strong> — "
            f"{n_flagged} parameter(s) have anomalous readings during {states_label}. "
            f"See the anomaly report below."
        )
    else:
        banner_ok(
            "<strong>All parameters look normal</strong> — "
            "No anomalies detected at the current threshold."
        )


def render_stats_panel(stats_df: pd.DataFrame | None) -> None:
    st.divider()
    st.subheader("📊 Stats Summary")
    if stats_df is not None:
        st.dataframe(stats_df, use_container_width=True)
    else:
        st.info("No numeric columns selected — stats not available.")


def render_anomaly_report(
    anomaly_summary: pd.DataFrame,
    anomaly_mask: pd.DataFrame,
    df_filtered: pd.DataFrame,
    selected_columns: list[str],
    zscore_threshold: float,
    selected_states: list[str],
) -> None:
    st.divider()
    st.subheader("🚨 Anomaly Report")
    st.caption(
        f"Z-score threshold: ±{zscore_threshold} | "
        f"States analysed: {', '.join(selected_states) if selected_states else 'all'}"
    )
    st.dataframe(anomaly_summary, use_container_width=True)

    any_flagged = anomaly_mask.any(axis=1)
    n_rows = int(any_flagged.sum())
    if n_rows > 0:
        with st.expander(f"🔎 View {n_rows} flagged row(s)"):
            st.dataframe(
                df_filtered[any_flagged][selected_columns],
                use_container_width=True,
            )


def render_limits_report(limits_df: pd.DataFrame) -> None:
    """Render the engineering limits check results."""
    st.divider()
    st.subheader("📏 Engineering Limits Check")

    n_violations = int((limits_df["Total violations"] > 0).sum())
    if n_violations > 0:
        banner_warning(
            f"<strong>{n_violations} parameter(s) exceeded engineering limits</strong> — "
            f"See table below for details."
        )
    else:
        banner_ok(
            "<strong>All parameters within engineering limits</strong> — "
            "No out-of-spec readings detected."
        )

    # Show full table but highlight the Note column lightly
    st.dataframe(limits_df, use_container_width=True)