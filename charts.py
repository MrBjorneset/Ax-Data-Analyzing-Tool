# charts.py — all Plotly figure construction.
# No Streamlit imports here. Functions take data in, return go.Figure out.

import plotly.graph_objects as go
import pandas as pd


def build_plot(
    df: pd.DataFrame,
    columns: list[str],
    plot_type: str,
    show_grid: bool,
    anomaly_mask: pd.DataFrame | None = None,
    x_values: pd.Series | None = None,
) -> go.Figure:
    """
    Build a Plotly figure for the selected columns and plot type.

    x_values : optional Series to use as the X-axis (e.g. parsed timestamps).
               If None, row index is used. Timestamps produce a time-axis with
               human-readable hover labels. Not applied to Histograms (value axis).
    """
    fig = go.Figure()
    x = x_values if (x_values is not None and plot_type != "Histogram") else None

    for col in columns:
        _add_data_trace(fig, df, col, plot_type, x)
        if anomaly_mask is not None and plot_type != "Histogram":
            _add_anomaly_overlay(fig, df, col, anomaly_mask, x)

    _apply_layout(fig, show_grid, x_is_time=(x is not None))
    return fig


def _add_data_trace(
    fig: go.Figure,
    df: pd.DataFrame,
    col: str,
    plot_type: str,
    x: pd.Series | None,
) -> None:
    """Add the primary data trace for one column."""
    if plot_type == "Line":
        fig.add_trace(go.Scattergl(x=x, y=df[col], mode="lines", name=col))
    elif plot_type == "Scatter":
        fig.add_trace(go.Scattergl(x=x, y=df[col], mode="markers", name=col))
    elif plot_type == "Histogram":
        fig.add_trace(go.Histogram(x=df[col], name=col, opacity=0.6))
    elif plot_type == "Bar":
        fig.add_trace(go.Bar(x=x, y=df[col], name=col))


def _add_anomaly_overlay(
    fig: go.Figure,
    df: pd.DataFrame,
    col: str,
    anomaly_mask: pd.DataFrame,
    x: pd.Series | None,
) -> None:
    """Overlay red X markers at anomalous data points for one column."""
    if col not in anomaly_mask.columns:
        return
    flagged_idx = df.index[anomaly_mask[col]].tolist()
    if not flagged_idx:
        return

    x_flagged = x.iloc[flagged_idx] if x is not None else flagged_idx

    fig.add_trace(go.Scatter(
        x=x_flagged,
        y=df[col].iloc[flagged_idx],
        mode="markers",
        marker=dict(color="red", size=8, symbol="x"),
        name=f"{col} — anomaly",
    ))


def _apply_layout(fig: go.Figure, show_grid: bool, x_is_time: bool) -> None:
    """Apply common layout settings."""
    xaxis_cfg = dict(showgrid=show_grid)
    if x_is_time:
        xaxis_cfg["type"] = "date"
        xaxis_cfg["tickformat"] = "%H:%M:%S"  # show time only; date visible on hover

    fig.update_layout(
        height=500,
        legend_title_text="Parameters",
        hovermode="x unified",
        margin=dict(l=40, r=20, t=40, b=40),
    )
    fig.update_xaxes(**xaxis_cfg)
    fig.update_yaxes(showgrid=show_grid)