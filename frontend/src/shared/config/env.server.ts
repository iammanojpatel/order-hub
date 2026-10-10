import "server-only";
import { z } from "zod";

/** Server-side environment, validated once at startup. Fails fast on misconfiguration. */
const ServerEnv = z.object({
  API_BASE_URL: z.url().default("http://localhost:8000"),
  API_TOKEN: z.string().default(""),
});

export const serverEnv = ServerEnv.parse({
  API_BASE_URL: process.env.API_BASE_URL,
  API_TOKEN: process.env.API_TOKEN,
});
