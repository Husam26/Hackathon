import { describe, expect, it } from "vitest";

import { formatMetric, formatPercent, humanize } from "./format";

describe("format helpers", () => {
  it("formats normalized confidence as a whole percent", () => {
    expect(formatPercent(0.943)).toBe("94%");
  });

  it("adds meaningful metric units", () => {
    expect(formatMetric("p99_latency_ms", 3200)).toBe("3,200 ms");
    expect(formatMetric("error_rate_5xx", 0.12)).toBe("12%");
  });

  it("humanizes machine labels", () => {
    expect(humanize("redis-pool_exhaustion")).toBe("redis pool exhaustion");
  });
});
