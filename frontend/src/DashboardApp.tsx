import {
  type FormEvent,
  lazy,
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  ApiError,
  api,
  createInitialAdministrator,
  getCurrentUser,
  getSetupStatus,
  login,
} from "./api";
import type {
  Alert,
  AuditLog,
  Explanation,
  EndpointSensor,
  Feedback,
  Incident,
  IncidentDetail,
  ModelCatalog,
  Overview,
  Recommendation,
  RecommendationResult,
  SensorServiceStatus,
  Severity,
  User,
  WorkflowRun,
} from "./types";
import "./dashboard.css";

type View =
  | "overview"
  | "devices"
  | "alerts"
  | "incident"
  | "graph"
  | "workflow"
  | "models"
  | "explain"
  | "feedback"
  | "audit";

const AttackGraphView = lazy(() => import("./AttackGraphView"));

const navigationGroups: Array<{
  label: string;
  items: Array<{ id: View; label: string; icon: string }>;
}> = [
  {
    label: "Monitor",
    items: [
      { id: "overview", label: "Home", icon: "◫" },
      { id: "devices", label: "This device", icon: "▣" },
      { id: "alerts", label: "Alerts", icon: "△" },
    ],
  },
  {
    label: "Investigate",
    items: [
      { id: "incident", label: "Incident", icon: "⌁" },
      { id: "graph", label: "Attack graph", icon: "⌘" },
      { id: "explain", label: "Why this alert?", icon: "◎" },
    ],
  },
  {
    label: "Intelligence",
    items: [
      { id: "workflow", label: "Agent workflow", icon: "⇢" },
      { id: "models", label: "Models & GNN", icon: "◇" },
      { id: "feedback", label: "Feedback", icon: "✓" },
    ],
  },
];

