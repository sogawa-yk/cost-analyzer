# OCI 認証方式の比較: Instance Principal vs API Key

## 概要

OKE (Oracle Container Engine for Kubernetes) 上にデプロイした cost-analyzer で、Instance Principal 認証では Usage API の呼び出しに失敗したが、API Key 認証に切り替えることで正常動作した。本レポートではその原理と原因を整理する。

## 発生した事象

| 認証方式 | GenAI Inference API | Usage API (`request_summarized_usages`) | 結果 |
|---|---|---|---|
| Instance Principal | OK | **404 NotAuthorizedOrNotFound** | 失敗 |
| API Key (ユーザー認証) | OK | OK | 成功 |

### エラー詳細

```
oci.exceptions.ServiceError: {
  'status': 404,
  'code': 'NotAuthorizedOrNotFound',
  'message': 'Authorization failed or requested resource not found.',
  'operation_name': 'request_summarized_usages',
  'request_endpoint': 'POST https://usageapi.us-ashburn-1.oci.oraclecloud.com/20200107/usage'
}
```

## 2つの認証方式の仕組み

### API Key 認証

```
ユーザー → API Key (秘密鍵 + フィンガープリント) → OCI API
```

- `~/.oci/config` に記載されたユーザー OCID、テナンシー OCID、秘密鍵で署名
- **ユーザーに紐づく IAM ポリシー**が適用される
- テナンシー管理者やAdminsグループのユーザーは、テナンシーレベルのリソースにアクセス可能

### Instance Principal 認証

```
OKE ノード(インスタンス) → Instance Principal証明書 → OCI API
```

- OKE ワーカーノードのインスタンスが自動的に取得する証明書で認証
- **Dynamic Group + IAM ポリシー** で権限が付与される
- ポリシー例: `Allow dynamic-group <dg-name> to <verb> <resource> in <scope>`

## 原因分析

### Usage API が特殊な理由

OCI Usage API (`usageapi`) はテナンシーレベルのサービスであり、以下の特性を持つ:

1. **テナンシースコープ必須**: `request_summarized_usages` の `tenant_id` パラメータはテナンシー OCID を要求する。コンパートメントスコープでは動作しない
2. **専用のポリシーが必要**: `usage-reports` リソースタイプへの読み取り権限が必要
3. **ホームリージョン限定**: Usage API はテナンシーのホームリージョンでのみ実行可能

### Instance Principal で失敗した理由

Instance Principal で Usage API を使うには、以下の IAM ポリシーが**テナンシーレベル**で必要:

```
Allow dynamic-group <OKE-nodes-dynamic-group> to read usage-reports in tenancy
```

このポリシーには以下の前提条件がある:

| 前提条件 | 説明 |
|---|---|
| Dynamic Group の作成 | OKE ワーカーノードのインスタンスを含む Dynamic Group が必要 |
| テナンシーレベルのポリシー | `in tenancy` スコープのため、テナンシー管理者権限が必要 |
| コンパートメントスコープ不可 | `in compartment <name>` では Usage API は動作しない |

本環境では:
- テナンシー管理者権限を持っていない
- コンパートメント管理者の権限のみ
- したがって `in tenancy` スコープのポリシーを追加できない

### API Key 認証で成功した理由

API Key で使用しているユーザーアカウントには、テナンシー管理者または Admins グループへの所属等により、テナンシーレベルの Usage API への読み取り権限が既に付与されていた。

## GenAI API が両方で動作した理由

GenAI Inference API は Usage API と異なり:

- **コンパートメントスコープ** で動作する（`compartment_id` パラメータを使用）
- Instance Principal に対して `Allow dynamic-group <dg> to use generative-ai-inference in compartment <name>` のようなコンパートメントレベルのポリシーで権限付与可能
- 本環境の OKE ノードにはこのポリシーが既に設定されていた

## 対応策の比較

| 対応策 | メリット | デメリット |
|---|---|---|
| **API Key 認証 (採用)** | 既存ユーザー権限をそのまま利用可能 | シークレット管理が必要、鍵のローテーション対応 |
| Instance Principal + テナンシーポリシー | シークレット不要、鍵管理不要 | テナンシー管理者権限が必要 |
| Resource Principal | ポリシーをより細かく制御可能 | 設定が複雑、OKE での対応が限定的 |

## 本プロジェクトでの実装

### K8s シークレット構成

```yaml
# OCI API Key をシークレットとして格納
kubectl create secret generic oci-api-key \
  --from-file=config=<oci-config> \
  --from-file=oci_api_key.pem=<private-key>
```

### Deployment でのマウント

```yaml
volumeMounts:
  - name: oci-config
    mountPath: /home/app/.oci
    readOnly: true
volumes:
  - name: oci-config
    secret:
      secretName: oci-api-key
```

### ConfigMap の認証設定

```yaml
OCI_AUTH_TYPE: "api_key"
OCI_CONFIG_FILE: "/home/app/.oci/config"
```

## 将来の改善案

1. **テナンシー管理者にポリシー追加を依頼**: Instance Principal に移行すれば、シークレット管理が不要になる
2. **OCI Vault でのシークレット管理**: API Key を OCI Vault に格納し、Kubernetes CSI ドライバ経由でマウント
3. **鍵のローテーション自動化**: API Key の有効期限管理と自動ローテーションの仕組みを構築

## 参考資料

- [OCI Instance Principal 認証](https://docs.oracle.com/ja-jp/iaas/Content/Identity/Tasks/callingservicesfrominstances.htm)
- [OCI Usage API - Required Policies](https://docs.oracle.com/ja-jp/iaas/Content/Billing/Concepts/usagereportsoverview.htm)
- [OKE でのワークロード認証](https://docs.oracle.com/ja-jp/iaas/Content/ContEng/Tasks/contenggrantingworkloadaccesstoresources.htm)
