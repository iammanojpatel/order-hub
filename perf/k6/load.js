// Load: ramp to the target throughput and hold. Thresholds = SLOs.
// Tune TARGET_RPS to your expected peak (default 200 req/s).
import { SLO_THRESHOLDS, userJourney } from "./lib/config.js";

const TARGET = Number(__ENV.TARGET_RPS || 200);

export const options = {
  scenarios: {
    steady: {
      executor: "ramping-arrival-rate",
      startRate: 10,
      timeUnit: "1s",
      preAllocatedVUs: 50,
      maxVUs: 500,
      stages: [
        { target: TARGET, duration: "2m" }, // ramp up
        { target: TARGET, duration: "5m" }, // hold at peak
        { target: 0, duration: "1m" }, // ramp down
      ],
    },
  },
  thresholds: SLO_THRESHOLDS,
};

export default function () {
  userJourney();
}
