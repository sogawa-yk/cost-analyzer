# Implementation Plan: NL チャット UI

**Branch**: `006-nl-chat-ui` | **Date**: 2026-03-20 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/006-nl-chat-ui/spec.md`

## Summary

単発クエリ形式のUIをチャット形式に変更する。会話履歴をブラウザメモリで保持し、コスト結果テーブルをチャットバブル内に整形表示する。OCI GenAI Service（gemini-2.5-flash）を活用して、データ結果を踏まえた対話的な応答文をLLMで生成する。既存の `/query` APIレスポンス形式を拡張し、`conversational_text` フィールドを追加する。

## Technical Context

**Language/Version**: Python 3.13（バックエンド）、JavaScript ES2022+（フロントエンド）
**Primary Dependencies**: FastAPI（HTTP）、OCI SDK（GenAI + Usage API）、Alpine.js 3.x（UI）、Jinja2（テンプレート）
**Storage**: N/A（ステートレス — ブラウザメモリのみ）
**Testing**: pytest（ユニット/統合）、Playwright（E2E）
**Target Platform**: Web ブラウザ（デスクトップ + モバイル 375px以上）
**Project Type**: Web サービス（FastAPI + Jinja2 SPA風）
**Performance Goals**: 既存UIと同等の応答速度（LLM呼び出し2回分のオーバーヘッドを許容）
**Constraints**: メモリ 512MB以下、API レスポンス p95 500ms以下（LLM呼び出し除く）
**Scale/Scope**: 1セッション100メッセージ以内

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Code Quality | PASS | 既存パターンに従う。新規モジュールは単一責任。40行/400行制限を遵守 |
| II. Testing Standards | PASS | ユニット80%、LLM応答生成パスは統合テストでカバー。E2Eテストでチャットフロー検証 |
| III. UX Consistency | PASS | i18n維持、一貫したフォーマット（TableUtils再利用）、全状態（loading/error/empty）を明示的にハンドリング |
| IV. Performance Requirements | PASS | LLM応答生成は既存LLMコール後の追加コールだがユーザー許容範囲。UIレンダリングは1秒以内 |

## Project Structure

### Documentation (this feature)

```text
specs/006-nl-chat-ui/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── query-api.md     # /query エンドポイント拡張契約
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/cost_analyzer/
├── api.py                          # /query エンドポイント拡張（conversational_text追加）
├── parser.py                       # 応答文生成LLMコール追加
├── engine.py                       # generate_conversational_response() 新規関数
├── models.py                       # ConversationalResponse モデル追加
├── config.py                       # 変更なし（既存設定で対応）
├── templates/
│   ├── index.html                  # チャットUI レイアウトに全面書き換え
│   └── partials/
│       ├── chat-message.html       # 新規：チャットメッセージバブル
│       ├── chat-welcome.html       # 新規：ウェルカムメッセージ
│       ├── breakdown.html          # チャットバブル内用に調整
│       ├── comparison.html         # チャットバブル内用に調整
│       ├── error.html              # チャットバブル内用に調整
│       └── clarification.html      # チャットバブル内用に調整
├── static/
│   ├── js/
│   │   ├── app.js                  # Alpine.js ストアをチャット形式に書き換え
│   │   ├── i18n.js                 # チャットUI用翻訳キー追加
│   │   └── table.js                # 変更なし
│   └── css/
│       └── style.css               # チャットUI スタイル追加

tests/
├── unit/
│   ├── test_chat_response.py       # 新規：応答文生成テスト
│   └── test_api.py                 # 既存：拡張レスポンスのテスト追加
├── integration/
│   └── test_genai_chat.py          # 新規：LLM応答生成統合テスト
└── e2e/
    └── test_chat_ui_e2e.py         # 新規：チャットUIフローE2Eテスト
```

**Structure Decision**: 既存のWebアプリ構造（src/cost_analyzer/ + tests/）をそのまま維持。新規ファイルは最小限（テンプレート2つ、テスト3つ）に抑え、既存ファイルの拡張で対応する。
