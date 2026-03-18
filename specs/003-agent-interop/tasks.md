# Tasks: エージェント間連携（Agent Interoperability）

**Input**: Design documents from `/specs/003-agent-interop/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/a2a.md, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: 依存関係の追加と A2A SDK の導入

- [x] T001 `pyproject.toml` に `a2a-sdk[http-server]` 依存を追加し `pip install -e .` で導入確認
- [x] T002 [P] `tests/unit/test_a2a_server.py` と `tests/integration/test_a2a.py` の空ファイル・`__init__.py` を作成

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: A2A サーバーの骨格実装。Agent Card 配信と JSON-RPC エンドポイントが動作する最小構成

**⚠️ CRITICAL**: ユーザーストーリーの実装はこのフェーズ完了後に開始

- [x] T003 `src/cost_analyzer/a2a_server.py` に Agent Card 定義を作成（name, description, url, capabilities, skills 6 つを `contracts/a2a.md` に準拠して定義）
- [x] T004 `src/cost_analyzer/a2a_server.py` に `CostAnalyzerAgentExecutor` クラスの骨格を実装（`AgentExecutor` インターフェース準拠、`execute()` で未実装スキルは `"Not implemented"` を返す）
- [x] T005 `src/cost_analyzer/a2a_server.py` に `create_a2a_app()` ヘルパー関数を作成（`DefaultRequestHandler` + `InMemoryTaskStore` + `A2AFastAPIApplication` を構成）
- [x] T006 `src/cost_analyzer/api.py` に `add_routes_to_app()` 呼び出しを追加し、既存 FastAPI アプリに A2A ルート（`/.well-known/agent-card.json`, `/a2a`）を統合
- [x] T007 `tests/unit/test_a2a_server.py` に Agent Card のスキル数・フィールド検証テストを作成
- [x] T008 `tests/integration/test_a2a.py` に `GET /.well-known/agent-card.json` が 200 を返す統合テストを作成

**Checkpoint**: `curl /.well-known/agent-card.json` で Agent Card が取得でき、`POST /a2a` で JSON-RPC が応答する

---

## Phase 3: User Story 1 — 外部エージェントからコスト分析ツールを発見・利用する (Priority: P1) 🎯 MVP

**Goal**: 自然言語クエリを A2A 経由で送信し、コスト内訳 or 比較結果を取得できる

**Independent Test**: `POST /a2a` に `TextPart` で自然言語クエリを送り、構造化されたコスト分析結果が `Artifact` として返る

### Implementation

- [x] T009 [US1] `src/cost_analyzer/a2a_server.py` の `execute()` に `TextPart` → 自然言語クエリのルーティングを実装（`analyze_cost` スキル: 既存 `parse_query()` + `fetch_breakdown/comparison` を呼び出し）
- [x] T010 [US1] `src/cost_analyzer/a2a_server.py` に `StructuredCostResponse` Pydantic モデル定義（`data-model.md` 準拠: type/data/summary）と レスポンス変換を実装（`CostBreakdown`/`CostComparison` → `StructuredCostResponse` → `DataPart` + `TextPart`（サマリー）を返す `Artifact` 構築）
- [x] T011 [US1] `src/cost_analyzer/a2a_server.py` にエラーハンドリングを実装（OCI 認証エラー・パースエラー・タイムアウト等を `ErrorResponse` → `DataPart` でラップし `Task.status=failed` を返す）
- [x] T012 [US1] `tests/unit/test_a2a_server.py` に `analyze_cost` スキルのユニットテストを追加（TextPart ルーティング、レスポンス変換、エラー変換の各ケース）
- [x] T013 [US1] `tests/integration/test_a2a.py` に自然言語クエリの JSON-RPC 統合テストを追加（`message/send` で TextPart 送信 → Task completed + Artifact 検証）

**Checkpoint**: 自然言語クエリを A2A 経由で送信し、コスト分析結果がエージェントに返る。エラー時は構造化エラーが返る

---

## Phase 4: User Story 2 — 構造化パラメータによるコスト分析（LLM 不要モード） (Priority: P2)

**Goal**: 構造化パラメータ（期間、フィルタ、分析タイプ）を直接指定し、LLM パースなしでコスト分析を実行する

**Independent Test**: `POST /a2a` に `DataPart` で `StructuredCostRequest` を送り、LLM 呼び出しなしでコスト結果が返る

### Implementation

- [x] T014 [US2] `src/cost_analyzer/a2a_server.py` に `StructuredCostRequest` Pydantic モデルを定義（`data-model.md` 準拠、バリデーションルール含む）
- [x] T015 [US2] `src/cost_analyzer/a2a_server.py` に `DataPart` → 構造化パラメータのルーティングを実装（`get_cost_breakdown` スキル: `StructuredCostRequest` → `CostQuery` 変換 → 直接 `fetch_breakdown` 呼び出し）
- [x] T016 [US2] `src/cost_analyzer/a2a_server.py` に `compare_costs` スキルのルーティングを実装（`StructuredCostRequest` → 2 期間の `CostQuery` 変換 → `fetch_comparison` 呼び出し）
- [x] T017 [US2] `src/cost_analyzer/a2a_server.py` にバリデーションエラーハンドリングを実装（必須パラメータ不足・日付範囲不正時に入力スキーマを含むエラーを返す）
- [x] T018 [P] [US2] `tests/unit/test_a2a_server.py` に `StructuredCostRequest` のバリデーションテストを追加（必須フィールド、日付範囲、スキル別バリデーション）
- [x] T019 [US2] `tests/integration/test_a2a.py` に構造化パラメータの JSON-RPC 統合テストを追加（`get_cost_breakdown` / `compare_costs` の DataPart 送信 → 結果検証、バリデーションエラー検証）

**Checkpoint**: 構造化パラメータでの `get_cost_breakdown` と `compare_costs` が動作し、不正入力時は入力スキーマ付きエラーが返る

---

## Phase 5: User Story 3 — 利用可能なフィルタ値の動的取得 (Priority: P3)

**Goal**: 外部エージェントがサービス一覧・コンパートメント一覧・ヘルスチェックを取得できる

**Independent Test**: `POST /a2a` に `DataPart` で `{"skill": "list_services"}` を送り、サービス名リストが返る

### Implementation

- [x] T020 [P] [US3] `src/cost_analyzer/a2a_server.py` に `list_services` スキルを実装（既存 `oci_client` の機能を呼び出しサービス名リストを `DataPart` で返す）
- [x] T021 [P] [US3] `src/cost_analyzer/a2a_server.py` に `list_compartments` スキルを実装（既存 `oci_client` の機能を呼び出しコンパートメント名・ID リストを `DataPart` で返す）
- [x] T022 [P] [US3] `src/cost_analyzer/a2a_server.py` に `health_check` スキルを実装（OCI 接続状態を確認し結果を `DataPart` で返す）
- [x] T023 [US3] `tests/unit/test_a2a_server.py` に `list_services`、`list_compartments`、`health_check` のユニットテストを追加
- [x] T024 [US3] `tests/integration/test_a2a.py` にリスト系・ヘルスチェックの JSON-RPC 統合テストを追加

**Checkpoint**: 6 つのスキルすべてが A2A 経由で呼び出し可能

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: 既存機能との共存確認・品質向上

- [x] T025 既存テスト（`tests/unit/`, `tests/integration/test_api.py`, `tests/e2e/`）が A2A 統合後も全パスすることを確認
- [x] T026 [P] `quickstart.md` の手順を実際に実行し動作を検証（SC-001: Agent Card 発見からコスト分析結果取得まで 5 分以内を確認）
- [x] T027 [P] `ruff check .` でコード品質を確認し、型アノテーション不足・lint エラーを修正
- [x] T028 [P] `tests/unit/test_a2a_server.py` に新規モジュール `a2a_server.py` のカバレッジが 80% 以上であることを確認（`pytest --cov=cost_analyzer.a2a_server --cov-fail-under=80`）
- [x] T029 [P] A2A エンドポイントの性能回帰テストを実施（`POST /a2a` の p95 レイテンシ ≤ 500ms を検証、SC-002: 構造化パラメータが自然言語クエリ比 50% 以上高速であることを計測）

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 依存なし — 即時開始可
- **Foundational (Phase 2)**: Phase 1 完了に依存 — **全ユーザーストーリーをブロック**
- **US1 (Phase 3)**: Phase 2 完了に依存 — 他のストーリーに非依存
- **US2 (Phase 4)**: Phase 2 完了に依存 — US1 の `execute()` 基盤を共有するが、独立テスト可能
- **US3 (Phase 5)**: Phase 2 完了に依存 — US1/US2 に非依存
- **Polish (Phase 6)**: Phase 3〜5 完了に依存

### User Story Dependencies

- **US1 (P1)**: Phase 2 完了後に開始可。他ストーリーに非依存
- **US2 (P2)**: Phase 2 完了後に開始可。US1 と同じ `execute()` メソッドに追加するため、US1 の後に実装推奨
- **US3 (P3)**: Phase 2 完了後に開始可。US1/US2 に非依存（スキル追加のみ）

### Within Each User Story

- モデル/変換ロジック → サービス呼び出し → エラーハンドリング → テスト
- 同一ファイル（`a2a_server.py`）への変更が中心のため、ストーリー間は順次実行を推奨

### Parallel Opportunities

- Phase 1: T001 と T002 は並列実行可
- Phase 2: T003〜T005 は同一ファイルのため順次、T007 と T008 は並列可
- Phase 5: T020、T021、T022 は独立したスキル実装のため並列可
- Phase 6: T025〜T029 のうち T026〜T029 は並列可（T025 は先行実行推奨）

---

## Parallel Example: User Story 3

```bash
# US3 の独立スキル実装を並列で実行:
Task: "list_services スキル実装 in src/cost_analyzer/a2a_server.py"
Task: "list_compartments スキル実装 in src/cost_analyzer/a2a_server.py"
Task: "health_check スキル実装 in src/cost_analyzer/a2a_server.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1: Setup（依存追加）
2. Phase 2: Foundational（Agent Card + 骨格 + FastAPI 統合）
3. Phase 3: User Story 1（自然言語クエリの A2A 公開）
4. **STOP and VALIDATE**: `curl` で Agent Card 取得 → 自然言語クエリ送信 → 結果確認
5. MVP として利用開始可能

### Incremental Delivery

1. Setup + Foundational → A2A エンドポイント稼働
2. US1 → 自然言語コスト分析が A2A 経由で利用可（MVP）
3. US2 → 構造化パラメータで LLM 不要の高速呼び出しが可能に
4. US3 → サービス/コンパートメント一覧・ヘルスチェックが利用可能に
5. 各ストーリーが前のストーリーを壊さず価値を追加

---

## Notes

- 全実装が `a2a_server.py` 1 ファイルに集約されるため、ストーリー間の並列実装はファイル競合に注意
- `api.py` への変更は T006 の 1 箇所のみ（`add_routes_to_app()` 呼び出し追加）
- 既存モデル（`models.py`）への変更は不要
- A2A SDK の `InMemoryTaskStore` を使用し、永続化は不要
