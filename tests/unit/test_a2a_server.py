"""Unit tests for A2A server module."""

from __future__ import annotations

import asyncio
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cost_analyzer.a2a_server import (
    CostAnalyzerAgentExecutor,
    StructuredCostRequest,
    StructuredCostResponse,
    _breakdown_to_response,
    _comparison_to_response,
    _error_to_data,
    build_agent_card,
)
from cost_analyzer.models import (
    CostBreakdown,
    CostComparison,
    ErrorResponse,
    ErrorType,
    ServiceCost,
    ServiceDelta,
)


# ---------------------------------------------------------------------------
# Agent Card tests (T007)
# ---------------------------------------------------------------------------


class TestBuildAgentCard:
    """Agent Card 定義の検証。"""

    def test_agent_card_has_six_skills(self):
        card = build_agent_card()
        assert len(card.skills) == 6

    def test_agent_card_skill_ids(self):
        card = build_agent_card()
        skill_ids = {s.id for s in card.skills}
        expected = {
            "analyze_cost",
            "get_cost_breakdown",
            "compare_costs",
            "list_services",
            "list_compartments",
            "health_check",
        }
        assert skill_ids == expected

    def test_agent_card_required_fields(self):
        card = build_agent_card()
        assert card.name == "Cost Analyzer Agent"
        assert card.version == "1.0.0"
        assert card.protocol_version == "0.3.0"
        assert card.capabilities.streaming is False
        assert card.capabilities.push_notifications is False

    def test_agent_card_url_uses_host_port(self):
        card = build_agent_card(host="10.0.0.1", port=9090)
        assert card.url == "http://10.0.0.1:9090/a2a"

    def test_agent_card_input_output_modes(self):
        card = build_agent_card()
        assert "text" in card.default_input_modes
        assert "data" in card.default_input_modes
        assert "text" in card.default_output_modes
        assert "data" in card.default_output_modes

    def test_each_skill_has_tags_and_description(self):
        card = build_agent_card()
        for skill in card.skills:
            assert skill.description, f"Skill {skill.id} missing description"
            assert skill.tags, f"Skill {skill.id} missing tags"
            assert skill.name, f"Skill {skill.id} missing name"


# ---------------------------------------------------------------------------
# StructuredCostRequest validation tests (T018)
# ---------------------------------------------------------------------------


class TestStructuredCostRequestValidation:
    """StructuredCostRequest のバリデーション。"""

    def test_valid_breakdown_request(self):
        req = StructuredCostRequest(
            skill="get_cost_breakdown",
            start_date=date(2026, 2, 1),
            end_date=date(2026, 3, 1),
        )
        assert req.skill == "get_cost_breakdown"

    def test_breakdown_missing_dates_raises(self):
        with pytest.raises(ValueError, match="start_date and end_date"):
            StructuredCostRequest(skill="get_cost_breakdown")

    def test_breakdown_invalid_date_range_raises(self):
        with pytest.raises(ValueError, match="start_date must be before"):
            StructuredCostRequest(
                skill="get_cost_breakdown",
                start_date=date(2026, 3, 1),
                end_date=date(2026, 2, 1),
            )

    def test_valid_compare_request(self):
        req = StructuredCostRequest(
            skill="compare_costs",
            start_date=date(2026, 2, 1),
            end_date=date(2026, 3, 1),
            comparison_start_date=date(2026, 1, 1),
            comparison_end_date=date(2026, 2, 1),
        )
        assert req.skill == "compare_costs"

    def test_compare_missing_comparison_dates_raises(self):
        with pytest.raises(ValueError, match="compare_costs requires"):
            StructuredCostRequest(
                skill="compare_costs",
                start_date=date(2026, 2, 1),
                end_date=date(2026, 3, 1),
            )

    def test_compare_invalid_comparison_range_raises(self):
        with pytest.raises(ValueError, match="comparison_start_date must be before"):
            StructuredCostRequest(
                skill="compare_costs",
                start_date=date(2026, 2, 1),
                end_date=date(2026, 3, 1),
                comparison_start_date=date(2026, 2, 1),
                comparison_end_date=date(2026, 1, 1),
            )

    def test_utility_skill_no_dates_required(self):
        req = StructuredCostRequest(skill="list_services")
        assert req.skill == "list_services"

    def test_extra_fields_ignored(self):
        req = StructuredCostRequest(
            skill="list_services",
            unknown_field="should_be_ignored",
        )
        assert req.skill == "list_services"
        assert not hasattr(req, "unknown_field")

    def test_default_lang_is_ja(self):
        req = StructuredCostRequest(skill="health_check")
        assert req.lang == "ja"


# ---------------------------------------------------------------------------
# Response conversion tests (T012)
# ---------------------------------------------------------------------------


