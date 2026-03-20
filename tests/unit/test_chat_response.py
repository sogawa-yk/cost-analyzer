"""Unit tests for generate_conversational_response()."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cost_analyzer.engine import (
    CONVERSATIONAL_PROMPT_TEMPLATE,
    generate_conversational_response,
)
from cost_analyzer.models import ConversationalResponse


class TestConversationalPromptTemplate:
    """CONVERSATIONAL_PROMPT_TEMPLATE のフォーマットを検証する。"""

    def test_template_contains_language_placeholder(self):
        assert "{language}" in CONVERSATIONAL_PROMPT_TEMPLATE

    def test_template_contains_result_type_placeholder(self):
        assert "{result_type}" in CONVERSATIONAL_PROMPT_TEMPLATE

    def test_template_contains_data_json_placeholder(self):
        assert "{data_json}" in CONVERSATIONAL_PROMPT_TEMPLATE

    def test_template_format_with_breakdown(self):
        result = CONVERSATIONAL_PROMPT_TEMPLATE.format(
            language="日本語",
            result_type="breakdown",
            data_json='{"type": "breakdown", "total": 1000}',
        )
        assert "日本語" in result
        assert "breakdown" in result
        assert '"total": 1000' in result

    def test_template_format_with_comparison(self):
        result = CONVERSATIONAL_PROMPT_TEMPLATE.format(
            language="English",
            result_type="comparison",
            data_json='{"type": "comparison"}',
        )
        assert "English" in result
        assert "comparison" in result


class TestGenerateConversationalResponse:
    """generate_conversational_response() の動作を検証する。"""

    def _make_mock_oci_client(self, response_text: str) -> MagicMock:
        """モック OCI クライアントを生成する。"""
        mock_client = MagicMock()
        mock_client.compartment_id = "test-compartment"

        mock_content = MagicMock()
        mock_content.text = response_text

        mock_message = MagicMock()
        mock_message.content = [mock_content]

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_chat_response = MagicMock()
        mock_chat_response.choices = [mock_choice]

        mock_response = MagicMock()
        mock_response.data.chat_response = mock_chat_response

        mock_client.genai_client.chat.return_value = mock_response
        return mock_client

    @patch("cost_analyzer.engine.get_settings")
    def test_successful_breakdown_response_returns_conversational_response(
        self, mock_settings
    ):
        mock_settings.return_value.oci_genai_model = "test-model"
        oci_client = self._make_mock_oci_client("先月のコスト内訳です。")
        data_json = '{"type": "breakdown", "total": 1000}'

        result = generate_conversational_response(
            "breakdown", data_json, "ja", oci_client
        )

        assert isinstance(result, ConversationalResponse)
        assert result.text == "先月のコスト内訳です。"
        assert result.language == "ja"

    @patch("cost_analyzer.engine.get_settings")
    def test_successful_comparison_response_in_english(self, mock_settings):
        mock_settings.return_value.oci_genai_model = "test-model"
        oci_client = self._make_mock_oci_client("Total cost increased by 5%.")
        data_json = '{"type": "comparison"}'

        result = generate_conversational_response(
            "comparison", data_json, "en", oci_client
        )

        assert isinstance(result, ConversationalResponse)
        assert result.text == "Total cost increased by 5%."
        assert result.language == "en"

    @patch("cost_analyzer.engine.get_settings")
    def test_llm_failure_returns_none(self, mock_settings):
        mock_settings.return_value.oci_genai_model = "test-model"
        oci_client = MagicMock()
        oci_client.compartment_id = "test-compartment"
        oci_client.genai_client.chat.side_effect = RuntimeError("LLM error")

        result = generate_conversational_response(
            "breakdown", '{"total": 100}', "ja", oci_client
        )

        assert result is None

    @patch("cost_analyzer.engine.get_settings")
    def test_response_text_is_stripped(self, mock_settings):
        mock_settings.return_value.oci_genai_model = "test-model"
        oci_client = self._make_mock_oci_client("  余分なスペース  \n")

        result = generate_conversational_response(
            "breakdown", '{"total": 100}', "ja", oci_client
        )

        assert result is not None
        assert result.text == "余分なスペース"

    @patch("cost_analyzer.engine.get_settings")
    def test_genai_called_with_correct_temperature(self, mock_settings):
        mock_settings.return_value.oci_genai_model = "test-model"
        oci_client = self._make_mock_oci_client("回答")

        generate_conversational_response(
            "breakdown", '{"total": 100}', "ja", oci_client
        )

        call_args = oci_client.genai_client.chat.call_args
        chat_detail = call_args[0][0]
        assert chat_detail.chat_request.temperature == 0.7
        assert chat_detail.chat_request.max_tokens == 256
