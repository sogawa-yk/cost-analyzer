"""Integration tests for A2A JSON-RPC endpoint."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def mock_oci_client():
    """OCI クライアントのモック。"""
    client = MagicMock()
    client.genai_client = MagicMock()
    client.compartment_id = "test-compartment"
    client.get_available_services.return_value = ["COMPUTE", "OBJECT_STORAGE"]
    client.get_available_compartments.return_value = ["root", "dev"]
    return client


@pytest.fixture
def app(mock_oci_client):
    """A2A ルート付き FastAPI テストアプリ。"""
    with patch("cost_analyzer.a2a_server._get_oci_client", return_value=mock_oci_client):
        with patch("cost_analyzer.api._get_oci_client", return_value=mock_oci_client):
            from cost_analyzer.api import app as fastapi_app
            yield fastapi_app


@pytest.fixture
async def client(app):
    """httpx AsyncClient for testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# T008: Agent Card integration test
# ---------------------------------------------------------------------------


class TestAgentCardEndpoint:
    """GET /.well-known/agent-card.json の統合テスト。"""

    @pytest.mark.asyncio
    async def test_agent_card_returns_200(self, client):
        resp = await client.get("/.well-known/agent-card.json")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_agent_card_has_required_fields(self, client):
        resp = await client.get("/.well-known/agent-card.json")
        data = resp.json()
        assert data["name"] == "Cost Analyzer Agent"
        assert data["protocolVersion"] == "0.3.0"
        assert len(data["skills"]) == 6

    @pytest.mark.asyncio
    async def test_agent_card_skills_have_ids(self, client):
        resp = await client.get("/.well-known/agent-card.json")
        skills = resp.json()["skills"]
        skill_ids = {s["id"] for s in skills}
        expected = {
            "analyze_cost", "get_cost_breakdown", "compare_costs",
            "list_services", "list_compartments", "health_check",
        }
        assert skill_ids == expected


# ---------------------------------------------------------------------------
# T013: Natural language query integration test
# ---------------------------------------------------------------------------


class TestNaturalLanguageQuery:
    """自然言語クエリの JSON-RPC 統合テスト。"""

    @pytest.mark.asyncio
    async def test_text_query_returns_completed_task(self, client, mock_oci_client):
        from datetime import date, datetime
        from decimal import Decimal
        from unittest.mock import patch as _patch

        from cost_analyzer.models import CostQuery, QueryType

        mock_query = CostQuery(
            query_type=QueryType.BREAKDOWN,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 3, 1),
            detected_language="ja",
        )

        mock_oci_client.request_cost_data.return_value = [
            MagicMock(
                service="COMPUTE",
                computed_amount=1234.56,
                amount=Decimal("1234.56"),
                currency="USD",
                compartment_name="root",
                compartment_path="/root",
                time_usage_started=datetime(2026, 2, 1),
                time_usage_ended=datetime(2026, 3, 1),
            ),
        ]

        with _patch("cost_analyzer.parser.parse_query", return_value=mock_query):
            resp = await client.post("/a2a", json={
                "jsonrpc": "2.0",
                "id": "1",
                "method": "message/send",
                "params": {
                    "message": {
                        "role": "user",
                        "parts": [{"kind": "text", "text": "先月のコスト"}],
                        "messageId": "msg-1",
                    }
                },
            })

        assert resp.status_code == 200
        result = resp.json()["result"]
        assert result["status"]["state"] == "completed"

    @pytest.mark.asyncio
    async def test_text_query_parse_error_returns_failed(self, client, mock_oci_client):
        from cost_analyzer.models import ErrorResponse, ErrorType
        from unittest.mock import patch as _patch

        error = ErrorResponse(
            error_type=ErrorType.PARSE_ERROR,
            message="Cannot parse query",
            guidance="Try rephrasing",
        )
        with _patch("cost_analyzer.parser.parse_query", return_value=error):
            resp = await client.post("/a2a", json={
                "jsonrpc": "2.0",
                "id": "2",
                "method": "message/send",
                "params": {
                    "message": {
                        "role": "user",
                        "parts": [{"kind": "text", "text": "???"}],
                        "messageId": "msg-2",
                    }
                },
            })

        assert resp.status_code == 200
        result = resp.json()["result"]
        assert result["status"]["state"] == "failed"


