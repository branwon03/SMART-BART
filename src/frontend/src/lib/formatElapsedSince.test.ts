import { describe, expect, it } from "vitest";
import { formatElapsedSince } from "./formatElapsedSince";

describe("formatElapsedSince", () => {
  it("returns 0m for missing, invalid, non-positive, or future-relative times", () => {
    const ref = new Date("2025-06-15T12:00:00Z");
    expect(formatElapsedSince(null, ref)).toBe("0m");
    expect(formatElapsedSince(undefined, ref)).toBe("0m");
    expect(formatElapsedSince("not-a-date", ref)).toBe("0m");
    expect(formatElapsedSince("2025-06-15T12:00:00Z", ref)).toBe("0m");
    expect(formatElapsedSince("2025-06-15T13:00:00Z", ref)).toBe("0m");
  });

  it("uses minutes under 60m", () => {
    const ref = new Date("2025-06-15T12:30:00Z");
    expect(formatElapsedSince("2025-06-15T12:00:00Z", ref)).toBe("30m");
  });

  it("uses whole hours from 1 hr up to before 24 hr", () => {
    const ref = new Date("2025-06-15T14:00:00Z");
    expect(formatElapsedSince("2025-06-15T12:00:00Z", ref)).toBe("2 hr");
    const ref23 = new Date("2025-06-16T11:59:00Z");
    expect(formatElapsedSince("2025-06-15T12:00:00Z", ref23)).toBe("23 hr");
  });

  it("uses days from 24 hr up to before 7 days", () => {
    const ref1d = new Date("2025-06-16T12:00:00Z");
    expect(formatElapsedSince("2025-06-15T12:00:00Z", ref1d)).toBe("1 day");
    const ref6d = new Date("2025-06-21T12:00:00Z");
    expect(formatElapsedSince("2025-06-15T12:00:00Z", ref6d)).toBe("6 days");
  });

  it("uses weeks from 7 days up to before 30 days", () => {
    const ref7d = new Date("2025-06-22T12:00:00Z");
    expect(formatElapsedSince("2025-06-15T12:00:00Z", ref7d)).toBe("1 week");
    const ref14d = new Date("2025-06-29T12:00:00Z");
    expect(formatElapsedSince("2025-06-15T12:00:00Z", ref14d)).toBe("2 weeks");
  });

  it("uses months from 30 days up to before 365 days", () => {
    const ref30d = new Date("2025-07-15T12:00:00Z");
    expect(formatElapsedSince("2025-06-15T12:00:00Z", ref30d)).toBe("1 month");
    const ref60d = new Date("2025-08-14T12:00:00Z");
    expect(formatElapsedSince("2025-06-15T12:00:00Z", ref60d)).toBe("2 months");
  });

  it("uses years at 365+ days", () => {
    const ref = new Date("2026-06-15T12:00:00Z");
    expect(formatElapsedSince("2025-06-15T12:00:00Z", ref)).toBe("1 year");
    const ref2y = new Date("2027-06-15T12:00:00Z");
    expect(formatElapsedSince("2025-06-15T12:00:00Z", ref2y)).toBe("2 years");
  });
});
