"""
Visualization Engine
=====================
Central Plotly chart engine with interactive hover tooltips.
Every analytics module imports from here for consistent rendering.

Falls back to ASCII tables when Plotly is not available.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Union

logger = logging.getLogger(__name__)

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False
    logger.info("Plotly not available - using ASCII fallback for charts")


class QuantViz:
    """
    Static chart factory producing interactive Plotly figures with hover tooltips.
    All methods return a go.Figure (or ASCII string if Plotly unavailable).
    """

    # -- consistent color palette --
    COLORS = [
        "#636EFA", "#EF553B", "#00CC96", "#AB63FA",
        "#FFA15A", "#19D3F3", "#FF6692", "#B6E880",
        "#FF97FF", "#FECB52",
    ]
    BG_COLOR = "#fafafa"
    GRID_COLOR = "#e0e0e0"

    @staticmethod
    def _base_layout(title: str, **kwargs) -> dict:
        """Shared layout defaults for all charts."""
        layout = dict(
            title=dict(text=title, x=0.5),
            template="plotly_white",
            plot_bgcolor=QuantViz.BG_COLOR,
            hovermode="x unified",
            margin=dict(l=60, r=30, t=50, b=40),
            font=dict(size=11),
        )
        layout.update(kwargs)
        return layout

    # ------------------------------------------------------------------
    # 1. Equity Curve + Drawdown Overlay
    # ------------------------------------------------------------------
    @staticmethod
    def equity_curve(portfolio_df: pd.DataFrame, title: str = "Equity Curve") -> Any:
        """
        Equity curve with drawdown overlay.
        Hover: date, capital, drawdown%, peak, return since start.

        Args:
            portfolio_df: DataFrame with 'capital' column (datetime index).
        """
        if not HAS_PLOTLY:
            return QuantViz._ascii_equity(portfolio_df)

        capital = portfolio_df["capital"]
        peak = capital.cummax()
        dd = (capital - peak) / peak * 100
        ret_since_start = (capital / capital.iloc[0] - 1) * 100

        fig = make_subplots(
            rows=2, cols=1, shared_xaxes=True,
            row_heights=[0.7, 0.3], vertical_spacing=0.04,
        )

        fig.add_trace(go.Scatter(
            x=capital.index, y=capital.values,
            mode="lines", name="Capital",
            line=dict(color=QuantViz.COLORS[0], width=2),
            customdata=np.column_stack([peak.values, dd.values, ret_since_start.values]),
            hovertemplate=(
                "<b>%{x|%Y-%m-%d %H:%M}</b><br>"
                "Capital: $%{y:,.2f}<br>"
                "Peak: $%{customdata[0]:,.2f}<br>"
                "Drawdown: %{customdata[1]:.2f}%%<br>"
                "Return: %{customdata[2]:.2f}%%"
                "<extra></extra>"
            ),
        ), row=1, col=1)

        fig.add_trace(go.Scatter(
            x=dd.index, y=dd.values,
            mode="lines", name="Drawdown",
            fill="tozeroy",
            line=dict(color=QuantViz.COLORS[1], width=1),
            hovertemplate=(
                "<b>%{x|%Y-%m-%d %H:%M}</b><br>"
                "Drawdown: %{y:.2f}%%"
                "<extra></extra>"
            ),
        ), row=2, col=1)

        fig.update_layout(**QuantViz._base_layout(title))
        fig.update_yaxes(title_text="Capital ($)", row=1, col=1)
        fig.update_yaxes(title_text="DD (%)", row=2, col=1)
        return fig

    # ------------------------------------------------------------------
    # 2. Drawdown Chart
    # ------------------------------------------------------------------
    @staticmethod
    def drawdown_chart(portfolio_df: pd.DataFrame, title: str = "Drawdown Analysis") -> Any:
        """
        Rolling drawdown with max-DD annotation.
        Hover: date, DD%, days in drawdown.
        """
        if not HAS_PLOTLY:
            return QuantViz._ascii_drawdown(portfolio_df)

        capital = portfolio_df["capital"]
        peak = capital.cummax()
        dd = (capital - peak) / peak * 100

        # compute days-in-drawdown
        in_dd = dd < 0
        groups = (~in_dd).cumsum()
        days_in = in_dd.groupby(groups).cumsum()

        max_dd_idx = dd.idxmin()
        max_dd_val = dd.min()

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=dd.index, y=dd.values,
            mode="lines", name="Drawdown",
            fill="tozeroy",
            line=dict(color=QuantViz.COLORS[1], width=1.5),
            customdata=days_in.values,
            hovertemplate=(
                "<b>%{x|%Y-%m-%d %H:%M}</b><br>"
                "Drawdown: %{y:.2f}%%<br>"
                "Bars in DD: %{customdata}"
                "<extra></extra>"
            ),
        ))

        fig.add_annotation(
            x=max_dd_idx, y=max_dd_val,
            text=f"Max DD: {max_dd_val:.2f}%",
            showarrow=True, arrowhead=2,
            font=dict(size=12, color=QuantViz.COLORS[1]),
        )

        fig.update_layout(**QuantViz._base_layout(title, yaxis_title="Drawdown (%)"))
        return fig

    # ------------------------------------------------------------------
    # 3. Monthly Return Heatmap
    # ------------------------------------------------------------------
    @staticmethod
    def monthly_heatmap(returns: pd.Series, title: str = "Monthly Returns (%)") -> Any:
        """
        Month x Year heatmap.
        Hover: month, year, return%, YTD at that point.
        """
        if not HAS_PLOTLY:
            return QuantViz._ascii_monthly(returns)

        monthly = returns.resample("ME").apply(lambda x: (1 + x).prod() - 1) * 100
        pivot = pd.DataFrame({
            "year": monthly.index.year,
            "month": monthly.index.month,
            "ret": monthly.values,
        })
        table = pivot.pivot(index="year", columns="month", values="ret")
        table = table.reindex(columns=range(1, 13))

        # YTD
        ytd = table.cumsum(axis=1)

        month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

        fig = go.Figure(data=go.Heatmap(
            z=table.values,
            x=month_labels,
            y=[str(y) for y in table.index],
            customdata=ytd.values,
            colorscale="RdYlGn",
            zmid=0,
            hovertemplate=(
                "<b>%{y} %{x}</b><br>"
                "Return: %{z:.2f}%%<br>"
                "YTD: %{customdata:.2f}%%"
                "<extra></extra>"
            ),
        ))

        fig.update_layout(**QuantViz._base_layout(title))
        return fig

    # ------------------------------------------------------------------
    # 4. Correlation Heatmap
    # ------------------------------------------------------------------
    @staticmethod
    def correlation_heatmap(
        corr_matrix: pd.DataFrame,
        names: Optional[List[str]] = None,
        title: str = "Strategy Correlation",
    ) -> Any:
        """
        NxN correlation heatmap.
        Hover: strat A, strat B, correlation, interpretation.
        """
        if not HAS_PLOTLY:
            return QuantViz._ascii_corr(corr_matrix)

        labels = names or list(corr_matrix.columns)
        n = len(labels)

        # build interpretation text
        interp = np.empty((n, n), dtype=object)
        for i in range(n):
            for j in range(n):
                val = corr_matrix.iloc[i, j]
                if i == j:
                    interp[i, j] = "Self"
                elif abs(val) > 0.7:
                    interp[i, j] = "HIGH - redundant"
                elif abs(val) > 0.4:
                    interp[i, j] = "MODERATE"
                else:
                    interp[i, j] = "LOW - diversifying"

        fig = go.Figure(data=go.Heatmap(
            z=corr_matrix.values,
            x=labels,
            y=labels,
            customdata=interp,
            colorscale="RdBu_r",
            zmid=0,
            zmin=-1, zmax=1,
            hovertemplate=(
                "<b>%{y} vs %{x}</b><br>"
                "Correlation: %{z:.3f}<br>"
                "%{customdata}"
                "<extra></extra>"
            ),
        ))

        fig.update_layout(**QuantViz._base_layout(title))
        return fig

    # ------------------------------------------------------------------
    # 5. Return Distribution
    # ------------------------------------------------------------------
    @staticmethod
    def return_distribution(
        returns: pd.Series,
        title: str = "Return Distribution",
    ) -> Any:
        """
        Histogram + VaR/CVaR lines.
        Hover: bin range, frequency, percentile.
        """
        if not HAS_PLOTLY:
            return QuantViz._ascii_dist(returns)

        r = returns.dropna()
        var_95 = float(np.percentile(r, 5))
        cvar_95 = float(r[r <= var_95].mean()) if len(r[r <= var_95]) > 0 else var_95

        fig = go.Figure()
        fig.add_trace(go.Histogram(
            x=r.values,
            nbinsx=80,
            name="Returns",
            marker_color=QuantViz.COLORS[0],
            opacity=0.75,
            hovertemplate=(
                "Bin: %{x:.4f}<br>"
                "Count: %{y}"
                "<extra></extra>"
            ),
        ))

        fig.add_vline(x=var_95, line_dash="dash", line_color="red",
                      annotation_text=f"VaR 95%: {var_95:.4f}")
        fig.add_vline(x=cvar_95, line_dash="dot", line_color="darkred",
                      annotation_text=f"CVaR 95%: {cvar_95:.4f}")
        fig.add_vline(x=float(r.mean()), line_dash="solid", line_color="green",
                      annotation_text=f"Mean: {float(r.mean()):.4f}")

        fig.update_layout(**QuantViz._base_layout(title, xaxis_title="Return", yaxis_title="Frequency"))
        return fig

    # ------------------------------------------------------------------
    # 6. Cost Attribution Chart
    # ------------------------------------------------------------------
    @staticmethod
    def cost_attribution_chart(cost_data: Dict[str, float], title: str = "Cost Attribution") -> Any:
        """
        Grouped bar: costless vs costful Sharpe.
        Hover: component, value, drag.
        """
        if not HAS_PLOTLY:
            return QuantViz._ascii_cost(cost_data)

        categories = ["Costless", "Costful", "Comm-only", "Exec-only", "Swap-only"]
        keys = ["sharpe_costless", "sharpe_costful", "sharpe_commful", "sharpe_execful", "sharpe_swapful"]
        values = [cost_data.get(k, 0) for k in keys]

        costless = cost_data.get("sharpe_costless", 0)
        drags = [0] + [costless - v for v in values[1:]]

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=categories, y=values,
            marker_color=[QuantViz.COLORS[2], QuantViz.COLORS[1],
                          QuantViz.COLORS[3], QuantViz.COLORS[4], QuantViz.COLORS[5]],
            customdata=drags,
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Sharpe: %{y:.4f}<br>"
                "Drag: %{customdata:.4f}"
                "<extra></extra>"
            ),
        ))

        fig.update_layout(**QuantViz._base_layout(title, yaxis_title="Sharpe Ratio"))
        return fig

    # ------------------------------------------------------------------
    # 7. Factor Exposure Chart
    # ------------------------------------------------------------------
    @staticmethod
    def factor_exposure_chart(factor_results: Dict[str, Any], title: str = "Factor Exposure (CAPM)") -> Any:
        """
        Scatter + regression line.
        Hover: date, strat ret, mkt ret, residual.
        """
        if not HAS_PLOTLY:
            return QuantViz._ascii_factor(factor_results)

        strat_ret = factor_results.get("strategy_returns", pd.Series(dtype=float))
        mkt_ret = factor_results.get("market_returns", pd.Series(dtype=float))
        alpha = factor_results.get("alpha", 0)
        beta = factor_results.get("beta", 0)

        predicted = alpha + beta * mkt_ret
        residual = strat_ret - predicted

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=mkt_ret.values, y=strat_ret.values,
            mode="markers", name="Returns",
            marker=dict(size=4, color=QuantViz.COLORS[0], opacity=0.5),
            customdata=residual.values,
            hovertemplate=(
                "Market: %{x:.4f}<br>"
                "Strategy: %{y:.4f}<br>"
                "Residual: %{customdata:.4f}"
                "<extra></extra>"
            ),
        ))

        x_line = np.linspace(float(mkt_ret.min()), float(mkt_ret.max()), 100)
        fig.add_trace(go.Scatter(
            x=x_line, y=alpha + beta * x_line,
            mode="lines", name=f"beta={beta:.3f}, alpha={alpha:.6f}",
            line=dict(color=QuantViz.COLORS[1], width=2),
        ))

        fig.update_layout(**QuantViz._base_layout(
            title,
            xaxis_title="Market Return",
            yaxis_title="Strategy Return",
        ))
        return fig

    # ------------------------------------------------------------------
    # 8. Position Sizing Chart
    # ------------------------------------------------------------------
    @staticmethod
    def position_sizing_chart(positions: Dict[str, Any], title: str = "Position Targets") -> Any:
        """
        Bar chart: targets vs current.
        Hover: instrument, units, dollar exposure.
        """
        if not HAS_PLOTLY:
            return QuantViz._ascii_positions(positions)

        instruments = positions.get("instruments", [])
        targets = positions.get("target_units", [])
        current = positions.get("current_units", [])
        dollar_exp = positions.get("dollar_exposure", [])

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=instruments, y=current,
            name="Current", marker_color=QuantViz.COLORS[0],
            customdata=dollar_exp,
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Current: %{y:.4f}<br>"
                "Exposure: $%{customdata:,.0f}"
                "<extra></extra>"
            ),
        ))
        fig.add_trace(go.Bar(
            x=instruments, y=targets,
            name="Target", marker_color=QuantViz.COLORS[2],
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Target: %{y:.4f}"
                "<extra></extra>"
            ),
        ))

        fig.update_layout(**QuantViz._base_layout(title, barmode="group", yaxis_title="Units"))
        return fig

    # ------------------------------------------------------------------
    # 9. Hypothesis Test Chart
    # ------------------------------------------------------------------
    @staticmethod
    def hypothesis_test_chart(
        p_values: Dict[str, float],
        significance: float = 0.05,
        title: str = "Hypothesis Tests",
    ) -> Any:
        """
        Horizontal bars with significance threshold line.
        Hover: test, p-value, interpretation.
        """
        if not HAS_PLOTLY:
            return QuantViz._ascii_hypothesis(p_values, significance)

        tests = list(p_values.keys())
        vals = list(p_values.values())
        interp = ["SIGNIFICANT" if v < significance else "NOT significant" for v in vals]
        colors = [QuantViz.COLORS[2] if v < significance else QuantViz.COLORS[1] for v in vals]

        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=tests, x=vals, orientation="h",
            marker_color=colors,
            customdata=interp,
            hovertemplate=(
                "<b>%{y}</b><br>"
                "p-value: %{x:.4f}<br>"
                "%{customdata}"
                "<extra></extra>"
            ),
        ))

        fig.add_vline(x=significance, line_dash="dash", line_color="black",
                      annotation_text=f"alpha={significance}")

        fig.update_layout(**QuantViz._base_layout(title, xaxis_title="p-value"))
        return fig

    # ------------------------------------------------------------------
    # 10. Multi-Strategy Radar Comparison
    # ------------------------------------------------------------------
    @staticmethod
    def multi_strategy_comparison(
        metrics_dict: Dict[str, Dict[str, float]],
        title: str = "Strategy Comparison",
    ) -> Any:
        """
        Radar chart comparing strategies across metrics.
        Hover: metric, strategy, value.
        """
        if not HAS_PLOTLY:
            return QuantViz._ascii_comparison(metrics_dict)

        display_metrics = ["sharpe", "sortino", "win_rate", "profit_factor", "omega"]
        strategies = list(metrics_dict.keys())

        fig = go.Figure()
        for idx, (name, metrics) in enumerate(metrics_dict.items()):
            vals = []
            for m in display_metrics:
                v = metrics.get(m, 0)
                vals.append(float(v) if v else 0)
            vals.append(vals[0])  # close the polygon
            cats = display_metrics + [display_metrics[0]]

            fig.add_trace(go.Scatterpolar(
                r=vals,
                theta=cats,
                name=name,
                line_color=QuantViz.COLORS[idx % len(QuantViz.COLORS)],
                fill="toself",
                opacity=0.5,
                hovertemplate=(
                    f"<b>{name}</b><br>"
                    "%{theta}: %{r:.4f}"
                    "<extra></extra>"
                ),
            ))

        fig.update_layout(**QuantViz._base_layout(title, polar=dict(radialaxis=dict(visible=True))))
        return fig

    # ------------------------------------------------------------------
    # 11. Amalgapha Allocation Chart
    # ------------------------------------------------------------------
    @staticmethod
    def amalgapha_allocation_chart(
        allocations_df: pd.DataFrame,
        title: str = "Strategy Allocations Over Time",
    ) -> Any:
        """
        Stacked area of strategy weights.
        Hover: date, strategy, weight%.
        """
        if not HAS_PLOTLY:
            return QuantViz._ascii_alloc(allocations_df)

        fig = go.Figure()
        for idx, col in enumerate(allocations_df.columns):
            fig.add_trace(go.Scatter(
                x=allocations_df.index,
                y=allocations_df[col].values * 100,
                mode="lines",
                stackgroup="one",
                name=col,
                line_color=QuantViz.COLORS[idx % len(QuantViz.COLORS)],
                hovertemplate=(
                    f"<b>{col}</b><br>"
                    "%{x|%Y-%m-%d %H:%M}<br>"
                    "Weight: %{y:.1f}%%"
                    "<extra></extra>"
                ),
            ))

        fig.update_layout(**QuantViz._base_layout(title, yaxis_title="Allocation (%)"))
        return fig

    # ------------------------------------------------------------------
    # 12. HFT Features Dashboard
    # ------------------------------------------------------------------
    @staticmethod
    def hft_features_dashboard(
        features: Dict[str, Any],
        title: str = "HFT Microstructure Features",
    ) -> Any:
        """
        Multi-panel: rolling vol, trade imbalance, flow PnL.
        Hover: timestamp, value.
        """
        if not HAS_PLOTLY:
            return QuantViz._ascii_hft(features)

        panels = []
        panel_names = []
        if "rolling_vol" in features:
            panels.append(features["rolling_vol"])
            panel_names.append("Rolling Vol")
        if "trade_imbalance" in features:
            panels.append(features["trade_imbalance"])
            panel_names.append("Trade Imbalance")
        if "flow_pnl" in features:
            panels.append(features["flow_pnl"])
            panel_names.append("Flow PnL")

        n_panels = max(len(panels), 1)
        fig = make_subplots(rows=n_panels, cols=1, shared_xaxes=True,
                            subplot_titles=panel_names, vertical_spacing=0.06)

        for idx, (data, name) in enumerate(zip(panels, panel_names)):
            if isinstance(data, pd.Series):
                x, y = data.index, data.values
            elif isinstance(data, dict) and "timestamps" in data:
                x, y = data["timestamps"], data["values"]
            elif isinstance(data, (list, np.ndarray)):
                x, y = list(range(len(data))), data
            else:
                continue

            fig.add_trace(go.Scatter(
                x=x, y=y,
                mode="lines", name=name,
                line=dict(color=QuantViz.COLORS[idx], width=1.5),
                hovertemplate=(
                    f"<b>{name}</b><br>"
                    "%{x}<br>"
                    "Value: %{y:.6f}"
                    "<extra></extra>"
                ),
            ), row=idx + 1, col=1)

        fig.update_layout(**QuantViz._base_layout(title, height=250 * n_panels))
        return fig

    # ------------------------------------------------------------------
    # 13. Regression Plot (for GeneticRegression)
    # ------------------------------------------------------------------
    @staticmethod
    def regression_plot(results: Dict[str, Any], title: str = "Regression Results") -> Any:
        """
        Scatter + fitted line with coefficient annotations.
        """
        if not HAS_PLOTLY:
            return QuantViz._ascii_regression(results)

        y_actual = results.get("y_actual", [])
        y_predicted = results.get("y_predicted", [])
        r_squared = results.get("r_squared", 0)

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=y_predicted, y=y_actual,
            mode="markers", name="Actual vs Predicted",
            marker=dict(size=3, color=QuantViz.COLORS[0], opacity=0.4),
            hovertemplate=(
                "Predicted: %{x:.4f}<br>"
                "Actual: %{y:.4f}"
                "<extra></extra>"
            ),
        ))

        if len(y_predicted) > 0:
            mn, mx = min(y_predicted), max(y_predicted)
            fig.add_trace(go.Scatter(
                x=[mn, mx], y=[mn, mx],
                mode="lines", name="Perfect Fit",
                line=dict(color="gray", dash="dash"),
            ))

        fig.update_layout(**QuantViz._base_layout(
            f"{title} (R2={r_squared:.4f})",
            xaxis_title="Predicted",
            yaxis_title="Actual",
        ))
        return fig

    # ------------------------------------------------------------------
    # Utility: show figure
    # ------------------------------------------------------------------
    @staticmethod
    def show(fig: Any):
        """Display a figure. If ASCII string, just print it."""
        if isinstance(fig, str):
            print(fig)
        elif HAS_PLOTLY and isinstance(fig, go.Figure):
            fig.show()
        else:
            print(str(fig))

    # ==================================================================
    # ASCII FALLBACKS
    # ==================================================================

    @staticmethod
    def _ascii_equity(df: pd.DataFrame) -> str:
        c = df["capital"]
        peak = c.cummax()
        dd = (c - peak) / peak * 100
        lines = [
            "=== EQUITY CURVE ===",
            f"  Start:     ${c.iloc[0]:,.2f}",
            f"  End:       ${c.iloc[-1]:,.2f}",
            f"  Peak:      ${peak.max():,.2f}",
            f"  Return:    {(c.iloc[-1]/c.iloc[0]-1)*100:.2f}%",
            f"  Max DD:    {dd.min():.2f}%",
            f"  Periods:   {len(c)}",
        ]
        return "\n".join(lines)

    @staticmethod
    def _ascii_drawdown(df: pd.DataFrame) -> str:
        c = df["capital"]
        peak = c.cummax()
        dd = (c - peak) / peak * 100
        return f"=== DRAWDOWN ===\n  Max DD: {dd.min():.2f}%\n  Current DD: {dd.iloc[-1]:.2f}%"

    @staticmethod
    def _ascii_monthly(returns: pd.Series) -> str:
        monthly = returns.resample("ME").apply(lambda x: (1 + x).prod() - 1) * 100
        lines = ["=== MONTHLY RETURNS (%) ==="]
        for dt, ret in monthly.items():
            lines.append(f"  {dt.strftime('%Y-%m')}: {ret:+.2f}%")
        return "\n".join(lines[-25:])  # last 24 months

    @staticmethod
    def _ascii_corr(corr: pd.DataFrame) -> str:
        lines = ["=== CORRELATION MATRIX ==="]
        cols = list(corr.columns)
        header = "         " + "  ".join(f"{c[:8]:>8}" for c in cols)
        lines.append(header)
        for i, row_name in enumerate(cols):
            vals = "  ".join(f"{corr.iloc[i, j]:8.3f}" for j in range(len(cols)))
            lines.append(f"{row_name[:8]:>8}  {vals}")
        return "\n".join(lines)

    @staticmethod
    def _ascii_dist(returns: pd.Series) -> str:
        r = returns.dropna()
        var_95 = float(np.percentile(r, 5))
        cvar_95 = float(r[r <= var_95].mean()) if len(r[r <= var_95]) > 0 else var_95
        return (
            f"=== RETURN DISTRIBUTION ===\n"
            f"  Mean:   {r.mean():.6f}\n"
            f"  Std:    {r.std():.6f}\n"
            f"  Skew:   {r.skew():.4f}\n"
            f"  Kurt:   {r.kurtosis():.4f}\n"
            f"  VaR95:  {var_95:.6f}\n"
            f"  CVaR95: {cvar_95:.6f}"
        )

    @staticmethod
    def _ascii_cost(data: Dict[str, float]) -> str:
        lines = ["=== COST ATTRIBUTION ==="]
        for k, v in data.items():
            lines.append(f"  {k}: {v:.4f}")
        return "\n".join(lines)

    @staticmethod
    def _ascii_factor(data: Dict[str, Any]) -> str:
        return (
            f"=== FACTOR EXPOSURE ===\n"
            f"  Alpha:     {data.get('alpha', 0):.6f}\n"
            f"  Beta:      {data.get('beta', 0):.4f}\n"
            f"  R-squared: {data.get('r_squared', 0):.4f}"
        )

    @staticmethod
    def _ascii_positions(data: Dict[str, Any]) -> str:
        lines = ["=== POSITION TARGETS ==="]
        for inst, tgt in zip(data.get("instruments", []), data.get("target_units", [])):
            lines.append(f"  {inst}: {tgt:.4f}")
        return "\n".join(lines)

    @staticmethod
    def _ascii_hypothesis(pvals: Dict[str, float], sig: float) -> str:
        lines = ["=== HYPOTHESIS TESTS ==="]
        for test, pv in pvals.items():
            tag = "[PASS]" if pv < sig else "[FAIL]"
            lines.append(f"  {tag} {test}: p={pv:.4f}")
        return "\n".join(lines)

    @staticmethod
    def _ascii_comparison(metrics_dict: Dict[str, Dict[str, float]]) -> str:
        lines = ["=== STRATEGY COMPARISON ==="]
        keys = ["sharpe", "sortino", "win_rate", "profit_factor", "omega"]
        header = f"{'Metric':<16}" + "  ".join(f"{n[:10]:>10}" for n in metrics_dict.keys())
        lines.append(header)
        for k in keys:
            vals = "  ".join(f"{m.get(k, 0):10.4f}" for m in metrics_dict.values())
            lines.append(f"{k:<16}{vals}")
        return "\n".join(lines)

    @staticmethod
    def _ascii_alloc(df: pd.DataFrame) -> str:
        lines = ["=== STRATEGY ALLOCATIONS ==="]
        last = df.iloc[-1] * 100
        for col in df.columns:
            lines.append(f"  {col}: {last[col]:.1f}%")
        return "\n".join(lines)

    @staticmethod
    def _ascii_hft(features: Dict[str, Any]) -> str:
        lines = ["=== HFT FEATURES ==="]
        for k, v in features.items():
            if isinstance(v, pd.Series):
                lines.append(f"  {k}: last={v.iloc[-1]:.6f}, mean={v.mean():.6f}")
            elif isinstance(v, dict) and "values" in v:
                vals = v["values"]
                lines.append(f"  {k}: last={vals[-1]:.6f}, mean={np.mean(vals):.6f}")
        return "\n".join(lines)

    @staticmethod
    def _ascii_regression(results: Dict[str, Any]) -> str:
        lines = ["=== REGRESSION RESULTS ==="]
        lines.append(f"  R-squared: {results.get('r_squared', 0):.4f}")
        for name, val in results.get("coefficients", {}).items():
            lines.append(f"  {name}: {val:.6f}")
        return "\n".join(lines)
