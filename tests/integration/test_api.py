"""FastAPI エンドポイントの統合テスト。"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from cost_analyzer.api import app
from cost_analyzer.models import (
    CostBreakdown,
    CostComparison,
    CostQuery,
    ErrorResponse,
    ErrorType,
    QueryType,
    ServiceCost,
    ServiceDelta,
    TrendSummary,
)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def _reset_oci_client():
    """テスト間でグローバル OCI クライアントをリセットする。"""
    import cost_analyzer.api as api_module

    api_module._oci_client = None
    yield
    api_module._oci_client = None


class TestQueryEndpoint:
    """POST /query のテスト。"""

    def test_breakdown_success(self, client):
        """内訳クエリが正常にレスポンスを返すことを確認する。"""
        breakdown = CostBreakdown(
            period_start=date(2026, 2, 1),
            period_end=date(2026, 3, 1),
            currency="USD",
            items=[
                ServiceCost(
                    service="COMPUTE",
                    amount=Decimal("1234.56"),
                    percentage=Decimal("100.0"),
                    rank=1,
                ),
            ],
            total=Decimal("1234.56"),
        )
        query = CostQuery(
            query_type=QueryType.BREAKDOWN,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 3, 1),
            detected_language="ja",
        )

        with (
            patch("cost_analyzer.api._get_oci_client") as mock_get_client,
            patch("cost_analyzer.parser.parse_query", return_value=query),
            patch(
                "cost_analyzer.engine.fetch_breakdown", return_value=breakdown
            ),
        ):
            mock_get_client.return_value = MagicMock()
            response = client.post("/query", json={"query": "先月のコスト"})

        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "breakdown"
        assert "period" in data
        assert data["currency"] == "USD"
        assert len(data["items"]) == 1

    def test_parse_error_returns_400(self, client):
        """パースエラー時に 400 が返ることを確認する。"""
        error = ErrorResponse(
            error_type=ErrorType.PARSE_ERROR,
            message="クエリを理解できませんでした。",
            guidance="具体的に入力してください。",
            example_queries=["先月のコストを教えて"],
        )

        with (
            patch("cost_analyzer.api._get_oci_client") as mock_get_client,
            patch("cost_analyzer.parser.parse_query", return_value=error),
        ):
            mock_get_client.return_value = MagicMock()
            response = client.post("/query", json={"query": "asdf"})

        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "parse_error"
        assert "example_queries" in data

    def test_auth_error_returns_401(self, client):
        """認証エラー時に 401 が返ることを確認する。"""
        error = ErrorResponse(
            error_type=ErrorType.AUTH_ERROR,
            message="認証に失敗しました。",
            guidance="認証情報を確認してください。",
        )

        with (
            patch("cost_analyzer.api._get_oci_client") as mock_get_client,
            patch("cost_analyzer.parser.parse_query", return_value=error),
        ):
            mock_get_client.return_value = MagicMock()
            response = client.post("/query", json={"query": "先月のコスト"})

        assert response.status_code == 401

    def test_api_error_returns_502(self, client):
        """API エラー時に 502 が返ることを確認する。"""
        error = ErrorResponse(
            error_type=ErrorType.API_ERROR,
            message="OCI コスト管理 API が一時的に利用できません。",
            guidance="数分後に再試行してください。",
        )

        with (
            patch("cost_analyzer.api._get_oci_client") as mock_get_client,
            patch("cost_analyzer.parser.parse_query", return_value=error),
        ):
            mock_get_client.return_value = MagicMock()
            response = client.post("/query", json={"query": "先月のコスト"})

        assert response.status_code == 502

    def test_no_data_error_returns_404(self, client):
        """データなしエラー時に適切なレスポンスが返ることを確認する。"""
        error = ErrorResponse(
            error_type=ErrorType.NO_DATA,
            message="指定された期間にコストデータがありません。",
            guidance="別の期間を試してください。",
        )
        query = CostQuery(
            query_type=QueryType.BREAKDOWN,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 3, 1),
            detected_language="ja",
        )

        with (
            patch("cost_analyzer.api._get_oci_client") as mock_get_client,
            patch("cost_analyzer.parser.parse_query", return_value=query),
            patch("cost_analyzer.engine.fetch_breakdown", return_value=error),
        ):
            mock_get_client.return_value = MagicMock()
            response = client.post("/query", json={"query": "先月のコスト"})

        assert response.status_code == 404

    def test_clarification_response(self, client):
        """確認が必要な場合に clarification レスポンスが返ることを確認する。"""
        query = CostQuery(
            query_type=QueryType.BREAKDOWN,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 17),
            needs_clarification=True,
            clarification_message="どの期間を指しますか？",
            detected_language="ja",
        )

        with (
            patch("cost_analyzer.api._get_oci_client") as mock_get_client,
            patch("cost_analyzer.parser.parse_query", return_value=query),
        ):
            mock_get_client.return_value = MagicMock()
            response = client.post("/query", json={"query": "最近のコスト"})

        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "clarification"
        assert "message" in data

    def test_comparison_success(self, client):
        """比較クエリが previous_period_total と current_period_total を含むことを確認する。"""
        prev_breakdown = CostBreakdown(
            period_start=date(2026, 1, 1),
            period_end=date(2026, 2, 1),
            currency="USD",
            items=[
                ServiceCost(service="COMPUTE", amount=Decimal("1000.00"), percentage=Decimal("100.0"), rank=1),
            ],
            total=Decimal("1000.00"),
        )
        curr_breakdown = CostBreakdown(
            period_start=date(2026, 2, 1),
            period_end=date(2026, 3, 1),
            currency="USD",
            items=[
                ServiceCost(service="COMPUTE", amount=Decimal("1200.00"), percentage=Decimal("100.0"), rank=1),
            ],
            total=Decimal("1200.00"),
        )
        comparison = CostComparison(
            current_period=curr_breakdown,
            previous_period=prev_breakdown,
            items=[
                ServiceDelta(
                    service="COMPUTE",
                    current_amount=Decimal("1200.00"),
                    previous_amount=Decimal("1000.00"),
                    absolute_change=Decimal("200.00"),
                    percent_change=Decimal("20.0"),
                ),
            ],
            total_change=Decimal("200.00"),
            total_change_percent=Decimal("20.0"),
        )
        trend = TrendSummary(
            language="ja",
            overall_direction="increase",
            total_change_text="$200.00 増加",
            top_increases=["COMPUTE +$200.00"],
            notable_decreases=[],
            summary_text="合計コストが $200.00 (+20.0%) 増加しました。",
        )
        query = CostQuery(
            query_type=QueryType.COMPARISON,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 3, 1),
            comparison_start_date=date(2026, 1, 1),
            comparison_end_date=date(2026, 2, 1),
            detected_language="ja",
        )

        with (
            patch("cost_analyzer.api._get_oci_client") as mock_get_client,
            patch("cost_analyzer.parser.parse_query", return_value=query),
            patch("cost_analyzer.engine.fetch_comparison", return_value=comparison),
            patch("cost_analyzer.engine.generate_trend_summary", return_value=trend),
        ):
            mock_get_client.return_value = MagicMock()
            response = client.post("/query", json={"query": "先月と今月を比較して"})

        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "comparison"
        assert data["previous_period_total"] == 1000.00
        assert data["current_period_total"] == 1200.00
        assert data["total_change"] == 200.00
        assert data["total_change_percent"] == 20.0
        assert data["summary"] == "合計コストが $200.00 (+20.0%) 増加しました。"

    def test_missing_query_field_returns_422(self, client):
        """必須フィールド欠落時に 422 が返ることを確認する。"""
        response = client.post("/query", json={})

        assert response.status_code == 422

    def test_format_and_lang_parameters(self, client):
        """format と lang パラメータが受け付けられることを確認する。"""
        breakdown = CostBreakdown(
            period_start=date(2026, 2, 1),
            period_end=date(2026, 3, 1),
            currency="USD",
            items=[
                ServiceCost(
                    service="COMPUTE",
                    amount=Decimal("500.00"),
                    percentage=Decimal("100.0"),
                    rank=1,
                ),
            ],
            total=Decimal("500.00"),
        )
        query = CostQuery(
            query_type=QueryType.BREAKDOWN,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 3, 1),
            detected_language="en",
        )

        with (
            patch("cost_analyzer.api._get_oci_client") as mock_get_client,
            patch("cost_analyzer.parser.parse_query", return_value=query),
            patch("cost_analyzer.engine.fetch_breakdown", return_value=breakdown),
        ):
            mock_get_client.return_value = MagicMock()
            response = client.post(
                "/query",
                json={"query": "last month costs", "format": "json", "lang": "en"},
            )

        assert response.status_code == 200


class TestHealthEndpoint:
    """GET /health のテスト。"""

    def test_health_when_client_available(self, client):
        """OCI クライアントが利用可能な場合に healthy を返すことを確認する。"""
        mock_client = MagicMock()
        mock_client.genai_client = MagicMock()

        with patch("cost_analyzer.api._get_oci_client", return_value=mock_client):
            response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["checks"]["oci_usage_api"] == "ok"

    def test_health_when_client_fails(self, client):
        """OCI クライアントの初期化に失敗した場合に unhealthy を返すことを確認する。"""
        with patch(
            "cost_analyzer.api._get_oci_client",
            side_effect=Exception("connection failed"),
        ):
            response = client.get("/health")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
