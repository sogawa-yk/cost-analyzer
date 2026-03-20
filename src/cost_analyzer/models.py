"""Pydantic データモデル: 自然言語 OCI コストクエリ。"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

# ---------------------------------------------------------------------------
# 列挙型
# ---------------------------------------------------------------------------


class QueryType(StrEnum):
    """クエリ種別。"""

    BREAKDOWN = "breakdown"
    COMPARISON = "comparison"


class ErrorType(StrEnum):
    """エラー種別。"""

    AUTH_ERROR = "auth_error"
    API_ERROR = "api_error"
    PARSE_ERROR = "parse_error"
    NO_DATA = "no_data"


# ---------------------------------------------------------------------------
# CostQuery（コストクエリ）
# ---------------------------------------------------------------------------


class CostQuery(BaseModel):
    """自然言語入力からパースされたユーザーリクエスト。"""

    query_type: QueryType
    start_date: date
    end_date: date
    comparison_start_date: date | None = None
    comparison_end_date: date | None = None
    service_filter: str | None = None
    compartment_filter: str | None = None
    needs_clarification: bool = False
    clarification_message: str | None = None
    detected_language: str

    @model_validator(mode="after")
    def _validate_cross_fields(self) -> CostQuery:
        # start_date < end_date
        if self.start_date >= self.end_date:
            msg = "start_date は end_date より前でなければなりません。"
            raise ValueError(msg)

        # COMPARISON の場合、比較期間の両日付が必須
        if self.query_type == QueryType.COMPARISON:
            if self.comparison_start_date is None or self.comparison_end_date is None:
                msg = "query_type が COMPARISON の場合、comparison_start_date と comparison_end_date の両方が必須です。"
                raise ValueError(msg)
            if self.comparison_start_date >= self.comparison_end_date:
                msg = "comparison_start_date は comparison_end_date より前でなければなりません。"
                raise ValueError(msg)

        # needs_clarification の場合、clarification_message が必須
        if self.needs_clarification and not self.clarification_message:
            msg = "needs_clarification が True の場合、clarification_message は必須です。"
            raise ValueError(msg)

        # detected_language は "ja" または "en"
        if self.detected_language not in ("ja", "en"):
            msg = 'detected_language は "ja" または "en" でなければなりません。'
            raise ValueError(msg)

        return self


# ---------------------------------------------------------------------------
# CostLineItem（コスト明細）
# ---------------------------------------------------------------------------


class CostLineItem(BaseModel):
    """OCI Usage API から返される単一のコストエントリ。"""

    service: str
    amount: Decimal
    currency: str
    compartment_name: str | None = None
    compartment_path: str | None = None
    time_usage_started: datetime
    time_usage_ended: datetime

    @model_validator(mode="after")
    def _validate_line_item(self) -> CostLineItem:
        if self.amount < 0:
            msg = "amount は 0 以上でなければなりません。"
            raise ValueError(msg)
        if self.time_usage_started >= self.time_usage_ended:
            msg = "time_usage_started は time_usage_ended より前でなければなりません。"
            raise ValueError(msg)
        return self


# ---------------------------------------------------------------------------
# ServiceCost（サービスコスト）
# ---------------------------------------------------------------------------


class ServiceCost(BaseModel):
    """コスト内訳テーブルの単一行。"""

    service: str
    amount: Decimal
    percentage: Decimal = Field(ge=0, le=100)
    rank: int = Field(ge=1)


# ---------------------------------------------------------------------------
# CostBreakdown（コスト内訳）
# ---------------------------------------------------------------------------


class CostBreakdown(BaseModel):
    """サービス別に集約されたコストデータ。"""

    period_start: date
    period_end: date
    currency: str
    items: list[ServiceCost]
    total: Decimal


# ---------------------------------------------------------------------------
# ServiceDelta（サービス差分）
# ---------------------------------------------------------------------------


class ServiceDelta(BaseModel):
    """コスト比較テーブルの単一行。"""

    service: str
    current_amount: Decimal
    previous_amount: Decimal
    absolute_change: Decimal
    percent_change: Decimal | None = None


# ---------------------------------------------------------------------------
# CostComparison（コスト比較）
# ---------------------------------------------------------------------------


class CostComparison(BaseModel):
    """2つの CostBreakdown のペア分析。"""

    current_period: CostBreakdown
    previous_period: CostBreakdown
    items: list[ServiceDelta]
    total_change: Decimal
    total_change_percent: Decimal


# ---------------------------------------------------------------------------
# TrendSummary（傾向サマリー）
# ---------------------------------------------------------------------------


class TrendSummary(BaseModel):
    """CostComparison から導出された自然言語ナラティブ。"""

    language: str
    overall_direction: str
    total_change_text: str
    top_increases: list[str]
    notable_decreases: list[str]
    summary_text: str


# ---------------------------------------------------------------------------
# ErrorResponse（エラーレスポンス）
# ---------------------------------------------------------------------------


class ConversationalResponse(BaseModel):
    """LLM が生成した対話的応答文。"""

    text: str = Field(min_length=1)
    language: str = Field(pattern=r"^(ja|en)$")


class ErrorResponse(BaseModel):
    """ユーザーに返される構造化エラー。"""

    error_type: ErrorType
    message: str
    guidance: str
    example_queries: list[str] | None = None
