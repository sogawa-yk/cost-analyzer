# Implementation Plan: NL クエリ品質改善

**Branch**: `005-nl-query-quality-fix` | **Date**: 2026-03-20 | **Spec**: [spec.md](spec.md)
**Input**: E2E テストレポート（23件中8件 WARN）に基づく品質改善

## Summary

E2E テスト（2026-03-20）で発見された3領域の問題（比較クエリ 0/5、エッジケース 2/5、サービスフィルタ 1/3）を修正する。主な対処は `parser.py` の (1) システムプロンプト強化、(2) `ValidationError` の防御的ハンドリング追加、(3) 比較日付フォールバック自動推定の3点。データモデル・API コントラクト・エンジンロジックへの変更はなし。

## Technical Context

**Language/Version**: Python 3.13
**Primary Dependencies**: FastAPI, OCI GenAI SDK (Llama 3.3 70B), Pydantic v2
**Storage**: N/A（ステートレス）
**Testing**: pytest
**Target Platform**: Linux (OKE クラスタ)
**Project Type**: Web service (REST API + CLI)
**Performance Goals**: クエリ応答 5 秒以内（既存要件、変更なし）
**Constraints**: LLM 出力の確率的性質。プロンプト改善で精度向上するが 100% 保証不可 → コード側の防御的処理が必須
**Scale/Scope**: 変更ファイル 2 件（parser.py + test_parser.py）

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 原則 | ステータス | 備考 |
|------|-----------|------|
| I. Code Quality | PASS | 単一責任（parser.py 内の変更）、40行/関数制限遵守、型アノテーション維持 |
| II. Testing Standards | PASS | 各修正に回帰テスト追加、80% カバレッジ維持 |
| III. UX Consistency | PASS | `api_error` → `parse_error` + クエリ例に変更。エラーメッセージがアクション可能に |
| IV. Performance Requirements | PASS | パフォーマンスへの影響なし（プロンプトの文字数増加は LLM レイテンシに対して無視可能） |
| Quality Gates | PASS | lint, test, UX gate すべて適合 |

## Project Structure

### Documentation (this feature)

```text
specs/005-nl-query-quality-fix/
├── spec.md
├── plan.md              # This file
├── research.md
├── data-model.md
├── quickstart.md
└── checklists/
    └── requirements.md
```

### Source Code (変更対象)

```text
src/cost_analyzer/
├── parser.py            # 主要変更: プロンプト強化、ValidationError ハンドリング、比較フォールバック
└── models.py            # 変更なし（参照のみ）

tests/unit/
└── test_parser.py       # テストケース追加
```

**Structure Decision**: 既存のプロジェクト構造を維持。新規ファイルの追加なし。

## 変更設計

### 変更 1: システムプロンプト強化 (`parser.py` L16-47)

**目的**: LLM の出力精度向上（比較クエリ、サービスフィルタ、非コストクエリ）

**変更内容**:

1. **比較クエリの JSON 出力例を追加** — LLM が `comparison_start_date`/`comparison_end_date` を正しく設定するための Few-shot example
2. **サービスフィルタの抽出例と OCI サービス名リストを追加** — "Object Storage" や "Database" のような複数語サービス名の抽出を安定化
3. **非コストクエリのハンドリングルール強化** — コスト無関係の入力に対して `needs_clarification=true` を設定するよう指示

**プロンプト追加セクション（概要）**:

```
## 出力例

### 比較クエリの例
入力: 「先月と今月のコストを比較して」（現在日: 2026-03-20）
出力:
{
  "query_type": "comparison",
  "start_date": "2026-03-01",
  "end_date": "2026-04-01",
  "comparison_start_date": "2026-02-01",
  "comparison_end_date": "2026-03-01",
  ...
}

### サービスフィルタの例
入力: 「先月のObject Storageのコストは？」
出力: { ..., "service_filter": "OBJECT_STORAGE", ... }

### 非コストクエリの例
入力: 「今日の天気は？」
出力: { ..., "needs_clarification": true, "clarification_message": "..." }
```

**サービス名リスト（プロンプトに追加）**:
COMPUTE, OBJECT_STORAGE, DATABASE, NETWORKING, BLOCK_STORAGE, FUNCTIONS, CONTAINER_ENGINE, LOAD_BALANCER, API_GATEWAY, LOGGING, MONITORING, VAULT, BASTION 等

### 変更 2: ValidationError の防御的ハンドリング (`parser.py` L136-169)

**目的**: LLM の不正出力時に `api_error` ではなく `parse_error` + クエリ例を返す

**変更内容**:

`CostQuery()` 構築の `try` ブロック内で以下の例外を個別ハンドリング:

1. `pydantic.ValidationError` を `json.JSONDecodeError` と同等に扱う
   - 現在: `except Exception` → `map_oci_error()` → `api_error`
   - 修正後: `except ValidationError` → `PARSE_ERROR` + クエリ例

2. `ValueError`（`date.fromisoformat()` 失敗時）も同様に捕捉

**変更前の例外フロー**:
```
LLM returns invalid data → CostQuery() raises ValidationError → except Exception → map_oci_error → api_error
```

**変更後の例外フロー**:
```
LLM returns invalid data → CostQuery() raises ValidationError → except (ValidationError, ValueError) → parse_error + クエリ例
```

### 変更 3: 比較日付フォールバック自動推定 (`parser.py` L136-147)

**目的**: LLM が比較日付を省略した場合、`api_error` ではなく自動推定で比較を実行

**変更内容**:

`CostQuery()` 構築前に、比較クエリのフォールバック推定を挿入:

```python
# query_type が comparison で比較日付が省略された場合、自動推定
if result["query_type"] == "comparison":
    if not _nullable_date(result.get("comparison_start_date")):
        # start_date〜end_date の期間長を計算し、直前の同期間を推定
        start = date.fromisoformat(result["start_date"])
        end = date.fromisoformat(result["end_date"])
        delta = end - start
        result["comparison_start_date"] = (start - delta).isoformat()
        result["comparison_end_date"] = start.isoformat()
```

**ロジック**: 「今月（3/1〜4/1）を比較」→ 期間長31日 → 前期間は 1/29〜3/1。ただし月単位での推定がより自然なため、`dateutil.relativedelta` を使用して月単位で前期間を推定することも検討。

**最終判断**: `relativedelta` を使用し、月の境界を尊重した推定を行う:
- start=3/1, end=4/1 (1ヶ月) → comparison=2/1〜3/1
- start=1/1, end=4/1 (3ヶ月) → comparison=10/1〜1/1

### テスト追加 (`tests/unit/test_parser.py`)

| テストケース | カテゴリ | 検証内容 |
|-------------|---------|---------|
| `test_comparison_fallback_infers_previous_period` | P1 比較 | LLM が比較日付を省略した場合、前期間が自動推定される |
| `test_comparison_with_explicit_dates` | P1 比較 | LLM が比較日付を正しく返した場合、そのまま使用される |
| `test_invalid_dates_return_parse_error` | P2 エッジ | `start_date >= end_date` の場合、`api_error` ではなく `parse_error` が返る |
| `test_none_dates_return_parse_error` | P2 エッジ | 日付が None の場合、`api_error` ではなく `parse_error` が返る |
| `test_validation_error_returns_parse_error` | P2 エッジ | `ValidationError` が `parse_error` として返される |
| `test_service_filter_preserved` | P3 フィルタ | `service_filter` が正しく CostQuery に設定される |

## Complexity Tracking

> 憲法違反なし。

該当なし。
