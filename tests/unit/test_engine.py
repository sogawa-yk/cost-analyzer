"""Unit tests for cost aggregation engine."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

from cost_analyzer.models import (
    CostBreakdown,
    CostComparison,
    CostLineItem,
    ErrorResponse,
    ErrorType,
    ServiceCost,
    TrendSummary,
)


class TestFetchBreakdown:
    """Tests for fetch_breakdown function."""

    def _make_query(self, **kwargs):
        from tests.conftest import make_cost_query
        return make_cost_query(**kwargs)

    def _make_client(self, items: list[CostLineItem]):
        client = MagicMock()
        client.request_cost_data.return_value = items
        return client

    def test_fetch_breakdown_sorts_by_amount_descending(self):
        from cost_analyzer.engine import fetch_breakdown
        from tests.conftest import make_cost_line_item

        items = [
            make_cost_line_item(service="SMALL", amount=Decimal("100")),
            make_cost_line_item(service="BIG", amount=Decimal("1000")),
            make_cost_line_item(service="MEDIUM", amount=Decimal("500")),
        ]
        query = self._make_query()
        client = self._make_client(items)

        result = fetch_breakdown(query, client)

        assert isinstance(result, CostBreakdown)
        assert result.items[0].service == "BIG"
        assert result.items[1].service == "MEDIUM"
        assert result.items[2].service == "SMALL"

    def test_fetch_breakdown_calculates_percentages_correctly(self):
        from cost_analyzer.engine import fetch_breakdown
        from tests.conftest import make_cost_line_item

        items = [
            make_cost_line_item(service="A", amount=Decimal("750")),
            make_cost_line_item(service="B", amount=Decimal("250")),
        ]
        query = self._make_query()
        client = self._make_client(items)

        result = fetch_breakdown(query, client)

        assert isinstance(result, CostBreakdown)
        assert result.items[0].percentage == Decimal("75.0")
        assert result.items[1].percentage == Decimal("25.0")

    def test_fetch_breakdown_includes_total(self):
        from cost_analyzer.engine import fetch_breakdown
        from tests.conftest import make_cost_line_item

        items = [
            make_cost_line_item(service="A", amount=Decimal("300")),
            make_cost_line_item(service="B", amount=Decimal("200")),
            make_cost_line_item(service="C", amount=Decimal("100")),
        ]
        query = self._make_query()
        client = self._make_client(items)

        result = fetch_breakdown(query, client)

        assert isinstance(result, CostBreakdown)
        assert result.total == Decimal("600")

    def test_fetch_breakdown_with_empty_data_returns_no_data_error(self):
        from cost_analyzer.engine import fetch_breakdown

        query = self._make_query()
        client = self._make_client([])

        result = fetch_breakdown(query, client)

        assert isinstance(result, ErrorResponse)
        assert result.error_type == ErrorType.NO_DATA

    def test_fetch_breakdown_with_zero_usage_returns_zero(self):
        from cost_analyzer.engine import fetch_breakdown
        from tests.conftest import make_cost_line_item

        items = [
            make_cost_line_item(service="A", amount=Decimal("0")),
            make_cost_line_item(service="B", amount=Decimal("0")),
        ]
        query = self._make_query()
        client = self._make_client(items)

        result = fetch_breakdown(query, client)

        assert isinstance(result, CostBreakdown)
        assert result.total == Decimal("0")

    def test_fetch_breakdown_aggregates_same_service(self):
        """Multiple line items for same service should be summed."""
        from cost_analyzer.engine import fetch_breakdown
        from tests.conftest import make_cost_line_item

        items = [
            make_cost_line_item(service="COMPUTE", amount=Decimal("100")),
            make_cost_line_item(service="COMPUTE", amount=Decimal("200")),
            make_cost_line_item(service="STORAGE", amount=Decimal("50")),
        ]
        query = self._make_query()
        client = self._make_client(items)

        result = fetch_breakdown(query, client)

        assert isinstance(result, CostBreakdown)
        assert result.items[0].service == "COMPUTE"
        assert result.items[0].amount == Decimal("300")
        assert result.total == Decimal("350")

    def test_fetch_breakdown_sets_ranks(self):
        from cost_analyzer.engine import fetch_breakdown
        from tests.conftest import make_cost_line_item

        items = [
            make_cost_line_item(service="A", amount=Decimal("100")),
            make_cost_line_item(service="B", amount=Decimal("200")),
        ]
        query = self._make_query()
        client = self._make_client(items)

        result = fetch_breakdown(query, client)

        assert isinstance(result, CostBreakdown)
        assert result.items[0].rank == 1
        assert result.items[1].rank == 2

    def test_fetch_breakdown_sets_period(self):
        from cost_analyzer.engine import fetch_breakdown
        from tests.conftest import make_cost_line_item

        items = [make_cost_line_item(service="A", amount=Decimal("100"))]
        query = self._make_query(start_date=date(2026, 1, 1), end_date=date(2026, 2, 1))
        client = self._make_client(items)

        result = fetch_breakdown(query, client)

        assert isinstance(result, CostBreakdown)
        assert result.period_start == date(2026, 1, 1)
        assert result.period_end == date(2026, 2, 1)


class TestFetchComparison:
    """Tests for fetch_comparison function."""

    def _make_comparison_query(self, **kwargs):
        from tests.conftest import make_cost_query

        defaults = dict(
            query_type="comparison",
            start_date=date(2026, 2, 1),
            end_date=date(2026, 3, 1),
            comparison_start_date=date(2026, 1, 1),
            comparison_end_date=date(2026, 2, 1),
        )
        defaults.update(kwargs)
        return make_cost_query(**defaults)

    def _make_client(self, current_items, previous_items):
        """Mock client that returns different items based on start_date."""

        client = MagicMock()

        def side_effect(start_date, end_date, service_filter=None, compartment_filter=None):
            if start_date == date(2026, 2, 1):
                return current_items
            else:
                return previous_items

        client.request_cost_data.side_effect = side_effect
        return client

    def test_fetch_comparison_calculates_deltas_correctly(self):
        from cost_analyzer.engine import fetch_comparison
        from tests.conftest import make_cost_line_item

        current = [
            make_cost_line_item(service="COMPUTE", amount=Decimal("1200")),
            make_cost_line_item(service="STORAGE", amount=Decimal("500")),
        ]
        previous = [
            make_cost_line_item(service="COMPUTE", amount=Decimal("1000")),
            make_cost_line_item(service="STORAGE", amount=Decimal("600")),
        ]
        query = self._make_comparison_query()
        client = self._make_client(current, previous)

        result = fetch_comparison(query, client)

        assert isinstance(result, CostComparison)
        compute_delta = next(d for d in result.items if d.service == "COMPUTE")
        assert compute_delta.absolute_change == Decimal("200")
        assert compute_delta.percent_change == Decimal("20.0")

        storage_delta = next(d for d in result.items if d.service == "STORAGE")
        assert storage_delta.absolute_change == Decimal("-100")
        assert storage_delta.percent_change == Decimal("-16.7")

    def test_fetch_comparison_sorts_by_absolute_change(self):
        from cost_analyzer.engine import fetch_comparison
        from tests.conftest import make_cost_line_item

        current = [
            make_cost_line_item(service="SMALL_CHANGE", amount=Decimal("110")),
            make_cost_line_item(service="BIG_CHANGE", amount=Decimal("500")),
        ]
        previous = [
            make_cost_line_item(service="SMALL_CHANGE", amount=Decimal("100")),
            make_cost_line_item(service="BIG_CHANGE", amount=Decimal("200")),
        ]
        query = self._make_comparison_query()
        client = self._make_client(current, previous)

        result = fetch_comparison(query, client)

        assert isinstance(result, CostComparison)
        # BIG_CHANGE has abs change 300, SMALL_CHANGE has abs change 10
        assert result.items[0].service == "BIG_CHANGE"
        assert result.items[1].service == "SMALL_CHANGE"

    def test_fetch_comparison_handles_new_service_in_current_period(self):
        from cost_analyzer.engine import fetch_comparison
        from tests.conftest import make_cost_line_item

        current = [
            make_cost_line_item(service="COMPUTE", amount=Decimal("1000")),
            make_cost_line_item(service="NEW_SERVICE", amount=Decimal("200")),
        ]
        previous = [
            make_cost_line_item(service="COMPUTE", amount=Decimal("1000")),
        ]
        query = self._make_comparison_query()
        client = self._make_client(current, previous)

        result = fetch_comparison(query, client)

        assert isinstance(result, CostComparison)
        new_svc = next(d for d in result.items if d.service == "NEW_SERVICE")
        assert new_svc.previous_amount == Decimal("0")
        assert new_svc.current_amount == Decimal("200")
        assert new_svc.absolute_change == Decimal("200")
        assert new_svc.percent_change is None  # division by zero

    def test_fetch_comparison_handles_removed_service(self):
        from cost_analyzer.engine import fetch_comparison
        from tests.conftest import make_cost_line_item

        current = [
            make_cost_line_item(service="COMPUTE", amount=Decimal("1000")),
        ]
        previous = [
            make_cost_line_item(service="COMPUTE", amount=Decimal("1000")),
            make_cost_line_item(service="OLD_SERVICE", amount=Decimal("300")),
        ]
        query = self._make_comparison_query()
        client = self._make_client(current, previous)

        result = fetch_comparison(query, client)

        assert isinstance(result, CostComparison)
        old_svc = next(d for d in result.items if d.service == "OLD_SERVICE")
        assert old_svc.current_amount == Decimal("0")
        assert old_svc.previous_amount == Decimal("300")
        assert old_svc.absolute_change == Decimal("-300")
        assert old_svc.percent_change == Decimal("-100.0")


class TestGenerateTrendSummary:
    """Tests for generate_trend_summary function."""

    def _make_comparison(self, current_items, previous_items, current_total, previous_total):
        from tests.conftest import make_cost_breakdown

        current = make_cost_breakdown(
            items=current_items,
            total=current_total,
            period_start=date(2026, 2, 1),
            period_end=date(2026, 3, 1),
        )
        previous = make_cost_breakdown(
            items=previous_items,
            total=previous_total,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 2, 1),
        )

        total_change = current_total - previous_total
        total_change_percent = (total_change / previous_total * 100).quantize(Decimal("0.1"))

        from cost_analyzer.models import ServiceDelta

        # Build deltas
        current_map = {i.service: i.amount for i in current_items}
        previous_map = {i.service: i.amount for i in previous_items}
        all_services = set(current_map.keys()) | set(previous_map.keys())

        deltas = []
        for svc in all_services:
            c = current_map.get(svc, Decimal("0"))
            p = previous_map.get(svc, Decimal("0"))
            ac = c - p
            pc = (ac / p * 100).quantize(Decimal("0.1")) if p != Decimal("0") else None
            deltas.append(ServiceDelta(
                service=svc, current_amount=c, previous_amount=p,
                absolute_change=ac, percent_change=pc,
            ))
        deltas.sort(key=lambda d: abs(d.absolute_change), reverse=True)

        return CostComparison(
            current_period=current,
            previous_period=previous,
            items=deltas,
            total_change=total_change,
            total_change_percent=total_change_percent,
        )

    def test_generate_trend_summary_identifies_top_3_increases(self):
        from cost_analyzer.engine import generate_trend_summary

        current_items = [
            ServiceCost(service="A", amount=Decimal("500"), percentage=Decimal("25.0"), rank=1),
            ServiceCost(service="B", amount=Decimal("400"), percentage=Decimal("20.0"), rank=2),
            ServiceCost(service="C", amount=Decimal("300"), percentage=Decimal("15.0"), rank=3),
            ServiceCost(service="D", amount=Decimal("200"), percentage=Decimal("10.0"), rank=4),
            ServiceCost(service="E", amount=Decimal("100"), percentage=Decimal("5.0"), rank=5),
        ]
        previous_items = [
            ServiceCost(service="A", amount=Decimal("100"), percentage=Decimal("10.0"), rank=1),
            ServiceCost(service="B", amount=Decimal("100"), percentage=Decimal("10.0"), rank=2),
            ServiceCost(service="C", amount=Decimal("100"), percentage=Decimal("10.0"), rank=3),
            ServiceCost(service="D", amount=Decimal("100"), percentage=Decimal("10.0"), rank=4),
            ServiceCost(service="E", amount=Decimal("200"), percentage=Decimal("20.0"), rank=5),
        ]

        comparison = self._make_comparison(
            current_items, previous_items,
            current_total=Decimal("1500"), previous_total=Decimal("600"),
        )
        summary = generate_trend_summary(comparison, "ja")

        assert isinstance(summary, TrendSummary)
        assert len(summary.top_increases) == 3
        # A increased by 400, B by 300, C by 200
        assert "A" in summary.top_increases[0]
        assert "B" in summary.top_increases[1]
        assert "C" in summary.top_increases[2]

    def test_generate_trend_summary_in_japanese(self):
        from cost_analyzer.engine import generate_trend_summary

        current_items = [
            ServiceCost(service="Compute", amount=Decimal("1200"), percentage=Decimal("70.6"), rank=1),
            ServiceCost(service="Storage", amount=Decimal("500"), percentage=Decimal("29.4"), rank=2),
        ]
        previous_items = [
            ServiceCost(service="Compute", amount=Decimal("1000"), percentage=Decimal("62.5"), rank=1),
            ServiceCost(service="Storage", amount=Decimal("600"), percentage=Decimal("37.5"), rank=2),
        ]

        comparison = self._make_comparison(
            current_items, previous_items,
            current_total=Decimal("1700"), previous_total=Decimal("1600"),
        )
        summary = generate_trend_summary(comparison, "ja")

        assert summary.language == "ja"
        assert summary.overall_direction == "increase"
        assert "増加" in summary.summary_text
        assert "Compute" in summary.summary_text

    def test_generate_trend_summary_in_english(self):
        from cost_analyzer.engine import generate_trend_summary

        current_items = [
            ServiceCost(service="Compute", amount=Decimal("1200"), percentage=Decimal("70.6"), rank=1),
            ServiceCost(service="Storage", amount=Decimal("500"), percentage=Decimal("29.4"), rank=2),
        ]
        previous_items = [
            ServiceCost(service="Compute", amount=Decimal("1000"), percentage=Decimal("62.5"), rank=1),
            ServiceCost(service="Storage", amount=Decimal("600"), percentage=Decimal("37.5"), rank=2),
        ]

        comparison = self._make_comparison(
            current_items, previous_items,
            current_total=Decimal("1700"), previous_total=Decimal("1600"),
        )
        summary = generate_trend_summary(comparison, "en")

        assert summary.language == "en"
        assert summary.overall_direction == "increase"
        assert "increased" in summary.summary_text.lower()
        assert "Compute" in summary.summary_text


class TestScopedQueries:
    """スコープ指定クエリ（US3）のテスト。"""

    def _make_query(self, **kwargs):
        from tests.conftest import make_cost_query
        return make_cost_query(**kwargs)

    def test_fetch_breakdown_with_service_filter_passes_filter_to_client(self):
        """service_filter が oci_client.request_cost_data() に渡されることを確認する。"""
        from cost_analyzer.engine import fetch_breakdown
        from tests.conftest import make_cost_line_item

        items = [make_cost_line_item(service="COMPUTE", amount=Decimal("500"))]
        client = MagicMock()
        client.request_cost_data.return_value = items

        query = self._make_query(service_filter="COMPUTE")
        result = fetch_breakdown(query, client)

        assert isinstance(result, CostBreakdown)
        # request_cost_data が service_filter="COMPUTE" で呼ばれたことを検証
        client.request_cost_data.assert_called_once_with(
            start_date=query.start_date,
            end_date=query.end_date,
            service_filter="COMPUTE",
            compartment_filter=None,
        )

    def test_fetch_breakdown_with_compartment_filter(self):
        """compartment_filter が oci_client.request_cost_data() に渡されることを確認する。"""
        from cost_analyzer.engine import fetch_breakdown
        from tests.conftest import make_cost_line_item

        items = [make_cost_line_item(service="COMPUTE", amount=Decimal("300"))]
        client = MagicMock()
        client.request_cost_data.return_value = items

        query = self._make_query(compartment_filter="production")
        result = fetch_breakdown(query, client)

        assert isinstance(result, CostBreakdown)
        # request_cost_data が compartment_filter="production" で呼ばれたことを検証
        client.request_cost_data.assert_called_once_with(
            start_date=query.start_date,
            end_date=query.end_date,
            service_filter=None,
            compartment_filter="production",
        )

    def test_scope_not_found_returns_suggestions(self):
        """フィルタ結果が空でフィルタなし結果が存在する場合、提案付き NO_DATA を返す。"""
        from cost_analyzer.engine import fetch_breakdown
        from tests.conftest import make_cost_line_item

        unfiltered_items = [
            make_cost_line_item(service="COMPUTE", amount=Decimal("1000")),
            make_cost_line_item(service="STORAGE", amount=Decimal("500")),
        ]

        client = MagicMock()
        # 最初の呼び出し（フィルタあり）→空、2回目（フィルタなし）→データあり
        client.request_cost_data.side_effect = [
            [],               # フィルタありの結果（空）
            unfiltered_items,  # フィルタなしの結果
        ]
        client.get_available_services.return_value = [
            "COMPUTE", "CONTAINER", "CONTENT_DELIVERY", "STORAGE",
        ]

        query = self._make_query(service_filter="COMPUT")
        result = fetch_breakdown(query, client)

        assert isinstance(result, ErrorResponse)
        assert result.error_type == ErrorType.NO_DATA
        assert "スコープ" in result.message
        # 類似サービス名が提案に含まれていることを検証
        assert "COMPUTE" in result.guidance
        client.get_available_services.assert_called_once()
