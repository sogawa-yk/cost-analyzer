"""Natural language query parser using OCI GenAI Service."""

from __future__ import annotations

import json
import logging
from datetime import date

from dateutil.relativedelta import relativedelta
from oci.generative_ai_inference import models as genai_models
from pydantic import ValidationError

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
3. comparison_start_date / comparison_end_date: comparison の場合は**必ず**設定すること。\
比較対象の前期間。「先月と今月を比較」なら start_date/end_date が今月、comparison_start_date/comparison_end_date が先月
4. service_filter: 特定のOCIサービスが指定された場合、以下のサービス名で設定:
   COMPUTE, OBJECT_STORAGE, DATABASE, NETWORKING, BLOCK_STORAGE, FUNCTIONS, \
CONTAINER_ENGINE, LOAD_BALANCER, API_GATEWAY, LOGGING, MONITORING, VAULT, BASTION, \
DATA_SCIENCE, INTEGRATION, ANALYTICS, STREAMING, EMAIL_DELIVERY, DNS, WAF
   ユーザーが「Object Storage」と言えば "OBJECT_STORAGE"、「Database」と言えば "DATABASE" に変換
5. compartment_filter: 特定のコンパートメントが指定された場合
6. needs_clarification: クエリが曖昧で解釈できない場合、**またはコストに無関係な入力の場合**はtrue。\
この場合clarification_messageに確認質問またはクエリ例を設定。\
コスト無関係の入力例: 天気、挨拶、雑談 → needs_clarification=true にし、\
clarification_message に使い方の説明とクエリ例を設定
7. clarification_message: needs_clarification=true の場合に、ユーザーに聞く確認質問
8. detected_language: クエリの言語（"ja" または "en"）
9. 日本語と英語以外の言語の場合は needs_clarification=true にし、
   clarification_message に「日本語または英語で入力してください」と設定

## 出力形式
JSON形式で以下のフィールドを返してください:
- query_type: "breakdown" | "comparison"
- start_date: "YYYY-MM-DD"
- end_date: "YYYY-MM-DD"
- comparison_start_date: "YYYY-MM-DD" | null（comparison の場合は必須）
- comparison_end_date: "YYYY-MM-DD" | null（comparison の場合は必須）
- service_filter: string | null
- compartment_filter: string | null
- needs_clarification: boolean
- clarification_message: string | null
- detected_language: "ja" | "en"

## 出力例

### 内訳クエリ
入力: 「先月のサービス別コストを教えて」（現在日: 2026-03-20）
{{"query_type":"breakdown","start_date":"2026-02-01","end_date":"2026-03-01",\
"comparison_start_date":null,"comparison_end_date":null,\
"service_filter":null,"compartment_filter":null,\
"needs_clarification":false,"clarification_message":null,"detected_language":"ja"}}

### 比較クエリ（相対表現）
入力: 「先月と今月のコストを比較して」（現在日: 2026-03-20）
{{"query_type":"comparison","start_date":"2026-03-01","end_date":"2026-04-01",\
"comparison_start_date":"2026-02-01","comparison_end_date":"2026-03-01",\
"service_filter":null,"compartment_filter":null,\
"needs_clarification":false,"clarification_message":null,"detected_language":"ja"}}

### 比較クエリ（絶対月指定）
入力: "Compare costs between January and February 2026"
{{"query_type":"comparison","start_date":"2026-02-01","end_date":"2026-03-01",\
"comparison_start_date":"2026-01-01","comparison_end_date":"2026-02-01",\
"service_filter":null,"compartment_filter":null,\
"needs_clarification":false,"clarification_message":null,"detected_language":"en"}}

### サービスフィルタ
入力: 「先月のObject Storageのコストは？」（現在日: 2026-03-20）
{{"query_type":"breakdown","start_date":"2026-02-01","end_date":"2026-03-01",\
"comparison_start_date":null,"comparison_end_date":null,\
"service_filter":"OBJECT_STORAGE","compartment_filter":null,\
"needs_clarification":false,"clarification_message":null,"detected_language":"ja"}}

