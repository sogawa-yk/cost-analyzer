# リサーチ: Web UI フロントエンド技術選定

**日付**: 2026-03-18
**ブランチ**: `002-web-ui`
**仕様書**: `specs/002-web-ui/spec.md`

---

## 1. フロントエンド技術アプローチ比較

### 比較対象

| # | アプローチ | 代表的技術 |
|---|---|---|
| A | バニラ HTML/CSS/JS | ES2022+, CSS Grid/Flexbox, Fetch API |
| B | 軽量フレームワーク | Alpine.js + htmx (または Petite Vue) |
| C | SPA フレームワーク | React + Vite (または Vue 3 + Vite) |

### 比較軸ごとの評価

#### 1.1 ビルド複雑性（Dockerfile への影響）

| アプローチ | 評価 | 詳細 |
|---|---|---|
| A: バニラ | **◎ 最良** | ビルドステップ不要。`src/cost_analyzer/static/` に HTML/CSS/JS を配置し、FastAPI の `StaticFiles` でマウントするだけ。既存の Dockerfile にファイルコピー1行追加のみ。 |
| B: Alpine.js + htmx | **◎ 良好** | CDN 読み込みなら A と同等。ローカルバンドルする場合でも `<script>` タグで読み込むだけ。ビルドステップ不要。 |
| C: React/Vue SPA | **△ 要注意** | Node.js ビルドステージが Dockerfile に必要。マルチステージビルドが3段階になる（Node ビルド → Python ビルド → ランタイム）。CI/CD パイプラインにも Node.js が追加。イメージビルド時間が 30-60 秒増加。 |

**現在の Dockerfile**: Python 3.13-slim のマルチステージビルド（2段階）。Node.js は未使用。

#### 1.2 テスト容易性（憲章: 80% テストカバレッジ、ファイル400行以下、関数40行以下）

| アプローチ | 評価 | 詳細 |
|---|---|---|
| A: バニラ | **○ 良好** | JS のユニットテストは可能だが、DOM 操作のテストには jsdom 等が必要。Python 側は FastAPI の TestClient + httpx でエンドポイントテスト。フロントエンド単体のカバレッジ計測にはツール追加（jest/vitest）が要る。ファイルサイズ制約は手動で管理。 |
| B: Alpine.js + htmx | **○ 良好** | htmx はサーバーサイドレンダリング中心のため、Python 側の Jinja2 テンプレートテストと FastAPI エンドポイントテストでカバレッジの大部分を確保可能。フロントエンド JS は最小限。ただし htmx の動作テストには E2E テスト（Playwright 等）が望ましい。 |
| C: React/Vue SPA | **◎ 最良** | コンポーネント単位テスト（React Testing Library / Vue Test Utils）が充実。カバレッジ計測ツールが成熟（vitest + c8）。ただし Python + JS 両方のテスト基盤が必要で、CI 設定が複雑化。 |

**注意**: 憲章の「80% テストカバレッジ」が Python コードのみを対象とするなら、A/B アプローチが有利（フロントエンド JS が最小限のため、Python 側のカバレッジだけで要件を満たせる）。

#### 1.3 i18n（日本語/英語）対応の容易さ

| アプローチ | 評価 | 詳細 |
|---|---|---|
| A: バニラ | **○ 良好** | JSON 翻訳ファイル + JS の簡易 i18n ヘルパー（20-30行）で実装可能。`data-i18n` 属性方式やシンプルな `t("key")` 関数で十分。外部ライブラリ不要。 |
| B: Alpine.js + htmx | **○ 良好** | Alpine.js の `$store` に翻訳辞書を保持し、`x-text="$store.i18n.t('key')"` で参照。サーバーサイドで Jinja2 テンプレート内の翻訳も可能（Accept-Language ヘッダーに基づく）。 |
| C: React/Vue SPA | **◎ 最良** | react-i18next / vue-i18n 等の成熟したライブラリが利用可能。複数形、補間、名前空間等の高度な機能。ただし本プロジェクトでは2言語・UIラベルのみのため、オーバースペック。 |

**本プロジェクトの i18n 要件**: UIラベル、プレースホルダー、エラーメッセージの2言語切替のみ。バックエンドからの応答テキストは `lang` パラメータで制御済み。高度な i18n 機能は不要。

#### 1.4 テーブル表示の品質

