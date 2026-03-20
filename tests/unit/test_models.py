"""Unit tests for Pydantic models."""

from datetime import date, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from cost_analyzer.models import (
    CostBreakdown,
    CostLineItem,
    CostQuery,
    ErrorResponse,
    ErrorType,
    QueryType,
    ServiceCost,
    ServiceDelta,
    TrendSummary,
)


class TestCostQuery:
    """Tests for CostQuery model."""

    def test_valid_breakdown_query(self):
        q = CostQuery(
            query_type=QueryType.BREAKDOWN,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 3, 1),
            detected_language="ja",
        )
        assert q.query_type == QueryType.BREAKDOWN
        assert q.needs_clarification is False

    def test_valid_comparison_query(self):
        q = CostQuery(
            query_type=QueryType.COMPARISON,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 3, 1),
            comparison_start_date=date(2026, 1, 1),
            comparison_end_date=date(2026, 2, 1),
            detected_language="en",
        )
        assert q.query_type == QueryType.COMPARISON

    def test_start_date_must_be_before_end_date(self):
        with pytest.raises(ValidationError, match="start_date.*end_date"):
            CostQuery(
                query_type=QueryType.BREAKDOWN,
                start_date=date(2026, 3, 1),
                end_date=date(2026, 2, 1),
                detected_language="ja",
            )

    def test_comparison_requires_comparison_dates(self):
        with pytest.raises(ValidationError, match="comparison"):
            CostQuery(
                query_type=QueryType.COMPARISON,
                start_date=date(2026, 2, 1),
                end_date=date(2026, 3, 1),
                detected_language="ja",
            )

    def test_needs_clarification_requires_message(self):
        with pytest.raises(ValidationError, match="clarification"):
            CostQuery(
                query_type=QueryType.BREAKDOWN,
                start_date=date(2026, 2, 1),
                end_date=date(2026, 3, 1),
                needs_clarification=True,
                detected_language="ja",
            )

    def test_valid_clarification(self):
        q = CostQuery(
            query_type=QueryType.BREAKDOWN,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 3, 1),
            needs_clarification=True,
            clarification_message="どの期間を指しますか？",
            detected_language="ja",
        )
        assert q.needs_clarification is True

    def test_service_filter(self):
        q = CostQuery(
            query_type=QueryType.BREAKDOWN,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 3, 1),
            service_filter="COMPUTE",
            detected_language="ja",
        )
        assert q.service_filter == "COMPUTE"


class TestCostLineItem:
    """Tests for CostLineItem model."""

    def test_valid_line_item(self):
        item = CostLineItem(
            service="COMPUTE",
            amount=Decimal("1234.56"),
            currency="USD",
            time_usage_started=datetime(2026, 2, 1),
            time_usage_ended=datetime(2026, 3, 1),
        )
        assert item.service == "COMPUTE"

    def test_amount_must_be_non_negative(self):
        with pytest.raises(ValidationError, match="amount"):
            CostLineItem(
                service="COMPUTE",
                amount=Decimal("-1"),
                currency="USD",
                time_usage_started=datetime(2026, 2, 1),
                time_usage_ended=datetime(2026, 3, 1),
            )

    def test_time_ordering(self):
        with pytest.raises(ValidationError, match="time"):
            CostLineItem(
                service="COMPUTE",
                amount=Decimal("100"),
                currency="USD",
                time_usage_started=datetime(2026, 3, 1),
                time_usage_ended=datetime(2026, 2, 1),
            )


class TestServiceCost:
    """Tests for ServiceCost model."""

    def test_valid_service_cost(self):
        sc = ServiceCost(
            group_key="COMPUTE",
            amount=Decimal("1234.56"),
            percentage=Decimal("45.2"),
            rank=1,
        )
        assert sc.percentage == Decimal("45.2")

    def test_percentage_must_be_0_to_100(self):
        with pytest.raises(ValidationError, match="percentage"):
            ServiceCost(
                group_key="COMPUTE",
                amount=Decimal("100"),
                percentage=Decimal("101"),
                rank=1,
            )

    def test_percentage_cannot_be_negative(self):
        with pytest.raises(ValidationError, match="percentage"):
            ServiceCost(
                group_key="COMPUTE",
                amount=Decimal("100"),
                percentage=Decimal("-1"),
                rank=1,
            )

    def test_rank_must_be_positive(self):
        with pytest.raises(ValidationError, match="rank"):
            ServiceCost(
                group_key="COMPUTE",
                amount=Decimal("100"),
                percentage=Decimal("50"),
                rank=0,
            )


class TestCostBreakdown:
    """Tests for CostBreakdown model."""

    def test_valid_breakdown(self):
        items = [
            ServiceCost(group_key="COMPUTE", amount=Decimal("100"), percentage=Decimal("60"), rank=1),
            ServiceCost(group_key="STORAGE", amount=Decimal("66.67"), percentage=Decimal("40"), rank=2),
        ]
        bd = CostBreakdown(
            period_start=date(2026, 2, 1),
            period_end=date(2026, 3, 1),
            currency="USD",
            items=items,
            total=Decimal("166.67"),
        )
        assert len(bd.items) == 2


class TestServiceDelta:
    """Tests for ServiceDelta model."""

    def test_valid_delta(self):
        d = ServiceDelta(
            group_key="COMPUTE",
            current_amount=Decimal("200"),
            previous_amount=Decimal("150"),
            absolute_change=Decimal("50"),
            percent_change=Decimal("33.33"),
        )
        assert d.absolute_change == Decimal("50")

    def test_percent_change_can_be_none(self):
        d = ServiceDelta(
            group_key="COMPUTE",
            current_amount=Decimal("200"),
            previous_amount=Decimal("0"),
            absolute_change=Decimal("200"),
            percent_change=None,
        )
        assert d.percent_change is None


class TestTrendSummary:
    """Tests for TrendSummary model."""

    def test_valid_trend(self):
        t = TrendSummary(
            language="ja",
            overall_direction="increase",
            total_change_text="合計コストが$150 (12%)増加しました",
            top_increases=["COMPUTE +$100", "STORAGE +$50"],
            notable_decreases=["NETWORKING -$20"],
            summary_text="全体的にコストが増加しています。",
        )
        assert t.overall_direction == "increase"


class TestErrorResponse:
    """Tests for ErrorResponse model."""

    def test_parse_error_with_examples(self):
        e = ErrorResponse(
            error_type=ErrorType.PARSE_ERROR,
            message="クエリを理解できませんでした。",
            guidance="具体的に入力してください。",
            example_queries=["先月のコストを教えて"],
        )
        assert e.error_type == ErrorType.PARSE_ERROR
        assert len(e.example_queries) == 1

    def test_auth_error_without_examples(self):
        e = ErrorResponse(
            error_type=ErrorType.AUTH_ERROR,
            message="認証に失敗しました。",
            guidance="認証情報を確認してください。",
        )
        assert e.example_queries is None
