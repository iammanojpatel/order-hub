import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CreateProductForm } from "../components/CreateProductForm";

describe("CreateProductForm", () => {
  it("submits the form data including an idempotency key", async () => {
    const action = vi.fn().mockResolvedValue({ ok: true, message: "Created MUG-001" });
    render(<CreateProductForm action={action} />);

    await userEvent.type(screen.getByLabelText("SKU"), "MUG-001");
    await userEvent.type(screen.getByLabelText("Name"), "Coffee mug");
    await userEvent.type(screen.getByLabelText("Price"), "249.00");
    await userEvent.click(screen.getByRole("button", { name: /create product/i }));

    expect(await screen.findByRole("status")).toHaveTextContent("Created MUG-001");
    const data = action.mock.calls[0]![1] as FormData;
    expect(data.get("sku")).toBe("MUG-001");
    expect(data.get("currency")).toBe("INR");
    expect(data.get("idempotencyKey")).toMatch(/^[0-9a-f-]{36}$/);
  });

  it("shows field errors accessibly", async () => {
    const action = vi.fn().mockResolvedValue({ ok: false, fieldErrors: { sku: ["3-32 letters"] } });
    render(<CreateProductForm action={action} />);

    await userEvent.click(screen.getByRole("button", { name: /create product/i }));

    const sku = screen.getByLabelText("SKU");
    expect(await screen.findByText("3-32 letters")).toBeInTheDocument();
    expect(sku).toHaveAttribute("aria-invalid", "true");
    expect(sku).toHaveAccessibleDescription("3-32 letters");
  });
});