const severityOrder: Severity[] = ["critical", "high", "medium", "low", "informational"];

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function titleCase(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

function SeverityPill({ severity }: { severity: Severity }) {
  return <span className={`severity severity-${severity}`}>{severity}</span>;
}

function SetupScreen({ onAuthenticated }: { onAuthenticated: (token: string, user: User) => void }) {
  const [fullName, setFullName] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (password !== confirmation) {
      setError("The passwords do not match.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const token = await createInitialAdministrator(username, fullName, password);
      const user = await getCurrentUser(token.access_token);
      onAuthenticated(token.access_token, user);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to finish local setup.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login-page">
      <section className="login-story">
        <div className="brand-lockup"><span>EC</span><strong>ECTI</strong></div>
        <div>
          <p className="section-kicker">First-run device setup</p>
          <h1>Protect this PC.<br />Own the account.</h1>
          <p>
            Create the only initial administrator. ECTI ships without demo identities, default
            passwords, or cloud accounts.
          </p>
        </div>
        <div className="login-proof">
          <span>Local web dashboard</span><span>Host telemetry sensor</span><span>Human-controlled response</span>
        </div>
      </section>
      <section className="login-panel">
        <form className="login-card" onSubmit={submit}>
          <div className="login-mark">EC</div>
          <p className="section-kicker">Create platform owner</p>
          <h2>Secure this installation</h2>
          <p className="muted">Choose unique credentials for this computer.</p>
          <label>Full name<input required minLength={2} maxLength={255} value={fullName} onChange={(event) => setFullName(event.target.value)} autoComplete="name" /></label>
          <label>Username<input required minLength={3} maxLength={100} pattern="[A-Za-z0-9_.-]+" value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" /></label>
          <label>Password<input required type="password" minLength={12} maxLength={128} value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="new-password" /></label>
          <label>Confirm password<input required type="password" minLength={12} maxLength={128} value={confirmation} onChange={(event) => setConfirmation(event.target.value)} autoComplete="new-password" /></label>
          {error && <p className="form-error" role="alert">{error}</p>}
          <button className="primary-button" disabled={loading}>{loading ? "Securing…" : "Create owner account"}</button>
          <p className="demo-note">This one-time screen closes permanently after account creation.</p>
        </form>
      </section>
    </main>
  );
}

function LoginScreen({ onAuthenticated }: { onAuthenticated: (token: string, user: User) => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const token = await login(username, password);
      const user = await getCurrentUser(token.access_token);
      onAuthenticated(token.access_token, user);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to sign in.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login-page">
      <section className="login-story">
        <div className="brand-lockup"><span>EC</span><strong>ECTI</strong></div>
        <div>
          <p className="section-kicker">Local endpoint protection</p>
          <h1>See the attack path.<br />Understand the decision.</h1>
          <p>
            Correlate security events, prioritize risk, and review every recommendation before a
            human analyst decides what happens next.
          </p>
        </div>
        <div className="login-proof">
          <span>Explainable detections</span><span>Audited workflow</span><span>No auto-response</span>
        </div>
      </section>
      <section className="login-panel">
        <form className="login-card" onSubmit={submit}>
          <div className="login-mark">EC</div>
          <p className="section-kicker">Secure analyst access</p>
          <h2>Welcome back</h2>
          <p className="muted">Sign in with the owner account created during local setup.</p>
          <label>
            Username
            <input value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" />
          </label>
          <label>
            Password
            <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" />
          </label>
          {error && <p className="form-error" role="alert">{error}</p>}
          <button className="primary-button" disabled={loading}>{loading ? "Verifying…" : "Enter workspace"}</button>
          <p className="demo-note">No default accounts or passwords are built into ECTI.</p>
        </form>
      </section>
    </main>
  );
}

function OverviewView({
  overview,
  service,
  latestWorkflow,
  onNavigate,
}: {
  overview: Overview | null;
  service: SensorServiceStatus | null;
  latestWorkflow?: WorkflowRun;
  onNavigate: (view: View) => void;
}) {
  if (!overview) return <LoadingState />;
  const total = Math.max(1, overview.severity_distribution.reduce((sum, item) => sum + item.count, 0));
  const metrics = [
    ["Open alerts", overview.open_alerts, "Needs triage"],
    ["Active incidents", overview.active_incidents, "Under investigation"],
    ["Critical signals", overview.critical_alerts, "High-priority evidence"],
    ["Events monitored", overview.monitored_events, "Host telemetry"],
  ];
  return (
    <div className="view-stack">
      <header className="view-heading">
        <div><p className="section-kicker">Operational picture</p><h1>Security overview</h1><p>Evidence, risk, and analyst decisions in one workspace.</p></div>
        <div className="live-chip"><span /> Live endpoint feed</div>
      </header>
      <section className="metric-grid">
        {metrics.map(([label, value, note]) => (
          <article className="metric-card" key={label as string}>
            <p>{label}</p><strong>{value}</strong><span>{note}</span>
          </article>
        ))}
      </section>
      <section className="journey-panel panel">
        <div className="panel-heading">
          <div><p className="section-kicker">Protection journey</p><h2>What should I look at next?</h2></div>
          <span className="count-chip">4 clear steps</span>
        </div>
        <div className="journey-steps">
          <button onClick={() => onNavigate("devices")} className={service?.sensors_online ? "complete" : "attention"}>
            <span>1</span><div><strong>Collect</strong><small>{service?.sensors_online ? "Device sensor is online" : "Start the device sensor"}</small></div><i>Open →</i>
          </button>
          <button onClick={() => onNavigate("alerts")} className={overview.open_alerts ? "attention" : "complete"}>
            <span>2</span><div><strong>Triage</strong><small>{overview.open_alerts ? `${overview.open_alerts} alerts need review` : "No open alerts"}</small></div><i>Open →</i>
          </button>
          <button onClick={() => onNavigate("workflow")} className={latestWorkflow?.status === "completed" ? "complete" : "attention"}>
            <span>3</span><div><strong>Understand</strong><small>{latestWorkflow ? "Review the latest agent handoffs" : "Waiting for an agent run"}</small></div><i>Open →</i>
          </button>
          <button onClick={() => onNavigate("feedback")}>
            <span>4</span><div><strong>Decide</strong><small>Record the human verdict</small></div><i>Open →</i>
          </button>
        </div>
      </section>
      <section className="overview-grid">
        <article className="panel">
          <div className="panel-heading"><div><p className="section-kicker">Detection load</p><h2>Severity distribution</h2></div><span className="model-badge">{overview.model_name} · v{overview.model_version}</span></div>
          <div className="severity-chart">
            {severityOrder.map((severity) => {
              const count = overview.severity_distribution.find((item) => item.severity === severity)?.count ?? 0;
              return <div className="severity-row" key={severity}><span>{severity}</span><div><i className={`bar-${severity}`} style={{ width: `${Math.max(count ? 10 : 0, (count / total) * 100)}%` }} /></div><strong>{count}</strong></div>;
            })}
          </div>
        </article>
        <article className="panel recent-panel">
          <div className="panel-heading"><div><p className="section-kicker">Priority queue</p><h2>Recent alerts</h2></div><button className="text-button" onClick={() => onNavigate("alerts")}>View all →</button></div>
          {overview.recent_alerts.map((alert) => <div className="recent-alert" key={alert.id}><span className={`signal-dot dot-${alert.severity}`} /><div><strong>{alert.title}</strong><small>{formatDate(alert.created_at)} · {(alert.confidence * 100).toFixed(0)}% confidence</small></div><SeverityPill severity={alert.severity} /></div>)}
        </article>
      </section>
      <section className="assurance-strip"><div><span className="assurance-icon">✓</span><div><strong>Human approval enforced</strong><p>All mitigation recommendations remain pending. This prototype has no execution route.</p></div></div><span className="operational">{overview.model_status}</span></section>
    </div>
  );
}

function DevicesView({ sensors, service }: { sensors: EndpointSensor[]; service: SensorServiceStatus | null }) {
  return (
    <div className="view-stack">
      <header className="view-heading">
        <div>
          <p className="section-kicker">Host telemetry</p>
          <h1>This device</h1>
          <p>The Windows sensor observes defensive signals on this PC and sends them to the local analysis service.</p>
        </div>
        <span className={`live-chip ${service?.sensors_online ? "" : "offline-chip"}`}><span />{service?.sensors_online ? "Sensor online" : "Sensor offline"}</span>
      </header>
      {!service?.ingest_configured && <div className="error-banner"><span>Sensor ingestion has not been configured. Run the Windows installer to generate the local secret.</span></div>}
      {!sensors.length ? (
        <section className="empty-state">
          <strong>No endpoint sensor has checked in yet.</strong>
          <p>Install or start the ECTI Windows sensor, then this page will update after its first heartbeat.</p>
        </section>
      ) : (
        <section className="device-grid">
          {sensors.map((sensor) => (
            <article className="panel device-card" key={sensor.id}>
              <div className="panel-heading"><div><p className="section-kicker">Protected endpoint</p><h2>{sensor.hostname}</h2></div><span className={`sensor-status sensor-${sensor.status}`}>{sensor.status}</span></div>
              <dl>
                <div><dt>Operating system</dt><dd>{sensor.operating_system}</dd></div>
                <div><dt>Sensor version</dt><dd>{sensor.agent_version}</dd></div>
                <div><dt>Last heartbeat</dt><dd>{formatDate(sensor.last_seen_at)}</dd></div>
                <div><dt>Last security event</dt><dd>{sensor.last_event_at ? formatDate(sensor.last_event_at) : "No signal reported"}</dd></div>
                <div><dt>Addresses</dt><dd>{sensor.ip_addresses.join(", ") || "Local only"}</dd></div>
              </dl>
              <div className="capability-list">
                {["windows_event_log", "process_monitor", "network_monitor"].map((capability) => (
                  <span key={capability} className={sensor.capabilities[capability] ? "enabled" : "disabled"}>
                    {sensor.capabilities[capability] ? "✓" : "–"} {titleCase(capability)}
                  </span>
                ))}
              </div>
              <p className="limitation">The sensor reports evidence and recommendations only. It cannot terminate processes, block traffic, or modify Windows security controls.</p>
            </article>
          ))}
        </section>
      )}
    </div>
  );
}

function AlertsView({ alerts, selectedId, onSelect }: { alerts: Alert[]; selectedId: string; onSelect: (id: string) => void }) {
  const [query, setQuery] = useState("");
  const [severity, setSeverity] = useState<Severity | "all">("all");
  const filtered = alerts.filter((alert) => (severity === "all" || alert.severity === severity) && alert.title.toLowerCase().includes(query.toLowerCase()));
  return (
    <div className="view-stack">
      <header className="view-heading"><div><p className="section-kicker">Analyst triage</p><h1>Alert queue</h1><p>Search, filter, and open the evidence behind each signal.</p></div><span className="count-chip">{filtered.length} results</span></header>
      <section className="filter-bar"><input aria-label="Search alerts" placeholder="Search alerts…" value={query} onChange={(event) => setQuery(event.target.value)} /><select aria-label="Filter by severity" value={severity} onChange={(event) => setSeverity(event.target.value as Severity | "all")}><option value="all">All severities</option>{severityOrder.map((item) => <option key={item}>{item}</option>)}</select></section>
      <section className="table-panel"><div className="alert-table table-header"><span>Signal</span><span>Severity</span><span>Confidence</span><span>Status</span><span>Observed</span></div>{filtered.map((alert) => <button className={`alert-table table-row ${selectedId === alert.id ? "selected-row" : ""}`} key={alert.id} onClick={() => onSelect(alert.id)}><span><i className={`signal-dot dot-${alert.severity}`} /><span><strong>{alert.title}</strong><small>{titleCase(alert.alert_type)}</small></span></span><SeverityPill severity={alert.severity} /><span className="confidence"><i style={{ width: `${alert.confidence * 100}%` }} /><em>{(alert.confidence * 100).toFixed(0)}%</em></span><span>{titleCase(alert.status)}</span><span>{formatDate(alert.created_at)}</span></button>)}</section>
    </div>
  );
}

function IncidentView({ detail, recommendations }: { detail: IncidentDetail | null; recommendations: Recommendation[] }) {
  if (!detail) return <LoadingState />;
  return (
    <div className="view-stack">
      <header className="view-heading incident-heading"><div><p className="section-kicker">Correlated investigation</p><h1>{detail.incident.title}</h1><p>{detail.incident.description}</p></div><div className="risk-orb"><strong>{detail.incident.risk_score.toFixed(0)}</strong><span>risk / 100</span></div></header>
      <section className="incident-grid">
        <article className="panel timeline-panel"><div className="panel-heading"><div><p className="section-kicker">Sequence</p><h2>Correlated timeline</h2></div><SeverityPill severity={detail.incident.severity} /></div><div className="timeline">{detail.alerts.map((alert, index) => <div className="timeline-event" key={alert.id}><span>{String(index + 1).padStart(2, "0")}</span><div><strong>{alert.title}</strong><p>{alert.description}</p><small>{formatDate(alert.created_at)} · {(alert.confidence * 100).toFixed(0)}% confidence</small></div></div>)}</div></article>
        <article className="panel"><div className="panel-heading"><div><p className="section-kicker">Decision support</p><h2>Recommended actions</h2></div><span className="pending-badge">Approval pending</span></div><div className="recommendation-list">{recommendations.map((item) => <div className="recommendation" key={`${item.action}-${item.target}`}><div><span>{titleCase(item.action)}</span><SeverityPill severity={item.priority} /></div><strong>{item.target}</strong><p>{item.rationale}</p><small>Human approval required · No automatic execution</small></div>)}</div></article>
      </section>
    </div>
  );
}

function ExplainView({ alert, explanations, recommendations }: { alert: Alert | undefined; explanations: Explanation[]; recommendations: Recommendation[] }) {
  if (!alert) return <div className="empty-state">Select an alert from the queue.</div>;
  const explanation = explanations[0];
  return (
    <div className="view-stack">
      <header className="view-heading"><div><p className="section-kicker">Model transparency</p><h1>Why this alert?</h1><p>{alert.title}</p></div><div className="confidence-orb"><strong>{(alert.confidence * 100).toFixed(0)}%</strong><span>confidence</span></div></header>
      <section className="explain-grid"><article className="panel explanation-copy"><p className="section-kicker">Analyst-readable reason</p><h2>{explanation?.summary ?? "No stored explanation is available."}</h2><p className="limitation">{explanation?.limitations}</p></article><article className="panel"><p className="section-kicker">Important evidence</p><h2>Contributing signals</h2><div className="feature-list">{explanation?.evidence.important_features?.map((feature, index) => <div key={feature.name}><span>{feature.name.replaceAll("_", " ")}</span><strong>{String(feature.value)}</strong><i style={{ width: `${95 - index * 18}%` }} /></div>) ?? <p className="muted">No feature evidence recorded.</p>}</div></article></section>
      <section className="panel safe-actions"><div className="panel-heading"><div><p className="section-kicker">Suggested next step</p><h2>Recommendations remain advisory</h2></div><span className="pending-badge">Human controlled</span></div><div className="compact-recommendations">{recommendations.map((item) => <div key={`${item.action}-${item.target}`}><strong>{titleCase(item.action)}</strong><span>{item.target}</span><p>{item.rationale}</p></div>)}</div></section>
    </div>
  );
}

const agentDescriptions = {
  detection: ["Detection", "Classifies each endpoint event and records contributing signals."],
  correlation: ["Correlation", "Groups related findings and constructs the attack graph."],
  risk: ["Risk", "Combines confidence, asset context, attack stage, and anomaly level."],
  explainability: ["Explainability", "Turns model and graph evidence into analyst-readable reasons."],
  response: ["Response", "Suggests bounded actions without executing any change."],
} as const;

function WorkflowView({ runs }: { runs: WorkflowRun[] }) {
  const run = runs[0];
  return (
    <div className="view-stack">
      <header className="view-heading">
        <div><p className="section-kicker">Audited orchestration</p><h1>How the agents work together</h1><p>Every endpoint signal passes through five bounded agents. Each handoff is validated, timed, hashed, and stopped at a human approval gate.</p></div>
        <span className={`workflow-state state-${run?.status ?? "waiting"}`}>{run ? titleCase(run.status) : "Waiting for a run"}</span>
      </header>
      <section className="agent-flow" aria-label="ECTI agent workflow">
        {Object.entries(agentDescriptions).map(([agent, [name, description]], index) => {
          const step = run?.steps.find((item) => item.agent === agent);
          return (
            <article className={`agent-card agent-${step?.status ?? "waiting"}`} key={agent}>
              <div className="agent-number">{index + 1}</div>
              <div className="agent-copy"><span>{name} agent</span><p>{description}</p></div>
              <div className="agent-result">
                <strong>{step ? titleCase(step.status) : "No run yet"}</strong>
                <small>{step ? `${step.duration_ms < 0.1 ? "<0.1" : step.duration_ms.toFixed(1)} ms` : "Waiting for telemetry"}</small>
              </div>
            </article>
          );
        })}
        <article className="agent-card approval-card">
          <div className="agent-number">6</div>
          <div className="agent-copy"><span>Human approval</span><p>An analyst verifies evidence and decides outside the automated workflow.</p></div>
          <div className="agent-result"><strong>Always required</strong><small>Execution disabled</small></div>
        </article>
      </section>
      {run ? (
        <section className="workflow-detail-grid">
          <article className="panel">
            <div className="panel-heading"><div><p className="section-kicker">Latest run</p><h2>{run.workflow_id}</h2></div><span className="model-badge">{run.detection_model} · v{run.detection_model_version}</span></div>
            <dl className="workflow-facts">
              <div><dt>Started</dt><dd>{formatDate(run.created_at)}</dd></div>
              <div><dt>Input</dt><dd>{run.event_count} event{run.event_count === 1 ? "" : "s"}</dd></div>
              <div><dt>Output</dt><dd>{run.alert_count} stored alert{run.alert_count === 1 ? "" : "s"}</dd></div>
              <div><dt>Actor</dt><dd>{run.actor}</dd></div>
            </dl>
          </article>
          <article className="panel handoff-panel">
            <div className="panel-heading"><div><p className="section-kicker">Validated handoffs</p><h2>Execution evidence</h2></div></div>
            {run.steps.map((step) => <div className="handoff-row" key={step.sequence}><span>{step.sequence}</span><div><strong>{titleCase(step.agent)}</strong><small>{step.detail}</small></div><code>{step.output_digest?.slice(0, 10) ?? "skipped"}</code></div>)}
          </article>
        </section>
      ) : (
        <section className="empty-state"><strong>No audited workflow is available yet.</strong><p>When the endpoint sensor reports a new security signal, this page will show every agent handoff.</p></section>
      )}
    </div>
  );
}

function ModelsView({ catalog }: { catalog: ModelCatalog | null }) {
  if (!catalog) return <LoadingState />;
  const graphSage = catalog.models.find((model) => model.id === "graphsage");
  return (
    <div className="view-stack">
      <header className="view-heading">
        <div><p className="section-kicker">Model transparency</p><h1>Models, GNN, and what is live</h1><p>ECTI separates the detector serving this device from research models evaluated offline. This prevents experimental metrics from being mistaken for live protection.</p></div>
        <span className="live-chip"><span /> Runtime model identified</span>
      </header>
      <section className="model-catalog">
        {catalog.models.map((model) => (
          <article className={`panel model-card model-${model.deployment}`} key={model.id}>
            <div className="panel-heading"><div><p className="section-kicker">{titleCase(model.kind)}</p><h2>{model.name}</h2></div><span className={model.deployment === "runtime" ? "runtime-badge" : "evaluation-badge"}>{model.deployment === "runtime" ? "Live now" : "Evaluated offline"}</span></div>
            <p>{model.purpose}</p><div className="architecture-note">{model.architecture}</div>
            {model.metrics ? <div className="model-metrics"><div><strong>{(model.metrics.precision * 100).toFixed(0)}%</strong><span>Precision</span></div><div><strong>{(model.metrics.recall * 100).toFixed(0)}%</strong><span>Recall</span></div><div><strong>{model.metrics.f1.toFixed(2)}</strong><span>F1</span></div><div><strong>{model.metrics.roc_auc.toFixed(2)}</strong><span>ROC-AUC</span></div></div> : <p className="runtime-note">Deterministic and auditable per event; offline comparison metrics do not apply.</p>}
          </article>
        ))}
      </section>
      {graphSage && <section className="panel gnn-explainer"><div><p className="section-kicker">Graph Neural Network</p><h2>How causal GraphSAGE reads an attack sequence</h2><p>Each event becomes a node. Only prior events sharing an IP, user, or host send information forward, avoiding future-data leakage.</p></div><div className="gnn-diagram"><div><span>01</span><strong>Event features</strong><small>16 encoded signals</small></div><i>→</i><div><span>02</span><strong>Causal neighbors</strong><small>Prior related nodes</small></div><i>→</i><div><span>03</span><strong>2-layer GraphSAGE</strong><small>Mean aggregation</small></div><i>→</i><div><span>04</span><strong>Attack probability</strong><small>Offline evaluation</small></div></div></section>}
      <section className="model-limitations"><div><strong>Read the metrics carefully</strong><span>{catalog.experiment_version} · {catalog.dataset_version}</span></div><ul>{catalog.limitations.map((item) => <li key={item}>{item}</li>)}</ul></section>
    </div>
  );
}

function FeedbackView({ alerts, items, onSubmitted, token }: { alerts: Alert[]; items: Feedback[]; onSubmitted: () => void; token: string }) {
  const [alertId, setAlertId] = useState(alerts[0]?.id ?? "");
  const [verdict, setVerdict] = useState("needs_review");
  const [comment, setComment] = useState("");
  const [message, setMessage] = useState("");
  useEffect(() => { if (!alertId && alerts[0]) setAlertId(alerts[0].id); }, [alertId, alerts]);
  async function submit(event: FormEvent) {
    event.preventDefault();
    await api("/platform/feedback", token, { method: "POST", body: JSON.stringify({ alert_id: alertId, verdict, comment: comment || null }) });
    setComment(""); setMessage("Feedback recorded in the audit trail."); onSubmitted();
  }
  return <div className="view-stack"><header className="view-heading"><div><p className="section-kicker">Human signal</p><h1>Analyst feedback</h1><p>Confirm, dismiss, or flag detections for later model evaluation.</p></div></header><section className="feedback-grid"><form className="panel feedback-form" onSubmit={submit}><label>Alert<select value={alertId} onChange={(event) => setAlertId(event.target.value)}>{alerts.map((alert) => <option value={alert.id} key={alert.id}>{alert.title}</option>)}</select></label><label>Verdict<select value={verdict} onChange={(event) => setVerdict(event.target.value)}><option value="confirmed">Confirmed threat</option><option value="dismissed">Dismissed</option><option value="needs_review">Needs review</option></select></label><label>Analyst note<textarea rows={5} maxLength={2000} value={comment} onChange={(event) => setComment(event.target.value)} placeholder="Record the evidence behind your decision…" /></label><button className="primary-button">Submit feedback</button>{message && <p className="success-message">{message}</p>}</form><article className="panel"><div className="panel-heading"><div><p className="section-kicker">Recent decisions</p><h2>Feedback history</h2></div></div><div className="feedback-history">{items.length ? items.map((item) => <div key={item.id}><span className={`verdict verdict-${item.verdict}`}>{titleCase(item.verdict)}</span><strong>{item.analyst}</strong><p>{item.comment || "No comment supplied."}</p><small>{formatDate(item.created_at)}</small></div>) : <p className="muted">No feedback has been submitted yet.</p>}</div></article></section></div>;
}

function AuditView({ items }: { items: AuditLog[] }) {
  return <div className="view-stack"><header className="view-heading"><div><p className="section-kicker">Administrator view</p><h1>Audit log</h1><p>Security-sensitive actions recorded by the platform.</p></div></header><section className="table-panel"><div className="audit-table table-header"><span>Action</span><span>Actor</span><span>Resource</span><span>Time</span></div>{items.map((item) => <div className="audit-table audit-row" key={item.id}><span>{titleCase(item.action)}</span><strong>{item.actor_username}</strong><span>{item.resource_type}</span><span>{formatDate(item.created_at)}</span></div>)}</section></div>;
}

function LoadingState() { return <div className="loading-state"><span /><p>Loading protected workspace…</p></div>; }

function Dashboard({ token, user, onLogout }: { token: string; user: User; onLogout: () => void }) {
  const [view, setView] = useState<View>("overview");
  const [overview, setOverview] = useState<Overview | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [selectedAlertId, setSelectedAlertId] = useState("");
  const [selectedIncidentId, setSelectedIncidentId] = useState("");
  const [incidentDetail, setIncidentDetail] = useState<IncidentDetail | null>(null);
  const [explanations, setExplanations] = useState<Explanation[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [feedback, setFeedback] = useState<Feedback[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [sensors, setSensors] = useState<EndpointSensor[]>([]);
  const [sensorService, setSensorService] = useState<SensorServiceStatus | null>(null);
  const [workflowRuns, setWorkflowRuns] = useState<WorkflowRun[]>([]);
  const [modelCatalog, setModelCatalog] = useState<ModelCatalog | null>(null);
  const [error, setError] = useState("");

  const handleError = useCallback((caught: unknown) => {
    if (caught instanceof ApiError && caught.status === 401) onLogout();
    else setError(caught instanceof Error ? caught.message : "The workspace could not be loaded.");
  }, [onLogout]);

  const loadFeedback = useCallback(() => api<Feedback[]>("/platform/feedback", token).then(setFeedback).catch(handleError), [handleError, token]);

  useEffect(() => {
    Promise.all([
      api<Overview>("/platform/overview", token),
      api<Alert[]>("/platform/alerts", token),
      api<Incident[]>("/platform/incidents", token),
      api<Feedback[]>("/platform/feedback", token),
      api<EndpointSensor[]>("/sensors", token),
      api<SensorServiceStatus>("/sensors/status", token),
      api<WorkflowRun[]>("/platform/workflows/recent", token),
      api<ModelCatalog>("/platform/models", token),
    ]).then(([nextOverview, nextAlerts, nextIncidents, nextFeedback, nextSensors, nextSensorService, nextWorkflowRuns, nextModelCatalog]) => {
      setOverview(nextOverview); setAlerts(nextAlerts); setIncidents(nextIncidents); setFeedback(nextFeedback);
      setSensors(nextSensors); setSensorService(nextSensorService);
      setWorkflowRuns(nextWorkflowRuns); setModelCatalog(nextModelCatalog);
      setSelectedAlertId((current) => current || nextAlerts[0]?.id || "");
      setSelectedIncidentId((current) => current || nextIncidents[0]?.id || "");
    }).catch(handleError);
  }, [handleError, token]);

  useEffect(() => {
    if (!selectedAlertId) return;
    Promise.all([
      api<Explanation[]>(`/platform/alerts/${selectedAlertId}/explanations`, token),
      api<RecommendationResult>(`/platform/alerts/${selectedAlertId}/recommendations`, token),
    ]).then(([nextExplanations, nextRecommendations]) => {
      setExplanations(nextExplanations); setRecommendations(nextRecommendations.recommendations);
    }).catch(handleError);
  }, [handleError, selectedAlertId, token]);

  useEffect(() => {
    if (!selectedIncidentId) return;
    api<IncidentDetail>(`/platform/incidents/${selectedIncidentId}`, token).then(setIncidentDetail).catch(handleError);
  }, [handleError, selectedIncidentId, token]);

  useEffect(() => {
    if (view === "audit" && user.role === "administrator") {
      api<AuditLog[]>("/platform/audit-logs", token).then(setAuditLogs).catch(handleError);
    }
  }, [handleError, token, user.role, view]);

  useEffect(() => {
    if (view !== "devices") return;
    const refresh = () => Promise.all([
      api<EndpointSensor[]>("/sensors", token),
      api<SensorServiceStatus>("/sensors/status", token),
    ]).then(([nextSensors, nextService]) => {
      setSensors(nextSensors);
      setSensorService(nextService);
    }).catch(handleError);
    const interval = window.setInterval(refresh, 30_000);
    return () => window.clearInterval(interval);
  }, [handleError, token, view]);

  useEffect(() => {
    if (view !== "workflow") return;
    const refresh = () => api<WorkflowRun[]>("/platform/workflows/recent", token).then(setWorkflowRuns).catch(handleError);
    const interval = window.setInterval(refresh, 15_000);
    return () => window.clearInterval(interval);
  }, [handleError, token, view]);

  const selectedAlert = useMemo(() => alerts.find((alert) => alert.id === selectedAlertId), [alerts, selectedAlertId]);
  const navGroups = user.role === "administrator"
    ? [...navigationGroups, { label: "Administration", items: [{ id: "audit" as View, label: "Audit log", icon: "▤" }] }]
    : navigationGroups;
  const navItems = navGroups.flatMap((group) => group.items);

  function openAlert(id: string) { setSelectedAlertId(id); setView("explain"); }

  return (
    <div className="dashboard-app">
      <aside className="sidebar">
        <div className="sidebar-brand"><span>EC</span><div><strong>ECTI</strong><small>Local security</small></div></div>
        <nav aria-label="Primary navigation">{navGroups.map((group) => <div className="nav-group" key={group.label}><p>{group.label}</p>{group.items.map((item) => <button key={item.id} aria-label={item.label} className={view === item.id ? "active" : ""} onClick={() => setView(item.id)}><span aria-hidden="true">{item.icon}</span>{item.label}</button>)}</div>)}</nav>
        <div className="sidebar-foot"><div className="user-avatar">{user.full_name.split(" ").map((part) => part[0]).slice(0, 2).join("")}</div><div><strong>{user.full_name}</strong><small>{titleCase(user.role)}</small></div><button aria-label="Sign out" onClick={onLogout}>↗</button></div>
      </aside>
      <main className="workspace">
        <header className="topbar"><div className="breadcrumb"><span>ECTI</span><i>/</i><strong>{navItems.find((item) => item.id === view)?.label}</strong></div><div><span className="protected-chip">● Local protected API</span><button className={`icon-button ${sensorService?.sensors_online ? "sensor-on" : ""}`} title="Open endpoint sensor status" onClick={() => setView("devices")}>{sensorService?.sensors_online ? "ON" : "OFF"}</button></div></header>
        {error && <div className="error-banner"><span>{error}</span><button onClick={() => setError("")}>Dismiss</button></div>}
        <div className="view-container">
          {view === "overview" && <OverviewView overview={overview} service={sensorService} latestWorkflow={workflowRuns[0]} onNavigate={setView} />}
          {view === "devices" && <DevicesView sensors={sensors} service={sensorService} />}
          {view === "alerts" && <AlertsView alerts={alerts} selectedId={selectedAlertId} onSelect={openAlert} />}
          {view === "incident" && <IncidentView detail={incidentDetail} recommendations={recommendations} />}
          {view === "graph" && <div className="view-stack"><header className="view-heading"><div><p className="section-kicker">Entity relationships</p><h1>Attack graph</h1><p>{incidentDetail?.incident.title ?? "Select an incident"}</p></div>{incidentDetail && <div className="risk-orb small"><strong>{incidentDetail.incident.risk_score.toFixed(0)}</strong><span>risk</span></div>}</header><Suspense fallback={<LoadingState />}><AttackGraphView graph={incidentDetail?.graph ?? null} /></Suspense></div>}
          {view === "workflow" && <WorkflowView runs={workflowRuns} />}
          {view === "models" && <ModelsView catalog={modelCatalog} />}
          {view === "explain" && <ExplainView alert={selectedAlert} explanations={explanations} recommendations={recommendations} />}
          {view === "feedback" && <FeedbackView alerts={alerts} items={feedback} token={token} onSubmitted={loadFeedback} />}
          {view === "audit" && <AuditView items={auditLogs} />}
        </div>
      </main>
    </div>
  );
}

export default function DashboardApp() {
  const [session, setSession] = useState<{ token: string; user: User } | null>(null);
  const [setupRequired, setSetupRequired] = useState<boolean | null>(null);
  const [startupError, setStartupError] = useState("");

  useEffect(() => {
    getSetupStatus()
      .then((status) => setSetupRequired(status.setup_required))
      .catch((caught) => setStartupError(
        caught instanceof Error ? caught.message : "Unable to reach the local ECTI service.",
      ));
  }, []);

  const authenticated = (token: string, user: User) => {
    setSetupRequired(false);
    setSession({ token, user });
  };
  if (session) return <Dashboard token={session.token} user={session.user} onLogout={() => setSession(null)} />;
  if (startupError) return <main className="login-page"><section className="login-story"><div className="brand-lockup"><span>EC</span><strong>ECTI</strong></div><div><p className="section-kicker">Local service unavailable</p><h1>ECTI could not start.</h1><p>{startupError}</p></div></section><section className="login-panel"><div className="login-card"><h2>Check the local services</h2><p className="muted">Start the ECTI application and reload this page.</p><button className="primary-button" onClick={() => window.location.reload()}>Retry connection</button></div></section></main>;
  if (setupRequired === null) return <LoadingState />;
  if (setupRequired) return <SetupScreen onAuthenticated={authenticated} />;
  return <LoginScreen onAuthenticated={authenticated} />;
}
