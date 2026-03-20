"""Unit tests for NL query parser."""

from __future__ import annotations

import json
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from cost_analyzer.models import ErrorResponse, ErrorType, QueryType
from cost_analyzer.parser import parse_query


def _make_mock_oci_client(response_data: dict | None = None, error: Exception | None = None):
    """Create a mock OCIClient with GenAI response."""
    mock_client = MagicMock()
    mock_client.compartment_id = "ocid1.compartment.test"

    if error:
        mock_client.genai_client.chat.side_effect = error
        return mock_client

    mock_text_content = MagicMock()
    mock_text_content.text = json.dumps(response_data or {})

    mock_message = MagicMock()
    mock_message.content = [mock_text_content]

    mock_choice = MagicMock()
    mock_choice.message = mock_message

    mock_chat_response = MagicMock()
    mock_chat_response.choices = [mock_choice]

    mock_response = MagicMock()
    mock_response.data.chat_response = mock_chat_response

    mock_client.genai_client.chat.return_value = mock_response
    return mock_client


@pytest.fixture(autouse=True)
def _patch_genai_models():
    """Patch OCI GenAI model classes to avoid real SDK instantiation."""
    with patch("cost_analyzer.parser.genai_models") as mock_models:
        # Make all model constructors return MagicMocks
        mock_models.GenericChatRequest.return_value = MagicMock()
        mock_models.SystemMessage.return_value = MagicMock()
        mock_models.UserMessage.return_value = MagicMock()
        mock_models.TextContent.return_value = MagicMock()
        mock_models.JsonSchemaResponseFormat.return_value = MagicMock()
        mock_models.ResponseJsonSchema.return_value = MagicMock()
        mock_models.ChatDetails.return_value = MagicMock()
        mock_models.OnDemandServingMode.return_value = MagicMock()
        yield mock_models


