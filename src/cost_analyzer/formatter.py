"""Output formatter: Rich tables, JSON, CSV."""

from __future__ import annotations

import csv
import io
import json
from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

if TYPE_CHECKING:
    from cost_analyzer.models import CostBreakdown, CostComparison, ErrorResponse, TrendSummary


def format_breakdown(breakdown: CostBreakdown, output_format: str = "table") -> str:
    """Format a CostBreakdown for display.

    Args:
        breakdown: Cost breakdown data.
        output_format: One of "table", "json", "csv".

    Returns:
        Formatted string.
    """
    if output_format == "json":
        return _format_breakdown_json(breakdown)
    if output_format == "csv":
        return _format_breakdown_csv(breakdown)
    return _format_breakdown_table(breakdown)


def _format_breakdown_table(breakdown: CostBreakdown) -> str:
    """Render CostBreakdown as a Rich Table string."""
    table = Table(title=None, show_header=True, header_style="bold")
    table.add_column("サービス", style="cyan", min_width=20)
    table.add_column("コスト", justify="right", style="green", min_width=12)
    table.add_column("%", justify="right", min_width=8)

    for item in breakdown.items:
        table.add_row(
            item.service,
            f"${item.amount:,.2f}",
            f"{item.percentage}%",
        )

    table.add_section()
    table.add_row(
        Text("合計", style="bold"),
        Text(f"${breakdown.total:,.2f}", style="bold green"),
        Text("100.0%", style="bold"),
    )

    console = Console(file=io.StringIO(), force_terminal=False, width=80)
    console.print(table)
    output = console.file.getvalue()
    output += f"期間: {breakdown.period_start} ~ {breakdown.period_end}\n"
    return output


def _format_breakdown_json(breakdown: CostBreakdown) -> str:
    """Render CostBreakdown as JSON matching API contract."""
    data = {
        "type": "breakdown",
        "period": {
            "start": str(breakdown.period_start),
            "end": str(breakdown.period_end),
        },
        "currency": breakdown.currency,
        "items": [
            {
                "service": item.service,
                "amount": float(item.amount),
                "percentage": float(item.percentage),
                "rank": item.rank,
            }
            for item in breakdown.items
        ],
        "total": float(breakdown.total),
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def _format_breakdown_csv(breakdown: CostBreakdown) -> str:
    """Render CostBreakdown as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["service", "amount", "percentage", "rank"])
    for item in breakdown.items:
        writer.writerow([item.service, float(item.amount), float(item.percentage), item.rank])
    return output.getvalue()


def format_error(error: ErrorResponse) -> str:
    """Format an ErrorResponse for display.

    Args:
        error: Error response data.

    Returns:
        Formatted error string.
    """
    lines = [f"エラー: {error.message}", f"{error.guidance}"]
    if error.example_queries:
        lines.append("以下の例を試してください:")
        for q in error.example_queries:
            lines.append(f'  - "{q}"')
    return "\n".join(lines)


def format_comparison(
    comparison: CostComparison,
    trend: TrendSummary | None = None,
    output_format: str = "table",
) -> str:
    """Format a CostComparison for display.

    Args:
        comparison: Cost comparison data.
        trend: Optional trend summary to append.
        output_format: One of "table", "json".

    Returns:
        Formatted string.
    """
    if output_format == "json":
        return format_comparison_json(comparison, trend)
    return _format_comparison_table(comparison, trend)


def _format_change_str(value) -> str:
    """金額の変化を +/- 付きで文字列化する。"""
    if value > 0:
        return f"+${value:,.2f}"
    elif value < 0:
        return f"-${abs(value):,.2f}"
    else:
        return "$0.00"


def _format_pct_change_str(value) -> str:
    """パーセント変化を +/- 付きで文字列化する。"""
    if value is None:
        return "N/A"
    if value > 0:
        return f"+{value}%"
    elif value < 0:
        return f"{value}%"
    else:
        return "0.0%"


def _format_comparison_table(comparison: CostComparison, trend: TrendSummary | None) -> str:
    """Render CostComparison as a Rich Table string."""
    table = Table(title=None, show_header=True, header_style="bold")
    table.add_column("サービス", style="cyan", min_width=20)
    table.add_column("前期", justify="right", style="green", min_width=12)
    table.add_column("当期", justify="right", style="green", min_width=12)
    table.add_column("変化", justify="right", min_width=10)
    table.add_column("%Δ", justify="right", min_width=8)

    for item in comparison.items:
        change_str = _format_change_str(item.absolute_change)
        pct_str = _format_pct_change_str(item.percent_change)
        table.add_row(
            item.service,
            f"${item.previous_amount:,.2f}",
            f"${item.current_amount:,.2f}",
            change_str,
            pct_str,
        )

    # 合計行
    table.add_section()
    total_change_str = _format_change_str(comparison.total_change)
    total_pct_str = _format_pct_change_str(comparison.total_change_percent)
    table.add_row(
        Text("合計", style="bold"),
        Text(f"${comparison.previous_period.total:,.2f}", style="bold green"),
        Text(f"${comparison.current_period.total:,.2f}", style="bold green"),
        Text(total_change_str, style="bold"),
        Text(total_pct_str, style="bold"),
    )

    console = Console(file=io.StringIO(), force_terminal=False, width=100)
    console.print(table)

    if trend is not None:
        panel = Panel(trend.summary_text, title="サマリー")
        console.print(panel)

    return console.file.getvalue()


def format_comparison_json(
    comparison: CostComparison,
    trend: TrendSummary | None = None,
) -> str:
    """Render CostComparison as JSON matching API contract."""
    data = {
        "type": "comparison",
        "current_period": {
            "start": str(comparison.current_period.period_start),
            "end": str(comparison.current_period.period_end),
        },
        "previous_period": {
            "start": str(comparison.previous_period.period_start),
            "end": str(comparison.previous_period.period_end),
        },
        "currency": comparison.current_period.currency,
        "items": [
            {
                "service": item.service,
                "previous_amount": float(item.previous_amount),
                "current_amount": float(item.current_amount),
                "absolute_change": float(item.absolute_change),
                "percent_change": float(item.percent_change) if item.percent_change is not None else None,
            }
            for item in comparison.items
        ],
        "total_change": float(comparison.total_change),
        "total_change_percent": float(comparison.total_change_percent),
    }
    if trend is not None:
        data["trend"] = {
            "overall_direction": trend.overall_direction,
            "total_change_text": trend.total_change_text,
            "top_increases": trend.top_increases,
            "notable_decreases": trend.notable_decreases,
            "summary_text": trend.summary_text,
        }
    return json.dumps(data, ensure_ascii=False, indent=2)
