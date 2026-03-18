# データモデル: Web UI フロントエンド

**ブランチ**: `002-web-ui` | **日付**: 2026-03-18

## 概要

Web UI フロントエンドはステートレスな表示層であり、永続的なデータモデルは持たない。バックエンド API のレスポンスを受け取り、ブラウザ上で表示する。ここではフロントエンドが扱うデータ構造を定義する。

## エンティティ

### AppState（アプリケーション状態）

フロントエンドのルート状態。Alpine.js の `$store` で管理される。

| フィールド | 型 | 説明 |
|---|---|---|
| lang | `"ja" \| "en"` | 現在の表示言語。デフォルト: `"ja"` |
| loading | `boolean` | クエリ送信中フラグ |
| result | `BreakdownResult \| ComparisonResult \| null` | 最新のクエリ結果 |
| clarification | `ClarificationResult \| null` | 確認要求 |
| error | `ErrorResult \| null` | エラー情報 |
| backendHealthy | `boolean` | バックエンド接続状態 |

### BreakdownResult（内訳結果）

バックエンド `POST /query` の `type: "breakdown"` レスポンスに対応。

| フィールド | 型 | 説明 |
|---|---|---|
| type | `"breakdown"` | 結果タイプ識別子 |
| period | `{ start: string, end: string }` | 対象期間 |
| currency | `string` | 通貨コード (例: "JPY", "USD") |
| items | `BreakdownItem[]` | サービス別コスト項目リスト |
| total | `number` | 合計金額 |

### BreakdownItem（内訳項目）

| フィールド | 型 | 説明 |
|---|---|---|
| service | `string` | サービス名 |
| amount | `number` | コスト金額 |
| percentage | `number` | 全体に対する割合 (%) |
| rank | `integer` | 金額順の順位 |

### ComparisonResult（比較結果）

バックエンド `POST /query` の `type: "comparison"` レスポンスに対応。

| フィールド | 型 | 説明 |
|---|---|---|
| type | `"comparison"` | 結果タイプ識別子 |
| current_period | `{ start: string, end: string }` | 当期 |
| previous_period | `{ start: string, end: string }` | 前期 |
| currency | `string` | 通貨コード |
| items | `ComparisonItem[]` | サービス別比較項目リスト |
| total_change | `number` | 合計変化額 |
| total_change_percent | `number` | 合計変化率 (%) |
| summary | `string` | トレンドサマリーテキスト |

### ComparisonItem（比較項目）

| フィールド | 型 | 説明 |
|---|---|---|
| service | `string` | サービス名 |
| current_amount | `number` | 当期金額 |
| previous_amount | `number` | 前期金額 |
| absolute_change | `number` | 変化額（正=増加、負=減少） |
| percent_change | `number \| null` | 変化率 (%)。前期がゼロの場合は null |

### ClarificationResult（確認要求）

| フィールド | 型 | 説明 |
|---|---|---|
| type | `"clarification"` | 結果タイプ識別子 |
| message | `string` | ユーザーへの確認メッセージ |
| suggestions | `string[]` | 提案候補リスト |

### ErrorResult（エラー）

| フィールド | 型 | 説明 |
|---|---|---|
| error | `string` | エラータイプ: `"parse_error" \| "auth_error" \| "api_error" \| "no_data"` |
| message | `string` | エラーメッセージ |
| guidance | `string \| undefined` | ユーザーへのガイダンス |
| example_queries | `string[] \| undefined` | クエリ例（parse_error 時） |

### I18nResource（翻訳リソース）

| フィールド | 型 | 説明 |
|---|---|---|
| query_placeholder | `string` | クエリ入力欄のプレースホルダー |
| submit_button | `string` | 送信ボタンテキスト |
| loading_message | `string` | ローディング中のメッセージ |
| service_column | `string` | テーブルの「サービス」カラムヘッダー |
| amount_column | `string` | テーブルの「金額」カラムヘッダー |
| percentage_column | `string` | テーブルの「割合」カラムヘッダー |
| total_label | `string` | 合計行のラベル |
| error_retry | `string` | リトライ促進メッセージ |
| error_contact_admin | `string` | 管理者連絡メッセージ |
| error_network | `string` | ネットワークエラーメッセージ |

## 状態遷移

```text
[初期状態] → (クエリ送信) → [ローディング中]
[ローディング中] → (breakdown 受信) → [内訳表示]
[ローディング中] → (comparison 受信) → [比較表示]
[ローディング中] → (clarification 受信) → [確認表示]
[ローディング中] → (error 受信) → [エラー表示]
[ローディング中] → (ネットワークエラー) → [エラー表示]
[任意の状態] → (新しいクエリ送信) → [ローディング中]
[任意の状態] → (言語切替) → [同じ状態、UIテキストのみ切替]
```

## バリデーションルール

- クエリテキストは1文字以上1000文字以下
- 言語設定は `"ja"` または `"en"` のみ
- 金額表示は `Intl.NumberFormat` で通貨コードに応じた桁区切りフォーマット
- 変化率の色分け: `absolute_change > 0` → 赤系、`absolute_change < 0` → 緑系、`0` → 中立
