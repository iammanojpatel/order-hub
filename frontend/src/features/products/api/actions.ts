"use server";

import { revalidatePath } from "next/cache";
import { z } from "zod";

import { ApiError } from "@/shared/lib/api-error";

import { CreateProductInput } from "../model/schemas";
import { createProduct } from "./products.server";

export interface CreateProductState {
  ok: boolean;
  message?: string;
  fieldErrors?: Partial<Record<keyof CreateProductInput, string[]>>;
}

/** Server Action: validates on the server (never trust the client), then calls the API. */
export async function createProductAction(
  _prev: CreateProductState,
  formData: FormData,
): Promise<CreateProductState> {
  const parsed = CreateProductInput.safeParse(Object.fromEntries(formData));
  if (!parsed.success) {
    return { ok: false, fieldErrors: z.flattenError(parsed.error).fieldErrors };
  }
  const idempotencyKey = String(formData.get("idempotencyKey") ?? crypto.randomUUID());
  try {
    await createProduct(parsed.data, idempotencyKey);
  } catch (err) {
    if (err instanceof ApiError) return { ok: false, message: err.message };
    throw err;
  }
  revalidatePath("/products");
  return { ok: true, message: `Created ${parsed.data.sku.toUpperCase()}` };
}
