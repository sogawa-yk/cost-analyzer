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
