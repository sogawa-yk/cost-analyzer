# リサーチ: 自然言語 OCI コストクエリ

**日付**: 2026-03-17
**ブランチ**: `001-nl-cost-query`
**仕様書**: `specs/001-nl-cost-query/spec.md`

---

## 1. OCI コスト管理 API

### 決定: `oci.usage_api.UsageapiClient.request_summarized_usages()`

**根拠**: この単一の OCI API 操作が仕様のすべての要件（コスト内訳、比較、サービス/コンパートメント/タグによるフィルタリング）をカバーします。日付範囲、粒度、グルーピングディメンション、フィルタを受け付けるため、FR-001 から FR-012 まで対応可能です。

**検討した代替案**:
- OCI コストレポート（CSV エクスポート）: 低速で、Object Storage バケットが必要、リアルタイムではない。
- OCI Billing API: 請求書中心で、利用レベルのコスト内訳ではない。

### 主要な API 詳細

**SDK モジュール**: `oci.usage_api`（パッケージ: `oci`）

**必須パラメータ** (`RequestSummarizedUsagesDetails`):
- `tenant_id` (str) — テナンシー OCID
- `time_usage_started` (datetime) — 日付範囲の開始
- `time_usage_ended` (datetime) — 日付範囲の終了
- `granularity` — `"DAILY"` | `"MONTHLY"` | `"TOTAL"`
- `query_type` — `"COST"`（デフォルトは `"USAGE"` のため、明示的に `"COST"` に設定が必要）

**重要なグルーピング要件**: `computed_amount` は `"currency"` が `group_by` に含まれている場合のみ値が入ります。コスト内訳クエリでは常に `["service", "currency"]` を `group_by` に含めてください。

**フィルタリング** (`Filter` モデル):
```python
Filter(
    operator="AND",
    dimensions=[
        Dimension(key="service", value="COMPUTE"),
        Dimension(key="compartmentName", value="production"),
    ]
)
```

**レスポンス**: `UsageAggregation` は `UsageSummary` アイテムのリストを含み、各アイテムには `service`, `computed_amount`, `currency`, `compartment_name`, `time_usage_started`, `time_usage_ended` フィールドがあります。

**ページネーション**: SDK は `oci.pagination.list_call_get_all_results()` による自動ページネーションを提供。レート制限は HTTP 429 を返し、`oci.retry.DEFAULT_RETRY_STRATEGY` を使用します。

### 認証戦略

| 環境 | 方法 | 実装 |
|---|---|---|
| ローカル開発 | API キー設定ファイル | `oci.config.from_file("~/.oci/config")` |
| OKE (Kubernetes) | インスタンスプリンシパル | `InstancePrincipalsSecurityTokenSigner()` |
| OCI Functions | リソースプリンシパル | `get_resource_principals_signer()` |

**決定**: API キー（ローカル）とインスタンスプリンシパル（OKE）を自動検出でサポート。インスタンスプリンシパルには動的グループと `usage-report` 読み取りアクセスおよび `generative-ai-inference` アクセスを付与する IAM ポリシーが必要です。

---

## 2. 自然言語クエリパーシング

### 決定: MVP は LLM のみ（OCI GenAI Service — Gemini 2.5 Flash）

**根拠**: SC-002（90% の正確な解釈）を達成する最短経路。Gemini 2.5 Flash は日本語と英語をネイティブに処理し、相対日付を解決し、意図（内訳 vs 比較）を検出します。OCI GenAI Service の `JsonSchemaResponseFormat` による構造化出力で Pydantic スキーマに一致する有効な JSON が保証されます。大阪リージョン (`ap-osaka-1`) で利用可能が確認済みです。

**検討した代替案**:
- ルールベース（正規表現 + dateparser）: 高速（<10ms）だがバイリンガル NL に対して脆弱; 多様な入力に対して推定 60-75% の精度で、広範なパターンエンジニアリングなしに SC-002 を達成する可能性は低い。
- ハイブリッド（ルール + LLM フォールバック）: 長期的に最良のアーキテクチャだが MVP には複雑性が追加される。実際のクエリパターンが観察された後の post-MVP 最適化として計画。
- Anthropic Claude (外部 API): 高性能だが外部依存が増え、認証が OCI と別系統になる。OCI GenAI に統一することで認証・ネットワーク管理が簡素化される。

### OCI GenAI Service 詳細

**SDK モジュール**: `oci.generative_ai_inference`
**モデル**: Google Gemini 2.5 Flash
**リージョン**: `ap-osaka-1`
**エンドポイント**: `https://inference.generativeai.ap-osaka-1.oci.oraclecloud.com`

**主要クラス**:
- `GenerativeAiInferenceClient` — メインクライアント
- `ChatDetails` — チャットリクエストラッパー
- `GenericChatRequest` — 汎用チャットリクエスト（ツール使用、構造化出力対応）
- `JsonSchemaResponseFormat` — 構造化出力スキーマ
- `OnDemandServingMode` — オンデマンドモデル指定

**認証の利点**: コスト管理 API と同じ OCI 認証（API キー / インスタンスプリンシパル）を使用。追加の API キー管理が不要。

**構造化出力の使用方法**:
```python
import oci
from oci.generative_ai_inference import models as genai_models

client = oci.generative_ai_inference.GenerativeAiInferenceClient(
    config=config,
    service_endpoint="https://inference.generativeai.ap-osaka-1.oci.oraclecloud.com"
)

chat_request = genai_models.GenericChatRequest(
    messages=[...],
    response_format=genai_models.JsonSchemaResponseFormat(
        json_schema=cost_query_schema
    ),
    temperature=0,
)

chat_detail = genai_models.ChatDetails(
    chat_request=chat_request,
    compartment_id=compartment_ocid,
    serving_mode=genai_models.OnDemandServingMode(
        model_id="google/gemini-2.5-flash"
    ),
)

response = client.chat(chat_detail)
```

