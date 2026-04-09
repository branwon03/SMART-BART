import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { deleteIncident } from "./incidents";

describe("deleteIncident", () => {
  let fetchSpy: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchSpy = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ deleted_incident_id: "abc123" }),
    });
    vi.stubGlobal("fetch", fetchSpy);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("sends a DELETE request to /api/incidents/{id}", async () => {
    await deleteIncident("abc123");

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [url, opts] = fetchSpy.mock.calls[0];
    expect(url).toContain("/api/incidents/abc123");
    expect(opts.method).toBe("DELETE");
  });

  it("returns the deleted incident id on success", async () => {
    const result = await deleteIncident("abc123");

    expect(result).toEqual({ deleted_incident_id: "abc123" });
  });

  it("throws on non-ok response", async () => {
    fetchSpy.mockResolvedValueOnce({
      ok: false,
      status: 404,
      text: () => Promise.resolve("Not found"),
    });

    await expect(deleteIncident("missing")).rejects.toThrow();
  });
});
