# K8s Discovery Contract: A2A エージェント サービスディスカバリ規約

**Date**: 2026-03-19
**Protocol**: A2A (Agent-to-Agent Protocol) v0.3.0
**Scope**: Kubernetes クラスタ内サービスディスカバリ

## 必須ラベル

```yaml
metadata:
  labels:
    a2a.protocol/enabled: "true"     # 必須: ディスカバリ対象
    a2a.protocol/version: "0.3"      # 必須: プロトコルバージョン
```

## 任意アノテーション

```yaml
metadata:
  annotations:
    a2a.protocol/agent-card-path: "/.well-known/agent-card.json"  # 省略時デフォルト
    a2a.protocol/transport: "JSONRPC"                              # 省略時デフォルト
    a2a.protocol/description: "OCI コスト分析エージェント"           # 推奨
```

## 推奨ポート名

```yaml
spec:
  ports:
    - name: a2a           # 推奨: reporter が優先使用
      port: 8080
      targetPort: 8080
```

ポート名が `a2a` でない場合、reporter は Service の最初のポートを使用する。

## 認証

### Secret 構成

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: mini-a2a-auth
type: Opaque
data:
  api-key: <base64 エンコードされた API キー>
```

### Deployment での Secret マウント

```yaml
env:
  - name: A2A_API_KEY
    valueFrom:
      secretKeyRef:
        name: mini-a2a-auth
        key: api-key
```

### 認証ヘッダー

| ヘッダー | サポート | 説明 |
|---------|---------|------|
| `x-api-key: <key>` | 必須（規約統一） | ディスカバリ規約の標準ヘッダー |
| `Authorization: Bearer <key>` | 任意（追加サポート） | OAuth2 互換 |
| `X-API-Key: <key>` | 同一（case-insensitive） | `x-api-key` と HTTP 仕様上同一 |

### 認証失敗時レスポンス

```json
HTTP/1.1 401 Unauthorized
Content-Type: application/json

{
  "error": "unauthorized",
  "message": "Invalid or missing API key."
}
```

## ディスカバリフロー

```
1. kubectl get svc -l a2a.protocol/enabled=true（全 namespace）
     ↓
2. 各 Service から接続情報を構築
   - URL: http://{name}.{namespace}.svc.cluster.local:{port}
   - Agent Card パス: アノテーション or デフォルト (/.well-known/agent-card.json)
     ↓
3. Agent Card を HTTP GET で取得（x-api-key ヘッダー付与）
     ↓
4. Agent Card の skills[] からスキル一覧を把握
     ↓
5. タスクに応じて適切なエージェントを選択・呼び出し
```

## reporter の API キー取得優先順位

1. `--api-key` CLI オプション
2. `REPORTER_API_KEY` 環境変数
3. Kubernetes Secret `mini-a2a-auth` から自動取得

## cost-analyzer Service マニフェスト（適用後）

```yaml
apiVersion: v1
kind: Service
metadata:
  name: cost-analyzer
  labels:
    app: cost-analyzer
    a2a.protocol/enabled: "true"
    a2a.protocol/version: "0.3"
  annotations:
    a2a.protocol/description: "OCI cost analysis agent — breakdown, comparison, and resource discovery"
spec:
  type: ClusterIP
  selector:
    app: cost-analyzer
  ports:
    - name: a2a
      port: 8080
      targetPort: 8080
      protocol: TCP
```

## エージェント開発者チェックリスト

- [ ] Service に `a2a.protocol/enabled: "true"` ラベルを付与した
- [ ] Service に `a2a.protocol/version: "0.3"` ラベルを付与した
- [ ] Agent Card エンドポイント（`/.well-known/agent-card.json`）が HTTP GET で応答する
- [ ] Agent Card に `name`, `description`, `skills[]` が含まれている
- [ ] 各 skill に `id`, `name`, `description`, `tags[]` が定義されている
- [ ] `message/send` に対して JSON-RPC 2.0 形式で応答する
- [ ] レスポンスの DataPart に構造化データを含めている
- [ ] `x-api-key` ヘッダーによる API キー認証を実装した
- [ ] Deployment で Secret `mini-a2a-auth` を環境変数としてマウントした
- [ ] API キー未指定時に `401 Unauthorized` を返すことを確認した
