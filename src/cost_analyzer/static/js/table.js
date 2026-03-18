/**
 * テーブルユーティリティ
 * 通貨・パーセンテージのフォーマットおよびコスト変動クラスの判定を行う
 */

const TableUtils = {
  /**
   * 通貨フォーマット
   * JPY は小数なし、USD は小数2桁で表示する
   */
  formatCurrency(amount, currency = "JPY") {
    const digits = currency === "JPY" ? 0 : 2;
    return new Intl.NumberFormat("ja-JP", {
      style: "currency",
      currency: currency,
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    }).format(amount);
  },

  /** パーセンテージ表示（小数1桁 + "%"） */
  formatPercentage(value) {
    return value.toFixed(1) + "%";
  },

  /** 変化額フォーマット（正: "+¥1,234" / 負: "-¥1,234"） */
  formatChange(amount, currency = "JPY") {
    const formatted = TableUtils.formatCurrency(Math.abs(amount), currency);
    return amount >= 0 ? "+" + formatted : "-" + formatted;
  },

  /** 変化率フォーマット（正: "+12.3%" / 負: "-12.3%" / null: "—"） */
  formatChangePercent(value) {
    if (value == null) return "\u2014";
    const sign = value >= 0 ? "+" : "-";
    return sign + Math.abs(value).toFixed(1) + "%";
  },

  /**
   * コスト増減に応じた CSS クラスを返す
   * 正 → 'cost-increase', 負 → 'cost-decrease', 0 → ''
   */
  changeClass(absoluteChange) {
    if (absoluteChange > 0) return "cost-increase";
    if (absoluteChange < 0) return "cost-decrease";
    return "";
  },
};

/* グローバルに公開 */
window.TableUtils = TableUtils;
