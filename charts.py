# charts.py — all Plotly figure construction.
# No Streamlit imports here. Functions take data in, return go.Figure out.

import plotly.graph_objects as go
import pandas as pd


def build_plot(
    df: pd.DataFrame,
    columns: list[str],
    plot_type: str,
    show_grid: bool,
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


def _apply_layout(fig: go.Figure, show_grid: bool, x_is_time: bool) -> None:
    """Apply common layout settings."""
    xaxis_cfg = dict(showgrid=show_grid)
    if x_is_time:
        xaxis_cfg["type"] = "date"
        xaxis_cfg["tickformat"] = "%H:%M:%S"  # show time only; date visible on hover

    fig.update_layout(
        height=500,
        hovermode="x unified",
        margin=dict(l=40, r=20, t=40, b=40),
        legend=dict(
            orientation="h",       # horizontal row of entries
            yanchor="top",
            y=-0.15,               # sit just below the plot area
            xanchor="left",
            x=0,
            title_text="",
        ),
    )
    fig.update_xaxes(**xaxis_cfg)
    fig.update_yaxes(showgrid=show_grid)