class TestParseQuery:
    """Tests for parse_query function."""

    def test_japanese_breakdown_query(self):
        """Test parsing Japanese breakdown query."""
        mock_client = _make_mock_oci_client({
            "query_type": "breakdown",
            "start_date": "2026-02-01",
            "end_date": "2026-03-01",
            "comparison_start_date": None,
            "comparison_end_date": None,
            "service_filter": None,
            "compartment_filter": None,
            "needs_clarification": False,
            "clarification_message": None,
            "detected_language": "ja",
        })

        result = parse_query("先月のサービス別コストを教えて", mock_client)

        assert not isinstance(result, ErrorResponse)
        assert result.query_type == QueryType.BREAKDOWN
        assert result.start_date == date(2026, 2, 1)
        assert result.end_date == date(2026, 3, 1)
        assert result.detected_language == "ja"

    def test_english_breakdown_query(self):
        """Test parsing English breakdown query."""
        mock_client = _make_mock_oci_client({
            "query_type": "breakdown",
            "start_date": "2026-02-01",
            "end_date": "2026-03-01",
            "comparison_start_date": None,
            "comparison_end_date": None,
            "service_filter": None,
            "compartment_filter": None,
            "needs_clarification": False,
            "clarification_message": None,
            "detected_language": "en",
        })

        result = parse_query("Show costs for February 2026", mock_client)

        assert not isinstance(result, ErrorResponse)
        assert result.query_type == QueryType.BREAKDOWN
        assert result.detected_language == "en"

    def test_ambiguous_query_returns_clarification(self):
        """Test that ambiguous queries return needs_clarification=True."""
        mock_client = _make_mock_oci_client({
            "query_type": "breakdown",
            "start_date": "2026-03-01",
            "end_date": "2026-03-17",
            "comparison_start_date": None,
            "comparison_end_date": None,
            "service_filter": None,
            "compartment_filter": None,
            "needs_clarification": True,
            "clarification_message": "「最近」はどの期間を指しますか？",
            "detected_language": "ja",
        })

        result = parse_query("最近のコスト", mock_client)

        assert not isinstance(result, ErrorResponse)
        assert result.needs_clarification is True
        assert result.clarification_message is not None

    def test_unparseable_query_returns_error(self):
        """Test that unparseable LLM response returns ErrorResponse."""
        mock_client = MagicMock()
        mock_client.compartment_id = "ocid1.compartment.test"

        mock_text_content = MagicMock()
        mock_text_content.text = "this is not json"

        mock_message = MagicMock()
        mock_message.content = [mock_text_content]

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_chat_response = MagicMock()
        mock_chat_response.choices = [mock_choice]

        mock_response = MagicMock()
        mock_response.data.chat_response = mock_chat_response

        mock_client.genai_client.chat.return_value = mock_response

        result = parse_query("asdfghjkl", mock_client)

        assert isinstance(result, ErrorResponse)
        assert result.error_type == ErrorType.PARSE_ERROR

    def test_oci_auth_error_returns_error_response(self):
        """Test that OCI auth errors are mapped correctly."""
        from oci.exceptions import ServiceError

        error = ServiceError(
            status=401,
            code="NotAuthenticated",
            headers={},
            message="Not authenticated",
        )
        mock_client = _make_mock_oci_client(error=error)

        result = parse_query("先月のコスト", mock_client)

        assert isinstance(result, ErrorResponse)
        assert result.error_type == ErrorType.AUTH_ERROR

    def test_comparison_query(self):
        """Test parsing comparison query."""
        mock_client = _make_mock_oci_client({
            "query_type": "comparison",
            "start_date": "2026-02-01",
            "end_date": "2026-03-01",
            "comparison_start_date": "2026-01-01",
            "comparison_end_date": "2026-02-01",
            "service_filter": None,
            "compartment_filter": None,
            "needs_clarification": False,
            "clarification_message": None,
            "detected_language": "ja",
        })

        result = parse_query("先月と今月を比較して", mock_client)

        assert not isinstance(result, ErrorResponse)
        assert result.query_type == QueryType.COMPARISON
        assert result.comparison_start_date == date(2026, 1, 1)

    def test_comparison_fallback_infers_previous_period(self):
        """LLM が比較日付を省略した場合、前期間が自動推定される。"""
        mock_client = _make_mock_oci_client({
            "query_type": "comparison",
            "start_date": "2026-03-01",
            "end_date": "2026-04-01",
            "comparison_start_date": None,
            "comparison_end_date": None,
            "service_filter": None,
            "compartment_filter": None,
            "needs_clarification": False,
            "clarification_message": None,
            "detected_language": "ja",
        })

        result = parse_query("先月と今月のコストを比較して", mock_client)

        assert not isinstance(result, ErrorResponse)
        assert result.query_type == QueryType.COMPARISON
        assert result.comparison_start_date == date(2026, 2, 1)
        assert result.comparison_end_date == date(2026, 3, 1)

    def test_comparison_with_explicit_dates_preserved(self):
        """LLM が比較日付を正しく返した場合、そのまま使用される。"""
        mock_client = _make_mock_oci_client({
            "query_type": "comparison",
            "start_date": "2026-02-01",
            "end_date": "2026-03-01",
            "comparison_start_date": "2026-01-01",
            "comparison_end_date": "2026-02-01",
            "service_filter": None,
            "compartment_filter": None,
            "needs_clarification": False,
            "clarification_message": None,
            "detected_language": "en",
        })

        result = parse_query("Compare January and February 2026", mock_client)

        assert not isinstance(result, ErrorResponse)
        assert result.comparison_start_date == date(2026, 1, 1)
        assert result.comparison_end_date == date(2026, 2, 1)

    def test_invalid_dates_return_parse_error(self):
        """start_date >= end_date の場合、api_error ではなく parse_error が返る。"""
        mock_client = _make_mock_oci_client({
            "query_type": "breakdown",
            "start_date": "2026-03-20",
            "end_date": "2026-03-01",
            "needs_clarification": False,
            "detected_language": "ja",
        })

        result = parse_query("今日の天気は？", mock_client)

        assert isinstance(result, ErrorResponse)
        assert result.error_type == ErrorType.PARSE_ERROR
        assert result.example_queries is not None

    def test_none_dates_return_parse_error(self):
        """日付が None の場合、api_error ではなく parse_error が返る。"""
        mock_client = _make_mock_oci_client({
            "query_type": "breakdown",
            "start_date": None,
            "end_date": None,
            "needs_clarification": False,
            "detected_language": "ja",
        })

        result = parse_query("コストを教えて", mock_client)

        assert isinstance(result, ErrorResponse)
        assert result.error_type == ErrorType.PARSE_ERROR
        assert result.example_queries is not None

    def test_validation_error_returns_parse_error(self):
        """Pydantic ValidationError が parse_error として返される。"""
        mock_client = _make_mock_oci_client({
            "query_type": "breakdown",
            "start_date": "2026-03-01",
            "end_date": "2026-04-01",
            "needs_clarification": False,
            "detected_language": "xx",
        })

        result = parse_query("Hello, what can you do?", mock_client)

        assert isinstance(result, ErrorResponse)
        assert result.error_type == ErrorType.PARSE_ERROR
        assert result.example_queries is not None

    def test_service_filter_object_storage_preserved(self):
        """service_filter が CostQuery に正しく設定される。"""
        mock_client = _make_mock_oci_client({
            "query_type": "breakdown",
            "start_date": "2026-02-01",
            "end_date": "2026-03-01",
            "comparison_start_date": None,
            "comparison_end_date": None,
            "service_filter": "OBJECT_STORAGE",
            "compartment_filter": None,
            "needs_clarification": False,
            "clarification_message": None,
            "detected_language": "ja",
        })

        result = parse_query("先月のObject Storageのコストは？", mock_client)

        assert not isinstance(result, ErrorResponse)
        assert result.service_filter == "OBJECT_STORAGE"

    def test_group_by_compartment_parsed(self):
        """「コンパートメント別」で group_by="compartment" が設定される。"""
        mock_client = _make_mock_oci_client({
            "query_type": "breakdown",
            "start_date": "2026-02-01",
            "end_date": "2026-03-01",
            "comparison_start_date": None,
            "comparison_end_date": None,
            "service_filter": None,
            "compartment_filter": None,
            "group_by": "compartment",
            "needs_clarification": False,
            "clarification_message": None,
            "detected_language": "ja",
        })

        result = parse_query("コンパートメント別のコストを教えて", mock_client)

        assert not isinstance(result, ErrorResponse)
        assert result.group_by == "compartment"

    def test_group_by_defaults_to_service(self):
        """集計軸未指定時はデフォルトで group_by="service" になる。"""
        mock_client = _make_mock_oci_client({
            "query_type": "breakdown",
            "start_date": "2026-02-01",
            "end_date": "2026-03-01",
            "comparison_start_date": None,
            "comparison_end_date": None,
            "service_filter": None,
            "compartment_filter": None,
            "group_by": "service",
            "needs_clarification": False,
            "clarification_message": None,
            "detected_language": "ja",
        })

        result = parse_query("今月のコストを教えて", mock_client)

        assert not isinstance(result, ErrorResponse)
        assert result.group_by == "service"

    def test_group_by_missing_defaults_to_service(self):
        """LLM が group_by を返さない場合、デフォルト service になる。"""
        mock_client = _make_mock_oci_client({
            "query_type": "breakdown",
            "start_date": "2026-02-01",
            "end_date": "2026-03-01",
            "comparison_start_date": None,
            "comparison_end_date": None,
            "service_filter": None,
            "compartment_filter": None,
            "needs_clarification": False,
            "clarification_message": None,
            "detected_language": "ja",
        })

        result = parse_query("先月のコストを教えて", mock_client)

        assert not isinstance(result, ErrorResponse)
        assert result.group_by == "service"

    def test_invalid_group_by_falls_back_to_service(self):
        """不正な group_by 値はデフォルト service にフォールバックする。"""
        mock_client = _make_mock_oci_client({
            "query_type": "breakdown",
            "start_date": "2026-02-01",
            "end_date": "2026-03-01",
            "comparison_start_date": None,
            "comparison_end_date": None,
            "service_filter": None,
            "compartment_filter": None,
            "group_by": "region",
            "needs_clarification": False,
            "clarification_message": None,
            "detected_language": "ja",
        })

        result = parse_query("リージョン別のコストを教えて", mock_client)

        assert not isinstance(result, ErrorResponse)
        assert result.group_by == "service"
