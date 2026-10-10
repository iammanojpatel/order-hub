// Stress + spike: push past expected peak to find the breaking point and verify recovery.
import { userJourney } from "./lib/config.js";

export const options = {
  scenarios: {
    stress: {
      executor: "ramping-arrival-rate",
      startRate: 50,
      timeUnit: "1s",
      preAllocatedVUs: 100,
      maxVUs: 2000,
      stages: [
        { target: 200, duration: "2m" },
        { target: 500, duration: "3m" },
        { target: 1000, duration: "3m" },
        { target: 2000, duration: "1m" }, // spike
        { target: 100, duration: "3m" }, // recovery: latency must return to normal
      ],
    },
  },
  thresholds: { http_req_failed: [{ threshold: "rate<0.05", abortOnFail: true, delayAbortEval: "30s" }] },
};

export default function () {
  userJourney();
}
