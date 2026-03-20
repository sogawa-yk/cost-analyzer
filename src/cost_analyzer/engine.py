"""Cost aggregation engine: fetch, aggregate, compare."""

from __future__ import annotations

import logging
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal
from difflib import get_close_matches

from oci.generative_ai_inference import models as genai_models

from cost_analyzer.config import get_settings, map_oci_error
from cost_analyzer.models import (
    ConversationalResponse,
    CostBreakdown,
    CostComparison,
    CostQuery,
    ErrorResponse,
    ErrorType,
    ServiceCost,
    ServiceDelta,
    TrendSummary,
)

logger = logging.getLogger("cost_analyzer.engine")

# ---------------------------------------------------------------------------
# 対話応答生成
# ---------------------------------------------------------------------------

CONVERSATIONAL_PROMPT_TEMPLATE = """\
あなたはフレンドリーなOCIコスト分析アシスタントです。\
以下のコストデータの分析結果を、ユーザーに対する自然な対話文として要約してください。

## ルール
1. {language}で回答してください
2. 200文字以内で簡潔にまとめてください
3. テーブルに表示されるデータの単純な繰り返しは避けてください
4. 最も注目すべきポイント（最大コストのサービス、大きな変化など）に焦点を当ててください
5. フレンドリーで分析的なトーンで書いてください
6. 数値には通貨記号と適切なフォーマットを使用してください

## データ
結果タイプ: {result_type}
{data_json}
"""


def generate_conversational_response(
    result_type: str,
    data_json: str,
    language: str,
    oci_client,
) -> ConversationalResponse | None:
    """LLM を使ってデータ結果から対話的な応答文を生成する。

    Args:
        result_type: "breakdown" or "comparison".
        data_json: 結果データの JSON 文字列.
        language: 出力言語 ("ja" or "en").
        oci_client: OCIClient インスタンス.

    Returns:
        ConversationalResponse on success, None on failure.
    """
    settings = get_settings()
    lang_label = "日本語" if language == "ja" else "English"

    prompt = CONVERSATIONAL_PROMPT_TEMPLATE.format(
        language=lang_label,
        result_type=result_type,
        data_json=data_json,
    )

    try:
        chat_request = genai_models.GenericChatRequest(
            messages=[
                genai_models.UserMessage(
                    content=[genai_models.TextContent(text=prompt)]
                ),
            ],
            temperature=0.7,
            max_tokens=256,
        )

        chat_detail = genai_models.ChatDetails(
            chat_request=chat_request,
            compartment_id=oci_client.compartment_id,
            serving_mode=genai_models.OnDemandServingMode(
                model_id=settings.oci_genai_model,
            ),
        )

        response = oci_client.genai_client.chat(chat_detail)
        text = response.data.chat_response.choices[0].message.content[0].text
        text = text.strip()

        logger.info(
            "Conversational response generated",
            extra={"extra_data": {"text_length": len(text)}},
        )

        return ConversationalResponse(text=text, language=language)

    except Exception:
        logger.warning(
            "Failed to generate conversational response, falling back to null",
            exc_info=True,
        )
        return None


def _get_scope_suggestions(oci_client, query: CostQuery) -> list[str]:
    """フィルタに一致するスコープが見つからなかった場合、類似名を提案する。"""
    suggestions: list[str] = []
    try:
        if query.service_filter and hasattr(oci_client, "get_available_services"):
            available = oci_client.get_available_services()
            matches = get_close_matches(query.service_filter, available, n=3, cutoff=0.4)
            for m in matches:
                suggestions.append(f"サービス: {m}")
        if query.compartment_filter and hasattr(oci_client, "get_available_compartments"):
            available = oci_client.get_available_compartments()
            matches = get_close_matches(query.compartment_filter, available, n=3, cutoff=0.4)
            for m in matches:
                suggestions.append(f"コンパートメント: {m}")
    except Exception:
        logger.debug("スコープ候補の取得に失敗しました", exc_info=True)
    return suggestions


