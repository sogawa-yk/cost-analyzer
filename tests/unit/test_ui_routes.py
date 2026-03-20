"""Web UI ルートのテスト。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from cost_analyzer.api import app


@pytest.fixture
def client():
    return TestClient(app)


class TestUIRoutes:
    """GET / エンドポイントのテスト。"""

    def test_index_returns_200(self, client):
        """トップページが正常にレンダリングされることを確認する。"""
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_index_contains_query_input(self, client):
        """トップページにチャット入力欄が含まれることを確認する。"""
        response = client.get("/")
        html = response.text
        assert "chat-input" in html
        assert "chat-send-btn" in html

    def test_index_loads_alpine_js(self, client):
        """Alpine.js が読み込まれることを確認する。"""
        response = client.get("/")
        html = response.text
        assert "alpine.min.js" in html

    def test_index_loads_htmx(self, client):
        """htmx が読み込まれることを確認する。"""
        response = client.get("/")
        html = response.text
        assert "htmx.min.js" in html

    def test_index_loads_app_js(self, client):
        """app.js が読み込まれることを確認する。"""
        response = client.get("/")
        html = response.text
        assert "app.js" in html

    def test_index_loads_css(self, client):
        """スタイルシートが読み込まれることを確認する。"""
        response = client.get("/")
        html = response.text
        assert "style.css" in html


class TestStaticFiles:
    """静的ファイルの配信テスト。"""

    def test_css_is_served(self, client):
        """CSS ファイルが配信されることを確認する。"""
        response = client.get("/static/css/style.css")
        assert response.status_code == 200
        assert "text/css" in response.headers["content-type"]

    def test_app_js_is_served(self, client):
        """app.js が配信されることを確認する。"""
        response = client.get("/static/js/app.js")
        assert response.status_code == 200

    def test_i18n_js_is_served(self, client):
        """i18n.js が配信されることを確認する。"""
        response = client.get("/static/js/i18n.js")
        assert response.status_code == 200

    def test_alpine_js_is_served(self, client):
        """Alpine.js が配信されることを確認する。"""
        response = client.get("/static/vendor/alpine.min.js")
        assert response.status_code == 200

    def test_htmx_js_is_served(self, client):
        """htmx が配信されることを確認する。"""
        response = client.get("/static/vendor/htmx.min.js")
        assert response.status_code == 200

    def test_nonexistent_static_returns_404(self, client):
        """存在しない静的ファイルが 404 を返すことを確認する。"""
        response = client.get("/static/nonexistent.js")
        assert response.status_code == 404