| アプローチ | 評価 | 詳細 |
|---|---|---|
| A: バニラ | **○ 良好** | HTML `<table>` + CSS でソート・レスポンシブ対応可能。CSS `position: sticky` でヘッダー固定。`Intl.NumberFormat` で通貨フォーマット。水平スクロールは `overflow-x: auto` で対応。カラムソートは JS 50行程度。 |
| B: Alpine.js + htmx | **◎ 良好** | Alpine.js でソート状態管理、htmx でサーバーサイドソートも可能。DOM 操作が Alpine のリアクティブバインディングで簡潔に記述可能。`x-for` でテーブル行を動的生成。 |
| C: React/Vue SPA | **◎ 最良** | TanStack Table 等の高機能テーブルライブラリが利用可能。仮想スクロール、カラムリサイズ、フィルタリング等。ただし本プロジェクトのテーブルは最大数十行程度で、これらの高度な機能は不要。 |

**本プロジェクトのテーブル要件**: コスト内訳（最大20-30行）と比較テーブル（同程度）。金額の通貨フォーマット、割合表示、変化額の色分け。仮想スクロールやカラムリサイズは不要。

#### 1.5 開発速度

| アプローチ | 評価 | 詳細 |
|---|---|---|
| A: バニラ | **○ 良好** | セットアップ即座。ただし DOM 操作・状態管理のボイラープレートが多い。ファイル400行制約内での構造化には工夫が必要。 |
| B: Alpine.js + htmx | **◎ 最良** | セットアップ即座（CDN スクリプトタグ2つ）。Alpine のディレクティブで宣言的に UI を構築。htmx でサーバーとの連携が簡潔。学習コストが低い。 |
| C: React/Vue SPA | **○ 良好** | コンポーネント分割が自然で大規模開発には最適。ただし初期セットアップ（Vite 設定、ルーティング、状態管理）に時間がかかる。本プロジェクトの規模（実質3画面: 入力 + 内訳結果 + 比較結果）にはオーバースペック。 |

---

## 2. 総合評価マトリクス

| 比較軸 | A: バニラ | B: Alpine.js + htmx | C: React/Vue SPA |
|---|---|---|---|
| ビルド複雑性 | ◎ | ◎ | △ |
| テスト容易性 | ○ | ○ | ◎ |
| i18n 対応 | ○ | ○ | ◎ |
| テーブル表示品質 | ○ | ◎ | ◎ |
| 開発速度 | ○ | ◎ | ○ |
| **総合** | **良好** | **最良** | **良好（オーバースペック）** |

---

## 3. Decision

### 決定: Alpine.js + htmx（軽量フレームワーク）

**配信方式**: FastAPI の `StaticFiles` + `Jinja2Templates` によるサーバーサイドレンダリング

### Rationale（根拠）

1. **ビルドステップ不要**: 既存の Dockerfile にファイルコピー追加のみ。Node.js ビルドステージ不要。CDN 利用または静的 JS ファイルとしてバンドル（Alpine.js ~15KB, htmx ~14KB gzip 済み）。

2. **プロジェクト規模に最適**: 本プロジェクトは単一ページ（クエリ入力 → 結果表示）で、SPA のルーティングや複雑な状態管理は不要。Alpine.js のリアクティブバインディングでテーブルのソート・色分け、htmx でバックエンドとの非同期通信が簡潔に記述可能。

3. **憲章への適合**:
   - **ファイル400行制約**: Alpine.js コンポーネントは HTML 内にインラインで記述でき、ロジックを JS モジュールに分離すれば各ファイルを小さく保てる。
   - **関数40行制約**: Alpine のデータ関数とメソッドは自然に小さくなる。
   - **80% テストカバレッジ**: htmx のサーバーサイド連携により、Python 側のテスト（FastAPI TestClient）でフロントエンド表示ロジックの大部分をカバー可能。Alpine.js の JS ロジックは最小限（ソート、i18n 切替等）。

4. **i18n の実装が明快**: Alpine.js の `$store` に翻訳辞書を保持し、`localStorage` で言語設定を永続化。FR-010, FR-011 を自然に実装可能。

5. **テーブル表示が十分**: `x-for` によるテーブル行の動的生成、`x-bind:class` による増減の色分け、`Intl.NumberFormat` による通貨フォーマット。本プロジェクトのテーブル規模（最大数十行）では仮想スクロール等の高度な機能は不要。

### Alternatives Considered（検討した代替案）

- **バニラ HTML/CSS/JS**: ビルド不要で最もシンプルだが、DOM 操作のボイラープレートが多く、400行制約内でテーブルソート・i18n・エラーハンドリングをすべて実装するとコードが散乱する。Alpine.js の宣言的ディレクティブの方が可読性・保守性で優れる。

- **React + Vite SPA**: テスト基盤と i18n ライブラリが最も充実しているが、(1) Dockerfile に Node.js ビルドステージ追加が必要、(2) 単一ページアプリに SPA フレームワークはオーバースペック、(3) 開発・CI パイプラインの複雑性が増す。テーブル表示が主体で最大数十行のデータであり、TanStack Table 等の高機能ライブラリの恩恵は限定的。

