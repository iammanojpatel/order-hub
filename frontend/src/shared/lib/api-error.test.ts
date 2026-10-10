import { describe, expect, it } from "vitest";

import { toApiError } from "./api-error";

describe("toApiError", () => {
  it("reads RFC 9457 problem details", async () => {
    const res = new Response(
      JSON.stringify({ type: "t", title: "Conflict", status: 409, detail: "SKU exists" }),
      { status: 409 },
    );
    const err = await toApiError(res);
    expect(err.status).toBe(409);
    expect(err.message).toBe("SKU exists");
  });

  it("falls back when the body is not JSON", async () => {
    const err = await toApiError(new Response("oops", { status: 502, statusText: "Bad Gateway" }));
    expect(err.status).toBe(502);
    expect(err.message).toBe("Bad Gateway");
  });
});
