// Smoke: 1 user for 30 s. Run after every deploy; must always pass.
import http from "k6/http";
import { check } from "k6";
import { BASE_URL, SLO_THRESHOLDS, userJourney } from "./lib/config.js";

export const options = { vus: 1, duration: "30s", thresholds: SLO_THRESHOLDS };

export function setup() {
  const r = http.get(`${BASE_URL}/health/ready`);
  if (!check(r, { "ready 200": (res) => res.status === 200 })) throw new Error("Service not ready");
}

export default function () {
  userJourney();
}
