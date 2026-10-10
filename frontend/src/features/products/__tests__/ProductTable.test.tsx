import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ProductTable } from "../components/ProductTable";
import type { Product } from "../model/schemas";

const product = (over: Partial<Product> = {}): Product => ({
  id: "01a12680-3abe-70b5-ac92-41ab420fc4b9",
  sku: "MUG-001",
  name: "Coffee Mug",
  price_amount: "1249.50",
  currency: "INR",
  status: "active",
  version: 0,
  ...over,
});

describe("ProductTable", () => {
  it("shows an empty state", () => {
    render(<ProductTable products={[]} />);
    expect(screen.getByRole("status")).toHaveTextContent(/no products yet/i);
  });

  it("renders one row per product with formatted price", () => {
    render(
      <ProductTable
        products={[
          product(),
          product({
            id: "01a12680-3ad6-7004-92bc-1d9564cdeb3a",
            sku: "TEE-002",
            status: "discontinued",
          }),
        ]}
      />,
    );
    const rows = screen.getAllByRole("row").slice(1); // skip header
    expect(rows).toHaveLength(2);
    expect(within(rows[0]!).getByText("MUG-001")).toBeInTheDocument();
    expect(within(rows[0]!).getByText(/1,249\.50/)).toBeInTheDocument();
    expect(within(rows[1]!).getByText("discontinued")).toBeInTheDocument();
  });
});
