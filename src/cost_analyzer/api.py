"""FastAPI application for HTTP interface."""

from __future__ import annotations

import hashlib
import hmac
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware

from cost_analyzer.a2a_server import create_a2a_app
from cost_analyzer.config import get_settings, setup_logging
from cost_analyzer.models import ErrorResponse, ErrorType, QueryType

logger = logging.getLogger("cost_analyzer.api")

_oci_client = None


def _get_oci_client():
    global _oci_client
    if _oci_client is None:
        from cost_analyzer.oci_client import OCIClient
        _oci_client = OCIClient()
    return _oci_client


def _build_asset_hash() -> str:
    """静的ファイルのハッシュからキャッシュバスティング用クエリパラメータを生成する。"""
    static_dir = Path(__file__).resolve().parent / "static"
    h = hashlib.md5()
    for p in sorted(static_dir.rglob("*")):
        if p.is_file() and not p.name.startswith("."):
            h.update(p.read_bytes())
    return h.hexdigest()[:8]


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(settings.log_level)
    yield


app = FastAPI(title="cost-analyzer", lifespan=lifespan)

# A2A エンドポイントの API キー認証ミドルウェア
_A2A_PROTECTED_PATHS = {"/a2a", "/.well-known/agent-card.json"}


class A2AApiKeyMiddleware(BaseHTTPMiddleware):
    """A2A エンドポイントへのリクエストに API キー認証を適用する。"""

    async def dispatch(self, request: Request, call_next):
        if request.url.path not in _A2A_PROTECTED_PATHS:
            return await call_next(request)

        settings = get_settings()
        if not settings.a2a_api_key:
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
        else:
            token = request.headers.get("X-API-Key", "")

        if not token or not hmac.compare_digest(token, settings.a2a_api_key):
            return JSONResponse(
                status_code=401,
                content={"error": "unauthorized", "message": "Invalid or missing API key."},
            )

        return await call_next(request)


app.add_middleware(A2AApiKeyMiddleware)

# A2A (Agent-to-Agent Protocol) ルートを統合
_a2a_app = create_a2a_app()
_a2a_app.add_routes_to_app(app, rpc_url="/a2a")

_BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=_BASE_DIR / "static"), name="static")
_templates = Jinja2Templates(directory=_BASE_DIR / "templates")
_asset_version = _build_asset_hash()


@app.get("/")
async def index(request: Request):
    return _templates.TemplateResponse(request, "index.html", {"v": _asset_version})


class QueryRequest(BaseModel):
    query: str
    format: str = Field(default="json")
    lang: str = Field(default="auto")


class PeriodResponse(BaseModel):
    start: str
    end: str


ERROR_STATUS_CODES = {
    ErrorType.PARSE_ERROR: 400,
    ErrorType.AUTH_ERROR: 401,
    ErrorType.API_ERROR: 502,
    ErrorType.NO_DATA: 404,
}


def _build_error_body(error: ErrorResponse) -> dict[str, Any]:
    """ErrorResponse を API コントラクトに合わせた dict に変換する。"""
    body: dict[str, Any] = {
        "error": error.error_type.value,
        "message": error.message,
    }
    if error.guidance:
        body["guidance"] = error.guidance
    if error.example_queries:
        body["example_queries"] = error.example_queries
    return body


@app.post("/query")
async def query_cost(request: QueryRequest) -> JSONResponse:
    """自然言語コストクエリを処理する。"""
    from cost_analyzer.engine import fetch_breakdown, fetch_comparison, generate_trend_summary
    from cost_analyzer.parser import parse_query

    oci_client = _get_oci_client()

    # パース
    result = parse_query(request.query, oci_client)
    if isinstance(result, ErrorResponse):
        status = ERROR_STATUS_CODES.get(result.error_type, 400)
        return JSONResponse(status_code=status, content=_build_error_body(result))

    # 確認が必要な場合
    if result.needs_clarification:
        return JSONResponse(content={
            "type": "clarification",
            "message": result.clarification_message,
            "suggestions": [],
        })

    # 内訳クエリ
    if result.query_type == QueryType.BREAKDOWN:
        data = fetch_breakdown(result, oci_client)
        if isinstance(data, ErrorResponse):
            status = ERROR_STATUS_CODES.get(data.error_type, 502)
            return JSONResponse(status_code=status, content=_build_error_body(data))
        return JSONResponse(content={
            "type": "breakdown",
            "period": {"start": str(data.period_start), "end": str(data.period_end)},
            "currency": data.currency,
            "items": [
                {
                    "service": item.service,
                    "amount": float(item.amount),
                    "percentage": float(item.percentage),
                    "rank": item.rank,
                }
                for item in data.items
            ],
            "total": float(data.total),
        })

    # 比較クエリ
    data = fetch_comparison(result, oci_client)
    if isinstance(data, ErrorResponse):
        status = ERROR_STATUS_CODES.get(data.error_type, 502)
        return JSONResponse(status_code=status, content=_build_error_body(data))

    trend = generate_trend_summary(data, result.detected_language)
    return JSONResponse(content={
        "type": "comparison",
        "current_period": {
            "start": str(data.current_period.period_start),
            "end": str(data.current_period.period_end),
        },
        "previous_period": {
            "start": str(data.previous_period.period_start),
            "end": str(data.previous_period.period_end),
        },
        "currency": data.current_period.currency,
        "items": [
            {
                "service": item.service,
                "current_amount": float(item.current_amount),
                "previous_amount": float(item.previous_amount),
                "absolute_change": float(item.absolute_change),
                "percent_change": float(item.percent_change) if item.percent_change is not None else None,
            }
            for item in data.items
        ],
        "previous_period_total": float(data.previous_period.total),
        "current_period_total": float(data.current_period.total),
        "total_change": float(data.total_change),
        "total_change_percent": float(data.total_change_percent),
        "summary": trend.summary_text,
    })


@app.get("/health")
async def health_check() -> JSONResponse:
    """Kubernetes プローブ用のヘルスチェック。"""
    checks: dict[str, str] = {}
    healthy = True

    # OCI Usage API の接続確認
    try:
        oci_client = _get_oci_client()
        # クライアント生成に成功すれば認証情報は有効
        checks["oci_usage_api"] = "ok"
    except Exception as e:
        checks["oci_usage_api"] = f"error: {e}"
        healthy = False

    # OCI GenAI の接続確認
    try:
        oci_client = _get_oci_client()
        if hasattr(oci_client, "genai_client") and oci_client.genai_client is not None:
            checks["oci_genai"] = "ok"
        else:
            checks["oci_genai"] = "error: genai client not initialized"
            healthy = False
    except Exception as e:
        checks["oci_genai"] = f"error: {e}"
        healthy = False

    status_code = 200 if healthy else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "healthy" if healthy else "unhealthy",
            "checks": checks,
        },
    )
