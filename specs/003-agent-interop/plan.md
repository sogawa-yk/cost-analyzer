# Implementation Plan: エージェント間連携（Agent Interoperability）

**Branch**: `003-agent-interop` | **Date**: 2026-03-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-agent-interop/spec.md`

## Summary

cost-analyzer の既存コスト分析能力（自然言語クエリ、構造化パラメータ、サービス/コンパートメント一覧、ヘルスチェック）を A2A（Agent-to-Agent Protocol）を通じて外部エージェントに公開する。Google 公式の `a2a-sdk` を使用し、既存の FastAPI アプリに `A2AFastAPIApplication.add_routes_to_app()` で統合する。

## Technical Context

**Language/Version**: Python 3.13
**Primary Dependencies**: FastAPI (既存), a2a-sdk[http-server] (新規), Typer (既存CLI), oci (既存OCI SDK), pydantic (既存)
**Storage**: N/A（InMemoryTaskStore — 同期処理のため永続化不要）
**Testing**: pytest, pytest-asyncio, httpx (既存テスト基盤を踏襲)
**Target Platform**: Linux server (ローカル / OKE)
**Project Type**: web-service + CLI
**Performance Goals**: API レスポンス 500ms p95（Constitution 準拠）。構造化パラメータ呼び出しは自然言語の 50% 以下のレイテンシ
**Constraints**: メモリ 512MB 以内、既存エンドポイント無影響
**Scale/Scope**: ローカル / 社内利用。同時接続数は少数

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Research Check

| Principle | Status | Notes |
|---|---|---|
| I. Code Quality | PASS | 新規モジュール `a2a_server.py` は単一責務（A2A 統合）。型アノテーション必須。関数 40 行 / ファイル 400 行制限を遵守 |
| II. Testing Standards | PASS | ユニットテスト 80%+、A2A エンドポイント統合テスト必須。OCI 境界テストは既存パターンを踏襲 |
| III. UX Consistency | PASS | Agent Card・エラーレスポンスは既存 ErrorResponse と同一構造。用語は A2A 標準に準拠 |
| IV. Performance | PASS | 同期処理のみ。500ms p95 は既存 API と同一基準 |

### Post-Design Check

| Principle | Status | Notes |
|---|---|---|
| I. Code Quality | PASS | `a2a_server.py`（AgentExecutor + Agent Card 定義）推定 200 行以内。スキルルーティングは辞書マッピングで実装 |
| II. Testing Standards | PASS | テスト計画: unit/test_a2a_server.py（スキルルーティング、エラー変換）、integration/test_a2a.py（JSON-RPC E2E） |
| III. UX Consistency | PASS | エラーレスポンスは既存 `ErrorResponse` モデルを `DataPart` でラップ。メッセージ構造統一 |
| IV. Performance | PASS | 構造化パラメータ呼び出しは LLM パースをスキップ。既存パフォーマンスへの影響なし |

## Project Structure

### Documentation (this feature)

```text
specs/003-agent-interop/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0: A2A SDK 調査結果
├── data-model.md        # Phase 1: データモデル定義
├── quickstart.md        # Phase 1: 利用開始ガイド
├── contracts/
│   └── a2a.md           # Phase 1: A2A プロトコルコントラクト
├── checklists/
│   └── requirements.md  # 仕様品質チェックリスト
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/cost_analyzer/
├── __init__.py          # (既存)
├── __main__.py          # (既存)
├── api.py               # (変更) A2A ルート統合を追加
├── cli.py               # (変更なし)
├── config.py            # (変更なし)
├── engine.py            # (変更なし)
├── formatter.py         # (変更なし)
├── models.py            # (変更なし)
├── oci_client.py        # (変更なし)
├── parser.py            # (変更なし)
├── a2a_server.py        # (新規) AgentExecutor, Agent Card, スキルルーティング
├── static/              # (既存, 変更なし)
└── templates/           # (既存, 変更なし)

tests/
├── conftest.py          # (変更) A2A テスト用フィクスチャ追加
├── unit/
│   ├── test_a2a_server.py  # (新規) AgentExecutor ユニットテスト
│   └── ...              # (既存, 変更なし)
├── integration/
│   ├── test_a2a.py      # (新規) A2A JSON-RPC 統合テスト
│   └── ...              # (既存, 変更なし)
└── e2e/
    └── ...              # (既存, 変更なし)

pyproject.toml           # (変更) a2a-sdk[http-server] 依存追加
```

**Structure Decision**: 既存の単一プロジェクト構造を維持。A2A 統合は `a2a_server.py` 1ファイルに集約し、`api.py` への変更は最小限（`add_routes_to_app()` 呼び出しの追加のみ）。
