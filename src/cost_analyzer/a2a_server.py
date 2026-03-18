"""A2A (Agent-to-Agent Protocol) server integration for cost-analyzer.

Exposes cost analysis capabilities to external agents via the A2A protocol.
Uses Google's official a2a-sdk for protocol handling.
"""

from __future__ import annotations

import logging
import uuid
from datetime import date
from typing import TYPE_CHECKING, Any

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.apps.jsonrpc import A2AFastAPIApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
    DataPart,
    Message,
    Part,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
    TextPart,
)
from pydantic import BaseModel, ConfigDict, model_validator

from cost_analyzer.models import (
    CostBreakdown,
    CostComparison,
    CostQuery,
    ErrorResponse,
    ErrorType,
    QueryType,
)

if TYPE_CHECKING:
    from a2a.server.events import EventQueue

logger = logging.getLogger("cost_analyzer.a2a_server")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

OCI_API_TIMEOUT_SECONDS = 30


def _get_oci_client():
    """Get or create a cached OCIClient instance via api module."""
    from cost_analyzer.api import _get_oci_client as api_get_oci_client
    return api_get_oci_client()

SKILL_IDS = {
    "analyze_cost",
    "get_cost_breakdown",
    "compare_costs",
    "list_services",
    "list_compartments",
    "health_check",
}


# ---------------------------------------------------------------------------
# Agent Card
# ---------------------------------------------------------------------------


