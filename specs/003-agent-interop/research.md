# Research: エージェント間連携（Agent Interoperability）

**Date**: 2026-03-18
**Feature**: 003-agent-interop

## Decision 1: A2A Python SDK の選定

**Decision**: 公式 `a2a-sdk` パッケージ（Google LLC）を使用する

**Rationale**:
- Google 公式の Apache 2.0 ライセンス SDK
- PyPI で `a2a-sdk` として配布（現バージョン: 0.3.25、1.0.0a0 プレリリースあり）
- Python 3.10+ 対応（3.13 互換確認済み）
- FastAPI 統合を `[http-server]` extra で直接サポート
- `A2AFastAPIApplication.add_routes_to_app()` で既存 FastAPI アプリに統合可能
- JSON-RPC、タスク管理、Agent Card 配信を SDK が全処理

**Alternatives considered**:
- `python-a2a`（コミュニティ実装）: 機能不完全、公式との互換性リスク
- `pya2a`（軽量実装）: メンテナンス状況不明
- 自前実装: 開発コスト大、プロトコル追従困難

**Install**: `pip install "a2a-sdk[http-server]"`

## Decision 2: FastAPI 統合方式

**Decision**: `A2AFastAPIApplication.add_routes_to_app()` で既存アプリに統合

**Rationale**:
- FR-011（同一プロセス統合）の要件を満たす
- 既存の `/query`、`/health`、`/` ルートと共存可能
- SDK が以下のエンドポイントを自動追加:
  - `GET /.well-known/agent-card.json` — Agent Card
  - `POST /a2a` — JSON-RPC エンドポイント（デフォルト `/` だが既存と衝突するため `/a2a` に変更）

**Alternatives considered**:
- `A2AStarletteApplication.build()` で別アプリ作成 + `app.mount()`: サブアプリ化で URL パスが複雑に
- 別ポートで A2A サーバーを起動: FR-011（同一プロセス）には合致するが運用が複雑

## Decision 3: AgentExecutor 実装パターン

**Decision**: 単一の `CostAnalyzerAgentExecutor` クラスでスキルルーティングを実装

**Rationale**:
- A2A SDK の `AgentExecutor` インターフェースは `execute()` と `cancel()` の2メソッド
- ユーザーメッセージの内容（テキスト vs 構造化データ）でスキルを判別:
  - `TextPart` → 自然言語クエリ（既存 `parse_query` + `fetch_breakdown/comparison`）
  - `DataPart` → 構造化パラメータ（直接 `fetch_breakdown/comparison`）
- レスポンスは `DataPart`（JSON 構造化データ）+ `TextPart`（サマリーテキスト）として返却

**Alternatives considered**:
- スキルごとに別 AgentExecutor: SDK が単一 executor のみサポート
- メッセージ metadata でスキル指定: A2A 標準ではないカスタム拡張になる

## Decision 4: タスクストア

**Decision**: SDK 組み込みの `InMemoryTaskStore` を使用

**Rationale**:
- 同期処理のみ（FR-011 clarification）のため永続化不要
- タスクは即座に completed/failed に遷移し保持不要
- スケール要件なし（ローカル / 社内利用）

**Alternatives considered**:
- Redis / DB バックエンドの TaskStore: オーバーエンジニアリング
- TaskStore なし: SDK の DefaultRequestHandler が TaskStore を要求

## Decision 5: JSON-RPC エンドポイント URL

**Decision**: `/a2a` をJSON-RPC エンドポイントとして使用

**Rationale**:
- SDK デフォルトの `/` は既存の Web UI ルート (`GET /`) と衝突
- `/a2a` は明確で、既存ルートとの混乱がない
- Agent Card の `url` フィールドで明示的に指定

**Alternatives considered**:
- `/rpc`: 汎用的すぎる
- `/agent`: 既存の `/` と紛らわしい可能性

## Decision 6: スキル定義

**Decision**: 6つのスキルを定義（仕様書の FR-003〜FR-008 に対応）

| スキル ID | 名前 | 入力方式 | FR |
|---|---|---|---|
| `analyze_cost` | Cost Analysis (NL) | text | FR-003 |
| `get_cost_breakdown` | Cost Breakdown | data | FR-004 |
| `compare_costs` | Cost Comparison | data | FR-005 |
| `list_services` | List Available Services | text/data | FR-006 |
| `list_compartments` | List Available Compartments | text/data | FR-007 |
| `health_check` | Health Check | text/data | FR-008 |

**Rationale**:
- 各スキルが独立したユースケースに対応
- `analyze_cost` は自然言語入力（TextPart）、その他は構造化入力（DataPart）も受付
- Agent Card の `skills` フィールドで外部エージェントにカタログ公開
