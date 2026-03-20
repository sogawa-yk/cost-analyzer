# Quickstart: NL チャット UI

**Feature**: 006-nl-chat-ui | **Date**: 2026-03-20

## 前提条件

- Python 3.13+
- OCI CLI 設定済み（`~/.oci/config`）
- OCI GenAI Service アクセス権限（コンパートメント: `ocid1.compartment.oc1..aaaaaaaanxm4oucgt5pkgd7sw2vouvckvvxan7ca2lirowaao7krnzlkdkhq`）

## ローカル開発

```bash
# 1. ブランチ切替
git checkout 006-nl-chat-ui

# 2. 依存関係インストール
pip install -e ".[dev]"

# 3. 環境変数設定（ローカル開発用）
export OCI_COMPARTMENT_ID="ocid1.compartment.oc1..aaaaaaaanxm4oucgt5pkgd7sw2vouvckvvxan7ca2lirowaao7krnzlkdkhq"
export OCI_GENAI_MODEL="google.gemini-2.5-flash"

# 4. 開発サーバー起動
python -m cost_analyzer serve --reload

# 5. ブラウザでアクセス
open http://localhost:8080
```

## テスト実行

```bash
# ユニットテスト
pytest tests/unit/ -v

# 統合テスト（OCI 接続必要）
pytest tests/integration/ -v

# E2E テスト（サーバー起動必要）
pytest tests/e2e/ -v
```

## K8s デプロイ

既存の ConfigMap（`k8s/configmap.yaml`）に必要な設定がすでに含まれている：
- `OCI_COMPARTMENT_ID`: 設定済み
- `OCI_GENAI_MODEL`: `google.gemini-2.5-flash` 設定済み

```bash
# マニフェスト適用
kubectl apply -f k8s/
```

## 主要な変更ファイル

| ファイル | 変更内容 |
|---------|---------|
| `src/cost_analyzer/api.py` | /query レスポンスに conversational_text 追加 |
| `src/cost_analyzer/engine.py` | generate_conversational_response() 新規関数 |
| `src/cost_analyzer/models.py` | ConversationalResponse モデル追加 |
| `src/cost_analyzer/templates/index.html` | チャットUI レイアウトに書き換え |
| `src/cost_analyzer/static/js/app.js` | Alpine.js ストアをメッセージ配列駆動に変更 |
| `src/cost_analyzer/static/js/i18n.js` | チャットUI用翻訳キー追加 |
| `src/cost_analyzer/static/css/style.css` | チャットバブル・レイアウトスタイル追加 |
