document.addEventListener('alpine:init', () => {

  // i18n ストアを先に初期化
  initI18n();

  Alpine.store('app', {
    loading: false,
    backendHealthy: true,
    queryText: '',
    messages: [],

    /** メッセージID生成 */
    _nextId() {
      return 'msg-' + Date.now() + '-' + Math.random().toString(36).slice(2, 7);
    },

    /** メッセージを追加して自動スクロール */
    addMessage(msg) {
      this.messages.push(msg);
      this._scrollToBottom();
    },

    /** ウェルカムメッセージを追加 */
    addWelcome() {
      this.addMessage({
        id: this._nextId(),
        role: 'assistant',
        type: 'welcome',
        text: null,
        data: null,
        timestamp: Date.now(),
      });
    },

    /** 会話クリア */
    clearMessages() {
      this.messages = [];
      this.queryText = '';
      this.addWelcome();
    },

    /** サジェストクリック */
    useSuggestion(text) {
      this.queryText = text;
      this.submitQuery();
    },

    /** 自動スクロール */
    _scrollToBottom() {
      requestAnimationFrame(() => {
        const el = document.getElementById('chat-messages');
        if (el) el.scrollTop = el.scrollHeight;
      });
    },

    async submitQuery() {
      const q = this.queryText.trim();
      if (!q) return;

      // ユーザーメッセージ追加
      this.addMessage({
        id: this._nextId(),
        role: 'user',
        type: 'text',
        text: q,
        data: null,
        timestamp: Date.now(),
      });

      this.queryText = '';
      this.loading = true;

      try {
        const resp = await fetch('/query', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            query: q,
            lang: Alpine.store('i18n').lang,
          }),
        });

        const data = await resp.json();

        if (!resp.ok) {
          // エラーレスポンス
          this.addMessage({
            id: this._nextId(),
            role: 'assistant',
            type: 'error',
            text: data.message || 'Unknown error',
            data: data,
            timestamp: Date.now(),
          });
        } else if (data.type === 'clarification') {
          // 確認要求
          this.addMessage({
            id: this._nextId(),
            role: 'assistant',
            type: 'clarification',
            text: data.message,
            data: data,
            timestamp: Date.now(),
          });
        } else {
          // 成功 (breakdown / comparison)
          this.addMessage({
            id: this._nextId(),
            role: 'assistant',
            type: data.type,
            text: data.conversational_text || null,
            data: data,
            timestamp: Date.now(),
          });
        }
      } catch (e) {
        this.addMessage({
          id: this._nextId(),
          role: 'assistant',
          type: 'error',
          text: e.message,
          data: { error: 'network', message: e.message },
          timestamp: Date.now(),
        });
      } finally {
        this.loading = false;
        this._scrollToBottom();
      }
    },

    async checkHealth() {
      try {
        const resp = await fetch('/health');
        this.backendHealthy = resp.ok;
      } catch {
        this.backendHealthy = false;
      }
    },
  });

  // ウェルカムメッセージ追加
  Alpine.store('app').addWelcome();

  // 初回ヘルスチェック
  Alpine.store('app').checkHealth();

  // 30秒ごとにポーリング
  setInterval(() => {
    Alpine.store('app').checkHealth();
  }, 30000);

});
