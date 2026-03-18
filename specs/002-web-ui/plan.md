# 実装計画: Web UI フロントエンド

**Branch**: `002-web-ui` | **Date**: 2026-03-18 | **Spec**: [spec.md](./spec.md)
**Input**: `/specs/002-web-ui/spec.md` の機能仕様書

## 概要

既存の FastAPI バックエンド (POST /query, GET /health) に Web UI フロントエンドを組み込む。Alpine.js + htmx による軽量フロントエンドで、自然言語コストクエリの入力、コスト内訳テーブル、比較テーブル（色分け + トレンドサマリー）、日本語/英語切替を提供する。FastAPI の StaticFiles + Jinja2Templates でサーバーサイドレンダリングし、追加コンテナ不要で同一 Dockerfile からデプロイする。

## Technical Context

**Language/Version**: Python 3.13 (バックエンド), JavaScript ES2022+ (フロントエンド)
**Primary Dependencies**: FastAPI (既存), Jinja2 (テンプレート), Alpine.js 3.x (UI リアクティブ), htmx 2.x (サーバー連携)
**Storage**: N/A（ステートレス — ブラウザの localStorage を言語設定のみに使用）
**Testing**: pytest + FastAPI TestClient (バックエンド), Playwright (E2E)
**Target Platform**: モダンブラウザ (Chrome, Firefox, Safari, Edge 最新2バージョン)
**Project Type**: Web アプリケーション（既存 CLI + API への UI 追加）
**Performance Goals**: 初期表示 1 秒以内、クエリ結果レンダリング即座（バックエンド応答後）
**Constraints**: 静的ファイル合計 < 100KB (gzip)、ファイル 400 行以下、関数 40 行以下
**Scale/Scope**: シングルユーザー利用想定、テーブル最大 100 行程度

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### リサーチ前チェック

| 原則 | ステータス | 備考 |
|---|---|---|
| I. コード品質 | 合格 | Alpine.js コンポーネント + JS モジュール分割で 400 行制約に適合。Jinja2 テンプレートは部分テンプレートで分割 |
| II. テスト基準 | 合格 | Python 側 FastAPI テスト + E2E テスト (Playwright) で 80% カバレッジ達成可能。JS ロジック最小限 |
| III. UX 一貫性 | 合格 | Intl.NumberFormat で通貨フォーマット統一。i18n リソースで全テキスト管理。全状態（ローディング/空/エラー）を明示的にハンドリング |
| IV. パフォーマンス | 合格 | 静的ファイル < 100KB、初期表示 1 秒以内。テーブルレンダリングはバックエンド応答後即座 |
| 品質ゲート | 合格 | ruff (Python), ESLint 不要 (JS 最小限) |

### 設計後チェック

| 原則 | ステータス | 備考 |
|---|---|---|
| I. コード品質 | 合格 | 8 ファイル構成、各 400 行以下。テンプレート 5 分割。JS 3 モジュール |
| II. テスト基準 | 合格 | テンプレートレンダリングテスト + API テスト + E2E テスト |
| III. UX 一貫性 | 合格 | contracts/ui.md で全画面状態と色分けルールを定義 |
| IV. パフォーマンス | 合格 | Alpine.js 15KB + htmx 14KB + アプリ JS/CSS < 20KB = 合計 < 50KB gzip |

**ゲート結果**: 合格 — 違反なし。

## Project Structure

### Documentation (this feature)

```text
specs/002-web-ui/
├── plan.md              # このファイル
├── research.md          # フェーズ 0 出力 — 技術選定
├── data-model.md        # フェーズ 1 出力 — フロントエンドデータ構造
├── quickstart.md        # フェーズ 1 出力 — セットアップガイド
├── contracts/
│   └── ui.md            # UI コントラクト — 画面構成・色分け・レスポンシブ
└── tasks.md             # フェーズ 2 出力（/speckit.tasks で生成）
```

### Source Code (repository root)

```text
src/cost_analyzer/
├── api.py               # 既存 — GET / エンドポイント追加、StaticFiles マウント
├── static/
│   ├── css/
│   │   └── style.css    # メインスタイルシート
│   ├── js/
│   │   ├── app.js       # Alpine.js アプリ初期化・コンポーネント
│   │   ├── i18n.js      # 翻訳ヘルパー・言語辞書
│   │   └── table.js     # テーブルフォーマットユーティリティ
│   └── vendor/
│       ├── alpine.min.js
│       └── htmx.min.js
└── templates/
    ├── base.html         # ベースレイアウト
    ├── index.html        # メインページ
    └── partials/
        ├── breakdown.html
        ├── comparison.html
        ├── clarification.html
        └── error.html

tests/
├── unit/
│   └── test_ui_routes.py     # GET / エンドポイントのテスト
├── integration/
│   └── test_ui_rendering.py  # テンプレートレンダリングテスト
└── e2e/
    └── test_ui_e2e.py        # Playwright E2E テスト
```

**Structure Decision**: 既存の `src/cost_analyzer/` に `static/` と `templates/` を追加。FastAPI の StaticFiles + Jinja2Templates で配信。既存のバックエンドコードへの変更は `api.py` への GET / ルートと静的ファイルマウントの追加のみ。テストは既存の `tests/` ディレクトリに追加。

## Complexity Tracking

違反なし。
