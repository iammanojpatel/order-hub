import { z } from "zod";

const AMOUNT = /^(?:[1-9][0-9]{0,11}(?:\.[0-9]{1,2})?|0\.(?:[1-9][0-9]?|0[1-9]))$/;

/** Mirrors the backend OpenAPI contract; parse every response (never trust the network). */
export const ProductSchema = z.object({
  id: z.uuid(),
  sku: z.string(),
  name: z.string(),
  price_amount: z.string().regex(AMOUNT),
  currency: z.string().length(3),
  status: z.enum(["active", "discontinued"]),
  version: z.number().int().nonnegative(),
});
export type Product = z.infer<typeof ProductSchema>;

export const ProductPageSchema = z.object({
  items: z.array(ProductSchema),
  next_cursor: z.uuid().nullable(),
});
export type ProductPage = z.infer<typeof ProductPageSchema>;

export const CreateProductInput = z.object({
  sku: z
    .string()
    .trim()
    .regex(/^[A-Za-z0-9][A-Za-z0-9-]{2,31}$/, "3-32 letters, digits or dashes"),
  name: z.string().trim().min(1, "Name is required").max(200),
  price_amount: z.string().trim().regex(AMOUNT, "Enter a positive amount, max 2 decimals"),
  currency: z
    .string()
    .trim()
    .regex(/^[A-Za-z]{3}$/, "3-letter ISO code")
    .transform((c) => c.toUpperCase()),
});
export type CreateProductInput = z.infer<typeof CreateProductInput>;