def fetch_breakdown(query: CostQuery, oci_client) -> CostBreakdown | ErrorResponse:
    """Fetch and aggregate cost data into a breakdown.

    Args:
        query: Parsed cost query with date range.
        oci_client: OCIClient instance.

    Returns:
        CostBreakdown on success, ErrorResponse on failure.
    """
    has_scope_filter = query.service_filter is not None or query.compartment_filter is not None

    try:
        line_items = oci_client.request_cost_data(
            start_date=query.start_date,
            end_date=query.end_date,
            service_filter=query.service_filter,
            compartment_filter=query.compartment_filter,
        )
    except Exception as e:
        logger.exception("Failed to fetch cost data")
        error_type, message, guidance = map_oci_error(e)
        return ErrorResponse(
            error_type=ErrorType(error_type),
            message=message,
            guidance=guidance,
        )

    if not line_items and has_scope_filter:
        # フィルタなしで再取得して、データ自体は存在するか確認
        try:
            unfiltered = oci_client.request_cost_data(
                start_date=query.start_date,
                end_date=query.end_date,
            )
        except Exception:
            unfiltered = []

        if unfiltered:
            suggestions = _get_scope_suggestions(oci_client, query)
            filter_desc = query.service_filter or query.compartment_filter or ""
            guidance = f"「{filter_desc}」に一致するデータが見つかりませんでした。"
            if suggestions:
                guidance += " 以下の候補を試してください: " + ", ".join(suggestions)
            return ErrorResponse(
                error_type=ErrorType.NO_DATA,
                message="指定されたスコープに一致するコストデータがありません。",
                guidance=guidance,
            )

    if not line_items:
        return ErrorResponse(
            error_type=ErrorType.NO_DATA,
            message="指定された期間にコストデータがありません。",
            guidance=(
                f"期間 {query.start_date} ~ {query.end_date} のデータを確認してください。"
                "別の期間を試すこともできます。"
            ),
        )

    # Aggregate by service
    service_totals: dict[str, Decimal] = defaultdict(Decimal)
    currency = "USD"
    for item in line_items:
        service_totals[item.service] += item.amount
        currency = item.currency

    total = sum(service_totals.values())

    # Build sorted service costs
    sorted_services = sorted(service_totals.items(), key=lambda x: x[1], reverse=True)
    items = []
    for rank, (service, amount) in enumerate(sorted_services, start=1):
        if total > 0:
            percentage = (amount / total * 100).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        else:
            percentage = Decimal("0.0")
        items.append(
            ServiceCost(
                service=service,
                amount=amount,
                percentage=percentage,
                rank=rank,
            )
        )

    return CostBreakdown(
        period_start=query.start_date,
        period_end=query.end_date,
        currency=currency,
        items=items,
        total=total,
    )


def fetch_comparison(query: CostQuery, oci_client) -> CostComparison | ErrorResponse:
    """2つの期間のコスト内訳を取得し、差分を計算する。

    Args:
        query: 比較期間を含む CostQuery。
        oci_client: OCIClient インスタンス。

    Returns:
        CostComparison（成功時）、ErrorResponse（失敗時）。
    """
    # 当期を取得
    current_result = fetch_breakdown(query, oci_client)
    if isinstance(current_result, ErrorResponse):
        return current_result

    # 前期用のクエリを作成（スコープフィルタを引き継ぐ、typeはbreakdown）
    from cost_analyzer.models import QueryType

    prev_query = CostQuery(
        query_type=QueryType.BREAKDOWN,
        start_date=query.comparison_start_date,
        end_date=query.comparison_end_date,
        service_filter=query.service_filter,
        compartment_filter=query.compartment_filter,
        detected_language=query.detected_language,
    )
    previous_result = fetch_breakdown(prev_query, oci_client)
    if isinstance(previous_result, ErrorResponse):
        return previous_result

    # サービス別の金額をマッピング
    current_map: dict[str, Decimal] = {
        item.service: item.amount for item in current_result.items
    }
    previous_map: dict[str, Decimal] = {
        item.service: item.amount for item in previous_result.items
    }

    all_services = set(current_map.keys()) | set(previous_map.keys())

    deltas: list[ServiceDelta] = []
    for service in all_services:
        current_amount = current_map.get(service, Decimal("0"))
        previous_amount = previous_map.get(service, Decimal("0"))
        absolute_change = current_amount - previous_amount

        if previous_amount != Decimal("0"):
            percent_change = (absolute_change / previous_amount * 100).quantize(
                Decimal("0.1"), rounding=ROUND_HALF_UP
            )
        else:
            percent_change = None

        deltas.append(
            ServiceDelta(
                service=service,
                current_amount=current_amount,
                previous_amount=previous_amount,
                absolute_change=absolute_change,
                percent_change=percent_change,
            )
        )

    # absolute_change の絶対値で降順ソート
    deltas.sort(key=lambda d: abs(d.absolute_change), reverse=True)

    total_change = current_result.total - previous_result.total
    if previous_result.total != Decimal("0"):
        total_change_percent = (total_change / previous_result.total * 100).quantize(
            Decimal("0.1"), rounding=ROUND_HALF_UP
        )
    else:
        total_change_percent = Decimal("0.0")

    return CostComparison(
        current_period=current_result,
        previous_period=previous_result,
        items=deltas,
        total_change=total_change,
        total_change_percent=total_change_percent,
    )


