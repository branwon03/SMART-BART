import { describe, expect, it } from "vitest";
import { displayCompactIncidentId } from "./formatIncidentId";

describe("displayCompactIncidentId", () => {
  it("abbreviates ids longer than 8 characters with an ellipsis", () => {
    expect(displayCompactIncidentId("bee50d2c5b654e499a9e409e55d24234")).toBe(
      "bee50d2c…",
    );
  });

  it("returns short ids unchanged", () => {
    expect(displayCompactIncidentId("abc12345")).toBe("abc12345");
    expect(displayCompactIncidentId("short")).toBe("short");
  });

  it("returns empty string for empty input", () => {
    expect(displayCompactIncidentId("")).toBe("");
  });
});
