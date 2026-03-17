"""Configuration management and error handling utilities."""

from __future__ import annotations

import json
import logging
import sys
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    oci_config_file: str = Field(default="~/.oci/config", alias="OCI_CONFIG_FILE")
    oci_config_profile: str = Field(default="DEFAULT", alias="OCI_CONFIG_PROFILE")
    oci_auth_type: Literal["api_key", "instance_principal"] = Field(
        default="api_key", alias="OCI_AUTH_TYPE"
    )
    oci_tenancy_id: str | None = Field(default=None, alias="OCI_TENANCY_ID")
    oci_compartment_id: str | None = Field(default=None, alias="OCI_COMPARTMENT_ID")
    oci_genai_endpoint: str = Field(
        default="https://inference.generativeai.ap-osaka-1.oci.oraclecloud.com",
        alias="OCI_GENAI_ENDPOINT",
    )
    oci_genai_model: str = Field(default="google/gemini-2.5-flash", alias="OCI_GENAI_MODEL")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    model_config = {"populate_by_name": True}


def get_settings() -> Settings:
    """Get application settings (cached)."""
    return Settings()


class JsonFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0] is not None:
            log_data["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)
        return json.dumps(log_data, ensure_ascii=False)


def setup_logging(level: str = "INFO") -> None:
    """Configure structured JSON logging."""
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger("cost_analyzer")
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))


def map_oci_error(error: Exception) -> tuple[str, str, str]:
    """Map OCI SDK exceptions to (error_type, message, guidance).

    Returns:
        Tuple of (error_type, message, guidance) for ErrorResponse construction.
    """
    from oci.exceptions import ServiceError

    if isinstance(error, ServiceError):
        if error.status in (401, 403):
            return (
                "auth_error",
                "OCI 認証に失敗しました。",
                "OCI 認証情報の設定を確認してください。~/.oci/config が正しく設定されているか確認してください。",
            )
        if error.status in (429, 500, 502, 503, 504):
            return (
                "api_error",
                "OCI API が一時的に利用できません。",
                "数分後に再試行してください。",
            )
        return (
            "api_error",
            f"OCI API エラー: {error.message}",
            "問題が続く場合はOCIサポートにお問い合わせください。",
        )
    return (
        "api_error",
        f"予期しないエラーが発生しました: {error}",
        "ログを確認し、問題が続く場合は再試行してください。",
    )
