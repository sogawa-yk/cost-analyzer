# Feature Specification: A2A エージェント Kubernetes サービスディスカバリ

**Feature Branch**: `004-a2a-k8s-discovery`
**Created**: 2026-03-19
**Status**: Draft
**Input**: User description: "Kubernetes クラスタ上で A2A 対応エージェントを自動発見可能にするためのラベル・アノテーション規約を定義する。reporter をはじめとする A2A クライアントが設定なしでクラスタ内の全エージェントを自動検出し、利用できるようにする。共通の Kubernetes Secret による API キー認証を含む。"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Kubernetes クラスタ内の A2A エージェントを自動検出する (Priority: P1)

reporter（A2A クライアント）が、Kubernetes クラスタ内にデプロイされた A2A 対応エージェントを設定ファイルなしで自動検出する。reporter は `a2a.protocol/enabled=true` ラベルを持つ Service を全 namespace から検索し、各 Service の Agent Card を取得してスキル一覧を把握し、タスクに応じて適切なエージェントを選択・呼び出す。

**Why this priority**: エージェント間連携の基盤。手動設定が不要になることで、新しいエージェントの追加がデプロイだけで完結し、運用コストが大幅に削減される。

**Independent Test**: A2A 対応エージェントをデプロイし、reporter がラベルベースの検索で自動検出してスキル一覧を取得できることを確認する。

**Acceptance Scenarios**:

1. **Given** A2A ラベル付き Service がクラスタ内に存在する, **When** reporter がディスカバリを実行する, **Then** `a2a.protocol/enabled=true` ラベルを持つ全 Service が検出される
2. **Given** 検出された Service, **When** reporter が Agent Card エンドポイントにアクセスする, **Then** A2A プロトコル準拠の Agent Card（name, description, skills[]）が取得される
3. **Given** Agent Card を取得済みの reporter, **When** タスクに適合するスキルを持つエージェントが存在する, **Then** reporter はそのエージェントに対して `message/send` でタスクを送信できる
4. **Given** A2A ラベルのない Service がクラスタ内に存在する, **When** reporter がディスカバリを実行する, **Then** ラベルのない Service は検出結果に含まれない

---

### User Story 2 - 共通 API キーによるエージェント間認証 (Priority: P2)

全 A2A エージェントが共通の Kubernetes Secret `mini-a2a-auth` に格納された API キーで認証する。エージェントは `x-api-key` ヘッダーで API キーを受け取り検証する。reporter は Secret から自動で API キーを取得してリクエストに付与する。

**Why this priority**: 認証なしではセキュリティリスクが高いが、ディスカバリ自体が動作しなければ認証は無意味なため P2。

**Independent Test**: API キーが設定されたエージェントに対して、正しい/不正な API キーでリクエストを送り、認証の成否を確認する。

**Acceptance Scenarios**:

1. **Given** エージェントが `mini-a2a-auth` Secret の API キーで起動している, **When** reporter が正しい API キーを `x-api-key` ヘッダーに付与してリクエストする, **Then** リクエストが成功する
2. **Given** エージェントが API キー認証を有効化している, **When** 不正な API キーまたは API キーなしでリクエストする, **Then** 401 Unauthorized が返される
3. **Given** reporter が起動する, **When** `--api-key` オプション、`REPORTER_API_KEY` 環境変数、Kubernetes Secret のいずれかが利用可能, **Then** 優先順位に従って API キーを取得し、全リクエストに付与する

---

### User Story 3 - 既存エージェントの移行とカスタム設定 (Priority: P3)

既にデプロイ済みの A2A エージェント（例: cost-analyzer）に Service ラベルを追加するだけで本規約に対応させる。Agent Card パスがデフォルトと異なる場合はアノテーションでカスタムパスを指定できる。

**Why this priority**: 新規デプロイが先に動作すれば、既存エージェントの移行は段階的に進められる。

