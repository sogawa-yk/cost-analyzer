# Tasks: コンパートメント別集計（group_by）対応

**Input**: Design documents from `/specs/007-compartment-groupby/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/query-api.md, quickstart.md

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup

**Purpose**: 既存テストが通ることを確認し、ベースラインを確立する

- [x] T001 既存テストの実行と全パスを確認: `cd src && pytest`
- [x] T002 lint チェック通過を確認: `ruff check .`

---

## Phase 2: Foundational (データモデル拡張)

**Purpose**: 全ユーザーストーリーが依存するデータモデルの変更。この Phase 完了まで他の実装は開始できない。

**CRITICAL**: この Phase が完了するまで Phase 3 以降の作業は開始不可

- [x] T003 `GROUP_BY_SERVICE = "service"`, `GROUP_BY_COMPARTMENT = "compartment"`, `VALID_GROUP_BY_VALUES = [GROUP_BY_SERVICE, GROUP_BY_COMPARTMENT]` の定数を定義する in `src/cost_analyzer/models.py`。以降の全タスクでこれらの定数を使用し、文字列リテラル直書きを禁止する（Constitution I: magic strings）
- [x] T004 `CostQuery` に `group_by: str = GROUP_BY_SERVICE` フィールドを追加する in `src/cost_analyzer/models.py`。バリデーションで `group_by` が `VALID_GROUP_BY_VALUES` 以外の場合は `GROUP_BY_SERVICE` にフォールバックする
- [x] T005 `ServiceCost` に `group_key: str` フィールドを追加し、`service` フィールドを `group_key` のエイリアス（`@property`）に変更する in `src/cost_analyzer/models.py`。既存の `service` 参照が壊れないよう後方互換性を維持する
- [x] T006 `ServiceDelta` に `group_key: str` フィールドを追加し、`service` フィールドを `group_key` のエイリアス（`@property`）に変更する in `src/cost_analyzer/models.py`。T005 と同じパターンを適用する
- [x] T007 `tests/conftest.py` の `make_cost_query()` ヘルパーに `group_by=GROUP_BY_SERVICE` パラメータを追加する
- [x] T008 既存テストが全パスすることを確認する（後方互換性チェック）: `cd src && pytest`

**Checkpoint**: データモデルが拡張され、既存テストが全パス — ユーザーストーリー実装開始可能

---

## Phase 3: User Story 1 - コンパートメント別コスト内訳の表示 (Priority: P1) MVP

**Goal**: 「コンパートメント別のコストを教えて」でコンパートメント名をキーとした集計テーブルが表示される

**Independent Test**: チャットUIで「コンパートメント別のコストを教えて」と入力し、コンパートメント名をキーとした集計テーブルが返ることを確認する

### Implementation for User Story 1

- [x] T009 [P] [US1] `COST_QUERY_SCHEMA` に `group_by` フィールド（enum: `["service", "compartment"]`, default: `"service"`）を追加する in `src/cost_analyzer/parser.py`
- [x] T010 [P] [US1] `SYSTEM_PROMPT_TEMPLATE` に集計軸判定ルールを追加する in `src/cost_analyzer/parser.py`。「コンパートメント別」「部門別」「コンパートメントごと」等の表現で `group_by: "compartment"` を返すルールを記述する。集計軸の指定がない場合は `group_by: "service"` をデフォルトとする
- [x] T011 [US1] `_build_cost_query()` で LLM レスポンスの `group_by` フィールドを `CostQuery` に渡す処理を追加する in `src/cost_analyzer/parser.py`。未対応の集計軸が指定された場合はデフォルトにフォールバックし、`clarification_message` でユーザーに通知する（FR-007）
- [x] T012 [US1] `request_cost_data()` に `api_group_by: list[str] | None = None` パラメータを追加し、指定時は OCI API の `group_by` パラメータを動的に設定する in `src/cost_analyzer/oci_client.py`。デフォルトは `["service", "currency"]` を維持する
- [x] T013 [US1] `fetch_breakdown()` で `query.group_by` に応じて集計キーを動的に選択する in `src/cost_analyzer/engine.py`。`group_by=GROUP_BY_SERVICE` → `item.service`、`group_by=GROUP_BY_COMPARTMENT` → `item.compartment_name`。同名コンパートメント重複時は `compartment_path` にフォールバックする（FR-008）。OCI API呼び出し時に `api_group_by` を渡す
- [x] T014 [US1] `fetch_comparison()` で `query.group_by` に応じて比較マッピングのキーを動的に選択する in `src/cost_analyzer/engine.py`。T013 と同じパターンを適用する
- [x] T015 [US1] `generate_trend_summary()` で `d.service` 参照を `d.group_key` に変更する in `src/cost_analyzer/engine.py`
- [x] T016 [US1] `/query` エンドポイントのレスポンスに `group_by` フィールドを追加し、items 配列内に `group_key` フィールドを追加する in `src/cost_analyzer/api.py`。後方互換のため `group_by=GROUP_BY_SERVICE` の場合は `service` フィールドも維持する
- [x] T017 [P] [US1] `i18n.js` に `compartment_column` 翻訳キーを追加する（ja: `"コンパートメント"`, en: `"Compartment"`）in `src/cost_analyzer/static/js/i18n.js`
- [x] T018 [P] [US1] `breakdown.html` のテーブルヘッダーを `group_by` に応じて動的に切替える in `src/cost_analyzer/templates/partials/breakdown.html`。`group_by` 値から i18n キーを導出する（`service` → `service_column`, `compartment` → `compartment_column`）。セル値も `item.group_key` を参照する
- [x] T019 [P] [US1] `comparison.html` のテーブルヘッダー・セル・`:key` を `group_by` に応じて動的に切替える in `src/cost_analyzer/templates/partials/comparison.html`。T018 と同じパターンを適用する
- [x] T020 [US1] テスト追加: `test_parser.py` に group_by パースのテストケースを追加する in `tests/unit/test_parser.py`。「コンパートメント別のコストを教えて」→ `group_by="compartment"`、「今月のコストを教えて」→ `group_by="service"`（デフォルト）
- [x] T021 [US1] テスト追加: `test_engine.py` にコンパートメント別 `fetch_breakdown()` と `fetch_comparison()` のテストケースを追加する in `tests/unit/test_engine.py`。コンパートメント名で正しく集計されることを検証する
- [x] T022 [US1] 統合テスト追加: `oci_client.py` の `request_cost_data()` が `group_by=["compartmentName", "currency"]` で正しく OCI API を呼び出すことをテストする in `tests/integration/test_oci_client.py`（Constitution II: 外部サービス境界の統合テスト必須）
- [x] T023 [US1] 全テスト実行と lint チェック: `cd src && pytest && ruff check .`

**Checkpoint**: コンパートメント別集計が動作 — MVP 完了

---

## Phase 4: User Story 2 - サービス別集計の後方互換性維持 (Priority: P1)

**Goal**: 既存のサービス別集計クエリが従来通り正しく動作することを保証する

**Independent Test**: 既存のサービス別クエリを実行し、従来と同じ結果が返ることを確認する

### Implementation for User Story 2

- [ ] T024 [US2] 後方互換テスト: 既存の全テストが `group_by` 追加後もパスすることを確認する。特に `test_engine.py` の `TestFetchBreakdown`, `TestFetchComparison`, `TestScopedQueries` が変更なしで動作することを検証する in `tests/unit/test_engine.py`
- [ ] T025 [US2] テスト追加: 集計軸未指定時にデフォルトで `group_by="service"` となることを明示的にテストする in `tests/unit/test_parser.py`
- [ ] T026 [US2] テスト追加: API レスポンスで `group_by="service"` の場合に `service` フィールドが維持されることをテストする in `tests/unit/test_engine.py`

**Checkpoint**: 後方互換性が保証された

---

## Phase 5: User Story 3 - フィルタリングとグルーピングの組み合わせ (Priority: P2)

**Goal**: `compartment_filter` + `group_by` や `service_filter` + `group_by` の組み合わせが正しく動作する

**Independent Test**: 「prodコンパートメントのサービス別コストを教えて」と入力し、prod に絞り込まれたサービス別集計が返ることを確認する

### Implementation for User Story 3

- [ ] T027 [US3] パーサーが filter と group_by を独立して抽出できることを確認・テストする in `tests/unit/test_parser.py`。「prodコンパートメントのサービス別コスト」→ `compartment_filter="prod"`, `group_by="service"` 等
- [ ] T028 [US3] エンジンが filter と group_by を独立して処理できることを確認・テストする in `tests/unit/test_engine.py`。`compartment_filter` で絞り込みつつ `group_by="service"` で集計、`service_filter` で絞り込みつつ `group_by="compartment"` で集計、`compartment_filter` + `group_by="compartment"` の組み合わせ（prod配下のサブコンパートメント集計）を検証する
- [ ] T029 [US3] エッジケーステスト: 未対応の集計軸要求時にデフォルトへフォールバックし通知することをテストする in `tests/unit/test_engine.py`
- [ ] T030 [US3] 全テスト実行: `cd src && pytest && ruff check .`

**Checkpoint**: フィルタリングとグルーピングの組み合わせが動作

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: パフォーマンス検証・デプロイ・検証・PR作成

- [ ] T031 パフォーマンス回帰テスト: `fetch_breakdown()` と `fetch_comparison()` の集計ロジック変更による p95 レイテンシが 10% 以上劣化していないことを確認する in `tests/performance/test_engine_perf.py`（Constitution IV: クリティカルデータパスのパフォーマンス回帰テスト必須）
- [ ] T032 全テスト実行と lint チェック最終確認: `cd src && pytest && ruff check .`
- [ ] T033 K8s クラスタにデプロイする
- [ ] T034 デプロイ環境で「コンパートメント別のコストを教えて」を実行し、コンパートメント別テーブルが表示されることを確認する。スクリーンショットを取得する
- [ ] T035 デプロイ環境で「今月のコストを教えて」を実行し、従来通りサービス別テーブルが表示されることを確認する（後方互換性）。スクリーンショットを取得する
- [ ] T036 デプロイ環境で「prodコンパートメントのサービス別コストを教えて」を実行し、フィルタ+グルーピング組み合わせが動作することを確認する
- [ ] T037 検証結果に問題があれば修正し、T032-T036 を繰り返す
- [ ] T038 改善が確認できたら PR を作成する。PR 本文に before/after スクリーンショットを添付する（Constitution Quality Gates: UX gate）

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 依存なし — 即座に開始可能
- **Foundational (Phase 2)**: Setup 完了後 — 全ユーザーストーリーをブロック
- **US1 (Phase 3)**: Foundational 完了後 — MVP
- **US2 (Phase 4)**: Foundational 完了後 — US1 と並行可能だが、US1 の実装が US2 のテスト対象
- **US3 (Phase 5)**: Foundational 完了後 — US1 完了後が望ましい
- **Polish (Phase 6)**: 全ユーザーストーリー完了後

### User Story Dependencies

- **User Story 1 (P1)**: Foundational 完了後に開始可能。他のストーリーに依存しない
- **User Story 2 (P1)**: Foundational 完了後に開始可能。US1 の実装が後方互換テストの前提
- **User Story 3 (P2)**: Foundational 完了後に開始可能。US1 の実装が前提

### Within Each User Story

- モデル → パーサー → OCI クライアント → エンジン → API → フロントエンド → テスト
- [P] マーク付きタスクは並行実行可能

### Parallel Opportunities

- T009, T010 は並行可能（同一ファイルだが異なるセクション）
- T017, T018, T019 は並行可能（異なるファイル）
- US2 のテスト作成は US1 完了後に並行実行可能

---

## Parallel Example: User Story 1

```bash
# パーサー変更（スキーマとプロンプトは独立セクション）:
Task T009: "COST_QUERY_SCHEMA に group_by フィールド追加 in parser.py"
Task T010: "SYSTEM_PROMPT_TEMPLATE に集計軸判定ルール追加 in parser.py"

# フロントエンド変更（全て異なるファイル）:
Task T017: "i18n.js に compartment_column 翻訳キー追加"
Task T018: "breakdown.html のテーブル動的化"
Task T019: "comparison.html のテーブル動的化"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1: Setup — テストベースライン確認
2. Phase 2: Foundational — データモデル拡張
3. Phase 3: User Story 1 — コンパートメント別集計の実装
4. **STOP and VALIDATE**: テスト実行 + K8s デプロイ検証
5. 問題なければ次のストーリーへ

### Incremental Delivery

1. Setup + Foundational → モデル準備完了
2. US1 完了 → コンパートメント別集計 MVP
3. US2 完了 → 後方互換性保証
4. US3 完了 → フィルタ+グルーピング組み合わせ
5. Polish → パフォーマンス検証・K8s デプロイ・検証・PR 作成

---

## Notes

- [P] tasks = 異なるファイル、依存関係なし
- [Story] label = ユーザーストーリーへのトレーサビリティ
- 各ストーリーは独立してテスト・完了可能
- タスク完了ごとにコミット推奨
- T037 は反復タスク — 検証が通るまで繰り返す
- 全定数は `models.py` の `GROUP_BY_*` を使用し、文字列リテラルの直書きを避ける
