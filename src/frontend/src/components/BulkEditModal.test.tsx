import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BulkEditModal } from "./BulkEditModal";
import type { Incident } from "../types/api";
import { updateIncident } from "../lib/incidents";

vi.mock("../lib/incidents", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/incidents")>();
  return {
    ...actual,
    updateIncident: vi.fn(),
  };
});

describe("BulkEditModal", () => {
  const inc1: Incident = {
    incident_id: "id-alpha",
    status: "New",
    issue_priority: "LOW",
    discipline: "ELECTRICAL",
    vlm_summary: "One",
    created_at: "2024-01-01T00:00:00.000Z",
  };
  const inc2: Incident = {
    incident_id: "id-beta",
    status: "New",
    issue_priority: "LOW",
    discipline: "ELECTRICAL",
    vlm_summary: "Two",
    created_at: "2024-01-01T00:00:00.000Z",
  };

  beforeEach(() => {
    vi.mocked(updateIncident).mockReset();
  });

  it("calls updateIncident with chosen discipline for each selected incident", async () => {
    const user = userEvent.setup();
    const onApplied = vi.fn();

    vi.mocked(updateIncident)
      .mockResolvedValueOnce({ ...inc1, discipline: "MECHANICAL" })
      .mockResolvedValueOnce({ ...inc2, discipline: "MECHANICAL" });

    render(
      <BulkEditModal
        incidents={[inc1, inc2]}
        onApplied={onApplied}
        onClose={vi.fn()}
      />,
    );

    await user.selectOptions(screen.getByLabelText("New discipline"), "MECHANICAL");
    await user.click(screen.getByRole("button", { name: /Apply to selected/i }));

    await waitFor(() => {
      expect(updateIncident).toHaveBeenCalledTimes(2);
    });

    expect(updateIncident).toHaveBeenCalledWith("id-alpha", { discipline: "MECHANICAL" });
    expect(updateIncident).toHaveBeenCalledWith("id-beta", { discipline: "MECHANICAL" });

    expect(onApplied).toHaveBeenCalledWith([
      { ...inc1, discipline: "MECHANICAL" },
      { ...inc2, discipline: "MECHANICAL" },
    ]);
  });
});