**Independent Test**: 既存の cost-analyzer Service にラベルを追加し、reporter から自動検出・呼び出しができることを確認する。

**Acceptance Scenarios**:

1. **Given** ラベルなしの既存 A2A エージェント Service, **When** `a2a.protocol/enabled=true` と `a2a.protocol/version=0.3` ラベルを追加する, **Then** reporter のディスカバリ結果に含まれるようになる
2. **Given** Agent Card パスが `/.well-known/agent-card.json` でないエージェント, **When** `a2a.protocol/agent-card-path` アノテーションでカスタムパスを指定する, **Then** reporter はアノテーションのパスから Agent Card を取得する
3. **Given** Service ポートに `a2a` という名前が付いていない, **When** reporter がディスカバリを実行する, **Then** Service の最初のポートを使用してアクセスする

---

### Edge Cases

- A2A ラベルは付いているが Agent Card エンドポイントが応答しない場合: 該当エージェントをスキップし、利用可能なエージェントのみを使用する
- 複数 namespace に同名の Service が存在する場合: namespace を含む FQDN（`{name}.{namespace}.svc.cluster.local`）で区別する
- reporter に RBAC 権限（全 namespace の Service list）がない場合: 権限不足を明示するエラーメッセージを返す
- Secret `mini-a2a-auth` が存在しない場合: reporter は CLI オプションまたは環境変数からの API キー取得にフォールバックし、いずれもなければ認証なしで接続を試みる
- エージェントが一時的にダウンしている場合: Agent Card 取得のタイムアウト後にスキップし、後続のディスカバリで再検出する

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A2A 対応エージェントの Kubernetes Service は `a2a.protocol/enabled: "true"` ラベルを付与しなければならない
- **FR-002**: A2A 対応エージェントの Kubernetes Service は `a2a.protocol/version` ラベルで A2A プロトコルバージョン（メジャー.マイナー）を明示しなければならない
- **FR-003**: reporter は `a2a.protocol/enabled=true` ラベルセレクタで全 namespace の Service を検索しなければならない
- **FR-004**: reporter は検出した各 Service に対して Agent Card エンドポイントに HTTP GET リクエストを送信し、A2A プロトコル準拠の Agent Card を取得しなければならない
- **FR-005**: Agent Card のデフォルトパスは `/.well-known/agent-card.json` とし、`a2a.protocol/agent-card-path` アノテーションで上書き可能でなければならない
- **FR-006**: reporter は Service の `a2a` 名前付きポートを優先的に使用し、存在しない場合は最初のポートを使用しなければならない
- **FR-007**: reporter は `http://{service-name}.{namespace}.svc.cluster.local:{port}` 形式で各エージェントの URL を構築しなければならない
- **FR-008**: 全 A2A エージェントは共通の Kubernetes Secret `mini-a2a-auth` に格納された API キーで認証しなければならない
- **FR-009**: エージェントは `x-api-key` ヘッダーで API キーを受け取り、不正または未指定の場合は 401 Unauthorized を返さなければならない
- **FR-010**: reporter は `--api-key` CLI オプション > `REPORTER_API_KEY` 環境変数 > Kubernetes Secret `mini-a2a-auth` の優先順位で API キーを取得しなければならない
- **FR-011**: reporter は取得した API キーを `x-api-key` ヘッダーとして全 A2A リクエストに付与しなければならない
- **FR-012**: Agent Card 取得に失敗したエージェントはスキップし、利用可能なエージェントのみでディスカバリ結果を構成しなければならない
- **FR-013**: エージェントは A2A プロトコル準拠の Agent Card（name, description, skills[], protocolVersion）を返さなければならない
- **FR-014**: エージェントのレスポンスは DataPart に構造化データを含めなければならない（テキストのみは非推奨）
- **FR-015**: エージェントのエラーレスポンスは FAILED 状態 + 構造化エラーメッセージ（error_type, message, guidance）を返さなければならない

