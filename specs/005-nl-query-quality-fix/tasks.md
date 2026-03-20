# Tasks: NL クエリ品質改善

**Input**: Design documents from `/specs/005-nl-query-quality-fix/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md

**Tests**: 回帰テスト追加が仕様で要求されているため、各ストーリーにテストタスクを含む。

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Source**: `src/cost_analyzer/`
- **Tests**: `tests/unit/`

---

## Phase 1: Setup

**Purpose**: 変更不要。既存プロジェクト構造をそのまま使用。

該当タスクなし（新規ファイル・依存関係の追加なし）。

---

## Phase 2: Foundational (共通プロンプト基盤)

**Purpose**: 3つのユーザーストーリーすべてに影響するシステムプロンプトの基盤改善

**⚠️ CRITICAL**: US1/US2/US3 すべてがこのフェーズのプロンプト変更に依存

- [x] T001 システムプロンプトに比較クエリの JSON 出力例を追加する in `src/cost_analyzer/parser.py` SYSTEM_PROMPT_TEMPLATE — ルールセクション末尾に「## 出力例」を追加し、comparison クエリの入出力例（先月と今月、2期間指定）を 2 例記載
- [x] T002 システムプロンプトに OCI サービス名リストとフィルタ抽出ルールを追加する in `src/cost_analyzer/parser.py` SYSTEM_PROMPT_TEMPLATE — ルール 4 を拡張し、主要 OCI サービス名（COMPUTE, OBJECT_STORAGE, DATABASE, NETWORKING, BLOCK_STORAGE, FUNCTIONS 等）のリストと、複数語サービス名（"Object Storage" → "OBJECT_STORAGE"）の抽出例を記載
- [x] T003 システムプロンプトに非コストクエリのハンドリングルールを追加する in `src/cost_analyzer/parser.py` SYSTEM_PROMPT_TEMPLATE — ルール 6 を拡張し、コスト無関係の入力（天気、挨拶等）に対して `needs_clarification=true` + クエリ例を設定するよう指示。出力例セクションにも非コスト入力の例を追加

**Checkpoint**: システムプロンプトの改善完了。LLM の出力精度が向上するが、コード側の防御的処理はまだ未実装。

---

## Phase 3: User Story 1 - 比較クエリが正しく動作する (Priority: P1) 🎯 MVP

**Goal**: 比較クエリ 5 件中 4 件以上を PASS にする（改善前: 0/5）

**Independent Test**: 「先月と今月のコストを比較して」などの比較クエリを発行し、`api_error` や `ValidationError` ではなく比較テーブルが返されることを検証

### Tests for User Story 1

- [x] T004 [P] [US1] 比較日付フォールバック推定のユニットテストを追加する in `tests/unit/test_parser.py` — LLM が `query_type=comparison` で `comparison_start_date`/`comparison_end_date` を省略した場合、前期間が自動推定されることを検証するテスト `test_comparison_fallback_infers_previous_period` を追加
- [x] T005 [P] [US1] 明示的比較日付が保持されるテストを追加する in `tests/unit/test_parser.py` — LLM が比較日付を正しく返した場合、そのまま使用されることを検証するテスト `test_comparison_with_explicit_dates_preserved` を追加

### Implementation for User Story 1

- [x] T006 [US1] 比較日付フォールバック自動推定ロジックを実装する in `src/cost_analyzer/parser.py` parse_query 関数内 — `CostQuery()` 構築前に、`result["query_type"] == "comparison"` かつ `comparison_start_date` が null/省略の場合、`start_date`/`end_date` の期間長から `dateutil.relativedelta` を使い前期間を推定して `result` に注入する。月の境界を尊重（例: 3/1〜4/1 → 前期間 2/1〜3/1）

**Checkpoint**: 比較クエリが LLM の出力不備に対しても動作する。T004/T005 のテストが PASS することを確認。

---

## Phase 4: User Story 2 - コスト無関係・曖昧入力のエラーハンドリング (Priority: P2)

**Goal**: エッジケース 5 件中 4 件以上を PASS にする（改善前: 2/5）。`api_error` を撲滅。

**Independent Test**: 「今日の天気は？」「コストを教えて」「Hello, what can you do?」を送信し、`api_error` ではなく `parse_error` + クエリ例が返されることを検証

### Tests for User Story 2

- [x] T007 [P] [US2] ValidationError が parse_error として返されるテストを追加する in `tests/unit/test_parser.py` — LLM が `start_date >= end_date` を返した場合に `ErrorType.PARSE_ERROR`（`api_error` ではなく）が返されることを検証するテスト `test_invalid_dates_return_parse_error` を追加
- [x] T008 [P] [US2] None 日付が parse_error として返されるテストを追加する in `tests/unit/test_parser.py` — LLM が日付フィールドに None を返した場合に `ErrorType.PARSE_ERROR` + `example_queries` が返されることを検証するテスト `test_none_dates_return_parse_error` を追加
- [x] T009 [P] [US2] Pydantic ValidationError が parse_error として返されるテストを追加する in `tests/unit/test_parser.py` — 任意の Pydantic ValidationError（例: `detected_language` が不正値）が `ErrorType.PARSE_ERROR` として返されることを検証するテスト `test_validation_error_returns_parse_error` を追加

### Implementation for User Story 2

- [x] T010 [US2] `pydantic.ValidationError` と `ValueError` を防御的にハンドリングする in `src/cost_analyzer/parser.py` parse_query 関数内 — 現在の `except Exception` ブロック（L161-169）の前に `except (ValidationError, ValueError)` ブロックを追加し、`json.JSONDecodeError` と同等の `ErrorResponse(error_type=ErrorType.PARSE_ERROR, ...)` + クエリ例を返す。`from pydantic import ValidationError` を import に追加

**Checkpoint**: すべてのエッジケースで `api_error` が返されなくなる。T007/T008/T009 のテストが PASS することを確認。

---

## Phase 5: User Story 3 - サービスフィルタが安定動作する (Priority: P3)

**Goal**: サービスフィルタ 3 件中 3 件を PASS にする（改善前: 1/3）

**Independent Test**: 「先月の Object Storage のコストは？」「先月の Database のコストを教えて」を送信し、指定サービスのコストのみが返されることを検証

### Tests for User Story 3

- [x] T011 [P] [US3] サービスフィルタが CostQuery に正しく設定されるテストを追加する in `tests/unit/test_parser.py` — LLM が `service_filter: "OBJECT_STORAGE"` を返した場合、`CostQuery.service_filter` が `"OBJECT_STORAGE"` に設定されることを検証するテスト `test_service_filter_object_storage_preserved` を追加

### Implementation for User Story 3

プロンプト改善は Phase 2（T002）で完了済み。追加のコード変更はなし。

**Checkpoint**: Phase 2 のプロンプト改善 + E2E テストで検証。T011 のテストが PASS することを確認。

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: 退行テストと最終検証

- [x] T012 既存ユニットテスト（test_parser.py 既存6件）が退行しないことを確認する — `pytest tests/unit/test_parser.py -v` を実行し、全件 PASS
- [x] T013 ruff lint が警告なしで通ることを確認する — `ruff check src/cost_analyzer/parser.py tests/unit/test_parser.py`
- [x] T014 quickstart.md の検証手順を実行する — テスト実行コマンドが正しく動作することを確認

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: 該当なし
- **Phase 2 (Foundational)**: プロンプト改善 — T001, T002, T003 は並列可（同一ファイルの異なるセクションだが、衝突回避のため順次実行を推奨）
- **Phase 3 (US1)**: Phase 2 完了後に開始。T004/T005 は並列可、T006 は T004/T005 後
- **Phase 4 (US2)**: Phase 2 完了後に開始。T007/T008/T009 は並列可、T010 は T007-T009 後
- **Phase 5 (US3)**: Phase 2 完了後に開始（T002 に依存）。T011 は独立
- **Phase 6 (Polish)**: Phase 3-5 すべて完了後

### User Story Dependencies

- **US1 (比較クエリ)**: Phase 2 に依存。US2/US3 との依存なし
- **US2 (エッジケース)**: Phase 2 に依存。US1/US3 との依存なし
- **US3 (サービスフィルタ)**: Phase 2（T002）に依存。US1/US2 との依存なし

### Parallel Opportunities

- US1, US2, US3 は Phase 2 完了後に並列実行可能
- 各 US 内のテストタスク（[P] マーク付き）は並列実行可能

---

## Parallel Example: User Story 2

```bash
# Launch all tests for US2 together:
Task: "T007 - ValidationError parse_error test in tests/unit/test_parser.py"
Task: "T008 - None dates parse_error test in tests/unit/test_parser.py"
Task: "T009 - Pydantic ValidationError parse_error test in tests/unit/test_parser.py"

# Then implement:
Task: "T010 - ValidationError handling in src/cost_analyzer/parser.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 2: プロンプト基盤改善（T001-T003）
2. Complete Phase 3: US1 比較クエリ修正（T004-T006）
3. **STOP and VALIDATE**: 比較クエリが動作することを確認
4. これだけで最大のインパクト（0/5 → 4/5+ 見込み）

### Incremental Delivery

1. Phase 2 完了 → プロンプト改善だけで一部のテストが改善する可能性あり
2. + US1 → 比較クエリ修正 → 最大インパクト (MVP!)
3. + US2 → エッジケース修正 → `api_error` 撲滅
4. + US3 → サービスフィルタ安定化 → プロンプト改善で対応済み
5. Phase 6 → 退行テスト＋lint 確認

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- 変更対象ファイルは主に `src/cost_analyzer/parser.py` と `tests/unit/test_parser.py` の 2 ファイル
- Phase 2 のプロンプト変更は同一ファイル（parser.py）の同一変数を編集するため、並列実行ではなく順次実行を推奨
- E2E テスト（23件）は本番環境の OCI GenAI を使用するため、ユニットテストで先に検証してから E2E テストで最終確認
