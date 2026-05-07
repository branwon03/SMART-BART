import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { IncidentDetailPanel } from "./IncidentDetailPanel";
import type { Incident } from "../types/api";
import { updateIncident } from "../lib/incidents";

vi.mock("../lib/incidents", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/incidents")>();
  return {
    ...actual,
    updateIncident: vi.fn(),
  };
});

describe("IncidentDetailPanel", () => {
  const incident: Incident = {
    incident_id: "inc-1",
    status: "New",
    issue_priority: "LOW",
    discipline: "ELECTRICAL",
    vlm_summary: "Test summary",
    location_id: "loc-1",
    created_at: "2024-01-01T00:00:00.000Z",
  };

  beforeEach(() => {
    vi.mocked(updateIncident).mockReset();
  });

  it("closes sidebar after edit issue saves successfully", async () => {
    const user = userEvent.setup();
    const updated: Incident = { ...incident, status: "Closed" };
    vi.mocked(updateIncident).mockResolvedValue(updated);

    const onClose = vi.fn();
    const onIncidentUpdated = vi.fn();

    render(
      <IncidentDetailPanel
        incident={incident}
        evidence={[]}
        allIncidents={[incident]}
        now={new Date("2024-06-01T12:00:00.000Z")}
        incidentIdExpanded={false}
        onToggleIncidentIdExpanded={vi.fn()}
        onClose={onClose}
        onIncidentUpdated={onIncidentUpdated}
        onIncidentDeleted={vi.fn()}
        onRefreshAfterMerge={vi.fn().mockResolvedValue(undefined)}
        onIncidentSplit={vi.fn()}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Edit Issue" }));
    await user.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => {
      expect(updateIncident).toHaveBeenCalled();
    });
    expect(onIncidentUpdated).toHaveBeenCalledWith(updated);
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