### コスト無関係の入力
入力: 「今日の天気は？」
{{"query_type":"breakdown","start_date":"2026-03-01","end_date":"2026-04-01",\
"comparison_start_date":null,"comparison_end_date":null,\
"service_filter":null,"compartment_filter":null,\
"needs_clarification":true,\
"clarification_message":"コスト分析に関する質問をしてください。例: 「先月のコストを教えて」「今月と先月を比較して」",\
"detected_language":"ja"}}
"""

COST_QUERY_SCHEMA = {
    "type": "object",
    "properties": {
        "query_type": {"type": "string", "enum": ["breakdown", "comparison"]},
        "start_date": {"type": "string"},
        "end_date": {"type": "string"},
        "comparison_start_date": {"type": "string"},
        "comparison_end_date": {"type": "string"},
        "service_filter": {"type": "string"},
        "compartment_filter": {"type": "string"},
        "needs_clarification": {"type": "boolean"},
        "clarification_message": {"type": "string"},
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

        return _build_cost_query(result)

    except json.JSONDecodeError:
        logger.warning("Failed to parse LLM response as JSON")
        return _make_parse_error()
    except (ValidationError, ValueError, TypeError):
        logger.warning("LLM returned invalid data for CostQuery construction")
        return _make_parse_error()
    except Exception as e:
        logger.exception("Error during query parsing")
        from cost_analyzer.config import map_oci_error
        error_type, message, guidance = map_oci_error(e)
        return ErrorResponse(
            error_type=ErrorType(error_type),
            message=message,
            guidance=guidance,
        )


def _make_parse_error() -> ErrorResponse:
    """パース失敗時の共通エラーレスポンスを生成する。"""
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


def _nullable_str(val: str | None) -> str | None:
    """LLM が返す "null" や空文字を None に変換する。"""
    if val is None or val in ("null", "None", ""):
        return None
    return val


def _nullable_date(val: str | None) -> date | None:
    """nullable な日付文字列を date に変換する。"""
    s = _nullable_str(val)
    return date.fromisoformat(s) if s else None


def _infer_comparison_dates(result: dict) -> None:
    """比較クエリで比較日付が省略された場合、前期間を自動推定する。

    start_date/end_date の期間長から relativedelta を使い、
    月の境界を尊重した前期間を算出して result を更新する。
    """
    if result.get("query_type") != "comparison":
        return
    if _nullable_str(result.get("comparison_start_date")):
        return

    start = date.fromisoformat(result["start_date"])
    end = date.fromisoformat(result["end_date"])

    # 月の1日同士の差なら relativedelta で月単位推定
    if start.day == 1 and end.day == 1:
        months_diff = (end.year - start.year) * 12 + (end.month - start.month)
        comp_end = start
        comp_start = start - relativedelta(months=months_diff)
    else:
        # 月の境界でない場合は日数差で推定
        delta = end - start
        comp_end = start
        comp_start = start - delta

    result["comparison_start_date"] = comp_start.isoformat()
    result["comparison_end_date"] = comp_end.isoformat()
    logger.info(
        "Inferred comparison dates",
        extra={"extra_data": {
            "comparison_start_date": result["comparison_start_date"],
            "comparison_end_date": result["comparison_end_date"],
        }},
    )


def _build_cost_query(result: dict) -> CostQuery:
    """LLM のパース結果辞書から CostQuery を構築する。

    比較クエリで比較日付が省略された場合は自動推定を試みる。
    """
    _infer_comparison_dates(result)

    return CostQuery(
        query_type=QueryType(result["query_type"]),
        start_date=date.fromisoformat(result["start_date"]),
        end_date=date.fromisoformat(result["end_date"]),
        comparison_start_date=_nullable_date(result.get("comparison_start_date")),
        comparison_end_date=_nullable_date(result.get("comparison_end_date")),
        service_filter=_nullable_str(result.get("service_filter")),
        compartment_filter=_nullable_str(result.get("compartment_filter")),
        needs_clarification=result.get("needs_clarification", False),
        clarification_message=_nullable_str(result.get("clarification_message")),
        detected_language=result.get("detected_language", "ja"),
    )
