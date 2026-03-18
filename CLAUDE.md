# cost-analyzer Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-03-18

## Language Requirement
**ALL outputs MUST be in Japanese.**

## Active Technologies
- Python 3.13 (バックエンド), JavaScript ES2022+ (フロントエンド) + FastAPI (既存), Jinja2 (テンプレート), Alpine.js 3.x (UI リアクティブ), htmx 2.x (サーバー連携) (002-web-ui)
- N/A（ステートレス — ブラウザの localStorage を言語設定のみに使用） (002-web-ui)

- Python 3.13 + Typer (CLI), FastAPI (HTTP), Rich (output), oci (OCI SDK), anthropic (LLM), pydantic / pydantic-settings (models/config), dateparser + python-dateutil (date utilities) (001-nl-cost-query)

## Project Structure

```text
backend/
frontend/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.13: Follow standard conventions

## Recent Changes
- 002-web-ui: Added Python 3.13 (バックエンド), JavaScript ES2022+ (フロントエンド) + FastAPI (既存), Jinja2 (テンプレート), Alpine.js 3.x (UI リアクティブ), htmx 2.x (サーバー連携)

- 001-nl-cost-query: Added Python 3.13 + Typer (CLI), FastAPI (HTTP), Rich (output), oci (OCI SDK), anthropic (LLM), pydantic / pydantic-settings (models/config), dateparser + python-dateutil (date utilities)

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
