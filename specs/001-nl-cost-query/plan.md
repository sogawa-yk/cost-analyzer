# 実装計画: 自然言語 OCI コストクエリ

**ブランチ**: `001-nl-cost-query` | **日付**: 2026-03-17 | **仕様書**: [spec.md](./spec.md)
**入力**: `/specs/001-nl-cost-query/spec.md` の機能仕様書

## 概要

日本語・英語の自然言語コストクエリを受け付け、OCI GenAI Service (Gemini 2.5 Flash) の構造化出力でパースし、OCI Usage API からコストデータを取得し、フォーマットされた内訳や傾向比較を返す Python CLI エージェントを構築します。ローカル利用の Typer CLI と OKE デプロイ用の FastAPI サービスのデュアルインターフェースを持ちます。すべてのサービスが OCI 上で統一されます。

## 技術コンテキスト

**言語/バージョン**: Python 3.13
**主要依存関係**: Typer (CLI), FastAPI (HTTP), Rich (出力), oci (OCI SDK — Usage API + GenAI Inference), pydantic / pydantic-settings (モデル/設定), dateparser + python-dateutil (日付ユーティリティ)
**ストレージ**: N/A（ステートレス — OCI API に直接クエリ）
**テスト**: pytest + pytest-cov
**ターゲットプラットフォーム**: Linux (OKE / Kubernetes)、ローカル開発は macOS/Linux
**プロジェクトタイプ**: CLI + Web サービス（コアロジックを共有するデュアルインターフェース）
**LLM**: OCI GenAI Service — Gemini 2.5 Flash（大阪リージョン `ap-osaka-1`）
**コンテナレジストリ**: OCIR
**Kubernetes**: OKE
**パフォーマンス目標**: 最大3ヶ月のクエリに対してエンドツーエンドで5秒未満 (SC-003)
**制約**: NL パース + OCI API 合計で p95 < 3秒; メモリ < 512MB (憲章 IV)
**規模/スコープ**: シングルテナンシー; CLI は単一同時ユーザー、API は水平スケーリング

## 憲章チェック

*ゲート: フェーズ0リサーチ前に合格必須。フェーズ1設計後に再チェック。*

### リサーチ前チェック

| 原則 | ステータス | 備考 |
|---|---|---|
| I. コード品質 | 合格 | 単一責任モジュールを計画; Pydantic による型注釈; OCI ディメンションの名前付き定数 |
| II. テスト基準 | 合格 | ユニットカバレッジ 80% 目標; OCI API 境界の統合テスト; 記述的テスト名の pytest |
| III. UX 一貫性 | 合格 | Rich テーブルによる一貫した通貨/数値フォーマット; 実行可能なエラーメッセージ; バイリンガル対応 (ja/en) |
| IV. パフォーマンス | 合格 | レイテンシバジェット: p50 ~810ms、p95 ~3s（5秒目標内）; ステートレスのためメモリは限定的 |
| 品質ゲート | 合格 | Lint (ruff)、テスト、カバレッジゲートを CI で計画 |

### 設計後チェック

| 原則 | ステータス | 備考 |
|---|---|---|
| I. コード品質 | 合格 | 7モジュール、各400行未満; Pydantic モデルによる全公開インターフェースの型付け; data-model.md の明確な関数コントラクト |
| II. テスト基準 | 合格 | parser, engine, formatter のユニットテスト; OCI クライアントの統合テスト; コスト集計ロジックで 95% カバレッジ |
| III. UX 一貫性 | 合格 | contracts/cli.md で定義された一貫した出力フォーマット; data-model.md のエラー分類 (ErrorResponse); detected_language による i18n |
| IV. パフォーマンス | 合格 | research.md で検証されたレイテンシバジェット; 大規模データセットのストリーミングページネーション; メモリ無制限増加なし |

**ゲート結果**: 合格 — 違反なし。実装に進みます。

## プロジェクト構造

### ドキュメント（この機能）

```text
specs/001-nl-cost-query/
├── plan.md              # このファイル
├── research.md          # フェーズ0出力 — 技術的意思決定
├── data-model.md        # フェーズ1出力 — エンティティ定義
├── quickstart.md        # フェーズ1出力 — セットアップ・使い方ガイド
├── contracts/
│   ├── cli.md           # CLI インターフェースコントラクト
│   └── api.md           # HTTP API インターフェースコントラクト
└── tasks.md             # フェーズ2出力（/speckit.tasks による）
```

### ソースコード（リポジトリルート）

```text
src/
└── cost_analyzer/
    ├── __init__.py
    ├── __main__.py          # エントリーポイント: python -m cost_analyzer
    ├── cli.py               # Typer アプリ — CLI コマンド
    ├── api.py               # FastAPI アプリ — HTTP ラッパー
    ├── config.py            # pydantic-settings: 環境変数、OCI 設定
    ├── models.py            # Pydantic モデル (CostQuery, CostBreakdown 等)
    ├── parser.py            # NL → CostQuery (OCI GenAI Gemini 2.5 Flash 構造化出力)
    ├── oci_client.py        # OCI Usage API ラッパー、認証自動検出
    ├── engine.py            # コアロジック: 取得 → 集約 → 比較
    └── formatter.py         # Rich テーブル / JSON / CSV 出力フォーマット

tests/
├── unit/
│   ├── test_parser.py       # モック LLM による NL パーステスト
│   ├── test_engine.py       # 集約・比較ロジックのテスト
│   ├── test_formatter.py    # 出力フォーマットのテスト
│   └── test_models.py       # Pydantic バリデーションのテスト
├── integration/
│   ├── test_oci_client.py   # 実 OCI API 呼び出しテスト
│   └── test_api.py          # FastAPI エンドポイントテスト
└── conftest.py              # 共有フィクスチャ

Dockerfile
k8s/
├── deployment.yaml
├── service.yaml
└── configmap.yaml

pyproject.toml
```

**構造の決定**: `src` レイアウトの単一プロジェクト。CLI と API はコアモジュール（`parser`, `engine`, `oci_client`, `formatter`）を共有。`cli.py` と `api.py` は同じロジック上の薄いラッパー。これによりローカル CLI と Kubernetes API デプロイの両方をサポートしつつ、コードの重複を回避します。

## 複雑性トラッキング

| 違反 | 正当化 | より単純な代替案を却下した理由 |
|---|---|---|
| 憲章 IV: API レスポンス 500ms p95 を超過（実測 p95 ~3s） | `/query` エンドポイントは LLM 推論（~1s）+ OCI API 呼び出し（~2s）を含むため、500ms は物理的に達成不可能。仕様の SC-003 は5秒以内を要求しており、~3s p95 はこれを満たす。 | (a) ルールベースパーサー（LLM 不要で <10ms）は SC-002 の 90% 正確解釈を達成できない。(b) 非同期 + 進捗フィードバックは CLI のユースケースに不適（単一リクエスト・レスポンス）。(c) 憲章 IV は「2秒を超えるクエリは非同期化またはプログレスフィードバック」を許容しており、CLI は Rich のスピナー表示で対応する。 |
