import { describe, expect, it } from "vitest";
import { formatPostedAt } from "./formatPostedAt";

describe("formatPostedAt", () => {
  it("returns an em dash for missing, empty, or invalid input", () => {
    expect(formatPostedAt(null)).toBe("—");
    expect(formatPostedAt(undefined)).toBe("—");
    expect(formatPostedAt("")).toBe("—");
    expect(formatPostedAt("not-a-date")).toBe("—");
  });

  it("formats local date-time without timezone as M/D/YY @ h:mmAM|PM", () => {
    // No trailing Z: parsed as local per ECMAScript ISO 8601 rules.
    expect(formatPostedAt("2026-01-01T12:32:00")).toBe("1/1/26 @ 12:32PM");
    expect(formatPostedAt("2026-01-09T10:00:00")).toBe("1/9/26 @ 10:00AM");
  });

  it("uses 12 for midnight and noon in 12-hour clock", () => {
    expect(formatPostedAt("2026-06-15T00:15:00")).toBe("6/15/26 @ 12:15AM");
    expect(formatPostedAt("2026-06-15T12:00:00")).toBe("6/15/26 @ 12:00PM");
  });

  it("pads minutes to two digits", () => {
    expect(formatPostedAt("2026-03-20T14:05:00")).toBe("3/20/26 @ 2:05PM");
  });

  it("uses two-digit year modulo 100", () => {
    expect(formatPostedAt("2000-07-04T09:00:00")).toBe("7/4/0 @ 9:00AM");
  });

  it("matches the expected display shape for any valid parseable string", () => {
    expect(formatPostedAt("2026-12-31T23:59:00")).toMatch(
      /^\d{1,2}\/\d{1,2}\/\d{1,2} @ \d{1,2}:\d{2}(AM|PM)$/,
    );
  });
});
