import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { submitReport, dataUrlToFile } from "./submissions";

const TINY_DATA_URL =
  "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAFRABAQAAAAAAAAAAAAAAAAAAAAf/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/aAAwDAQACEQMRAD8AJgA//9k=";

const FAKE_RESULT = {
  incident_id: "abc123",
  description: "test",
  timestamp: "2025-01-01T00:00:00Z",
};

describe("submitReport", () => {
  let fetchSpy: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchSpy = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(FAKE_RESULT),
    });
    vi.stubGlobal("fetch", fetchSpy);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("POSTs to /api/submissions with FormData containing media and description", async () => {
    await submitReport({
      images: [TINY_DATA_URL],
      description: "Broken escalator",
      priority: "high",
      location: "West Oakland",
      fullName: "Jane Rider",
      contact: "jane@example.com",
    });

    expect(fetchSpy).toHaveBeenCalledTimes(1);

    const [url, opts] = fetchSpy.mock.calls[0];
    expect(url).toBe("/api/submissions");
    expect(opts.method).toBe("POST");

    const body = opts.body as FormData;
    expect(body.get("description")).toBe("Broken escalator");
    expect(body.get("reporter_name")).toBe("Jane Rider");
    expect(body.get("reporter_contact")).toBe("jane@example.com");
    expect(body.get("media")).toBeInstanceOf(File);
  });

  it("does not send user_priority field", async () => {
    await submitReport({
      images: [],
      description: "test",
      priority: "critical",
      location: "foo",
      fullName: "A",
      contact: "b",
    });

    const body = fetchSpy.mock.calls[0][1].body as FormData;
    expect(body.has("user_priority")).toBe(false);
  });

  it("returns the parsed JSON on success", async () => {
    const result = await submitReport({
      images: [],
      description: "test",
      priority: "",
      location: "x",
      fullName: "x",
      contact: "x",
    });

    expect(result).toEqual(FAKE_RESULT);
  });

  it("throws on non-ok response", async () => {
    fetchSpy.mockResolvedValueOnce({
      ok: false,
      status: 500,
      text: () => Promise.resolve("Internal Server Error"),
    });

    await expect(
      submitReport({
        images: [],
        description: "test",
        priority: "",
        location: "",
        fullName: "",
        contact: "",
      }),
    ).rejects.toThrow("Submission failed (500)");
  });
});

describe("dataUrlToFile", () => {
  it("converts a data URL to a File with the correct MIME type", () => {
    const file = dataUrlToFile(TINY_DATA_URL, "photo.jpg");
    expect(file).toBeInstanceOf(File);
    expect(file.name).toBe("photo.jpg");
    expect(file.type).toBe("image/jpeg");
    expect(file.size).toBeGreaterThan(0);
  });
});