### 具体的な MVP スタック

- `oci.generative_ai_inference` で Gemini 2.5 Flash（大阪リージョン）
- `JsonSchemaResponseFormat` で CostQuery JSON スキーマを構造化出力として使用
- 決定論的パーシングのため `temperature=0`
- システムプロンプトに現在の日付、利用可能な OCI サービス名、コンパートメント名を含める
- 後処理の日付演算に `dateparser` + `python-dateutil`

### CostQuery スキーマ (Pydantic)

```python
class QueryType(str, Enum):
    BREAKDOWN = "breakdown"
    COMPARISON = "comparison"

class CostQuery(BaseModel):
    query_type: QueryType
    start_date: date
    end_date: date
    comparison_start_date: date | None = None
    comparison_end_date: date | None = None
    service_filter: str | None = None
    compartment_filter: str | None = None
    needs_clarification: bool = False
    clarification_message: str | None = None
    detected_language: str  # "ja" or "en"
```

### レイテンシバジェット（SC-003 の5秒目標内）

| ステップ | p50 | p95 |
|---|---|---|
| NL パーシング (Gemini 2.5 Flash via OCI GenAI) | ~300ms | ~1s |
| OCI API 呼び出し | ~500ms | ~2s |
| レスポンスフォーマット | <10ms | <10ms |
| **合計** | **~810ms** | **~3s** |

---

## 3. CLI アーキテクチャ & デプロイ

### 決定: Typer CLI + OKE 用 FastAPI ラッパー

**根拠**: Typer はローカル使用とテストに最もクリーンな開発者体験を提供します。Kubernetes デプロイには、薄い FastAPI HTTP レイヤーが同じコアロジックをラップし、標準的な Deployment + Service + ヘルスチェックを実現します。

**検討した代替案**:
- Click: 成熟しているがより冗長; Typer は Click をより良い API でラップ。
- argparse: 会話型 CLI には冗長すぎる; Rich 統合なし。
- K8s での CLI のみ (CronJob): スケジュール済みレポートには適しているが対話型クエリには不適。

### 技術スタック

| コンポーネント | 選択 | バージョン |
|---|---|---|
| 言語 | Python | 3.13 |
| CLI フレームワーク | Typer | 最新 |
| HTTP ラッパー | FastAPI | 最新 |
| 出力フォーマット | Rich | 最新 |
| 設定管理 | pydantic-settings | 最新 |
| パッケージマネージャー | uv | 最新 |
| OCI SDK | oci | 最新 |
| LLM | OCI GenAI Service (Gemini 2.5 Flash) | — |
| 日付パーシング | dateparser + python-dateutil | 最新 |
| テスト | pytest | 最新 |
| コンテナベース | python:3.13-slim | — |
| コンテナレジストリ | OCIR | — |
| Kubernetes | OKE | — |

### デプロイアーキテクチャ (OKE)

**主要**: FastAPI Deployment + ClusterIP Service
- `/query` エンドポイントで NL 入力を受け付け、JSON コスト内訳を返す
- `/health` で K8s の liveness/readiness プローブ
- インスタンスプリンシパル認証（OCI 統一 — コスト API と GenAI の両方）
- 外部 API キー不要

**補助**（将来）: 日次コストレポート用の CronJob

### Dockerfile 戦略

uv を使用したマルチステージビルド:
1. ビルドステージ: `python:3.13-slim` + uv、ロックファイルから依存関係をインストール
2. ランタイムステージ: `python:3.13-slim`、`.venv` のみコピー、非 root ユーザー
3. エントリーポイント: `python -m cost_analyzer`

---

## 4. Post-MVP 最適化ロードマップ

1. トップ10クエリパターン用のルールベース高速パスを追加（~70-80% キャッシュヒット、<10ms）
2. 繰り返しクエリの LLM パーシング結果をキャッシュ
3. タグベースフィルタリングを追加（FR は MVP P3 を超えて拡張）
4. 大規模データセット用のストリーミングレスポンスを追加

---

## 出典

- [OCI Usage API - Python SDK](https://docs.oracle.com/en-us/iaas/tools/python/latest/api/usage_api/client/oci.usage_api.UsageapiClient.html)
- [RequestSummarizedUsagesDetails](https://docs.oracle.com/en-us/iaas/tools/python/latest/api/usage_api/models/oci.usage_api.models.RequestSummarizedUsagesDetails.html)
- [OCI SDK 認証方法](https://docs.oracle.com/en-us/iaas/Content/API/Concepts/sdk_authentication_methods.htm)
- [OCI GenAI Service プレトレーニングモデル](https://docs.oracle.com/en-us/iaas/Content/generative-ai/pretrained-models.htm)
- [OCI GenAI リージョン別モデル可用性](https://docs.oracle.com/en-us/iaas/Content/generative-ai/model-endpoint-regions.htm)
- [GenericChatRequest Python SDK](https://docs.oracle.com/en-us/iaas/tools/python/latest/api/generative_ai_inference/models/oci.generative_ai_inference.models.GenericChatRequest.html)
- [JsonSchemaResponseFormat Python SDK](https://docs.oracle.com/en-us/iaas/tools/python/latest/api/generative_ai_inference/models/oci.generative_ai_inference.models.JsonSchemaResponseFormat.html)
- [dateparser ドキュメント](https://dateparser.readthedocs.io/en/latest/)
- [Typer ドキュメント](https://typer.tiangolo.com/)
- [FastAPI ドキュメント](https://fastapi.tiangolo.com/)
- [Rich ドキュメント](https://rich.readthedocs.io/)
- [Docker マルチステージビルド](https://docs.docker.com/build/building/multi-stage/)
