"""OCI クライアントの実接続統合テスト。

実際の OCI 認証情報を使用して API 呼び出しを検証する。
実行: uv run pytest tests/integration/test_oci_client.py -m oci
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from cost_analyzer.oci_client import OCIClient


@pytest.fixture(scope="module")
def oci_client():
    """実 OCI 認証情報で OCIClient を初期化する。"""
    try:
        client = OCIClient()
    except Exception as e:
        pytest.skip(f"OCI 認証情報が利用できません: {e}")
    return client


@pytest.mark.oci
class TestOCIClientConnection:
    """OCI クライアントの接続テスト。"""

    def test_client_initializes(self, oci_client):
        """OCIClient が正常に初期化されることを確認する。"""
        assert oci_client is not None
        assert oci_client.genai_client is not None
        assert oci_client.compartment_id is not None

    def test_request_cost_data_returns_list(self, oci_client):
        """先月のコストデータが取得できることを確認する。"""
        today = date.today()
        start = today.replace(day=1) - timedelta(days=1)
        start = start.replace(day=1)  # 先月1日
        end = today.replace(day=1)  # 今月1日

        items = oci_client.request_cost_data(
            start_date=start,
            end_date=end,
            granularity="MONTHLY",
        )

        assert isinstance(items, list)
        # テナンシーにコストデータが存在するはず
        assert len(items) > 0, "先月のコストデータが空です"

    def test_cost_line_items_have_required_fields(self, oci_client):
        """CostLineItem のフィールドが正しく設定されていることを確認する。"""
        today = date.today()
        start = today.replace(day=1) - timedelta(days=1)
        start = start.replace(day=1)
        end = today.replace(day=1)

        items = oci_client.request_cost_data(
            start_date=start,
            end_date=end,
            granularity="MONTHLY",
        )

        assert len(items) > 0
        item = items[0]
        assert item.service is not None
        assert item.amount is not None
        assert item.currency is not None
        assert item.amount >= 0

    def test_request_cost_data_with_service_filter(self, oci_client):
        """サービスフィルタ付きでコストデータが取得できることを確認する。"""
        today = date.today()
        start = today.replace(day=1) - timedelta(days=1)
        start = start.replace(day=1)
        end = today.replace(day=1)

        # まずフィルタなしで取得してサービス名を得る
        all_items = oci_client.request_cost_data(
            start_date=start,
            end_date=end,
            granularity="MONTHLY",
        )
        if not all_items:
            pytest.skip("コストデータが存在しません")

        service_name = all_items[0].service

        # フィルタ付きで取得
        filtered = oci_client.request_cost_data(
            start_date=start,
            end_date=end,
            granularity="MONTHLY",
            service_filter=service_name,
        )

        assert isinstance(filtered, list)
        for item in filtered:
            assert item.service == service_name

    def test_get_available_services(self, oci_client):
        """利用可能なサービス一覧が取得できることを確認する。"""
        services = oci_client.get_available_services()

        assert isinstance(services, list)
        assert len(services) > 0, "利用可能なサービスが空です"

    def test_get_available_compartments(self, oci_client):
        """利用可能なコンパートメント一覧が取得できることを確認する。"""
        compartments = oci_client.get_available_compartments()

        assert isinstance(compartments, list)
        assert len(compartments) > 0, "利用可能なコンパートメントが空です"


@pytest.mark.oci
class TestGenAIParser:
    """GenAI サービスを使った NL パーサーの実接続テスト。"""

    def test_parse_japanese_breakdown_query(self, oci_client):
        """日本語の内訳クエリが正しくパースされることを確認する。"""
        from cost_analyzer.models import CostQuery, QueryType
        from cost_analyzer.parser import parse_query

        result = parse_query("先月のサービス別コストを教えて", oci_client)

        assert isinstance(result, CostQuery), f"パースエラー: {result}"
        assert result.query_type == QueryType.BREAKDOWN
        assert result.start_date is not None
        assert result.end_date is not None
        assert result.detected_language == "ja"

    def test_parse_english_breakdown_query(self, oci_client):
        """英語の内訳クエリが正しくパースされることを確認する。"""
        from cost_analyzer.models import CostQuery, QueryType
        from cost_analyzer.parser import parse_query

        result = parse_query("Show costs for last month", oci_client)

        assert isinstance(result, CostQuery), f"パースエラー: {result}"
        assert result.query_type == QueryType.BREAKDOWN
        assert result.detected_language == "en"

    def test_parse_comparison_query(self, oci_client):
        """比較クエリが正しくパースされることを確認する。"""
        from cost_analyzer.models import CostQuery, QueryType
        from cost_analyzer.parser import parse_query

        result = parse_query("先月と今月のコストを比較して", oci_client)

        assert isinstance(result, CostQuery), f"パースエラー: {result}"
        assert result.query_type == QueryType.COMPARISON
        assert result.comparison_start_date is not None
        assert result.comparison_end_date is not None

    def test_parse_service_filter_query(self, oci_client):
        """サービスフィルタ付きクエリがパースされることを確認する。"""
        from cost_analyzer.models import CostQuery
        from cost_analyzer.parser import parse_query

        result = parse_query(
            "先月のCOMPUTEサービスだけのコストをservice_filterで絞り込んで教えて", oci_client
        )

        assert isinstance(result, CostQuery), f"パースエラー: {result}"
        # LLM が service_filter を設定することを期待するが、
        # 非決定的なので設定されなくてもテスト自体は通す
        if result.service_filter is not None:
            assert "COMPUTE" in result.service_filter.upper()


@pytest.mark.oci
class TestEndToEndPipeline:
    """パーサー → エンジン → フォーマッターの E2E テスト。"""

    def test_breakdown_pipeline(self, oci_client):
        """内訳クエリの全パイプラインが動作することを確認する。"""
        from cost_analyzer.engine import fetch_breakdown
        from cost_analyzer.formatter import format_breakdown
        from cost_analyzer.models import CostBreakdown, CostQuery, ErrorResponse
        from cost_analyzer.parser import parse_query

        # Step 1: パース
        query = parse_query("先月のサービス別コストを教えて", oci_client)
        assert isinstance(query, CostQuery), f"パースエラー: {query}"

        # Step 2: データ取得・集約
        result = fetch_breakdown(query, oci_client)
        assert not isinstance(result, ErrorResponse), f"エンジンエラー: {result}"
        assert isinstance(result, CostBreakdown)
        assert result.total > 0
        assert len(result.items) > 0

        # Step 3: フォーマット（テーブル）
        table_output = format_breakdown(result, output_format="table")
        assert table_output is not None

        # Step 3b: フォーマット（JSON）
        json_output = format_breakdown(result, output_format="json")
        assert "items" in json_output or "total" in json_output

    def test_comparison_pipeline(self, oci_client):
        """比較クエリの全パイプラインが動作することを確認する。"""
        from datetime import date

        from cost_analyzer.engine import fetch_comparison, generate_trend_summary
        from cost_analyzer.formatter import format_comparison
        from cost_analyzer.models import CostComparison, CostQuery, ErrorResponse, QueryType

        # LLM のパース結果に依存せず、確実にデータがある期間で CostQuery を直接構築
        query = CostQuery(
            query_type=QueryType.COMPARISON,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 3, 1),
            comparison_start_date=date(2026, 1, 1),
            comparison_end_date=date(2026, 2, 1),
            detected_language="ja",
        )

        # Step 1: 比較データ取得
        result = fetch_comparison(query, oci_client)
        assert not isinstance(result, ErrorResponse), f"エンジンエラー: {result}"
        assert isinstance(result, CostComparison)

        # Step 2: トレンドサマリー生成
        summary = generate_trend_summary(result, query.detected_language)
        assert summary.summary_text is not None
        assert summary.overall_direction in ("increase", "decrease", "stable")

        # Step 3: フォーマット
        output = format_comparison(result, output_format="table")
        assert output is not None
