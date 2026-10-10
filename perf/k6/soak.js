// Soak: moderate load for a long time to expose leaks, pool exhaustion, log/disk growth.
import { SLO_THRESHOLDS, userJourney } from "./lib/config.js";

export const options = {
  scenarios: {
    soak: {
      executor: "constant-arrival-rate",
      rate: Number(__ENV.SOAK_RPS || 80),
      timeUnit: "1s",
      duration: __ENV.SOAK_DURATION || "1h",
      preAllocatedVUs: 50,
      maxVUs: 300,
    },
  },
  thresholds: SLO_THRESHOLDS,
};

export default function () {
  userJourney();
}
