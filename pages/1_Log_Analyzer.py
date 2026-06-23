# pages/1_Log_Analyzer.py — Uberlog CSV analyzer page.
# Business logic lives in logic.py / charts.py / ui.py.
# All rows/states are plotted (no state filtering).

import io

import streamlit as st

from config import APP_TITLE, APP_ICON, PLOT_PRESETS, DEFAULT_PRESET, MAX_PLOT_POINTS
from logic import (
    load_and_clean_csv,
    find_timestamp_column,
    parse_timestamps,
    get_log_date_range,
    resolve_columns,
    compute_stats,
)
from charts import build_plot
from ui import (
    render_page_header,
    render_sidebar_controls,
    render_metadata_panel,
    render_parameter_selector,
    render_preset_controls,
    render_preset_toggles,
    render_stats_panel,
)

st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="wide")


@st.cache_data(show_spinner="Parsing log…")
def _parse_log(data: bytes):
    """Cached CSV parse — keyed on the file's raw bytes, so a given log is
    parsed only once no matter how many times the page reruns."""
    return load_and_clean_csv(io.BytesIO(data))


def _fmt_size(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n / (1024 * 1024):.1f} MB"


def _resolve_source(controls) -> bytes | None:
    """Return the raw CSV bytes from the sidebar upload, or a backup log."""
    uploaded = controls["uploaded_file"]
    if uploaded is not None:
        return uploaded.getvalue()

    backup_csvs = st.session_state.get("backup_csvs", [])
    if backup_csvs:
        st.caption("Using a log from the service backup uploaded on the Home page.")
        labels = {f"{n}  ·  {_fmt_size(len(d))}": n for n, d in backup_csvs}
        pick_label = st.selectbox("Log from backup", ["—"] + list(labels))
        if pick_label != "—":
            return dict(backup_csvs)[labels[pick_label]]

    return None


def _render_preset_section(df, controls, x_values):
    """Preset plots shown at the top, each toggleable, laid out in a grid."""
    preset_name, ncols = render_preset_controls(list(PLOT_PRESETS), DEFAULT_PRESET)

    preset_plots = [
        {"title": spec["title"], "cols": resolve_columns(df, spec["vars"])}
        for spec in PLOT_PRESETS[preset_name]
    ]

    enabled = render_preset_toggles(preset_plots)

    st.divider()

    to_show = [p for i, p in enumerate(preset_plots) if enabled.get(i) and p["cols"]]
    if not to_show:
        st.info("No preset plots selected (or none of their parameters are in this log).")
        return

    height = 300 if ncols > 1 else 460
    max_points = MAX_PLOT_POINTS if controls["downsample"] else None
    grid = st.columns(ncols)
    for slot, p in enumerate(to_show):
        with grid[slot % ncols]:
            st.markdown(f"**{p['title']}**")
            fig = build_plot(df, p["cols"], controls["plot_type"],
                             controls["show_grid"], None, x_values, max_points)
            fig.update_layout(height=height, showlegend=len(p["cols"]) > 1)
            st.plotly_chart(fig, use_container_width=True)


def _render_custom_section(df, param_map, controls, x_values):
    """Manual parameter selection + plots + stats, inside an expander."""
    with st.expander("🔧 Custom plot", expanded=False):
        selected_columns = render_parameter_selector(param_map, df)

        if not st.button("📈 Plot selected", use_container_width=True):
            return
        if not selected_columns:
            st.warning("Please select at least one parameter.")
            return

        max_points = MAX_PLOT_POINTS if controls["downsample"] else None
        if controls["multi_plot"]:
            for col in selected_columns:
                fig = build_plot(df, [col], controls["plot_type"],
                                 controls["show_grid"], None, x_values, max_points)
                st.plotly_chart(fig, use_container_width=True)
        else:
            fig = build_plot(df, selected_columns, controls["plot_type"],
                             controls["show_grid"], None, x_values, max_points)
            st.plotly_chart(fig, use_container_width=True)

        if controls["show_stats"]:
            render_stats_panel(compute_stats(df, selected_columns))


def main() -> None:
    render_page_header()
    controls = render_sidebar_controls()

    data = _resolve_source(controls)
    if data is None:
        st.info(
            "Upload a CSV log from the sidebar, or upload a service backup on the "
            "Home page and pick a log here."
        )
        return

    try:
        df, param_map, metadata = _parse_log(data)
    except ValueError as e:
        st.error(str(e))
        return

    # X-axis: timestamp or row index. All rows/states are kept.
    timestamp_col = find_timestamp_column(df)
    x_values = (
        parse_timestamps(df, timestamp_col)
        if timestamp_col and controls["x_axis"] == "Timestamp" else None
    )
    date_range = get_log_date_range(df, timestamp_col) if timestamp_col else None

    render_metadata_panel(metadata, date_range)
    st.divider()

    _render_preset_section(df, controls, x_values)
    st.divider()
    _render_custom_section(df, param_map, controls, x_values)


main()