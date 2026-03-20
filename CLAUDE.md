# cost-analyzer Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-03-20

## Language Requirement
**ALL outputs MUST be in Japanese.**

## Active Technologies
- Python 3.13 (バックエンド), JavaScript ES2022+ (フロントエンド) + FastAPI (既存), Jinja2 (テンプレート), Alpine.js 3.x (UI リアクティブ), htmx 2.x (サーバー連携) (002-web-ui)
- N/A（ステートレス — ブラウザの localStorage を言語設定のみに使用） (002-web-ui)
- Python 3.13 + FastAPI (既存), a2a-sdk[http-server] (新規), Typer (既存CLI), oci (既存OCI SDK), pydantic (既存) (003-agent-interop)
- N/A（InMemoryTaskStore — 同期処理のため永続化不要） (003-agent-interop)
- Python 3.13（既存バックエンド）、YAML（K8s マニフェスト） + FastAPI（既存）、a2a-sdk（既存） (004-a2a-k8s-discovery)
- N/A（ステートレス） (004-a2a-k8s-discovery)
- Python 3.13（バックエンド）、JavaScript ES2022+（フロントエンド） + FastAPI（HTTP）、OCI SDK（GenAI + Usage API）、Alpine.js 3.x（UI）、Jinja2（テンプレート） (006-nl-chat-ui)
- N/A（ステートレス — ブラウザメモリのみ） (006-nl-chat-ui)

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
- 006-nl-chat-ui: Added Python 3.13（バックエンド）、JavaScript ES2022+（フロントエンド） + FastAPI（HTTP）、OCI SDK（GenAI + Usage API）、Alpine.js 3.x（UI）、Jinja2（テンプレート）
- 005-nl-query-quality-fix: Added [if applicable, e.g., PostgreSQL, CoreData, files or N/A]
- 004-a2a-k8s-discovery: Added Python 3.13（既存バックエンド）、YAML（K8s マニフェスト） + FastAPI（既存）、a2a-sdk（既存）


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
