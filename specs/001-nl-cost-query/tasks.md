# タスク: 自然言語 OCI コストクエリ

**入力**: `/specs/001-nl-cost-query/` の設計ドキュメント
**前提条件**: plan.md (必須), spec.md (必須), research.md, data-model.md, contracts/

**テスト**: 憲章 II に基づき、ユニットテスト（80% カバレッジ、コスト集計パスは 95%）と統合テストを含みます。

**構成**: タスクはユーザーストーリーごとにグループ化され、各ストーリーの独立した実装とテストを可能にします。

## フォーマット: `[ID] [P?] [Story] 説明`

- **[P]**: 並列実行可能（異なるファイル、依存関係なし）
- **[Story]**: このタスクが属するユーザーストーリー（例: US1, US2, US3）
- 正確なファイルパスを説明に含める

---

## フェーズ 1: セットアップ（共通インフラストラクチャ）

**目的**: プロジェクト初期化、依存関係管理、基本構造

- [X] T001 Python 3.13 プロジェクトを uv で初期化し、pyproject.toml に依存関係を作成: typer, fastapi, uvicorn, rich, oci, pydantic, pydantic-settings, dateparser, python-dateutil; 開発依存関係: pytest, pytest-cov, pytest-asyncio
- [X] T002 plan.md に基づきプロジェクトディレクトリ構造を作成: src/cost_analyzer/, tests/unit/, tests/integration/, k8s/
- [X] T003 [P] src/cost_analyzer/__init__.py をパッケージバージョン付きで作成
- [X] T004 [P] src/cost_analyzer/__main__.py をエントリーポイントとして作成 (`python -m cost_analyzer`)
- [X] T005 [P] pyproject.toml で ruff のリンティングとフォーマットを設定（行長、Python 3.13 ターゲット、インポートソート）; pytest の設定も追加（カバレッジ閾値 80%、tests/ ディレクトリ）
- [X] T006 [P] research.md の推奨に基づきマルチステージビルドの Dockerfile を作成 (python:3.13-slim + uv)
- [X] T007 [P] tests/conftest.py に共有フィクスチャを作成: サンプル CostQuery, CostLineItem, CostBreakdown のファクトリ関数、モック OCI レスポンス用フィクスチャ

---

## フェーズ 2: 基盤（ブロッキング前提条件）

**目的**: いずれのユーザーストーリーの実装前にも完了しなければならないコアインフラストラクチャ

**⚠️ 重要**: このフェーズが完了するまでユーザーストーリーの作業は開始できません

