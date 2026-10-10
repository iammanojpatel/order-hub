import type { Metadata } from "next";

import { CreateProductForm, createProductAction, ProductTable } from "@/features/products";
import { listProducts } from "@/features/products/server";

export const metadata: Metadata = { title: "Products" };
export const dynamic = "force-dynamic";

export default async function ProductsPage() {
  const page = await listProducts();
  return (
    <main>
      <h1>Products</h1>
      <CreateProductForm action={createProductAction} />
      <ProductTable products={page.items} />
    </main>
  );
}
