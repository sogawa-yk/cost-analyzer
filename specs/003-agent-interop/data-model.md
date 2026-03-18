# Data Model: エージェント間連携（Agent Interoperability）

**Date**: 2026-03-18
**Feature**: 003-agent-interop

## 概要

A2A SDK が提供する型（`AgentCard`, `AgentSkill`, `Task`, `Message`, `Part`, `Artifact` 等）をそのまま使用する。本フィーチャーで新規定義するモデルは、既存の cost-analyzer モデルと A2A プロトコルの間を橋渡しするものに限定する。

## 新規エンティティ

### StructuredCostRequest

構造化パラメータによるコスト分析リクエスト。外部エージェントが `DataPart` で送信する JSON の形式。

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `skill` | string (enum) | Yes | スキル ID（`get_cost_breakdown`, `compare_costs`, `list_services`, `list_compartments`, `health_check`） |
| `start_date` | string (ISO 8601 date) | skill による | 分析開始日 |
| `end_date` | string (ISO 8601 date) | skill による | 分析終了日 |
| `comparison_start_date` | string (ISO 8601 date) | No | 比較期間の開始日（`compare_costs` 時のみ） |
| `comparison_end_date` | string (ISO 8601 date) | No | 比較期間の終了日（`compare_costs` 時のみ） |
| `service_filter` | string | No | サービス名フィルタ |
| `compartment_filter` | string | No | コンパートメント名フィルタ |
| `lang` | string | No | 結果の言語（`ja` / `en`、デフォルト: `ja`） |

**バリデーションルール**:
- `get_cost_breakdown`: `start_date`, `end_date` 必須
- `compare_costs`: `start_date`, `end_date`, `comparison_start_date`, `comparison_end_date` すべて必須
- `list_services`, `list_compartments`, `health_check`: 追加パラメータ不要
- `start_date` < `end_date`（比較期間も同様）

### StructuredCostResponse

構造化されたコスト分析結果。`Artifact` の `DataPart` として返却される JSON の形式。

| フィールド | 型 | 説明 |
|---|---|---|
| `type` | string (enum) | `breakdown` / `comparison` / `services` / `compartments` / `health` |
| `data` | object | 既存モデル（`CostBreakdown` / `CostComparison` / `list[str]` 等）の JSON 表現 |
| `summary` | string | 人間可読なサマリーテキスト |

## 既存エンティティとのマッピング

| A2A 概念 | cost-analyzer 既存モデル | 変換方向 |
|---|---|---|
| `Message` (user, TextPart) | `parse_query()` への入力文字列 | A2A → cost-analyzer |
| `Message` (user, DataPart) | `StructuredCostRequest` → `CostQuery` | A2A → cost-analyzer |
| `Artifact` (DataPart) | `CostBreakdown` / `CostComparison` の JSON | cost-analyzer → A2A |
| `Artifact` (TextPart) | `TrendSummary.summary_text` / エラーメッセージ | cost-analyzer → A2A |
| `Task.status` (failed) | `ErrorResponse` | cost-analyzer → A2A |
| `AgentSkill` | FR-003〜FR-008 の各機能 | 静的定義 |

## 状態遷移

同期処理のため、タスクの状態遷移は単純:

```
submitted → working → completed  (正常系)
submitted → working → failed     (エラー系)
```

SDK の `InMemoryTaskStore` が状態管理を自動処理する。

## 既存モデルへの変更

既存の `models.py` への変更は不要。`StructuredCostRequest` を `CostQuery` に変換するマッピング関数を新規モジュール内に定義する。
