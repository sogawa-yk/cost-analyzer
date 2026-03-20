"""Shared test fixtures and factory functions."""

from datetime import date, datetime
from decimal import Decimal

import pytest


def make_cost_query(
    query_type="breakdown",
    start_date=None,
    end_date=None,
    comparison_start_date=None,
    comparison_end_date=None,
    service_filter=None,
    compartment_filter=None,
    group_by="service",
    needs_clarification=False,
    clarification_message=None,
    detected_language="ja",
):
    """Factory for CostQuery test data."""
    from cost_analyzer.models import CostQuery, QueryType

    return CostQuery(
        query_type=QueryType(query_type),
        start_date=start_date or date(2026, 2, 1),
        end_date=end_date or date(2026, 3, 1),
        comparison_start_date=comparison_start_date,
        comparison_end_date=comparison_end_date,
        service_filter=service_filter,
        compartment_filter=compartment_filter,
        group_by=group_by,
        needs_clarification=needs_clarification,
        clarification_message=clarification_message,
        detected_language=detected_language,
    )


def make_cost_line_item(
    service="COMPUTE",
    amount=Decimal("1234.56"),
    currency="USD",
    compartment_name="root",
    compartment_path="/root",
    time_usage_started=None,
    time_usage_ended=None,
):
    """Factory for CostLineItem test data."""
    from cost_analyzer.models import CostLineItem

    return CostLineItem(
        service=service,
        amount=amount,
        currency=currency,
        compartment_name=compartment_name,
        compartment_path=compartment_path,
        time_usage_started=time_usage_started or datetime(2026, 2, 1),
        time_usage_ended=time_usage_ended or datetime(2026, 3, 1),
    )


def make_cost_breakdown(items=None, total=None, currency="USD", period_start=None, period_end=None):
    """Factory for CostBreakdown test data."""
    from cost_analyzer.models import CostBreakdown, ServiceCost

    if items is None:
        items = [
            ServiceCost(group_key="COMPUTE", amount=Decimal("1234.56"), percentage=Decimal("64.5"), rank=1),
            ServiceCost(group_key="OBJECT_STORAGE", amount=Decimal("678.90"), percentage=Decimal("35.5"), rank=2),
        ]
    return CostBreakdown(
        period_start=period_start or date(2026, 2, 1),
        period_end=period_end or date(2026, 3, 1),
        currency=currency,
        items=items,
        total=total or sum(item.amount for item in items),
    )


@pytest.fixture
def sample_cost_query():
    """Sample CostQuery for breakdown."""
    return make_cost_query()


@pytest.fixture
def sample_comparison_query():
    """Sample CostQuery for comparison."""
    return make_cost_query(
        query_type="comparison",
        start_date=date(2026, 2, 1),
        end_date=date(2026, 3, 1),
        comparison_start_date=date(2026, 1, 1),
        comparison_end_date=date(2026, 2, 1),
    )


@pytest.fixture
def sample_line_items():
    """Sample CostLineItem list from OCI API."""
    return [
        make_cost_line_item(service="COMPUTE", amount=Decimal("1234.56")),
        make_cost_line_item(service="OBJECT_STORAGE", amount=Decimal("678.90")),
        make_cost_line_item(service="NETWORKING", amount=Decimal("456.78")),
        make_cost_line_item(service="DATABASE", amount=Decimal("234.56")),
        make_cost_line_item(service="OTHER", amount=Decimal("128.34")),
    ]


@pytest.fixture
def sample_breakdown():
    """Sample CostBreakdown."""
    return make_cost_breakdown()


@pytest.fixture
def mock_oci_usage_summary():
    """Mock OCI UsageSummary response data."""

    class MockUsageSummary:
        def __init__(self, service, computed_amount, currency, compartment_name=None):
            self.service = service
            self.computed_amount = computed_amount
            self.currency = currency
            self.compartment_name = compartment_name or "root"
            self.compartment_path = f"/{self.compartment_name}"
            self.time_usage_started = datetime(2026, 2, 1)
            self.time_usage_ended = datetime(2026, 3, 1)

    return [
        MockUsageSummary("COMPUTE", 1234.56, "USD"),
        MockUsageSummary("OBJECT_STORAGE", 678.90, "USD"),
        MockUsageSummary("NETWORKING", 456.78, "USD"),
    ]
