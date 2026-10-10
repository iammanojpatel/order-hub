// Public API of the products feature — other modules import only from here.
export { createProductAction } from "./api/actions";
export { CreateProductForm } from "./components/CreateProductForm";
export { ProductTable } from "./components/ProductTable";
export type { Product, ProductPage } from "./model/schemas";
