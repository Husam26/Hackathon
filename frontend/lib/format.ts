export function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function formatMetric(key: string, value: number): string {
  if (key.includes("rate")) return formatPercent(value);
  if (key.endsWith("_ms")) return `${value.toLocaleString()} ms`;
  if (key.endsWith("_seconds")) return `${value}s`;
  return value.toLocaleString();
}

export function humanize(value: string): string {
  return value.replaceAll("_", " ").replaceAll("-", " ");
}
