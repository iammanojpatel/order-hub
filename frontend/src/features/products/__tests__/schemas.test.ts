import { describe, expect, it } from "vitest";

import { CreateProductInput, ProductPageSchema } from "../model/schemas";

describe("CreateProductInput", () => {
  it("normalises currency to upper case", () => {
    const r = CreateProductInput.parse({
      sku: "MUG-1",
      name: "Mug",
      price_amount: "9.50",
      currency: "inr",
    });
    expect(r.currency).toBe("INR");
  });

  it.each(["0", "-1", "1.234", "abc", "0.00"])("rejects invalid amount %s", (amount) => {
    const r = CreateProductInput.safeParse({
      sku: "MUG-1",
      name: "Mug",
      price_amount: amount,
      currency: "INR",
    });
    expect(r.success).toBe(false);
  });

  it("rejects a too-short SKU with a helpful message", () => {
    const r = CreateProductInput.safeParse({
      sku: "ab",
      name: "Mug",
      price_amount: "1",
      currency: "INR",
    });
    expect(r.success).toBe(false);
    expect(r.error?.issues[0]?.message).toMatch(/3-32/);
  });
});

describe("ProductPageSchema", () => {
  it("rejects responses that drift from the contract", () => {
    const r = ProductPageSchema.safeParse({ items: [{ id: "not-a-uuid" }], next_cursor: null });
    expect(r.success).toBe(false);
  });
});