### Key Entities

- **Service ラベル**: Kubernetes Service に付与するメタデータ。`a2a.protocol/enabled` と `a2a.protocol/version` で構成され、ディスカバリの検索条件となる
- **Service アノテーション**: Kubernetes Service に付与する補足設定。`a2a.protocol/agent-card-path`（Agent Card パス）、`a2a.protocol/transport`（トランスポート種別）、`a2a.protocol/description`（エージェント説明）で構成される
- **Agent Card**: エージェントが自身の能力を外部に公開するための JSON メタデータ。name, description, url, version, protocolVersion, capabilities, skills[] で構成される
- **mini-a2a-auth Secret**: 全エージェントが共有する Kubernetes Secret。`api-key` キーに API キーを格納する
- **ディスカバリ結果**: reporter が構築するエージェント一覧。Service 名、namespace、URL、Agent Card（スキル一覧含む）で構成される

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 新しい A2A エージェントをデプロイしてから reporter がスキル一覧を認識するまで、追加の設定ファイル変更なしで完了できる
- **SC-002**: クラスタ内の全 A2A 対応エージェント（10 エージェント以上を想定）を 10 秒以内にディスカバリできる
- **SC-003**: API キー認証により、正しいキーを持たないリクエストの 100% が拒否される
- **SC-004**: 一部のエージェントがダウンしている場合でも、利用可能なエージェントのディスカバリが正常に完了する
- **SC-005**: 既存の A2A エージェントの移行が、ラベル追加のみ（コード変更なし）で完了できる
- **SC-006**: reporter の API キー取得が 3 段階のフォールバック（CLI > 環境変数 > Secret）で確実に動作する

## Clarifications

### Session 2026-03-19

- Q: エージェント間通信プロトコル → A: A2A（Agent-to-Agent Protocol）v0.3.0、JSON-RPC 2.0 トランスポート
- Q: 認証方式 → A: 共通 Kubernetes Secret `mini-a2a-auth` に格納された API キーを `x-api-key` ヘッダーで送受信
- Q: ディスカバリ対象の namespace → A: 全 namespace（RBAC で `list services` 権限が必要）
- Q: Agent Card のデフォルトパス → A: `/.well-known/agent-card.json`（アノテーションで上書き可能）
- Q: Service ポート選択 → A: `a2a` 名前付きポート優先、なければ最初のポート
- Q: 認証ヘッダー名 → A: `x-api-key`（cost-analyzer 既存実装の `Authorization: Bearer` / `X-API-Key` に加え、クラスタ内統一規約として）

## Assumptions

- ディスカバリ対象は同一 Kubernetes クラスタ内の Service に限定される。クラスタ間のディスカバリは対象外
- reporter は Kubernetes クラスタ内で実行され、Service API へのアクセス権（RBAC: list services across namespaces）を持つ
- 全 A2A エージェントは同一の API キーを共有する（エージェントごとの個別キーは対象外）
- Agent Card は静的であり、エージェント起動後に内容が変化しない前提で reporter はキャッシュしてよい
- A2A プロトコルバージョンは 0.3 系を対象とする
- Service の DNS 解決は Kubernetes 標準の `{name}.{namespace}.svc.cluster.local` に従う

## Scope Boundaries

### In Scope

- Kubernetes Service ラベル・アノテーション規約の定義
- reporter によるラベルベースのサービスディスカバリ
- 共通 Kubernetes Secret による API キー認証
- Agent Card 取得とスキル一覧の構築
- 既存エージェントの移行手順
- エージェント開発者向けチェックリスト

### Out of Scope

- クラスタ間のエージェントディスカバリ
- エージェントごとの個別 API キー管理
- mTLS やサービスメッシュベースの認証
- エージェントの自動スケーリングやヘルスベースのルーティング
- reporter 自体の実装（本 spec はディスカバリ規約の定義に焦点）
- Agent Card の動的更新やプッシュ通知
