import { describe, expect, it, vi, afterEach } from "vitest";
import { formatDateTime, formatShortDate } from "./formatDate";

describe("formatShortDate", () => {
  it("returns em dash for missing or invalid", () => {
    expect(formatShortDate(null)).toBe("—");
    expect(formatShortDate(undefined)).toBe("—");
    expect(formatShortDate("")).toBe("—");
    expect(formatShortDate("not-a-date")).toBe("—");
  });

  it("formats using local calendar M/D/YY", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-01-01T12:00:00Z"));
    try {
      const d = new Date("2026-05-12T15:00:00.000Z");
      const m = d.getMonth() + 1;
      const day = d.getDate();
      const y = String(d.getFullYear()).slice(-2);
      expect(formatShortDate("2026-05-12T15:00:00.000Z")).toBe(`${m}/${day}/${y}`);
    } finally {
      vi.useRealTimers();
    }
  });
});

describe("formatDateTime", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("returns em dash for missing or invalid", () => {
    expect(formatDateTime(null)).toBe("—");
    expect(formatDateTime(undefined)).toBe("—");
    expect(formatDateTime("bad")).toBe("—");
  });

  it("uses 12h clock with zero-padded minutes", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-01-01T12:00:00Z"));
    const iso = "2026-05-12T22:05:00.000Z";
    const d = new Date(iso);
    const m = d.getMonth() + 1;
    const day = d.getDate();
    const y = String(d.getFullYear()).slice(-2);
    const hours = d.getHours();
    const mins = String(d.getMinutes()).padStart(2, "0");
    const ampm = hours >= 12 ? "PM" : "AM";
    const h12 = hours % 12 || 12;
    expect(formatDateTime(iso)).toBe(`${m}/${day}/${y} ${h12}:${mins} ${ampm}`);
  });
});
