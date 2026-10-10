import { describe, expect, it } from "vitest";

import { formatMoney } from "./format";

describe("formatMoney", () => {
  it("formats INR with Indian digit grouping", () => {
    expect(formatMoney("123456.5", "INR")).toBe("₹1,23,456.50");
  });
});
