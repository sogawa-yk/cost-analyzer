# Issue #7 問題分析レポート: コンパートメントごとの集計に対応していない

**Issue**: [#7 コンパートメントごとの集計に対応していない](https://github.com/sogawa-yk/cost-analyzer/issues/7)
**作成日**: 2026-03-20
**ステータス**: Open

## 1. 問題の概要

ユーザーが「コンパートメント別のコストを教えて」と問い合わせても、システムはサービス別の集計結果を返す。現在の実装は**集計軸がサービス（service）にハードコードされており**、コンパートメント別やその他の軸での集計に対応していない。

### 再現手順

1. チャットUIで「コンパートメント別のコストを教えて」と入力
2. システムはサービス別のコスト内訳テーブルを返す
3. コンパートメント別の集計結果は表示されない

### 期待される動作

コンパートメント名をキーとした集計テーブルが表示される。

## 2. 根本原因

**フィルタリング（絞り込み）とグルーピング（集計軸）の混同**が根本原因である。

現在の実装は `compartment_filter`（コンパートメントで結果を絞り込む機能）のみを持ち、`group_by`（コンパートメント別に集計する機能）を持たない。

| 機能 | 現在の対応状況 | 例 |
|------|--------------|------|
| サービス別集計 | 対応済み | 「サービス別のコストを教えて」→ サービス別テーブル |
| コンパートメント絞り込み | 対応済み | 「prod コンパートメントのコストを教えて」→ prod のみのサービス別テーブル |
| コンパートメント別集計 | **未対応** | 「コンパートメント別のコストを教えて」→ ~~コンパートメント別テーブル~~ サービス別テーブルが返る |

## 3. 影響範囲

問題は以下の7ファイルにまたがっている。

### 3.1 パーサー（parser.py）

`COST_QUERY_SCHEMA` と `SYSTEM_PROMPT_TEMPLATE` に `group_by` フィールドが存在しない。LLM がユーザーの意図（コンパートメント別集計）をパース結果に反映できない。

```
COST_QUERY_SCHEMA = {
    "properties": {
        "query_type": ...,
        "service_filter": ...,
        "compartment_filter": ...,
        # group_by が存在しない
    }
}
```

システムプロンプトにも集計軸の判定ルールがなく、「コンパートメント別」という表現を適切に解釈できない。

### 3.2 データモデル（models.py）

`CostQuery` に `group_by` フィールドがない。

```python
class CostQuery(BaseModel):
    query_type: QueryType
    start_date: date
    end_date: date
    service_filter: str | None = None
    compartment_filter: str | None = None
    # group_by がない
```

`ServiceCost` と `ServiceDelta` は `service: str` フィールドがハードコードされており、コンパートメント名を格納する柔軟性がない。

ただし、`CostLineItem` には既に `compartment_name` と `compartment_path` フィールドが存在する。OCI Usage API からコンパートメント情報は取得済みであり、集計ロジックのみが問題である。

### 3.3 集計エンジン（engine.py）

`fetch_breakdown()` の集計ロジックがサービスにハードコードされている。

```python
# engine.py line 192-197
service_totals: dict[str, Decimal] = defaultdict(Decimal)
for item in line_items:
    service_totals[item.service] += item.amount  # ← service 固定
```

`fetch_comparison()` も同様にサービス名でマッピングしている。`generate_trend_summary()` も `d.service` を直接参照している。

### 3.4 OCI クライアント（oci_client.py）

`request_cost_data()` の `group_by` パラメータがサービス固定。

```python
# oci_client.py line 141
group_by=["service", "currency"]  # ← compartmentName を含まない
```

OCI Usage API 自体は `group_by=["compartmentName", "currency"]` をサポートしている。

### 3.5 API エンドポイント（api.py）

`/query` レスポンスの `items` 配列が `service` キーにハードコードされている。

```python
"items": [{"service": item.service, "amount": ..., ...}]
```

### 3.6 テンプレート（breakdown.html / comparison.html）

テーブルヘッダーとセルが `service` 固定。

```html
<th x-text="$store.i18n.t('service_column')"></th>
<td x-text="item.service"></td>
```

## 4. 現在のデータフロー（問題箇所の図示）

```
ユーザー入力: 「コンパートメント別のコストを教えて」
    │
    ▼
[parser.py] LLM パース
    │  ❌ group_by フィールドがない → 意図を取りこぼす
    ▼
CostQuery(service_filter=None, compartment_filter=None)
    │  ❌ group_by 情報なし
    ▼
[oci_client.py] OCI Usage API 呼び出し
    │  group_by=["service", "currency"]  ❌ compartmentName なし
    ▼
[engine.py] fetch_breakdown()
    │  service_totals[item.service] += amount  ❌ service 固定集計
    ▼
[api.py] レスポンス構築
    │  "items": [{"service": "COMPUTE", ...}]  ❌ service 固定
    ▼
[breakdown.html] テーブル表示
       ❌ サービス別テーブルが表示される
```

## 5. 修正に必要な変更

| ファイル | 変更内容 | 影響度 |
|---------|---------|--------|
| `parser.py` | `COST_QUERY_SCHEMA` に `group_by` フィールド追加。システムプロンプトに集計軸判定ルール追加 | 高 |
| `models.py` | `CostQuery` に `group_by: str = "service"` 追加。`ServiceCost.service` を汎用キーに変更 | 高 |
| `engine.py` | `fetch_breakdown()` の集計ロジックを `query.group_by` に基づいて動的に変更 | 高 |
| `oci_client.py` | `request_cost_data()` の `group_by` パラメータを動的に変更可能にする | 中 |
| `api.py` | レスポンスに `group_by` フィールド追加、`items` のキーを動的化 | 中 |
| `breakdown.html` | テーブルヘッダー・セルを `group_by` に応じて動的切替 | 低 |
| `comparison.html` | 同上 | 低 |
| `i18n.js` | `compartment_column` 翻訳キー追加 | 低 |

## 6. 好材料

以下の点は既に対応済みであり、修正コストを低減する。

- **OCI Usage API** は `group_by=["compartmentName"]` をネイティブサポートしている
- **CostLineItem** には既に `compartment_name` / `compartment_path` フィールドが存在する
- **compartment_filter** の仕組み（パーサー → OCI クライアント）が既に動作しており、パイプラインの参考になる
- `group_by` のデフォルト値を `"service"` にすれば、**既存動作との後方互換性**を維持できる

## 7. 将来の拡張性

`group_by` フィールドを導入すれば、以下の集計軸にも拡張可能。

| 集計軸 | OCI Usage API group_by 値 | ユーザー入力例 |
|--------|--------------------------|--------------|
| サービス別 | `service` | 「サービス別のコストを教えて」 |
| コンパートメント別 | `compartmentName` | 「コンパートメント別のコストを教えて」 |
| リージョン別 | `region` | 「リージョン別のコストを教えて」 |
| SKU別 | `skuName` | 「SKU別のコストを教えて」 |
| タグ別 | `tagKey`, `tagValue` | 「環境タグ別のコストを教えて」 |
