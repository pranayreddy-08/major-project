import {
  type FormEvent,
  lazy,
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import { ApiError, api, getCurrentUser, login } from "./api";
import type {
  Alert,
  AuditLog,
  Explanation,
  Feedback,
  Incident,
  IncidentDetail,
  Overview,
  Recommendation,
  RecommendationResult,
  Severity,
  User,
} from "./types";
import "./dashboard.css";

type View = "overview" | "alerts" | "incident" | "graph" | "explain" | "feedback" | "audit";

const AttackGraphView = lazy(() => import("./AttackGraphView"));

const navigation: Array<{ id: View; label: string; icon: string }> = [
  { id: "overview", label: "Overview", icon: "◫" },
  { id: "alerts", label: "Alert queue", icon: "△" },
  { id: "incident", label: "Incident", icon: "⌁" },
  { id: "graph", label: "Attack graph", icon: "⌘" },
  { id: "explain", label: "Explainability", icon: "◎" },
  { id: "feedback", label: "Feedback", icon: "✓" },
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

function LoginScreen({ onAuthenticated }: { onAuthenticated: (token: string, user: User) => void }) {
  const [username, setUsername] = useState("analyst");
  const [password, setPassword] = useState("analyst-demo-only");
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
          <p className="section-kicker">Decision support · Phase 6</p>
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
          <p className="muted">Use the local synthetic-demo account to inspect the dashboard.</p>
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
          <p className="demo-note">Demo analyst: <code>analyst</code> / <code>analyst-demo-only</code></p>
        </form>
      </section>
    </main>
  );
}

function OverviewView({ overview, onOpenAlerts }: { overview: Overview | null; onOpenAlerts: () => void }) {
  if (!overview) return <LoadingState />;
  const total = Math.max(1, overview.severity_distribution.reduce((sum, item) => sum + item.count, 0));
  const metrics = [
    ["Open alerts", overview.open_alerts, "Needs triage"],
    ["Active incidents", overview.active_incidents, "Under investigation"],
    ["Critical signals", overview.critical_alerts, "High-priority evidence"],
    ["Events monitored", overview.monitored_events, "Synthetic workspace"],
  ];
  return (
    <div className="view-stack">
      <header className="view-heading">
        <div><p className="section-kicker">Operational picture</p><h1>Security overview</h1><p>Evidence, risk, and analyst decisions in one workspace.</p></div>
        <div className="live-chip"><span /> Live synthetic feed</div>
      </header>
      <section className="metric-grid">
        {metrics.map(([label, value, note]) => (
          <article className="metric-card" key={label as string}>
            <p>{label}</p><strong>{value}</strong><span>{note}</span>
          </article>
        ))}
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
          <div className="panel-heading"><div><p className="section-kicker">Priority queue</p><h2>Recent alerts</h2></div><button className="text-button" onClick={onOpenAlerts}>View all →</button></div>
          {overview.recent_alerts.map((alert) => <div className="recent-alert" key={alert.id}><span className={`signal-dot dot-${alert.severity}`} /><div><strong>{alert.title}</strong><small>{formatDate(alert.created_at)} · {(alert.confidence * 100).toFixed(0)}% confidence</small></div><SeverityPill severity={alert.severity} /></div>)}
        </article>
      </section>
      <section className="assurance-strip"><div><span className="assurance-icon">✓</span><div><strong>Human approval enforced</strong><p>All mitigation recommendations remain pending. This prototype has no execution route.</p></div></div><span className="operational">{overview.model_status}</span></section>
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
    ]).then(([nextOverview, nextAlerts, nextIncidents, nextFeedback]) => {
      setOverview(nextOverview); setAlerts(nextAlerts); setIncidents(nextIncidents); setFeedback(nextFeedback);
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

  const selectedAlert = useMemo(() => alerts.find((alert) => alert.id === selectedAlertId), [alerts, selectedAlertId]);
  const navItems = user.role === "administrator" ? [...navigation, { id: "audit" as View, label: "Audit log", icon: "▤" }] : navigation;

  function openAlert(id: string) { setSelectedAlertId(id); setView("explain"); }

  return (
    <div className="dashboard-app">
      <aside className="sidebar"><div className="sidebar-brand"><span>EC</span><div><strong>ECTI</strong><small>Analyst workspace</small></div></div><nav>{navItems.map((item) => <button key={item.id} className={view === item.id ? "active" : ""} onClick={() => setView(item.id)}><span>{item.icon}</span>{item.label}</button>)}</nav><div className="sidebar-foot"><div className="user-avatar">{user.full_name.split(" ").map((part) => part[0]).slice(0, 2).join("")}</div><div><strong>{user.full_name}</strong><small>{titleCase(user.role)}</small></div><button aria-label="Sign out" onClick={onLogout}>↗</button></div></aside>
      <main className="workspace"><header className="topbar"><div className="breadcrumb"><span>ECTI</span><i>/</i><strong>{navItems.find((item) => item.id === view)?.label}</strong></div><div><span className="protected-chip">● Protected API</span><button className="icon-button" title="Synthetic environment">SYN</button></div></header>{error && <div className="error-banner"><span>{error}</span><button onClick={() => setError("")}>Dismiss</button></div>}<div className="view-container">{view === "overview" && <OverviewView overview={overview} onOpenAlerts={() => setView("alerts")} />}{view === "alerts" && <AlertsView alerts={alerts} selectedId={selectedAlertId} onSelect={openAlert} />}{view === "incident" && <IncidentView detail={incidentDetail} recommendations={recommendations} />}{view === "graph" && <div className="view-stack"><header className="view-heading"><div><p className="section-kicker">Entity relationships</p><h1>Attack graph</h1><p>{incidentDetail?.incident.title ?? "Select an incident"}</p></div>{incidentDetail && <div className="risk-orb small"><strong>{incidentDetail.incident.risk_score.toFixed(0)}</strong><span>risk</span></div>}</header><Suspense fallback={<LoadingState />}><AttackGraphView graph={incidentDetail?.graph ?? null} /></Suspense></div>}{view === "explain" && <ExplainView alert={selectedAlert} explanations={explanations} recommendations={recommendations} />}{view === "feedback" && <FeedbackView alerts={alerts} items={feedback} token={token} onSubmitted={loadFeedback} />}{view === "audit" && <AuditView items={auditLogs} />}</div></main>
    </div>
  );
}

export default function DashboardApp() {
  const [session, setSession] = useState<{ token: string; user: User } | null>(null);
  if (!session) return <LoginScreen onAuthenticated={(token, user) => setSession({ token, user })} />;
  return <Dashboard token={session.token} user={session.user} onLogout={() => setSession(null)} />;
}