# ---------------------------------------------------------------------------
# T019: Structured parameter integration test
# ---------------------------------------------------------------------------


class TestStructuredParameterQuery:
    """構造化パラメータの JSON-RPC 統合テスト。"""

    @pytest.mark.asyncio
    async def test_breakdown_with_structured_params(self, client, mock_oci_client):
        from datetime import datetime
        from decimal import Decimal

        mock_oci_client.request_cost_data.return_value = [
            MagicMock(
                service="COMPUTE",
                computed_amount=500.0,
                amount=Decimal("500.0"),
                currency="USD",
                compartment_name="root",
                compartment_path="/root",
                time_usage_started=datetime(2026, 2, 1),
                time_usage_ended=datetime(2026, 3, 1),
            ),
        ]

        resp = await client.post("/a2a", json={
            "jsonrpc": "2.0",
            "id": "3",
            "method": "message/send",
            "params": {
                "message": {
                    "role": "user",
                    "parts": [{
                        "kind": "data",
                        "data": {
                            "skill": "get_cost_breakdown",
                            "start_date": "2026-02-01",
                            "end_date": "2026-03-01",
                            "lang": "en",
                        },
                    }],
                    "messageId": "msg-3",
                }
            },
        })

        assert resp.status_code == 200
        result = resp.json()["result"]
        assert result["status"]["state"] == "completed"

    @pytest.mark.asyncio
    async def test_validation_error_returns_failed(self, client):
        resp = await client.post("/a2a", json={
            "jsonrpc": "2.0",
            "id": "4",
            "method": "message/send",
            "params": {
                "message": {
                    "role": "user",
                    "parts": [{
                        "kind": "data",
                        "data": {
                            "skill": "get_cost_breakdown",
                            # Missing required dates
                        },
                    }],
                    "messageId": "msg-4",
                }
            },
        })

        assert resp.status_code == 200
        result = resp.json()["result"]
        assert result["status"]["state"] == "failed"


# ---------------------------------------------------------------------------
# T024: Utility skills integration test
# ---------------------------------------------------------------------------


class TestUtilitySkillsIntegration:
    """リスト系・ヘルスチェックの JSON-RPC 統合テスト。"""

    @pytest.mark.asyncio
    async def test_list_services_returns_data(self, client):
        resp = await client.post("/a2a", json={
            "jsonrpc": "2.0",
            "id": "5",
            "method": "message/send",
            "params": {
                "message": {
                    "role": "user",
                    "parts": [{"kind": "data", "data": {"skill": "list_services"}}],
                    "messageId": "msg-5",
                }
            },
        })

        assert resp.status_code == 200
        result = resp.json()["result"]
        assert result["status"]["state"] == "completed"

    @pytest.mark.asyncio
    async def test_list_compartments_returns_data(self, client):
        resp = await client.post("/a2a", json={
            "jsonrpc": "2.0",
            "id": "6",
            "method": "message/send",
            "params": {
                "message": {
                    "role": "user",
                    "parts": [{"kind": "data", "data": {"skill": "list_compartments"}}],
                    "messageId": "msg-6",
                }
            },
        })

        assert resp.status_code == 200
        result = resp.json()["result"]
        assert result["status"]["state"] == "completed"

    @pytest.mark.asyncio
    async def test_health_check_returns_data(self, client):
        resp = await client.post("/a2a", json={
            "jsonrpc": "2.0",
            "id": "7",
            "method": "message/send",
            "params": {
                "message": {
                    "role": "user",
                    "parts": [{"kind": "data", "data": {"skill": "health_check"}}],
                    "messageId": "msg-7",
                }
            },
        })

        assert resp.status_code == 200
        result = resp.json()["result"]
        assert result["status"]["state"] == "completed"
