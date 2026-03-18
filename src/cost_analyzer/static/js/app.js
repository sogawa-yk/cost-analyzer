document.addEventListener('alpine:init', () => {

  // i18n ストアを先に初期化
  initI18n();

  Alpine.store('app', {
    loading: false,
    result: null,
    clarification: null,
    error: null,
    backendHealthy: true,
    queryText: '',

    async submitQuery() {
      this.loading = true;
      this.result = null;
      this.clarification = null;
      this.error = null;

      try {
        const resp = await fetch('/query', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            query: this.queryText,
            lang: Alpine.store('i18n').lang,
          }),
        });

        const data = await resp.json();

        if (!resp.ok) {
          this.error = data;
        } else if (data.type === 'clarification') {
          this.clarification = data;
        } else {
          this.result = data;
        }
      } catch (e) {
        this.error = { error: 'network', message: e.message };
      } finally {
        this.loading = false;
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

  // 初回ヘルスチェック
  Alpine.store('app').checkHealth();

  // 30秒ごとにポーリング
  setInterval(() => {
    Alpine.store('app').checkHealth();
  }, 30000);

});
