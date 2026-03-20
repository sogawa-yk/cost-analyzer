"""Unit tests for output formatter."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

import pytest

from cost_analyzer.models import (
    CostBreakdown,
    CostComparison,
    ErrorResponse,
    ErrorType,
    ServiceCost,
    ServiceDelta,
    TrendSummary,
)


class TestFormatBreakdown:
    """Tests for format_breakdown function."""

    def _make_breakdown(self):
        return CostBreakdown(
            period_start=date(2026, 2, 1),
            period_end=date(2026, 3, 1),
            currency="USD",
            items=[
                ServiceCost(group_key="Compute", amount=Decimal("1234.56"), percentage=Decimal("64.5"), rank=1),
                ServiceCost(group_key="Object Storage", amount=Decimal("678.90"), percentage=Decimal("35.5"), rank=2),
            ],
            total=Decimal("1913.46"),
        )

    def test_format_breakdown_renders_table_with_correct_columns(self):
        from cost_analyzer.formatter import format_breakdown

        result = format_breakdown(self._make_breakdown(), output_format="table")

        assert "サービス" in result or "Compute" in result
        assert "1,234.56" in result or "1234.56" in result
        assert "64.5%" in result or "64.5" in result

    def test_format_breakdown_formats_currency_consistently(self):
        from cost_analyzer.formatter import format_breakdown

        result = format_breakdown(self._make_breakdown(), output_format="table")

        # Should have dollar sign and comma formatting
        assert "$1,234.56" in result
        assert "$678.90" in result

    def test_format_breakdown_json_output_matches_contract(self):
        from cost_analyzer.formatter import format_breakdown

        result = format_breakdown(self._make_breakdown(), output_format="json")
        data = json.loads(result)

        assert data["type"] == "breakdown"
        assert "period" in data
        assert data["period"]["start"] == "2026-02-01"
        assert data["period"]["end"] == "2026-03-01"
        assert data["currency"] == "USD"
        assert len(data["items"]) == 2
        assert data["items"][0]["service"] == "Compute"
        assert data["total"] == pytest.approx(1913.46)

    def test_format_breakdown_csv_output(self):
        from cost_analyzer.formatter import format_breakdown

        result = format_breakdown(self._make_breakdown(), output_format="csv")

        lines = result.strip().split("\n")
        assert len(lines) == 3  # header + 2 items
        assert "service" in lines[0].lower() or "サービス" in lines[0]

    def test_format_breakdown_includes_period_label(self):
        from cost_analyzer.formatter import format_breakdown

        result = format_breakdown(self._make_breakdown(), output_format="table")

        assert "2026-02-01" in result
        assert "2026-03-01" in result


class TestFormatError:
    """Tests for format_error function."""

    def test_format_error_includes_actionable_guidance(self):
        from cost_analyzer.formatter import format_error

        error = ErrorResponse(
            error_type=ErrorType.PARSE_ERROR,
            message="クエリを理解できませんでした。",
            guidance="もう少し具体的に入力してください。",
            example_queries=["先月のサービス別コストを教えて"],
        )

        result = format_error(error)

        assert "クエリを理解できませんでした" in result
        assert "具体的に" in result
        assert "先月のサービス別コストを教えて" in result

    def test_format_error_auth_error(self):
        from cost_analyzer.formatter import format_error

        error = ErrorResponse(
            error_type=ErrorType.AUTH_ERROR,
            message="OCI 認証に失敗しました。",
            guidance="認証情報を確認してください。",
        )

        result = format_error(error)

        assert "認証" in result


class TestFormatComparison:
    """Tests for format_comparison function."""

    def _make_comparison(self):
        current = CostBreakdown(
            period_start=date(2026, 2, 1),
            period_end=date(2026, 3, 1),
            currency="USD",
            items=[
                ServiceCost(group_key="Compute", amount=Decimal("1234.56"), percentage=Decimal("64.5"), rank=1),
                ServiceCost(group_key="Object Storage", amount=Decimal("678.90"), percentage=Decimal("35.5"), rank=2),
            ],
            total=Decimal("1913.46"),
        )
        previous = CostBreakdown(
            period_start=date(2026, 1, 1),
            period_end=date(2026, 2, 1),
            currency="USD",
            items=[
                ServiceCost(group_key="Compute", amount=Decimal("1100.00"), percentage=Decimal("61.1"), rank=1),
                ServiceCost(group_key="Object Storage", amount=Decimal("700.00"), percentage=Decimal("38.9"), rank=2),
            ],
            total=Decimal("1800.00"),
        )
        return CostComparison(
            current_period=current,
            previous_period=previous,
            items=[
                ServiceDelta(
                    group_key="Compute",
                    current_amount=Decimal("1234.56"),
                    previous_amount=Decimal("1100.00"),
                    absolute_change=Decimal("134.56"),
                    percent_change=Decimal("12.2"),
                ),
                ServiceDelta(
                    group_key="Object Storage",
                    current_amount=Decimal("678.90"),
                    previous_amount=Decimal("700.00"),
                    absolute_change=Decimal("-21.10"),
                    percent_change=Decimal("-3.0"),
                ),
            ],
            total_change=Decimal("113.46"),
            total_change_percent=Decimal("6.3"),
        )

    def _make_trend(self):
        return TrendSummary(
            language="ja",
            overall_direction="increase",
            total_change_text="合計コストが $113.46 (6.3%) 増加しました。",
            top_increases=["Compute (+$134.56)"],
            notable_decreases=["Object Storage (-$21.10)"],
            summary_text=(
                "合計コストが $113.46 (6.3%) 増加しました。"
                "Compute の増加額が最大 (+$134.56)。Object Storage はわずかに減少 (-$21.10)。"
            ),
        )

    def test_format_comparison_renders_delta_columns(self):
        from cost_analyzer.formatter import format_comparison

        result = format_comparison(self._make_comparison(), output_format="table")

        assert "サービス" in result
        assert "前期" in result
        assert "当期" in result
        assert "変化" in result
        assert "%Δ" in result

    def test_format_comparison_shows_positive_negative_signs(self):
        from cost_analyzer.formatter import format_comparison

        result = format_comparison(self._make_comparison(), output_format="table")

        assert "+$134.56" in result
        assert "-$21.10" in result
        assert "+12.2%" in result
        assert "-3.0%" in result

    def test_format_comparison_appends_trend_summary_panel(self):
        from cost_analyzer.formatter import format_comparison

        trend = self._make_trend()
        result = format_comparison(self._make_comparison(), trend=trend, output_format="table")

        assert "サマリー" in result
        assert "増加" in result
        assert "Compute" in result