class TestBreakdownToResponse:
    """CostBreakdown → StructuredCostResponse 変換。"""

    def test_converts_breakdown_to_response(self):
        breakdown = CostBreakdown(
            period_start=date(2026, 2, 1),
            period_end=date(2026, 3, 1),
            currency="USD",
            items=[
                ServiceCost(service="COMPUTE", amount=Decimal("1234.56"), percentage=Decimal("100.0"), rank=1),
            ],
            total=Decimal("1234.56"),
        )
        resp = _breakdown_to_response(breakdown, "ja")
        assert resp.type == "breakdown"
        assert resp.data["total"] == 1234.56
        assert len(resp.data["items"]) == 1
        assert "合計" in resp.summary

    def test_converts_breakdown_to_english(self):
        breakdown = CostBreakdown(
            period_start=date(2026, 2, 1),
            period_end=date(2026, 3, 1),
            currency="USD",
            items=[],
            total=Decimal("0"),
        )
        resp = _breakdown_to_response(breakdown, "en")
        assert "Cost breakdown" in resp.summary


class TestComparisonToResponse:
    """CostComparison → StructuredCostResponse 変換。"""

    def test_converts_comparison_to_response(self):
        current = CostBreakdown(
            period_start=date(2026, 2, 1),
            period_end=date(2026, 3, 1),
            currency="USD",
            items=[ServiceCost(service="COMPUTE", amount=Decimal("1500"), percentage=Decimal("100"), rank=1)],
            total=Decimal("1500"),
        )
        previous = CostBreakdown(
            period_start=date(2026, 1, 1),
            period_end=date(2026, 2, 1),
            currency="USD",
            items=[ServiceCost(service="COMPUTE", amount=Decimal("1000"), percentage=Decimal("100"), rank=1)],
            total=Decimal("1000"),
        )
        comparison = CostComparison(
            current_period=current,
            previous_period=previous,
            items=[
                ServiceDelta(
                    service="COMPUTE",
                    current_amount=Decimal("1500"),
                    previous_amount=Decimal("1000"),
                    absolute_change=Decimal("500"),
                    percent_change=Decimal("50.0"),
                ),
            ],
            total_change=Decimal("500"),
            total_change_percent=Decimal("50.0"),
        )
        resp = _comparison_to_response(comparison, "ja")
        assert resp.type == "comparison"
        assert resp.data["total_change"] == 500.0


# ---------------------------------------------------------------------------
# Error conversion tests (T012)
# ---------------------------------------------------------------------------


class TestErrorToData:
    """ErrorResponse → DataPart dict 変換。"""

    def test_converts_error_with_all_fields(self):
        error = ErrorResponse(
            error_type=ErrorType.AUTH_ERROR,
            message="OCI authentication failed",
            guidance="Check OCI config",
            example_queries=["先月のコスト"],
        )
        data = _error_to_data(error)
        assert data["error_type"] == "auth_error"
        assert data["message"] == "OCI authentication failed"
        assert data["guidance"] == "Check OCI config"
        assert data["example_queries"] == ["先月のコスト"]

    def test_converts_error_without_examples(self):
        error = ErrorResponse(
            error_type=ErrorType.API_ERROR,
            message="API error",
            guidance="Retry later",
        )
        data = _error_to_data(error)
        assert "example_queries" not in data


# ---------------------------------------------------------------------------
# AgentExecutor tests (T012)
# ---------------------------------------------------------------------------


