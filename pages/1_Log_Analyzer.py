# pages/1_Log_Analyzer.py — Uberlog CSV analyzer page.
# Business logic lives in logic.py / charts.py / limits.py / ui.py.

import io

import streamlit as st

from config import APP_TITLE, APP_ICON, PLOT_PRESETS, DEFAULT_PRESET
from logic import (
    load_and_clean_csv,
    find_status_column,
    find_timestamp_column,
    parse_timestamps,
    get_log_date_range,
    get_available_states,
    filter_by_states,
    resolve_columns,
    compute_stats,
    compute_zscore_anomalies,
)
from limits import check_limits, get_pressure_limits, get_viscosity_limits
from charts import build_plot
from ui import (
    render_page_header,
    render_sidebar_controls,
    render_state_filter_sidebar,
    render_metadata_panel,
    render_state_filter_banner,
    render_parameter_selector,
    render_preset_controls,
    render_preset_toggles,
    render_anomaly_banner,
    render_stats_panel,
    render_anomaly_report,
    render_limits_report,
)

st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="wide")


def _fmt_size(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n / (1024 * 1024):.1f} MB"


def _resolve_source(controls):
    """Return a file-like CSV source: sidebar upload, or a backup log."""
    source = controls["uploaded_file"]
    backup_csvs = st.session_state.get("backup_csvs", [])

    if source is None and backup_csvs:
        st.caption("Using a log from the service backup uploaded on the Home page.")
        labels = {f"{n}  ·  {_fmt_size(len(d))}": n for n, d in backup_csvs}
        pick_label = st.selectbox("Log from backup", ["—"] + list(labels))
        if pick_label != "—":
            name = labels[pick_label]
            source = io.BytesIO(dict(backup_csvs)[name])

    return source


def _render_preset_section(df_filtered, controls, x_values):
    """Preset plots shown at the top, each toggleable, laid out in a grid."""
    preset_name, ncols = render_preset_controls(list(PLOT_PRESETS), DEFAULT_PRESET)

    preset_plots = [
        {"title": spec["title"], "cols": resolve_columns(df_filtered, spec["vars"])}
        for spec in PLOT_PRESETS[preset_name]
    ]

    enabled = render_preset_toggles(preset_plots)

    # One anomaly mask covering every column used by the preset
    union_cols = sorted({c for p in preset_plots for c in p["cols"]})
    preset_mask = None
    if controls["enable_anomaly"] and union_cols:
        preset_mask, _, _ = compute_zscore_anomalies(
            df_filtered, union_cols, threshold=controls["zscore_threshold"]
        )

    st.divider()

    to_show = [p for i, p in enumerate(preset_plots) if enabled.get(i) and p["cols"]]
    if not to_show:
        st.info("No preset plots selected (or none of their parameters are in this log).")
        return

    height = 300 if ncols > 1 else 460
    grid = st.columns(ncols)
    for slot, p in enumerate(to_show):
        with grid[slot % ncols]:
            st.markdown(f"**{p['title']}**")
            fig = build_plot(
                df_filtered, p["cols"], controls["plot_type"],
                controls["show_grid"], preset_mask, x_values,
            )
            fig.update_layout(height=height, showlegend=len(p["cols"]) > 1)
            st.plotly_chart(fig, use_container_width=True)


def _render_custom_section(df_filtered, param_map, controls, x_values, selected_states):
    """Manual parameter selection + stats / anomaly / limits, inside an expander."""
    with st.expander("🔧 Custom plot & analysis", expanded=False):
        selected_columns = render_parameter_selector(param_map, df_filtered)

        if not st.button("📈 Plot selected", use_container_width=True):
            return
        if not selected_columns:
            st.warning("Please select at least one parameter.")
            return

        # Anomaly detection
        if controls["enable_anomaly"]:
            anomaly_mask, _, anomaly_summary = compute_zscore_anomalies(
                df_filtered, selected_columns, threshold=controls["zscore_threshold"]
            )
        else:
            anomaly_mask, anomaly_summary = None, None

        if anomaly_summary is not None:
            n_flagged = int((anomaly_summary["Anomalies detected"] > 0).sum())
            render_anomaly_banner(n_flagged, selected_states)

        # Plots
        if controls["multi_plot"]:
            for col in selected_columns:
                fig = build_plot(df_filtered, [col], controls["plot_type"],
                                 controls["show_grid"], anomaly_mask, x_values)
                st.plotly_chart(fig, use_container_width=True)
        else:
            fig = build_plot(df_filtered, selected_columns, controls["plot_type"],
                             controls["show_grid"], anomaly_mask, x_values)
            st.plotly_chart(fig, use_container_width=True)

        # Stats
        if controls["show_stats"]:
            render_stats_panel(compute_stats(df_filtered, selected_columns))

        # Anomaly report
        if anomaly_summary is not None and anomaly_mask is not None:
            render_anomaly_report(
                anomaly_summary, anomaly_mask, df_filtered,
                selected_columns, controls["zscore_threshold"], selected_states,
            )

        # Engineering limits
        if controls["enable_limits"]:
            extra_limits = {}
            pressure_lim = get_pressure_limits(df_filtered)
            viscosity_lim = get_viscosity_limits(df_filtered)
            for col in selected_columns:
                if "ink system pressure" in col.lower() and pressure_lim:
                    extra_limits[col] = pressure_lim
                if "actual cp" in col.lower() and viscosity_lim:
                    extra_limits[col] = viscosity_lim

            limits_df = check_limits(df_filtered, selected_columns, extra_limits)
            if limits_df is not None:
                render_limits_report(limits_df)
            else:
                st.info("\u2139\ufe0f No engineering limits defined for selected parameters.")


def main() -> None:
    render_page_header()
    controls = render_sidebar_controls()

    source = _resolve_source(controls)
    if source is None:
        st.info(
            "Upload a CSV log from the sidebar, or upload a service backup on the "
            "Home page and pick a log here."
        )
        return

    try:
        df, param_map, metadata = load_and_clean_csv(source)
    except ValueError as e:
        st.error(str(e))
        return

    # --- State filter (sidebar, data-dependent) ---
    status_col = find_status_column(df)
    available_states = get_available_states(df, status_col) if status_col else []
    selected_states = (
        render_state_filter_sidebar(available_states)
        if status_col and available_states else []
    )
    df_filtered = filter_by_states(df, status_col, selected_states) if status_col else df.copy()

    # --- Timestamp / X-axis ---
    timestamp_col = find_timestamp_column(df_filtered)
    x_values = (
        parse_timestamps(df_filtered, timestamp_col)
        if timestamp_col and controls["x_axis"] == "Timestamp" else None
    )

    timestamp_col_full = find_timestamp_column(df)
    date_range = get_log_date_range(df, timestamp_col_full) if timestamp_col_full else None

    # --- Main panel ---
    render_metadata_panel(metadata, date_range)
    st.divider()

    if status_col:
        excluded_states = [s for s in available_states if s not in selected_states]
        render_state_filter_banner(len(df), len(df_filtered), selected_states, excluded_states)

    # Preset plots first (shown at start), custom analysis tucked away below.
    _render_preset_section(df_filtered, controls, x_values)
    st.divider()
    _render_custom_section(df_filtered, param_map, controls, x_values, selected_states)


main()