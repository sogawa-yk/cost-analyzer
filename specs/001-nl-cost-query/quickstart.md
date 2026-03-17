# クイックスタート: 自然言語 OCI コストクエリ

## 前提条件

- Python 3.13 以上
- [uv](https://docs.astral.sh/uv/) パッケージマネージャー
- コスト管理 API および GenAI Service へのアクセス権を持つ OCI 認証情報（`~/.oci/config`）

## セットアップ

```bash
# プロジェクトに移動
cd cost-analyzer

# 依存関係のインストール
uv sync

# OCI 認証情報の確認
uv run python -c "import oci; oci.config.from_file(); print('OCI config OK')"
```

## 使い方 (CLI)

```bash
# 基本的なコスト内訳
uv run cost-analyzer "先月のサービス別コストを教えて"
uv run cost-analyzer "Show costs for February 2026"

# コスト比較
uv run cost-analyzer "先月と今月を比較して"
uv run cost-analyzer "Compare costs between January and February"

# スコープ指定クエリ
uv run cost-analyzer "Compute のコストだけ見せて"
uv run cost-analyzer "Show production compartment costs for last month"
```

## 使い方 (API — Kubernetes デプロイ用)

```bash
# API サーバーの起動
uv run cost-analyzer serve --port 8080

# HTTP 経由でクエリ
curl -X POST http://localhost:8080/query \
  -H "Content-Type: application/json" \
  -d '{"query": "先月のサービス別コストを教えて"}'
```

## 設定

| 環境変数 | 必須 | デフォルト | 説明 |
|---|---|---|---|
| `OCI_CONFIG_FILE` | いいえ | `~/.oci/config` | OCI 設定ファイルのパス |
| `OCI_CONFIG_PROFILE` | いいえ | `DEFAULT` | OCI 設定プロファイル名 |
| `OCI_AUTH_TYPE` | いいえ | `api_key` | `api_key` または `instance_principal` |
| `OCI_TENANCY_ID` | いいえ | 設定ファイルから | テナンシー OCID のオーバーライド |
| `OCI_COMPARTMENT_ID` | いいえ | 設定ファイルから | GenAI 呼び出し用コンパートメント OCID |
| `OCI_GENAI_ENDPOINT` | いいえ | `https://inference.generativeai.ap-osaka-1.oci.oraclecloud.com` | OCI GenAI Service エンドポイント |
| `OCI_GENAI_MODEL` | いいえ | `google/gemini-2.5-flash` | 使用するモデル ID |
| `LOG_LEVEL` | いいえ | `INFO` | ログレベル |

## テストの実行

```bash
# 全テスト
uv run pytest

# ユニットテストのみ
uv run pytest tests/unit/

# 統合テスト（OCI 認証情報が必要）
uv run pytest tests/integration/

# カバレッジ付き
uv run pytest --cov=cost_analyzer --cov-report=term-missing
```
