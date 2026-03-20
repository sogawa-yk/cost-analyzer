# Quickstart: コンパートメント別集計（group_by）対応

**Date**: 2026-03-20

## 変更概要

全レイヤーを貫通する変更。修正順序に沿って実装する。

## 修正順序と各ファイルの変更ポイント

### Step 1: models.py — データモデル拡張
- `CostQuery` に `group_by: str = "service"` フィールド追加
- `ServiceCost` に `group_key: str` フィールド追加、`service` を `@property` エイリアス化
- `ServiceDelta` も同様

### Step 2: parser.py — LLMパーサー拡張
- `COST_QUERY_SCHEMA` に `group_by` フィールド（enum: `["service", "compartment"]`）追加
- `SYSTEM_PROMPT_TEMPLATE` に集計軸判定ルール追加
- `_build_cost_query()` で `group_by` フィールドを処理

### Step 3: oci_client.py — OCI API 動的化
- `request_cost_data()` に `api_group_by: list[str] | None` パラメータ追加
- `group_by` 値に応じて OCI API の `group_by` パラメータを動的に設定

### Step 4: engine.py — 集計ロジック動的化
- `fetch_breakdown()` で `query.group_by` に応じて集計キーを選択
- `fetch_comparison()` も同様
- 同名コンパートメント重複時の `compartment_path` フォールバック実装

### Step 5: api.py — レスポンス拡張
- レスポンスに `group_by` フィールド追加
- items 配列に `group_key` フィールド追加

### Step 6: フロントエンド
- `i18n.js` に `compartment_column` 翻訳キー追加
- `breakdown.html` / `comparison.html` のテーブルヘッダー・セルを動的化

### Step 7: テスト
- `conftest.py` の `make_cost_query()` に `group_by` パラメータ追加
- パーサーテスト: group_by 判定テスト追加
- エンジンテスト: コンパートメント集計テスト追加
- APIテスト: レスポンス構造テスト追加

### Step 8: デプロイ・検証
- K8sクラスタにデプロイ
- 「コンパートメント別のコストを教えて」で実際にクエリ実行
- コンパートメント別テーブルが表示されることを確認
- 既存クエリの後方互換性も確認
- 改善確認後、PR作成

## テスト実行

```bash
cd src && pytest
ruff check .
```
