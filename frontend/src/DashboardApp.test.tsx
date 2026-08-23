import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import DashboardApp from "./DashboardApp";

const createdAt = "2026-08-23T09:00:00Z";

const alert = {
  id: "alert-1",
  normalized_event_id: "event-1",
  incident_id: "incident-1",
  alert_type: "suspicious_login",
  title: "Suspicious privileged login",
  description: "A privileged account authenticated from a new source.",
  severity: "high",
  confidence: 0.94,
  status: "open",
  created_at: createdAt,
};

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function successfulApi() {
  return vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith("/auth/token")) {
      return jsonResponse({ access_token: "test-token", token_type: "bearer", expires_in: 1800 });
    }
    if (url.endsWith("/auth/me")) {
      return jsonResponse({ id: "user-1", username: "analyst", full_name: "Demo Analyst", role: "analyst", active: true });
    }
    if (url.endsWith("/platform/overview")) {
      return jsonResponse({
        open_alerts: 1,
        active_incidents: 1,
        critical_alerts: 0,
        monitored_events: 12,
        severity_distribution: [{ severity: "high", count: 1 }],
        recent_alerts: [alert],
        model_status: "operational",
        model_name: "ECTI ensemble",
        model_version: "1.0",
      });
    }
    if (url.endsWith("/platform/alerts")) return jsonResponse([alert]);
    if (url.endsWith("/platform/incidents")) {
      return jsonResponse([{ id: "incident-1", title: "Privileged access chain", description: "Correlated activity", status: "open", severity: "high", risk_score: 82, created_at: createdAt, updated_at: createdAt }]);
    }
    if (url.endsWith("/platform/feedback")) return jsonResponse([]);
    if (url.endsWith("/platform/alerts/alert-1/explanations")) {
      return jsonResponse([{ id: "explanation-1", alert_id: "alert-1", method: "rules", summary: "New privileged source", evidence: {}, limitations: "Synthetic evidence", created_at: createdAt }]);
    }
    if (url.endsWith("/platform/alerts/alert-1/recommendations")) {
      return jsonResponse({ alert_id: "alert-1", recommendations: [] });
    }
    if (url.endsWith("/platform/incidents/incident-1")) {
      return jsonResponse({ incident: { id: "incident-1", title: "Privileged access chain", description: "Correlated activity", status: "open", severity: "high", risk_score: 82, created_at: createdAt, updated_at: createdAt }, alerts: [alert], graph: { nodes: [], edges: [] } });
    }
    return jsonResponse({ detail: `Unhandled test URL: ${url}` }, 500);
  });
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("DashboardApp", () => {
  it("starts at the secure demo login", () => {
    render(<DashboardApp />);

    expect(screen.getByRole("heading", { name: "Welcome back" })).toBeInTheDocument();
    expect(screen.getByLabelText("Username")).toHaveValue("analyst");
    expect(screen.getByLabelText("Password")).toHaveValue("analyst-demo-only");
  });

  it("authenticates and loads the protected overview", async () => {
    const fetchMock = successfulApi();
    vi.stubGlobal("fetch", fetchMock);
    render(<DashboardApp />);

    fireEvent.click(screen.getByRole("button", { name: "Enter workspace" }));

    expect(await screen.findByRole("heading", { name: "Security overview" })).toBeInTheDocument();
    expect(await screen.findByText("Suspicious privileged login")).toBeInTheDocument();
    expect(screen.getByText(/Protected API/)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/auth/me",
      expect.objectContaining({ headers: expect.objectContaining({ Authorization: "Bearer test-token" }) }),
    );
  });

  it("shows a generic message when credentials are rejected", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse({ detail: "internal authentication detail" }, 401)));
    render(<DashboardApp />);

    fireEvent.click(screen.getByRole("button", { name: "Enter workspace" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("The username or password was not accepted.");
    await waitFor(() => expect(screen.getByRole("button", { name: "Enter workspace" })).toBeEnabled());
  });
});
