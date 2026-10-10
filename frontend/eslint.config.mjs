import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

export default defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    rules: {
      "@typescript-eslint/no-explicit-any": "error",
      "@typescript-eslint/consistent-type-imports": "error",
      "no-console": ["error", { allow: ["warn", "error"] }],
      // Feature isolation: features may not reach into each other's internals
      "no-restricted-imports": [
        "error",
        {
          patterns: [
            {
              group: ["@/features/*/*/**"],
              message: "Import from the feature's public index instead.",
            },
          ],
        },
      ],
    },
  },
  {
    files: ["src/features/**/*"],
    rules: { "no-restricted-imports": "off" },
  },
  globalIgnores([
    ".next/**",
    "out/**",
    "coverage/**",
    "playwright-report/**",
    "test-results/**",
    "next-env.d.ts",
    "src/shared/api-schema.d.ts",
  ]),
]);