def build_agent_card(host: str = "localhost", port: int = 8080) -> AgentCard:
    """Build the Agent Card for the cost-analyzer agent."""
    return AgentCard(
        name="Cost Analyzer Agent",
        description=(
            "OCI cost analysis agent that provides cost breakdown, "
            "comparison, and resource discovery capabilities "
            "via natural language or structured parameters."
        ),
        url=f"http://{host}:{port}/a2a",
        version="1.0.0",
        protocol_version="0.3.0",
        capabilities=AgentCapabilities(
            streaming=False,
            push_notifications=False,
        ),
        default_input_modes=["text", "data"],
        default_output_modes=["text", "data"],
        skills=[
            AgentSkill(
                id="analyze_cost",
                name="Cost Analysis (Natural Language)",
                description=(
                    "Analyze OCI costs using natural language queries "
                    "in Japanese or English. Automatically detects whether "
                    "to show a breakdown or comparison."
                ),
                tags=["oci", "cost", "natural-language"],
                examples=[
                    "先月のサービス別コストを教えて",
                    "Show me last month's cost breakdown",
                    "先月と今月のコストを比較して",
                ],
                input_modes=["text"],
                output_modes=["text", "data"],
            ),
            AgentSkill(
                id="get_cost_breakdown",
                name="Cost Breakdown",
                description=(
                    "Get cost breakdown by service for a specified period "
                    "using structured parameters. No LLM parsing required."
                ),
                tags=["oci", "cost", "breakdown", "structured"],
                examples=["Get cost breakdown for February 2026"],
                input_modes=["data"],
                output_modes=["text", "data"],
            ),
            AgentSkill(
                id="compare_costs",
                name="Cost Comparison",
                description=(
                    "Compare costs between two periods using structured "
                    "parameters. Returns absolute and percentage changes "
                    "per service."
                ),
                tags=["oci", "cost", "comparison", "structured"],
                examples=["Compare January and February 2026 costs"],
                input_modes=["data"],
                output_modes=["text", "data"],
            ),
            AgentSkill(
                id="list_services",
                name="List Available Services",
                description=(
                    "List all OCI services with cost data available "
                    "in the tenancy."
                ),
                tags=["oci", "services", "discovery"],
                examples=["What services are available?"],
                input_modes=["text", "data"],
                output_modes=["data"],
            ),
            AgentSkill(
                id="list_compartments",
                name="List Available Compartments",
                description=(
                    "List all OCI compartments available in the tenancy."
                ),
                tags=["oci", "compartments", "discovery"],
                examples=["List compartments"],
                input_modes=["text", "data"],
                output_modes=["data"],
            ),
            AgentSkill(
                id="health_check",
                name="Health Check",
                description=(
                    "Check connectivity to OCI Usage API and GenAI service."
                ),
                tags=["health", "status"],
                examples=["Check system health"],
                input_modes=["text", "data"],
                output_modes=["data"],
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------


class StructuredCostRequest(BaseModel):
    """構造化パラメータによるコスト分析リクエスト。"""

    model_config = ConfigDict(extra="ignore")

    skill: str
    start_date: date | None = None
    end_date: date | None = None
    comparison_start_date: date | None = None
    comparison_end_date: date | None = None
    service_filter: str | None = None
    compartment_filter: str | None = None
    lang: str = "ja"

    @model_validator(mode="after")
    def _validate_by_skill(self) -> StructuredCostRequest:
        if self.skill == "get_cost_breakdown":
            if not self.start_date or not self.end_date:
                msg = "get_cost_breakdown requires start_date and end_date."
                raise ValueError(msg)
            if self.start_date >= self.end_date:
                msg = "start_date must be before end_date."
                raise ValueError(msg)
        elif self.skill == "compare_costs":
            for field in ("start_date", "end_date", "comparison_start_date", "comparison_end_date"):
                if getattr(self, field) is None:
                    msg = f"compare_costs requires {field}."
                    raise ValueError(msg)
            if self.start_date >= self.end_date:
                msg = "start_date must be before end_date."
                raise ValueError(msg)
            if self.comparison_start_date >= self.comparison_end_date:
                msg = "comparison_start_date must be before comparison_end_date."
                raise ValueError(msg)
        return self


class StructuredCostResponse(BaseModel):
    """構造化されたコスト分析結果。"""

    type: str
    data: Any
    summary: str


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _breakdown_to_response(breakdown: CostBreakdown, lang: str = "ja") -> StructuredCostResponse:
    """CostBreakdown を StructuredCostResponse に変換する。"""
    data = {
        "period_start": str(breakdown.period_start),
        "period_end": str(breakdown.period_end),
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
    if lang == "ja":
        summary = (
            f"{breakdown.period_start}〜{breakdown.period_end}のコスト内訳: "
            f"合計 ${breakdown.total:,.2f}"
        )
    else:
        summary = (
            f"Cost breakdown for {breakdown.period_start} to {breakdown.period_end}: "
            f"total ${breakdown.total:,.2f}"
        )
    return StructuredCostResponse(type="breakdown", data=data, summary=summary)


def _comparison_to_response(
    comparison: CostComparison, lang: str = "ja",
) -> StructuredCostResponse:
    """CostComparison を StructuredCostResponse に変換する。"""
    from cost_analyzer.engine import generate_trend_summary

    trend = generate_trend_summary(comparison, lang)
    data = {
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
                "current_amount": float(item.current_amount),
                "previous_amount": float(item.previous_amount),
                "absolute_change": float(item.absolute_change),
                "percent_change": float(item.percent_change) if item.percent_change is not None else None,
            }
            for item in comparison.items
        ],
        "total_change": float(comparison.total_change),
        "total_change_percent": float(comparison.total_change_percent),
    }
    return StructuredCostResponse(type="comparison", data=data, summary=trend.summary_text)


def _error_to_data(error: ErrorResponse) -> dict[str, Any]:
    """ErrorResponse を A2A DataPart 用の dict に変換する。"""
    result: dict[str, Any] = {
        "error_type": error.error_type.value,
        "message": error.message,
        "guidance": error.guidance,
    }
    if error.example_queries:
        result["example_queries"] = error.example_queries
    return result


# ---------------------------------------------------------------------------
# AgentExecutor
# ---------------------------------------------------------------------------


class CostAnalyzerAgentExecutor(AgentExecutor):
    """A2A AgentExecutor implementation for cost-analyzer."""

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Process an incoming A2A message and enqueue the result."""
        task_id = context.task_id or str(uuid.uuid4())
        context_id = context.context_id or str(uuid.uuid4())

        try:
            message = context.message
            if not message or not message.parts:
                await self._enqueue_error(
                    event_queue, task_id, context_id,
                    ErrorResponse(
                        error_type=ErrorType.PARSE_ERROR,
                        message="No message parts provided.",
                        guidance="Send a TextPart or DataPart with your request.",
                    ),
                )
                return

            # Determine request type from first part
            first_part = message.parts[0].root if hasattr(message.parts[0], "root") else message.parts[0]

            if isinstance(first_part, TextPart):
                await self._handle_text_query(
                    event_queue, task_id, context_id, first_part.text,
                )
            elif isinstance(first_part, DataPart):
                await self._handle_data_query(
                    event_queue, task_id, context_id, first_part.data,
                )
            else:
                await self._enqueue_error(
                    event_queue, task_id, context_id,
                    ErrorResponse(
                        error_type=ErrorType.PARSE_ERROR,
                        message="Unsupported message part type.",
                        guidance="Send a TextPart (natural language) or DataPart (structured parameters).",
                    ),
                )

        except Exception as e:
            logger.exception("Unexpected error in A2A execute")
            await self._enqueue_error(
                event_queue, task_id, context_id,
                ErrorResponse(
                    error_type=ErrorType.API_ERROR,
                    message=f"Unexpected error: {e}",
                    guidance="Please retry. If the issue persists, check server logs.",
                ),
            )

    async def cancel(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Cancel is not supported for synchronous processing."""
        task_id = context.task_id or str(uuid.uuid4())
        context_id = context.context_id or str(uuid.uuid4())
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=task_id,
                context_id=context_id,
                final=True,
                status=TaskStatus(state=TaskState.canceled),
            )
        )

    # ---- Text query (analyze_cost) ----

    async def _handle_text_query(
        self,
        event_queue: EventQueue,
        task_id: str,
        context_id: str,
        text: str,
    ) -> None:
        """Handle natural language cost analysis query."""
        from cost_analyzer.engine import fetch_breakdown, fetch_comparison
        from cost_analyzer.parser import parse_query

        oci_client = _get_oci_client()
        result = parse_query(text, oci_client)

        if isinstance(result, ErrorResponse):
            await self._enqueue_error(event_queue, task_id, context_id, result)
            return

        if result.needs_clarification:
            await self._enqueue_error(
                event_queue, task_id, context_id,
                ErrorResponse(
                    error_type=ErrorType.PARSE_ERROR,
                    message=result.clarification_message or "Clarification needed.",
                    guidance="Please rephrase your query.",
                ),
            )
            return

        lang = result.detected_language

        if result.query_type == QueryType.BREAKDOWN:
            data = fetch_breakdown(result, oci_client)
            if isinstance(data, ErrorResponse):
                await self._enqueue_error(event_queue, task_id, context_id, data)
                return
            response = _breakdown_to_response(data, lang)
        else:
            data = fetch_comparison(result, oci_client)
            if isinstance(data, ErrorResponse):
                await self._enqueue_error(event_queue, task_id, context_id, data)
                return
            response = _comparison_to_response(data, lang)

        await self._enqueue_success(event_queue, task_id, context_id, response)

    # ---- Data query (structured parameters) ----

    async def _handle_data_query(
        self,
        event_queue: EventQueue,
        task_id: str,
        context_id: str,
        data: dict[str, Any],
    ) -> None:
        """Handle structured parameter cost analysis query."""
        skill = data.get("skill", "")

        if skill == "analyze_cost":
            # Text-based skill sent via DataPart — extract text if present
            text = data.get("text", "")
            if text:
                await self._handle_text_query(event_queue, task_id, context_id, text)
            else:
                await self._enqueue_error(
                    event_queue, task_id, context_id,
                    ErrorResponse(
                        error_type=ErrorType.PARSE_ERROR,
                        message="analyze_cost skill requires a 'text' field.",
                        guidance="Send a TextPart or include 'text' in DataPart.",
                    ),
                )
            return

        if skill in ("list_services", "list_compartments", "health_check"):
            await self._handle_utility_skill(event_queue, task_id, context_id, skill)
            return

        if skill in ("get_cost_breakdown", "compare_costs"):
            await self._handle_structured_cost(event_queue, task_id, context_id, data)
            return

        await self._enqueue_error(
            event_queue, task_id, context_id,
            ErrorResponse(
                error_type=ErrorType.PARSE_ERROR,
                message=f"Unknown skill: '{skill}'.",
                guidance=f"Available skills: {', '.join(sorted(SKILL_IDS))}",
            ),
        )

    async def _handle_structured_cost(
        self,
        event_queue: EventQueue,
        task_id: str,
        context_id: str,
        data: dict[str, Any],
    ) -> None:
        """Handle get_cost_breakdown / compare_costs with structured params."""
        from cost_analyzer.engine import fetch_breakdown, fetch_comparison

        try:
            request = StructuredCostRequest(**data)
        except Exception as e:
            await self._enqueue_error(
                event_queue, task_id, context_id,
                ErrorResponse(
                    error_type=ErrorType.PARSE_ERROR,
                    message=f"Invalid parameters: {e}",
                    guidance="Check required fields and value constraints.",
                ),
            )
            return

        oci_client = _get_oci_client()
        lang = request.lang

        if request.skill == "get_cost_breakdown":
            query = CostQuery(
                query_type=QueryType.BREAKDOWN,
                start_date=request.start_date,
                end_date=request.end_date,
                service_filter=request.service_filter,
                compartment_filter=request.compartment_filter,
                detected_language=lang,
            )
            result = fetch_breakdown(query, oci_client)
            if isinstance(result, ErrorResponse):
                await self._enqueue_error(event_queue, task_id, context_id, result)
                return
            response = _breakdown_to_response(result, lang)

        else:  # compare_costs
            query = CostQuery(
                query_type=QueryType.COMPARISON,
                start_date=request.start_date,
                end_date=request.end_date,
                comparison_start_date=request.comparison_start_date,
                comparison_end_date=request.comparison_end_date,
                service_filter=request.service_filter,
                compartment_filter=request.compartment_filter,
                detected_language=lang,
            )
            result = fetch_comparison(query, oci_client)
            if isinstance(result, ErrorResponse):
                await self._enqueue_error(event_queue, task_id, context_id, result)
                return
            response = _comparison_to_response(result, lang)

        await self._enqueue_success(event_queue, task_id, context_id, response)

    # ---- Utility skills ----

    async def _handle_utility_skill(
        self,
        event_queue: EventQueue,
        task_id: str,
        context_id: str,
        skill: str,
    ) -> None:
        """Handle list_services, list_compartments, health_check."""
        try:
            oci_client = _get_oci_client()

            if skill == "list_services":
                services = oci_client.get_available_services()
                response = StructuredCostResponse(
                    type="services",
                    data=services,
                    summary=f"{len(services)} services available.",
                )
            elif skill == "list_compartments":
                compartments = oci_client.get_available_compartments()
                response = StructuredCostResponse(
                    type="compartments",
                    data=compartments,
                    summary=f"{len(compartments)} compartments available.",
                )
            else:  # health_check
                checks: dict[str, str] = {}
                healthy = True
                try:
                    checks["oci_usage_api"] = "ok"
                except Exception as e:
                    checks["oci_usage_api"] = f"error: {e}"
                    healthy = False
                try:
                    if hasattr(oci_client, "genai_client") and oci_client.genai_client is not None:
                        checks["oci_genai"] = "ok"
                    else:
                        checks["oci_genai"] = "error: genai client not initialized"
                        healthy = False
                except Exception as e:
                    checks["oci_genai"] = f"error: {e}"
                    healthy = False

                response = StructuredCostResponse(
                    type="health",
                    data={"status": "healthy" if healthy else "unhealthy", "checks": checks},
                    summary="healthy" if healthy else "unhealthy",
                )

            await self._enqueue_success(event_queue, task_id, context_id, response)

        except Exception as e:
            logger.exception("Error in utility skill: %s", skill)
            from cost_analyzer.config import map_oci_error

            error_type, message, guidance = map_oci_error(e)
            await self._enqueue_error(
                event_queue, task_id, context_id,
                ErrorResponse(
                    error_type=ErrorType(error_type),
                    message=message,
                    guidance=guidance,
                ),
            )

    # ---- Event helpers ----

    async def _enqueue_success(
        self,
        event_queue: EventQueue,
        task_id: str,
        context_id: str,
        response: StructuredCostResponse,
    ) -> None:
        """Enqueue a successful task result."""
        msg = Message(
            message_id=str(uuid.uuid4()),
            role="agent",
            parts=[
                Part(root=DataPart(data=response.model_dump())),
                Part(root=TextPart(text=response.summary)),
            ],
        )
        # Enqueue status update with completed state
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=task_id,
                context_id=context_id,
                final=True,
                status=TaskStatus(state=TaskState.completed, message=msg),
            )
        )

    async def _enqueue_error(
        self,
        event_queue: EventQueue,
        task_id: str,
        context_id: str,
        error: ErrorResponse,
    ) -> None:
        """Enqueue a failed task result."""
        error_data = _error_to_data(error)
        msg = Message(
            message_id=str(uuid.uuid4()),
            role="agent",
            parts=[Part(root=DataPart(data=error_data))],
        )
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=task_id,
                context_id=context_id,
                final=True,
                status=TaskStatus(state=TaskState.failed, message=msg),
            )
        )


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def create_a2a_app(
    host: str = "localhost",
    port: int = 8080,
) -> A2AFastAPIApplication:
    """Create A2AFastAPIApplication with all components wired up."""
    agent_card = build_agent_card(host, port)
    executor = CostAnalyzerAgentExecutor()
    task_store = InMemoryTaskStore()
    handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=task_store,
    )
    return A2AFastAPIApplication(
        agent_card=agent_card,
        http_handler=handler,
    )
