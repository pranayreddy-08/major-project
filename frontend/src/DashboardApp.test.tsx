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

const scenario = {
  id: "credential-attack",
  title: "Credential attack",
  category: "Credential access",
  technique: "Repeated failure followed by credential attack",
  description: "An external address repeatedly targets a privileged account.",
  expected_classification: "attack",
  severity: "critical",
  event_count: 2,
  signals: ["Authentication failure", "Credential attack"],
  learning_points: ["Shared user/IP correlation"],
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
    if (url.endsWith("/auth/setup-status")) {
      return jsonResponse({ setup_required: false });
    }
    if (url.endsWith("/auth/token")) {
      return jsonResponse({ access_token: "test-token", token_type: "bearer", expires_in: 1800 });
    }
    if (url.endsWith("/auth/me")) {
      return jsonResponse({ id: "user-1", username: "owner", full_name: "Local Owner", role: "administrator", active: true });
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
    if (url.endsWith("/platform/workflows/recent")) {
      return jsonResponse([{
        workflow_id: "workflow-test",
        status: "completed",
        actor: "endpoint-sensor",
        created_at: createdAt,
        event_count: 1,
        alert_count: 1,
        persisted: true,
        detection_model: "severity-anomaly-baseline",
        detection_model_version: "1.0.0",
        human_approval_required: true,
        execution_permitted: false,
        steps: ["detection", "correlation", "risk", "explainability", "response"].map((agent, index) => ({
          sequence: index + 1,
          agent,
          status: "completed",
          started_at: createdAt,
          completed_at: createdAt,
          duration_ms: 0.4,
          detail: "Structured handoff completed.",
          input_digest: `input-${index}`,
          output_digest: `output-${index}`,
        })),
      }]);
    }
    if (url.endsWith("/platform/models")) {
      return jsonResponse({
        experiment_version: "phase7-evaluation-v1",
        dataset_version: "synthetic-events-v1",
        models: [
          { id: "severity-anomaly-baseline", name: "Severity + anomaly baseline", version: "1.0.0", kind: "deterministic_baseline", deployment: "runtime", purpose: "Live findings", architecture: "Auditable contributions", metrics: null },
          { id: "graphsage", name: "Causal GraphSAGE", version: "phase7-evaluation-v1", kind: "graph_neural_network", deployment: "evaluated_offline", purpose: "Graph classification", architecture: "Two-layer causal mean aggregation", metrics: { precision: 1, recall: 0.6667, f1: 0.8, roc_auc: 0.7778, samples: 18 } },
        ],
        limitations: ["Synthetic test data only."],
      });
    }
    if (url.endsWith("/platform/scenarios")) return jsonResponse([scenario]);
    if (url.endsWith("/platform/scenarios/credential-attack/run")) {
      return jsonResponse({
        workflow: {
          workflow_id: "workflow-scenario",
          status: "completed",
          detection: {
            findings: [
              { event_id: "sample-1", classification: "attack", confidence: 0.95, anomaly_score: 0.95, model_name: "severity-anomaly-baseline", model_version: "1.0.0" },
              { event_id: "sample-2", classification: "attack", confidence: 1, anomaly_score: 1, model_name: "severity-anomaly-baseline", model_version: "1.0.0" },
            ],
          },
          correlation: { incidents: [{ id: "incident-sample", event_ids: ["sample-1", "sample-2"] }], attack_graph: { nodes: [{ id: "node-1", entity_type: "host", key: "sample-host", label: "sample-host", risk_score: 90 }], edges: [] } },
          risk: { assessments: [{ event_id: "sample-1", risk: { score: 91, level: "critical", components: {} } }] },
          explainability: { explanations: [{ event_id: "sample-1", summary: "Classified as attack from severity and anomaly evidence.", limitations: "Simulation" }] },
          response: { recommendations: [{ recommendation: { action: "reset_credentials", target: "sample-admin", priority: "critical", rationale: "Protect the account.", requires_human_approval: true, automatic_execution: false }, supporting_event_ids: ["sample-1"] }] },
          audit_trail: ["detection", "correlation", "risk", "explainability", "response"].map((agent, index) => ({ sequence: index + 1, agent, status: "completed", started_at: createdAt, completed_at: createdAt, detail: "Structured handoff completed." })),
          human_approval: { required: true, approval_status: "pending", execution_permitted: false },
        },
        stored_event_ids: [],
        stored_alert_ids: [],
      });
    }
    if (url.endsWith("/sensors")) return jsonResponse([]);
    if (url.endsWith("/sensors/status")) {
      return jsonResponse({ ingest_configured: true, sensors_total: 0, sensors_online: 0 });
    }
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
  it("starts at a blank secure login when setup is complete", async () => {
    vi.stubGlobal("fetch", successfulApi());
    render(<DashboardApp />);

    expect(await screen.findByRole("heading", { name: "Welcome back" })).toBeInTheDocument();
    expect(screen.getByLabelText("Username")).toHaveValue("");
    expect(screen.getByLabelText("Password")).toHaveValue("");
    expect(screen.getByText(/No default accounts/)).toBeInTheDocument();
  });

  it("shows one-time owner creation on a fresh installation", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse({ setup_required: true })));
    render(<DashboardApp />);

    expect(await screen.findByRole("heading", { name: "Secure this installation" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create owner account" })).toBeInTheDocument();
  });

  it("authenticates and loads the protected overview", async () => {
    const fetchMock = successfulApi();
    vi.stubGlobal("fetch", fetchMock);
    render(<DashboardApp />);

    await screen.findByRole("heading", { name: "Welcome back" });
    fireEvent.change(screen.getByLabelText("Username"), { target: { value: "owner" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "correct-password" } });
    fireEvent.click(screen.getByRole("button", { name: "Enter workspace" }));

    expect(await screen.findByRole("heading", { name: "Security overview" })).toBeInTheDocument();
    expect(await screen.findByText("Suspicious privileged login")).toBeInTheDocument();
    expect(screen.getByText(/Local protected API/i)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/auth/me",
      expect.objectContaining({ headers: expect.objectContaining({ Authorization: "Bearer test-token" }) }),
    );
  });

  it("shows audited agent handoffs and the honest GNN deployment state", async () => {
    vi.stubGlobal("fetch", successfulApi());
    render(<DashboardApp />);

    await screen.findByRole("heading", { name: "Welcome back" });
    fireEvent.change(screen.getByLabelText("Username"), { target: { value: "owner" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "correct-password" } });
    fireEvent.click(screen.getByRole("button", { name: "Enter workspace" }));

    await screen.findByRole("heading", { name: "Security overview" });
    fireEvent.click(screen.getByRole("button", { name: "Agent workflow" }));
    expect(await screen.findByRole("heading", { name: "How the agents work together" })).toBeInTheDocument();
    expect(screen.getByText("Detection agent")).toBeInTheDocument();
    expect(screen.getByText("Always required")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Models & GNN" }));
    expect(await screen.findByRole("heading", { name: "Models, GNN, and what is live" })).toBeInTheDocument();
    expect(screen.getByText("Causal GraphSAGE")).toBeInTheDocument();
    expect(screen.getByText("Evaluated offline")).toBeInTheDocument();
    expect(screen.getByText("Live now")).toBeInTheDocument();
  });

  it("runs a simulated threat scenario through all agents without persisting it", async () => {
    vi.stubGlobal("fetch", successfulApi());
    render(<DashboardApp />);

    await screen.findByRole("heading", { name: "Welcome back" });
    fireEvent.change(screen.getByLabelText("Username"), { target: { value: "owner" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "correct-password" } });
    fireEvent.click(screen.getByRole("button", { name: "Enter workspace" }));
    await screen.findByRole("heading", { name: "Security overview" });

    fireEvent.click(screen.getByRole("button", { name: "Threat scenarios" }));
    expect(await screen.findByRole("heading", { name: "Threat scenarios" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Credential attack" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Run scenario" }));

    expect(await screen.findByText(/Classification matched/)).toBeInTheDocument();
    expect(screen.getByText("Safe simulation verified")).toBeInTheDocument();
    expect(screen.getByText(/0 events stored/)).toBeInTheDocument();
  });

  it("shows a generic message when credentials are rejected", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).endsWith("/auth/setup-status")) return jsonResponse({ setup_required: false });
      return jsonResponse({ detail: "internal authentication detail" }, 401);
    }));
    render(<DashboardApp />);

    await screen.findByRole("heading", { name: "Welcome back" });
    fireEvent.change(screen.getByLabelText("Username"), { target: { value: "owner" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "incorrect-password" } });
    fireEvent.click(screen.getByRole("button", { name: "Enter workspace" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("The username or password was not accepted.");
    await waitFor(() => expect(screen.getByRole("button", { name: "Enter workspace" })).toBeEnabled());
  });
});
