import { describe, expect, it } from "vitest";

import { importanceLabel } from "./App";

describe("importanceLabel", () => {
  it("prioritizes novel high-score candidates", () => {
    expect(importanceLabel(0.8, true)).toBe("Priority follow-up");
  });

  it("keeps mid-score candidates in the watchlist tier", () => {
    expect(importanceLabel(0.58, false)).toBe("Worth watching");
  });
});
