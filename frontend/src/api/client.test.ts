import { describe, expect, it } from "vitest";

import { ApiError } from "@/api/client";

describe("ApiError", () => {
  it("carries status, code and message", () => {
    const err = new ApiError(429, "quota_exceeded", "No prompts left");
    expect(err.status).toBe(429);
    expect(err.code).toBe("quota_exceeded");
    expect(err.message).toBe("No prompts left");
  });
});