- [X] T008 src/cost_analyzer/config.py に pydantic-settings BaseSettings を使用した設定管理を実装: OCI_CONFIG_FILE, OCI_CONFIG_PROFILE, OCI_AUTH_TYPE (api_key | instance_principal), OCI_TENANCY_ID, OCI_COMPARTMENT_ID, OCI_GENAI_ENDPOINT (デフォルト: https://inference.generativeai.ap-osaka-1.oci.oraclecloud.com), OCI_GENAI_MODEL (デフォルト: google/gemini-2.5-flash), LOG_LEVEL
- [X] T009 [P] src/cost_analyzer/models.py に Pydantic モデルを実装: QueryType 列挙型, CostQuery, CostLineItem, ServiceCost, CostBreakdown, ServiceDelta, CostComparison, TrendSummary, ErrorType 列挙型, ErrorResponse — data-model.md のエンティティ定義とバリデーションルールに準拠
- [X] T010 [P] tests/unit/test_models.py に Pydantic モデルのユニットテストを作成: バリデーションルールの検証（start_date < end_date、COMPARISON 時の comparison_dates 必須、needs_clarification 時の clarification_message 必須、percentage 範囲 0-100）、正常系・異常系の両方をカバー
- [X] T011 [P] src/cost_analyzer/oci_client.py に OCI クライアントラッパーを実装: 認証方法の自動検出 (api_key vs instance_principal) で共通の config/signer を作成、UsageapiClient の作成、group_by=["service", "currency"] と query_type="COST" で request_summarized_usages を呼び出す request_cost_data() の実装、list_call_get_all_results によるページネーション処理、UsageSummary レスポンスを CostLineItem モデルにマッピング; 同じ config/signer を使用して GenerativeAiInferenceClient も初期化（エンドポイントは OCI_GENAI_ENDPOINT）
- [X] T012 [P] src/cost_analyzer/parser.py に NL クエリパーサーを実装: oci.generative_ai_inference の GenerativeAiInferenceClient を使用し、GenericChatRequest + JsonSchemaResponseFormat で CostQuery JSON スキーマを構造化出力として Gemini 2.5 Flash に送信、OnDemandServingMode でモデル指定、システムプロンプトに現在の日付と detected_language を含める、temperature=0 に設定、CostQuery モデルまたは失敗時の ErrorResponse を返す
- [X] T013 [P] tests/unit/test_parser.py に NL パーサーのユニットテストを作成: GenerativeAiInferenceClient をモックし、日本語クエリ（「先月のサービス別コストを教えて」）と英語クエリ（「Show costs for February 2026」）のパーシング結果を検証、曖昧クエリでの needs_clarification=True の検証、パース不可クエリでの ErrorResponse 返却の検証
- [X] T014 src/cost_analyzer/config.py にエラー処理ユーティリティを実装（既存に追記）: LOG_LEVEL による構造化ログの設定、OCI API エラーの ErrorResponse へのマッピング（認証エラー → AUTH_ERROR、429/5xx → API_ERROR）

**チェックポイント**: 基盤準備完了 — ユーザーストーリーの実装を並列で開始可能

---

## フェーズ 3: ユーザーストーリー 1 — 期間別サービスコスト内訳 (優先度: P1) 🎯 MVP

**ゴール**: ユーザーが期間を含む自然言語クエリを入力すると、システムはコスト降順でソートされたサービス別コスト内訳テーブルを合計行付きで返す。

**独立テスト**: 「先月のサービス別コストを教えて」または「Show costs for February 2026」を発行し、OCI コンソールのデータと一致する正確なサービス別内訳テーブルが返されることを検証。

### ユーザーストーリー 1 のテスト

> **注意: テストを先に書き、実装前にフェイルすることを確認**

- [X] T015 [P] [US1] tests/unit/test_engine.py にコスト集約エンジンのユニットテストを作成: test_fetch_breakdown_sorts_by_amount_descending, test_fetch_breakdown_calculates_percentages_correctly, test_fetch_breakdown_includes_total_row, test_fetch_breakdown_with_empty_data_returns_no_data_error, test_fetch_breakdown_with_zero_usage_returns_zero — OCI クライアントをモックし、CostLineItem リストからの CostBreakdown 生成を検証（コスト集計パスのため 95% カバレッジ目標）
- [X] T016 [P] [US1] tests/unit/test_formatter.py に出力フォーマッターのユニットテストを作成: test_format_breakdown_renders_table_with_correct_columns, test_format_breakdown_formats_currency_consistently, test_format_breakdown_json_output_matches_contract, test_format_error_includes_actionable_guidance

### ユーザーストーリー 1 の実装

- [X] T017 [US1] src/cost_analyzer/engine.py にコスト集約エンジンを実装: CostQuery を受け取り、クエリの日付範囲でフィルタなしの oci_client.request_cost_data() を呼び出し、CostLineItem を金額降順ソートの ServiceCost アイテムを持つ CostBreakdown に集約し、割合と順位を計算し、合計行を追加する fetch_breakdown() 関数
- [X] T018 [US1] src/cost_analyzer/formatter.py に出力フォーマッターを実装: CostBreakdown を Rich Table としてレンダリングする format_breakdown() 関数（カラム: サービス、コスト、%）、憲章 III に準拠した一貫した通貨フォーマット、末尾に期間ラベル行; ErrorResponse のレンダリング用 format_error() も実装（実行可能なガイダンス付き）; output_format パラメータ (table, json, csv) をサポート; 2秒以上のレスポンス待ちには Rich スピナーを表示（憲章 IV 準拠）
- [X] T019 [US1] src/cost_analyzer/cli.py に CLI コマンドを実装: QUERY 引数と --format/--lang オプションを受け付ける main コマンドを持つ Typer アプリ、parser.parse_query() を呼び出し、needs_clarification を処理（確認メッセージを表示して終了）、engine.fetch_breakdown() を呼び出し、formatter.format_breakdown() を呼び出し、stdout に出力; エラーは formatter.format_error() で stderr に出力し、contracts/cli.md に準拠した適切な終了コードで処理
- [X] T020 [US1] src/cost_analyzer/engine.py にデータなし・曖昧クエリの処理を実装: OCI が期間に対して空の結果を返した場合、NO_DATA タイプの ErrorResponse を利用可能な日付範囲の提案付きで返す; CostQuery.needs_clarification が True の場合、提案されたオプション付きの clarification_message を返す
- [X] T021 [US1] src/cost_analyzer/parser.py にパース不可クエリのフォールバックを実装: Gemini が入力をコストクエリにマッピングできない場合、PARSE_ERROR タイプの ErrorResponse を検出された言語（contracts/cli.md の日本語または英語の例）の example_queries リスト付きで返す
- [X] T022 [US1] T015, T016 のテストを実行し全パスを確認、tests/unit/test_engine.py のコスト集計パスで 95% カバレッジを確認

**チェックポイント**: この時点で、ユーザーストーリー 1 が完全に機能する状態 — ユーザーは CLI 経由で任意の期間のサービス別コスト内訳を取得可能

---

## フェーズ 4: ユーザーストーリー 2 — コスト傾向比較 (優先度: P2)

**ゴール**: ユーザーが2期間のコスト比較を依頼すると、システムはサービスごとの差分、変化率、および自然言語傾向サマリーを返す。

**独立テスト**: 「先月と今月を比較して」または「Compare costs between January and February」を発行し、出力にサービスごとの差分、変化率、およびトップの増加/減少を強調する読みやすいサマリーが含まれることを検証。

### ユーザーストーリー 2 のテスト

- [X] T023 [P] [US2] tests/unit/test_engine.py に比較エンジンのユニットテストを追加: test_fetch_comparison_calculates_deltas_correctly, test_fetch_comparison_sorts_by_absolute_change, test_fetch_comparison_handles_new_service_in_current_period, test_fetch_comparison_handles_removed_service, test_generate_trend_summary_identifies_top_3_increases, test_generate_trend_summary_in_japanese, test_generate_trend_summary_in_english（コスト集計パスのため 95% カバレッジ目標）
- [X] T024 [P] [US2] tests/unit/test_formatter.py に比較フォーマッターのユニットテストを追加: test_format_comparison_renders_delta_columns, test_format_comparison_shows_positive_negative_signs, test_format_comparison_appends_trend_summary_panel

### ユーザーストーリー 2 の実装

- [X] T025 [US2] src/cost_analyzer/engine.py に比較エンジンを実装: 比較日付を持つ CostQuery を受け取り、両期間で fetch_breakdown() を呼び出し、ServiceDelta アイテム (absolute_change, percent_change) を計算し、absolute_change 降順でソートし、total_change と total_change_percent を計算し、CostComparison モデルを返す fetch_comparison() 関数を追加
- [X] T026 [US2] src/cost_analyzer/engine.py に傾向サマリー生成を実装: CostComparison と detected_language を受け取り、overall_direction を決定し、トップ3の増加と顕著な減少を特定し、検出された言語（日本語または英語）で summary_text を生成し、TrendSummary モデルを返す generate_trend_summary() 関数を追加
- [X] T027 [US2] src/cost_analyzer/formatter.py に比較フォーマッターを実装: CostComparison を contracts/cli.md に準拠した Rich Table としてレンダリングする format_comparison() 関数を追加（カラム: サービス、前期、当期、変化、%Δ）、テーブルの下に TrendSummary.summary_text を Rich Panel として追加
- [X] T028 [US2] src/cost_analyzer/cli.py に比較フローを統合: parse_query() の後、query_type で分岐 — COMPARISON の場合、engine.fetch_comparison() を呼び出し、次に formatter.format_comparison(); 一方の期間にデータがない場合の処理（利用可能な日付範囲のガイダンス付き ErrorResponse）
- [X] T029 [US2] T023, T024 のテストを実行し全パスを確認

**チェックポイント**: この時点で、ユーザーストーリー 1 と 2 の両方が独立して動作する状態

---

## フェーズ 5: ユーザーストーリー 3 — スコープ指定コストクエリ (優先度: P3)

**ゴール**: ユーザーがサービスタイプ、コンパートメント、またはタグフィルタでコストクエリを絞り込む。結果には一致するコスト項目のみが含まれる。

**独立テスト**: 「Compute の先月のコストは？」または「Show production compartment costs for last month」を発行し、指定されたサービス/コンパートメントのコストのみが結果に表示されることを検証。

### ユーザーストーリー 3 のテスト

- [X] T030 [P] [US3] tests/unit/test_engine.py にスコープ指定クエリのユニットテストを追加: test_fetch_breakdown_with_service_filter_passes_filter_to_client, test_fetch_breakdown_with_compartment_filter, test_scope_not_found_returns_suggestions

### ユーザーストーリー 3 の実装

- [X] T031 [US3] src/cost_analyzer/oci_client.py の OCI クライアントフィルタリングを拡張: CostQuery の service_filter と compartment_filter から oci.usage_api.models.Filter を Dimension エントリ付きで構築する filter パラメータを request_cost_data() に追加; 複数フィルタがある場合は operator="AND" を使用
- [X] T032 [US3] src/cost_analyzer/engine.py でスコープフィルタを接続: fetch_breakdown() と fetch_comparison() の両方で CostQuery.service_filter と compartment_filter を oci_client.request_cost_data() に渡す
- [X] T033 [US3] src/cost_analyzer/engine.py にスコープ未検出の処理を実装: フィルタリングされた結果が空だがフィルタなしの結果が存在する場合、NO_DATA タイプの ErrorResponse を返し、一致するスコープが見つからなかったメッセージと、OCI メタデータからの類似サービス名またはコンパートメント名の提案を含める（必要に応じて request_summarized_configurations を呼び出す）
- [X] T034 [US3] src/cost_analyzer/oci_client.py に利用可能なスコープの検出を追加: ユーザーが存在しないフィルタを指定した場合にスコープの提案を提供するため、UsageapiClient.request_summarized_configurations() を使用した get_available_services() と get_available_compartments() を実装
- [X] T035 [US3] T030 のテストを実行し全パスを確認

**チェックポイント**: すべてのユーザーストーリーが独立して機能する状態

---

## フェーズ 6: API & デプロイ

**目的**: Kubernetes デプロイ用の HTTP ラッパーと K8s マニフェスト

- [X] T036 [P] tests/integration/test_api.py に FastAPI エンドポイントの統合テストを作成: TestClient を使用し、POST /query の正常系（内訳・比較・確認レスポンス）と異常系（パースエラー、認証エラー）を検証、GET /health のレスポンス形式を検証
- [X] T037 [P] src/cost_analyzer/api.py に FastAPI アプリケーションを実装: contracts/api.md に準拠した {query, format, lang} JSON ボディを受け付ける POST /query エンドポイント、CLI と同じ parser→engine→formatter パイプラインを呼び出し、内訳/比較/確認/エラーの各ケースで JSON レスポンスを返す; OCI 認証の接続性をチェックする GET /health エンドポイント（Usage API と GenAI Service の両方を確認）
- [X] T038 [P] k8s/ に Kubernetes マニフェストを作成: deployment.yaml (1レプリカ、リソースリミット 512Mi/500m、/health の liveness/readiness プローブ、configmap からの環境変数)、service.yaml (ClusterIP ポート 8080)、configmap.yaml (OCI_AUTH_TYPE=instance_principal, OCI_GENAI_ENDPOINT, OCI_GENAI_MODEL, LOG_LEVEL=INFO)
- [X] T039 src/cost_analyzer/cli.py に serve コマンドを接続: FastAPI アプリを uvicorn で起動する --host と --port オプション付きの `serve` サブコマンドを追加
- [X] T040 T036 のテストを実行し全パスを確認

**チェックポイント**: アプリケーションを OKE に Kubernetes サービスとしてデプロイ可能

---

## フェーズ 7: ポリッシュ & 横断的関心事

**目的**: 複数のユーザーストーリーに影響する改善

- [X] T041 [P] src/cost_analyzer/ の全モジュールに Python logging の JSON フォーマットを使用した構造化ログを追加、クエリパーシング結果、OCI API 呼び出し時間、エラー詳細をログに記録
- [X] T042 [P] tests/integration/test_oci_client.py に OCI クライアントの統合テストを作成: 実 OCI 認証情報を使用して request_cost_data() の呼び出しを検証（CI 環境ではスキップ可能なマーカー付き）
- [X] T043 [P] quickstart.md をエンドツーエンドで検証: すべてのセットアップ手順を実行し、すべてのサンプルクエリを実行し、出力がコントラクトと一致することを確認
- [X] T044 全テストスイートを実行し、カバレッジレポートを確認: 全体 80% 以上、engine.py のコスト集計パスで 95% 以上を達成していること
- [X] T045 ruff リンターを実行し、src/ と tests/ 全体のすべての警告を修正

---

## 依存関係 & 実行順序

### フェーズ依存関係

- **セットアップ (フェーズ 1)**: 依存関係なし — 即座に開始可能
- **基盤 (フェーズ 2)**: セットアップ完了に依存 — すべてのユーザーストーリーをブロック
- **ユーザーストーリー 1 (フェーズ 3)**: 基盤 (フェーズ 2) に依存
- **ユーザーストーリー 2 (フェーズ 4)**: US1 (フェーズ 3) に依存。US1 の engine.py をベースに新しい関数を追加
- **ユーザーストーリー 3 (フェーズ 5)**: US1 (フェーズ 3) に依存。US1 の oci_client.py と engine.py を拡張
- **API & デプロイ (フェーズ 6)**: 少なくとも US1 (フェーズ 3) の完了に依存
- **ポリッシュ (フェーズ 7)**: すべての希望するフェーズの完了に依存

### ユーザーストーリー依存関係

- **ユーザーストーリー 1 (P1)**: 基盤 (フェーズ 2) 完了後に開始可能 — 他のストーリーへの依存なし
- **ユーザーストーリー 2 (P2)**: US1 (フェーズ 3) 完了後に開始可能 — US1 の engine.fetch_breakdown() に依存
- **ユーザーストーリー 3 (P3)**: US1 (フェーズ 3) 完了後に開始可能 — US1 の oci_client.request_cost_data() を拡張

### 各ユーザーストーリー内の順序

- テストを先に書き、フェイルを確認
- モデルの前にサービス
- サービスの前にエンドポイント/CLI 統合
- エラー処理のエッジケースの前にコア実装
- テストのパスを確認してからストーリーを完了
- 次の優先度に移る前にストーリーを完了

### 並列実行の機会

- T003, T004, T005, T006, T007 はすべて並列実行可能（フェーズ 1）
- T009, T010, T011, T012, T013 はすべて並列実行可能（フェーズ 2 — 異なるファイル）
- T015, T016 は並列実行可能（フェーズ 3 テスト — 異なるファイル）
- T023, T024 は並列実行可能（フェーズ 4 テスト — 異なるファイル）
- T036, T037, T038 は並列実行可能（フェーズ 6 — 異なるファイル）
- T041, T042, T043 は並列実行可能（フェーズ 7）

---

## 並列実行例: フェーズ 2（基盤）

```bash
# すべての独立した基盤タスクを同時に起動:
Task: "src/cost_analyzer/models.py に Pydantic モデルを実装"
Task: "tests/unit/test_models.py に Pydantic モデルのテストを作成"
Task: "src/cost_analyzer/oci_client.py に OCI クライアントラッパーを実装"
Task: "src/cost_analyzer/parser.py に NL クエリパーサーを実装"
Task: "tests/unit/test_parser.py に NL パーサーのテストを作成"
```

## 並列実行例: フェーズ 3 テスト（US1）

```bash
# 実装前にテストを先行作成:
Task: "tests/unit/test_engine.py にコスト集約のテストを作成"
Task: "tests/unit/test_formatter.py にフォーマッターのテストを作成"
```

---

## 実装戦略

### MVP ファースト（ユーザーストーリー 1 のみ）

1. フェーズ 1: セットアップを完了
2. フェーズ 2: 基盤を完了（重要 — すべてのストーリーをブロック）
3. フェーズ 3: ユーザーストーリー 1 を完了（テスト先行）
4. **停止して検証**: US1 を「先月のサービス別コストを教えて」で独立テスト + 全テストパス確認
5. 準備ができればデプロイ/デモ

### インクリメンタルデリバリー

1. セットアップ + 基盤を完了 → 基盤準備完了
2. ユーザーストーリー 1 を追加 → テストパス確認 → デプロイ/デモ (MVP!)
3. ユーザーストーリー 2 を追加 → テストパス確認 → デプロイ/デモ
4. ユーザーストーリー 3 を追加 → テストパス確認 → デプロイ/デモ
5. API & デプロイを追加 → OKE にデプロイ
6. 各ストーリーは前のストーリーを壊さずに価値を追加

### コンテナレジストリに関する注記

OKE へのデプロイ前にコンテナレジストリ (OCIR) を作成する必要があります。ユーザーは必要な場面で通知をリクエストしています — これはフェーズ 6 (T038) で Docker イメージのビルドとプッシュ時に関係します。

---

## 注意事項

- [P] タスク = 異なるファイル、依存関係なし
- [Story] ラベルはタスクを特定のユーザーストーリーにマッピング（トレーサビリティ用）
- 各ユーザーストーリーは独立して完了・テスト可能であるべき
- テストを先に書き、実装前にフェイルすることを確認（テスト先行）
- 各タスクまたは論理グループの完了後にコミット
- 任意のチェックポイントで停止してストーリーを独立検証
- 統合テストの実行前に OCI 認証情報の設定が必要
- カバレッジ目標: 全体 80%、コスト集計パス (engine.py) 95%
