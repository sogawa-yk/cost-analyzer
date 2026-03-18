# クイックスタート: Web UI フロントエンド

**ブランチ**: `002-web-ui` | **日付**: 2026-03-18

## 前提条件

- Python 3.13 以上
- uv (パッケージマネージャー)
- OCI 認証情報 (`~/.oci/config`)
- 環境変数: `OCI_HOME_REGION`, `OCI_COMPARTMENT_ID`, `OCI_GENAI_MODEL`

## セットアップ

```bash
# リポジトリのクローン
git clone <repo-url>
cd cost-analyzer
git checkout 002-web-ui

# 依存関係のインストール
uv sync
```

## ローカル実行

```bash
# 環境変数の設定
export OCI_HOME_REGION=us-ashburn-1
export OCI_COMPARTMENT_ID=<your-compartment-ocid>
export OCI_GENAI_MODEL=google.gemini-2.5-flash

# サーバー起動
uv run python -m cost_analyzer serve

# ブラウザで開く
# http://localhost:8080
```

## 使い方

1. ブラウザで `http://localhost:8080` にアクセス
2. テキスト入力欄にコストクエリを入力:
   - 「先月のサービス別コストを教えて」
   - 「先月と今月のコストを比較して」
   - "Show costs for last month"
3. 送信ボタンをクリック（またはEnterキー）
4. 結果テーブルが表示される

## テスト実行

```bash
# ユニットテスト（モックテスト）
uv run pytest tests/unit/ -v

# OCI 統合テスト（実接続）
OCI_HOME_REGION=us-ashburn-1 \
OCI_COMPARTMENT_ID=<your-compartment-ocid> \
OCI_GENAI_MODEL=google.gemini-2.5-flash \
uv run pytest tests/integration/ -m oci -v

# 全テスト
uv run pytest
```

## Kubernetes デプロイ

```bash
# イメージビルド・プッシュ
docker build -t yyz.ocir.io/orasejapan/cost-analyzer:latest .
docker push yyz.ocir.io/orasejapan/cost-analyzer:latest

# デプロイ
kubectl apply -f k8s/configmap.yaml -f k8s/deployment.yaml -f k8s/service.yaml

# 確認
kubectl rollout status deployment/cost-analyzer
kubectl port-forward svc/cost-analyzer 8080:8080

# ブラウザで http://localhost:8080 にアクセス
```
