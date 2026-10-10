import { formatMoney } from "@/shared/lib/format";

import type { Product } from "../model/schemas";
import styles from "./products.module.css";

interface Props {
  products: Product[];
}

/** Presentational, server-compatible component: no state, no effects. */
export function ProductTable({ products }: Props) {
  if (products.length === 0) {
    return <p role="status">No products yet. Create the first one above.</p>;
  }
  return (
    <table className={styles.table}>
      <caption className={styles.srOnly}>Products</caption>
      <thead>
        <tr>
          <th scope="col">SKU</th>
          <th scope="col">Name</th>
          <th scope="col" className={styles.num}>
            Price
          </th>
          <th scope="col">Status</th>
        </tr>
      </thead>
      <tbody>
        {products.map((p) => (
          <tr key={p.id}>
            <td>
              <code>{p.sku}</code>
            </td>
            <td>{p.name}</td>
            <td className={styles.num}>{formatMoney(p.price_amount, p.currency)}</td>
            <td>
              <span className={p.status === "active" ? styles.active : styles.inactive}>
                {p.status}
              </span>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
