import { expect, test } from "@playwright/test";

// System test: real browser → Next.js → FastAPI → MySQL. Run with the stack up (`make up`).
test.describe("Products journey", () => {
  test("user creates a product and sees it in the list", async ({ page }) => {
    const sku = `E2E-${Date.now().toString(36).toUpperCase()}`;
    await page.goto("/products");
    await expect(page.getByRole("heading", { name: "Products", level: 1 })).toBeVisible();

    await page.getByLabel("SKU").fill(sku);
    await page.getByLabel("Name").fill("Playwright Mug");
    await page.getByLabel("Price").fill("499.00");
    await page.getByRole("button", { name: /create product/i }).click();

    await expect(page.getByRole("status")).toHaveText(`Created ${sku}`);
    await expect(page.getByRole("cell", { name: sku })).toBeVisible();
  });

  test("invalid input shows accessible field errors", async ({ page }) => {
    await page.goto("/products");
    await page.getByRole("button", { name: /create product/i }).click();
    await expect(page.getByLabel("SKU")).toHaveAttribute("aria-invalid", "true");
  });
});
