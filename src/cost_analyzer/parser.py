"""Natural language query parser using OCI GenAI Service."""

from __future__ import annotations

import json
import logging
from datetime import date

from oci.generative_ai_inference import models as genai_models

from cost_analyzer.config import get_settings
from cost_analyzer.models import CostQuery, ErrorResponse, ErrorType, QueryType

logger = logging.getLogger("cost_analyzer.parser")

SYSTEM_PROMPT_TEMPLATE = """\
あなたはOCIコスト分析アシスタントです。\
ユーザーの自然言語クエリをコストクエリのJSON構造に変換してください。

## 現在の日付
{today}

## ルール
1. query_type: ユーザーが2つの期間を比較する場合は "comparison"、それ以外は "breakdown"
2. start_date / end_date: クエリ期間（start は含む、end は含まない）。相対表現（「先月」「今月」等）は現在の日付から計算
3. comparison_start_date / comparison_end_date: comparison の場合のみ設定。比較対象の前期間
4. service_filter: 特定のOCIサービス名が指定された場合（例: "COMPUTE", "OBJECT_STORAGE"）
5. compartment_filter: 特定のコンパートメントが指定された場合
6. needs_clarification: クエリが曖昧で解釈できない場合はtrue。この場合clarification_messageに確認質問を設定
7. clarification_message: needs_clarification=true の場合に、ユーザーに聞く確認質問
8. detected_language: クエリの言語（"ja" または "en"）

## 出力形式
JSON形式で以下のフィールドを返してください:
- query_type: "breakdown" | "comparison"
- start_date: "YYYY-MM-DD"
- end_date: "YYYY-MM-DD"
- comparison_start_date: "YYYY-MM-DD" | null
- comparison_end_date: "YYYY-MM-DD" | null
- service_filter: string | null
- compartment_filter: string | null
- needs_clarification: boolean
- clarification_message: string | null
- detected_language: "ja" | "en"
"""

COST_QUERY_SCHEMA = {
    "type": "object",
    "properties": {
        "query_type": {"type": "string", "enum": ["breakdown", "comparison"]},
        "start_date": {"type": "string", "format": "date"},
        "end_date": {"type": "string", "format": "date"},
        "comparison_start_date": {"type": ["string", "null"], "format": "date"},
        "comparison_end_date": {"type": ["string", "null"], "format": "date"},
        "service_filter": {"type": ["string", "null"]},
        "compartment_filter": {"type": ["string", "null"]},
        "needs_clarification": {"type": "boolean"},
        "clarification_message": {"type": ["string", "null"]},
        "detected_language": {"type": "string", "enum": ["ja", "en"]},
    },
    "required": [
        "query_type",
        "start_date",
        "end_date",
        "needs_clarification",
        "detected_language",
    ],
}


def parse_query(query: str, oci_client) -> CostQuery | ErrorResponse:
    """Parse a natural language query into a CostQuery using OCI GenAI.

    Args:
        query: Natural language cost query string.
        oci_client: OCIClient instance with genai_client.

    Returns:
        CostQuery on success, ErrorResponse on failure.
    """
    settings = get_settings()
    today = date.today().isoformat()
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(today=today)

    logger.info(
        "Parsing query",
        extra={"extra_data": {"query": query}},
    )

    try:
        chat_request = genai_models.GenericChatRequest(
            messages=[
                genai_models.SystemMessage(content=[genai_models.TextContent(text=system_prompt)]),
                genai_models.UserMessage(content=[genai_models.TextContent(text=query)]),
            ],
            response_format=genai_models.JsonSchemaResponseFormat(
                json_schema=genai_models.ResponseJsonSchema(
                    name="CostQuery",
                    schema=COST_QUERY_SCHEMA,
                    is_strict=True,
                )
            ),
            temperature=0,
            max_tokens=1024,
        )

        chat_detail = genai_models.ChatDetails(
            chat_request=chat_request,
            compartment_id=oci_client.compartment_id,
            serving_mode=genai_models.OnDemandServingMode(
                model_id=settings.oci_genai_model,
            ),
        )

        response = oci_client.genai_client.chat(chat_detail)
        result_text = response.data.chat_response.choices[0].message.content[0].text
        result = json.loads(result_text)

        logger.info(
            "Query parsed successfully",
            extra={"extra_data": {"result": result}},
        )

        return CostQuery(
            query_type=QueryType(result["query_type"]),
            start_date=date.fromisoformat(result["start_date"]),
            end_date=date.fromisoformat(result["end_date"]),
            comparison_start_date=(
                date.fromisoformat(result["comparison_start_date"])
                if result.get("comparison_start_date")
                else None
            ),
            comparison_end_date=(
                date.fromisoformat(result["comparison_end_date"])
                if result.get("comparison_end_date")
                else None
            ),
            service_filter=result.get("service_filter"),
            compartment_filter=result.get("compartment_filter"),
            needs_clarification=result.get("needs_clarification", False),
            clarification_message=result.get("clarification_message"),
            detected_language=result.get("detected_language", "ja"),
        )

    except json.JSONDecodeError:
        logger.warning("Failed to parse LLM response as JSON")
        return ErrorResponse(
            error_type=ErrorType.PARSE_ERROR,
            message="クエリを理解できませんでした。",
            guidance="もう少し具体的に入力してください。",
            example_queries=[
                "先月のサービス別コストを教えて",
                "Show costs for February 2026",
                "先月と今月を比較して",
            ],
        )
    except Exception as e:
        logger.exception("Error during query parsing")
        from cost_analyzer.config import map_oci_error
        error_type, message, guidance = map_oci_error(e)
        return ErrorResponse(
            error_type=ErrorType(error_type),
            message=message,
            guidance=guidance,
        )