def generate_trend_summary(comparison: CostComparison, language: str) -> TrendSummary:
    """CostComparison から傾向サマリーを生成する。

    Args:
        comparison: コスト比較データ。
        language: 出力言語（"ja" または "en"）。

    Returns:
        TrendSummary。
    """
    pct = comparison.total_change_percent

    # overall_direction の判定（-1〜1% は stable）
    if pct > Decimal("1"):
        overall_direction = "increase"
    elif pct < Decimal("-1"):
        overall_direction = "decrease"
    else:
        overall_direction = "stable"

    # 増加・減少サービスを抽出
    increases = [d for d in comparison.items if d.absolute_change > Decimal("0")]
    decreases = [d for d in comparison.items if d.absolute_change < Decimal("0")]

    # 増加額の大きい順にソート済み（absolute_change desc）
    increases.sort(key=lambda d: d.absolute_change, reverse=True)
    decreases.sort(key=lambda d: d.absolute_change)  # 最も減少が大きいものが先

    if language == "ja":
        top_increases = [
            f"{d.service} (+${d.absolute_change:,.2f})" for d in increases[:3]
        ]
        notable_decreases = [
            f"{d.service} (-${abs(d.absolute_change):,.2f})" for d in decreases[:3]
        ]

        change_amount = comparison.total_change
        change_pct = comparison.total_change_percent

        if overall_direction == "increase":
            total_change_text = f"合計コストが ${change_amount:,.2f} ({change_pct}%) 増加しました。"
        elif overall_direction == "decrease":
            total_change_text = f"合計コストが ${abs(change_amount):,.2f} ({abs(change_pct)}%) 減少しました。"
        else:
            total_change_text = "合計コストはほぼ横ばいです。"

        parts = [total_change_text]
        if top_increases:
            parts.append(f"{increases[0].service} の増加額が最大 (+${increases[0].absolute_change:,.2f})。")
        if notable_decreases:
            parts.append(
                f"{decreases[0].service} はわずかに減少 (-${abs(decreases[0].absolute_change):,.2f})。"
            )
        summary_text = "".join(parts)
    else:
        top_increases = [
            f"{d.service} (+${d.absolute_change:,.2f})" for d in increases[:3]
        ]
        notable_decreases = [
            f"{d.service} (-${abs(d.absolute_change):,.2f})" for d in decreases[:3]
        ]

        change_amount = comparison.total_change
        change_pct = comparison.total_change_percent

        if overall_direction == "increase":
            total_change_text = f"Total cost increased by ${change_amount:,.2f} ({change_pct}%)."
        elif overall_direction == "decrease":
            total_change_text = f"Total cost decreased by ${abs(change_amount):,.2f} ({abs(change_pct)}%)."
        else:
            total_change_text = "Total cost remained stable."

        parts = [total_change_text]
        if top_increases:
            parts.append(f" {increases[0].service} had the largest increase (+${increases[0].absolute_change:,.2f}).")
        if notable_decreases:
            parts.append(
                f" {decreases[0].service} decreased slightly (-${abs(decreases[0].absolute_change):,.2f})."
            )
        summary_text = "".join(parts)

    return TrendSummary(
        language=language,
        overall_direction=overall_direction,
        total_change_text=total_change_text,
        top_increases=top_increases,
        notable_decreases=notable_decreases,
        summary_text=summary_text,
    )
