# Quickstart: A2A K8s サービスディスカバリ

## 既存エージェントの移行（cost-analyzer）

### 1. Service にラベルを追加

```bash
kubectl label svc cost-analyzer \
  a2a.protocol/enabled=true \
  a2a.protocol/version=0.3
```

### 2. アノテーション追加（任意）

```bash
kubectl annotate svc cost-analyzer \
  a2a.protocol/description="OCI cost analysis agent"
```

### 3. ポート名を設定（推奨）

```bash
kubectl patch svc cost-analyzer --type='json' \
  -p='[{"op":"replace","path":"/spec/ports/0/name","value":"a2a"}]'
```

### 4. 動作確認

```bash
# ラベルで検索
kubectl get svc -l a2a.protocol/enabled=true -A

# Agent Card 取得テスト
kubectl run --rm -it test --image=curlimages/curl -- \
  curl -s -H "x-api-key: $(kubectl get secret mini-a2a-auth -o jsonpath='{.data.api-key}' | base64 -d)" \
  http://cost-analyzer:8080/.well-known/agent-card.json | python3 -m json.tool
```

## 新規エージェントのデプロイ

### 1. Service マニフェスト

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-agent
  labels:
    app: my-agent
    a2a.protocol/enabled: "true"
    a2a.protocol/version: "0.3"
spec:
  selector:
    app: my-agent
  ports:
    - name: a2a
      port: 8080
      targetPort: 8080
```

### 2. Deployment マニフェスト（認証部分）

```yaml
env:
  - name: A2A_API_KEY
    valueFrom:
      secretKeyRef:
        name: mini-a2a-auth
        key: api-key
```

### 3. デプロイ & 確認

```bash
kubectl apply -f my-agent.yaml
kubectl get svc -l a2a.protocol/enabled=true -A
```