class TestCostAnalyzerAgentExecutor:
    """CostAnalyzerAgentExecutor のルーティングテスト。"""

    @pytest.fixture
    def executor(self):
        return CostAnalyzerAgentExecutor()

    @pytest.fixture
    def event_queue(self):
        return MagicMock(spec=["enqueue_event"])

    @pytest.fixture
    def make_context(self):
        def _make(parts):
            from a2a.types import Message, Part

            msg = Message(
                message_id="test-msg",
                role="user",
                parts=parts,
            )
            ctx = MagicMock(spec=["message", "task_id", "context_id"])
            ctx.message = msg
            ctx.task_id = "test-task-id"
            ctx.context_id = "test-ctx-id"
            return ctx
        return _make

    @pytest.mark.asyncio
    async def test_empty_message_returns_error(self, executor, event_queue):
        event_queue.enqueue_event = AsyncMock()
        ctx = MagicMock(spec=["message", "task_id", "context_id"])
        ctx.message = None
        ctx.task_id = "t1"
        ctx.context_id = "c1"

        await executor.execute(ctx, event_queue)
        event_queue.enqueue_event.assert_called_once()
        event = event_queue.enqueue_event.call_args[0][0]
        assert event.status.state == "failed"

    @pytest.mark.asyncio
    async def test_unknown_skill_returns_error(self, executor, event_queue, make_context):
        from a2a.types import DataPart, Part

        event_queue.enqueue_event = AsyncMock()
        ctx = make_context([Part(root=DataPart(data={"skill": "nonexistent"}))])

        await executor.execute(ctx, event_queue)
        event = event_queue.enqueue_event.call_args[0][0]
        assert event.status.state == "failed"
        # Check error message mentions unknown skill
        error_data = event.status.message.parts[0].root.data
        assert "nonexistent" in error_data["message"]

    @pytest.mark.asyncio
    async def test_text_part_routes_to_analyze_cost(self, executor, event_queue, make_context):
        from a2a.types import Part, TextPart

        event_queue.enqueue_event = AsyncMock()
        ctx = make_context([Part(root=TextPart(text="先月のコスト"))])

        with patch.object(executor, "_handle_text_query", new_callable=AsyncMock) as mock:
            await executor.execute(ctx, event_queue)
            mock.assert_called_once_with(event_queue, "test-task-id", "test-ctx-id", "先月のコスト")

    @pytest.mark.asyncio
    async def test_data_part_routes_to_structured_cost(self, executor, event_queue, make_context):
        from a2a.types import DataPart, Part

        event_queue.enqueue_event = AsyncMock()
        data = {"skill": "get_cost_breakdown", "start_date": "2026-02-01", "end_date": "2026-03-01"}
        ctx = make_context([Part(root=DataPart(data=data))])

        with patch.object(executor, "_handle_structured_cost", new_callable=AsyncMock) as mock:
            await executor.execute(ctx, event_queue)
            mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_data_part_routes_to_utility_skill(self, executor, event_queue, make_context):
        from a2a.types import DataPart, Part

        event_queue.enqueue_event = AsyncMock()
        ctx = make_context([Part(root=DataPart(data={"skill": "list_services"}))])

        with patch.object(executor, "_handle_utility_skill", new_callable=AsyncMock) as mock:
            await executor.execute(ctx, event_queue)
            mock.assert_called_once_with(event_queue, "test-task-id", "test-ctx-id", "list_services")


# ---------------------------------------------------------------------------
# Utility skill tests (T023)
# ---------------------------------------------------------------------------


class TestUtilitySkills:
    """list_services, list_compartments, health_check のユニットテスト。"""

    @pytest.fixture
    def executor(self):
        return CostAnalyzerAgentExecutor()

    @pytest.fixture
    def event_queue(self):
        q = MagicMock()
        q.enqueue_event = AsyncMock()
        return q

    @pytest.mark.asyncio
    async def test_list_services_returns_service_list(self, executor, event_queue):
        mock_client = MagicMock()
        mock_client.get_available_services.return_value = ["COMPUTE", "OBJECT_STORAGE"]

        with patch("cost_analyzer.a2a_server._get_oci_client", return_value=mock_client):
            await executor._handle_utility_skill(event_queue, "t1", "c1", "list_services")

        event = event_queue.enqueue_event.call_args[0][0]
        assert event.status.state == "completed"
        data = event.status.message.parts[0].root.data
        assert data["type"] == "services"
        assert data["data"] == ["COMPUTE", "OBJECT_STORAGE"]

    @pytest.mark.asyncio
    async def test_list_compartments_returns_compartment_list(self, executor, event_queue):
        mock_client = MagicMock()
        mock_client.get_available_compartments.return_value = ["root", "dev"]

        with patch("cost_analyzer.a2a_server._get_oci_client", return_value=mock_client):
            await executor._handle_utility_skill(event_queue, "t1", "c1", "list_compartments")

        event = event_queue.enqueue_event.call_args[0][0]
        assert event.status.state == "completed"
        data = event.status.message.parts[0].root.data
        assert data["type"] == "compartments"
        assert data["data"] == ["root", "dev"]

    @pytest.mark.asyncio
    async def test_health_check_returns_health_status(self, executor, event_queue):
        mock_client = MagicMock()
        mock_client.genai_client = MagicMock()

        with patch("cost_analyzer.a2a_server._get_oci_client", return_value=mock_client):
            await executor._handle_utility_skill(event_queue, "t1", "c1", "health_check")

        event = event_queue.enqueue_event.call_args[0][0]
        assert event.status.state == "completed"
        data = event.status.message.parts[0].root.data
        assert data["type"] == "health"
        assert data["data"]["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_utility_skill_oci_error_returns_failed(self, executor, event_queue):
        with patch("cost_analyzer.a2a_server._get_oci_client", side_effect=Exception("connection refused")):
            await executor._handle_utility_skill(event_queue, "t1", "c1", "list_services")

        event = event_queue.enqueue_event.call_args[0][0]
        assert event.status.state == "failed"