- **Vue 3 (CDN) ビルドレス**: Alpine.js と同様にビルドレスで使えるが、Vue のフルランタイム（~33KB gzip）は Alpine.js（~15KB）の約2倍。SFC（.vue ファイル）を使わない場合の Vue は Alpine.js と機能面で大差なく、Alpine.js の方が軽量で目的に合致する。

- **Petite Vue**: Vue チームの軽量代替（~6KB）だが、エコシステムが小さく、Alpine.js ほどのコミュニティ・ドキュメントがない。

---

## 4. 実装方針

### 技術スタック

| コンポーネント | 選択 | バージョン / サイズ |
|---|---|---|
| UI リアクティブ | Alpine.js | 3.x (~15KB gzip) |
| サーバー連携 | htmx | 2.x (~14KB gzip) |
| テンプレート | Jinja2 (FastAPI) | FastAPI 組み込み |
| CSS | バニラ CSS (CSS Grid + Flexbox) | — |
| i18n | Alpine.js $store + JSON 翻訳ファイル | — |
| 通貨フォーマット | Intl.NumberFormat (ブラウザ組み込み) | — |

### ファイル構成案

```text
src/cost_analyzer/
├── static/
│   ├── css/
│   │   └── style.css           # メインスタイルシート
│   ├── js/
│   │   ├── app.js              # Alpine.js アプリ初期化・コンポーネント
│   │   ├── i18n.js             # 翻訳ヘルパー・言語辞書
│   │   └── table.js            # テーブルソート・フォーマットユーティリティ
│   └── vendor/
│       ├── alpine.min.js       # Alpine.js (CDN フォールバック用)
│       └── htmx.min.js         # htmx (CDN フォールバック用)
└── templates/
    ├── base.html               # ベースレイアウト（Alpine.js/htmx 読み込み）
    ├── index.html              # メインページ（クエリ入力 + 結果表示）
    └── partials/
        ├── breakdown.html      # 内訳テーブル部分テンプレート
        ├── comparison.html     # 比較テーブル部分テンプレート
        ├── clarification.html  # 確認メッセージ部分テンプレート
        └── error.html          # エラー表示部分テンプレート
```

### Dockerfile への影響

既存の Dockerfile に対する変更は最小限:

```dockerfile
# 追加: テンプレートと静的ファイルのコピー（ランタイムステージ）
COPY --from=builder /app/src src
# ↑ 既存の行で src/ ごとコピーされるため、追加変更不要
```

`src/cost_analyzer/static/` と `src/cost_analyzer/templates/` は既存の `COPY src/ src/` でコピーされるため、Dockerfile の変更は不要。

### FastAPI への統合

```python
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app.mount("/static", StaticFiles(directory="src/cost_analyzer/static"), name="static")
templates = Jinja2Templates(directory="src/cost_analyzer/templates")

@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
```

### Python 追加依存関係

```toml
# pyproject.toml に追加
"jinja2>=3.1",
```

FastAPI は Jinja2 をオプショナル依存として扱うため、明示的な追加が必要。`python-multipart` は不要（フォーム送信ではなく htmx/fetch で JSON 送信するため）。

---

## 5. リスクと軽減策

| リスク | 影響 | 軽減策 |
|---|---|---|
| Alpine.js/htmx の CDN 障害 | UI が動作しない | `vendor/` にローカルコピーを配置し、CDN フォールバックとして使用 |
| htmx のレスポンスが HTML 前提 | JSON API との整合性 | htmx の `hx-ext="json-enc"` 拡張または `fetch` API と Alpine.js の `$fetch` で JSON 通信。htmx は部分テンプレート返却にも対応可能 |
| フロントエンド JS のテストカバレッジ | 80% 要件への影響 | JS ロジックを最小限にし、Python 側のテンプレートレンダリングテスト + E2E テスト（Playwright）でカバー |
| Alpine.js の学習コスト | 開発遅延 | Alpine.js のドキュメントは簡潔で、Vue.js 経験者なら即座に習得可能。API サーフェスが小さい |

---

## 出典

- [Alpine.js ドキュメント](https://alpinejs.dev/)
- [htmx ドキュメント](https://htmx.org/)
- [FastAPI StaticFiles](https://fastapi.tiangolo.com/tutorial/static-files/)
- [FastAPI Templates (Jinja2)](https://fastapi.tiangolo.com/advanced/templates/)
- [Intl.NumberFormat - MDN](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl/NumberFormat)
- [Alpine.js Global Store](https://alpinejs.dev/globals/alpine-store)
- [htmx Extensions](https://htmx.org/extensions/)
