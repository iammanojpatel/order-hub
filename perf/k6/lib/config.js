// Shared k6 config. Env: BASE_URL (default http://localhost:8000), TOKEN (from `make token`).
import http from "k6/http";
import { check } from "k6";

export const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";
const TOKEN = __ENV.TOKEN || "";

export const params = (extra = {}) => ({
  headers: { Authorization: `Bearer ${TOKEN}`, "Content-Type": "application/json", ...extra },
  timeout: "10s",
});

// SLOs from CLAUDE.md — the build fails if these are breached.
export const SLO_THRESHOLDS = {
  http_req_failed: ["rate<0.001"],
  "http_req_duration{kind:read}": ["p(95)<200", "p(99)<500"],
  "http_req_duration{kind:write}": ["p(95)<300", "p(99)<700"],
  checks: ["rate>0.999"],
};

export function listProducts() {
  const r = http.get(`${BASE_URL}/api/v1/products?limit=20`, { ...params(), tags: { kind: "read", name: "list" } });
  check(r, { "list 200": (res) => res.status === 200 });
  return r;
}

export function getProduct(id) {
  const r = http.get(`${BASE_URL}/api/v1/products/${id}`, { ...params(), tags: { kind: "read", name: "get" } });
  check(r, { "get 200": (res) => res.status === 200 });
  return r;
}

export function createProduct() {
  const sku = `K6-${__VU}-${__ITER}-${Date.now().toString(36)}`.toUpperCase().slice(0, 32);
  const body = JSON.stringify({ sku, name: `Load ${sku}`, price_amount: "199.00", currency: "INR" });
  const r = http.post(`${BASE_URL}/api/v1/products`, body, {
    ...params({ "Idempotency-Key": sku }),
    tags: { kind: "write", name: "create" },
  });
  check(r, { "create 201": (res) => res.status === 201 });
  return r;
}

/** Realistic mix: 80 % reads, 20 % writes. */
export function userJourney() {
  const page = listProducts();
  const items = page.status === 200 ? page.json("items") : [];
  if (items.length > 0) getProduct(items[Math.floor(Math.random() * items.length)].id);
  if (Math.random() < 0.2) createProduct();
}
