"""Playwright による E2E テスト。

実行方法:
    pytest -m e2e tests/e2e/

前提:
    - playwright install chromium を事前実行
    - OCI 認証情報が設定済み、または環境変数でモック化
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.e2e


class TestPageLoad:
    """初期ページ読み込みのテスト。"""

    def test_index_page_loads(self, page, base_url):
        """トップページが正常に表示されることを確認する。"""
        page.goto(base_url)
        assert page.title() != ""
        page.wait_for_selector(".query-input")

    def test_query_input_exists(self, page, base_url):
        """クエリ入力欄と送信ボタンが表示されることを確認する。"""
        page.goto(base_url)
        page.wait_for_selector(".query-input")
        input_el = page.locator(".query-input")
        submit_btn = page.locator(".submit-btn")
        assert input_el.is_visible()
        assert submit_btn.is_visible()

    def test_submit_button_disabled_when_empty(self, page, base_url):
        """入力が空の場合、送信ボタンが無効であることを確認する。"""
        page.goto(base_url)
        page.wait_for_selector(".submit-btn")
        submit_btn = page.locator(".submit-btn")
        assert submit_btn.is_disabled()


class TestLanguageSwitch:
    """言語切替のテスト。"""

    def test_language_toggle_exists(self, page, base_url):
        """言語切替ボタンが表示されることを確認する。"""
        page.goto(base_url)
        page.wait_for_selector(".lang-switcher")
        lang_switcher = page.locator(".lang-switcher")
        assert lang_switcher.is_visible()

    def test_switch_to_english(self, page, base_url):
        """英語に切り替えるとプレースホルダが英語になることを確認する。"""
        page.goto(base_url)
        page.wait_for_selector(".query-input")

        # EN ボタンをクリック
        en_btn = page.get_by_text("EN")
        if en_btn.is_visible():
            en_btn.click()
            page.wait_for_timeout(500)
            placeholder = page.locator(".query-input").get_attribute("placeholder")
            assert placeholder is not None
            # 英語プレースホルダが設定されていることを確認
            assert "cost" in placeholder.lower() or "show" in placeholder.lower()


class TestConnectionStatus:
    """接続状態インジケーターのテスト。"""

    def test_connection_indicator_visible(self, page, base_url):
        """接続状態インジケーターが表示されることを確認する。"""
        page.goto(base_url)
        page.wait_for_selector(".health-dot", timeout=5000)
        indicator = page.locator(".health-dot")
        assert indicator.is_visible()


class TestQuerySubmission:
    """クエリ送信のテスト。"""

    def test_submit_enables_with_input(self, page, base_url):
        """テキスト入力後に送信ボタンが有効になることを確認する。"""
        page.goto(base_url)
        page.wait_for_selector(".query-input")
        page.locator(".query-input").fill("先月のコスト")
        submit_btn = page.locator(".submit-btn")
        assert not submit_btn.is_disabled()

    def test_loading_state_on_submit(self, page, base_url):
        """送信後にローディング状態が表示されることを確認する。"""
        page.goto(base_url)
        page.wait_for_selector(".query-input")
        page.locator(".query-input").fill("先月のサービス別コストを教えて")
        page.locator(".submit-btn").click()
        # ローディング状態を確認（スピナーまたは無効化ボタン）
        page.wait_for_selector(".spinner, .spinner-large, .loading-overlay", timeout=3000)
