const formatters = new Map<string, Intl.NumberFormat>();

/** Formats a decimal-string amount without float rounding surprises in the UI layer. */
export function formatMoney(amount: string, currency: string, locale = "en-IN"): string {
  const key = `${locale}:${currency}`;
  let fmt = formatters.get(key);
  if (!fmt) {
    fmt = new Intl.NumberFormat(locale, { style: "currency", currency });
    formatters.set(key, fmt);
  }
  return fmt.format(Number(amount));
}
