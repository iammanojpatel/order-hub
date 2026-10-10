import "server-only";

import { serverEnv } from "@/shared/config/env.server";
import { toApiError } from "@/shared/lib/api-error";

import {
  type CreateProductInput,
  type Product,
  type ProductPage,
  ProductPageSchema,
  ProductSchema,
} from "../model/schemas";

function headers(extra: Record<string, string> = {}): HeadersInit {
  return {
    Authorization: `Bearer ${serverEnv.API_TOKEN}`,
    "Content-Type": "application/json",
    ...extra,
  };
}

export async function listProducts(cursor?: string, limit = 20): Promise<ProductPage> {
  const url = new URL("/api/v1/products", serverEnv.API_BASE_URL);
  url.searchParams.set("limit", String(limit));
  if (cursor) url.searchParams.set("cursor", cursor);
  const res = await fetch(url, {
    headers: headers(),
    cache: "no-store",
    signal: AbortSignal.timeout(5_000),
  });
  if (!res.ok) throw await toApiError(res);
  return ProductPageSchema.parse(await res.json());
}

export async function createProduct(
  input: CreateProductInput,
  idempotencyKey: string,
): Promise<Product> {
  const res = await fetch(new URL("/api/v1/products", serverEnv.API_BASE_URL), {
    method: "POST",
    headers: headers({ "Idempotency-Key": idempotencyKey }),
    body: JSON.stringify(input),
    signal: AbortSignal.timeout(5_000),
  });
  if (!res.ok) throw await toApiError(res);
  return ProductSchema.parse(await res.json());
}
