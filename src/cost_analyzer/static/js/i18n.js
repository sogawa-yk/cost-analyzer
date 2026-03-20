/**
 * i18n (国際化) モジュール
 * Alpine.js $store として言語切替・翻訳機能を提供する
 */

/* 翻訳辞書 */
const translations = {
  ja: {
    query_placeholder: "先月のサービス別コストを教えて",
    submit_button: "送信",
    loading_message: "処理中...",
    service_column: "サービス",
    amount_column: "金額",
    percentage_column: "割合",
    total_label: "合計",
    error_retry: "再試行",
    error_contact_admin: "管理者に連絡してください",
    error_network: "ネットワーク接続を確認してください",
    prev_period: "前期",
    current_period: "当期",
    change_column: "変化額",
    change_rate_column: "変化率",
    trend_summary_title: "トレンドサマリー",
    app_title: "OCI コスト分析",
    connected: "接続中",
    disconnected: "切断",
    status_connected: "接続中",
    status_disconnected: "切断",
    clarification_title: "確認が必要です",
    welcome_message: "OCI コスト分析アシスタントです。コストに関する質問をどうぞ。",
    welcome_suggestion_1: "先月のサービス別コストを教えて",
    welcome_suggestion_2: "今月と先月のコストを比較して",
    welcome_suggestion_3: "先月のComputeのコストは？",
    clear_conversation: "会話をクリア",
    typing_indicator: "回答を生成中...",
  },
  en: {
    query_placeholder: "Show me last month's cost by service",
    submit_button: "Submit",
    loading_message: "Processing...",
    service_column: "Service",
    amount_column: "Amount",
    percentage_column: "Percentage",
    total_label: "Total",
    error_retry: "Retry",
    error_contact_admin: "Please contact the administrator",
    error_network: "Please check your network connection",
    prev_period: "Previous Period",
    current_period: "Current Period",
    change_column: "Change",
    change_rate_column: "Change Rate",
    trend_summary_title: "Trend Summary",
    app_title: "OCI Cost Analyzer",
    connected: "Connected",
    disconnected: "Disconnected",
    status_connected: "Connected",
    status_disconnected: "Disconnected",
    clarification_title: "Clarification Needed",
    welcome_message: "I'm the OCI Cost Analyzer assistant. Ask me anything about your costs.",
    welcome_suggestion_1: "Show me last month's cost by service",
    welcome_suggestion_2: "Compare this month with last month",
    welcome_suggestion_3: "What was last month's Compute cost?",
    clear_conversation: "Clear conversation",
    typing_indicator: "Generating response...",
  },
};

/** 現在の言語を返すヘルパー */
function currentLang() {
  return (Alpine.store("i18n") && Alpine.store("i18n").lang) || "ja";
}

/** キーに対応する翻訳文字列を返す */
function t(key) {
  const lang = currentLang();
  return (translations[lang] && translations[lang][key]) || key;
}

/** 言語を切り替え、localStorage に保存する */
function setLang(lang) {
  if (!translations[lang]) return;
  Alpine.store("i18n").lang = lang;
  localStorage.setItem("cost_analyzer_lang", lang);
}

/**
 * Alpine.js ストアとして i18n を初期化する
 * app.js の alpine:init ハンドラから呼び出される
 */
function initI18n() {
  const saved = localStorage.getItem("cost_analyzer_lang") || "ja";
  Alpine.store("i18n", {
    lang: saved,
    get currentLang() {
      return this.lang;
    },
    t(key) {
      return t(key);
    },
    setLang(newLang) {
      setLang(newLang);
    },
  });
}

/* グローバルに公開 */
window.initI18n = initI18n;
window.t = t;
window.setLang = setLang;
