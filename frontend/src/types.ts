export type Role = "analyst" | "administrator";
export type Severity = "informational" | "low" | "medium" | "high" | "critical";

export interface User {
  id: string;
  username: string;
  full_name: string;
  role: Role;
  active: boolean;
}

export interface SetupStatus {
  setup_required: boolean;
}

export interface EndpointSensor {
  id: string;
  sensor_id: string;
  hostname: string;
  operating_system: string;
  agent_version: string;
  ip_addresses: string[];
  capabilities: Record<string, unknown>;
  last_seen_at: string;
  last_event_at: string | null;
  status: "online" | "offline";
}

export interface SensorServiceStatus {
  ingest_configured: boolean;
  sensors_total: number;
  sensors_online: number;
}

export interface Alert {
  id: string;
  normalized_event_id: string | null;
  incident_id: string | null;
  alert_type: string;
  title: string;
  description: string | null;
  severity: Severity;
  confidence: number;
  status: string;
  created_at: string;
}

export interface Incident {
  id: string;
  title: string;
  description: string | null;
  status: string;
  severity: Severity;
  risk_score: number;
  created_at: string;
  updated_at: string;
}

export interface GraphNode {
  id: string;
  entity_type: string;
  key: string;
  label: string;
  risk_score: number;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  relationship: string;
  event_id: string;
  timestamp: string;
}

export interface AttackGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface IncidentDetail {
  incident: Incident;
  alerts: Alert[];
  graph: AttackGraph;
}

export interface SeverityCount {
  severity: Severity;
  count: number;
}

export interface Overview {
  open_alerts: number;
  active_incidents: number;
  critical_alerts: number;
  monitored_events: number;
  severity_distribution: SeverityCount[];
  recent_alerts: Alert[];
  model_status: string;
  model_name: string;
  model_version: string;
}

export interface WorkflowAgentStep {
  sequence: number;
  agent: "detection" | "correlation" | "risk" | "explainability" | "response";
  status: "completed" | "failed" | "skipped";
  started_at: string;
  completed_at: string;
  duration_ms: number;
  detail: string;
  input_digest: string;
  output_digest: string | null;
}

export interface WorkflowRun {
  workflow_id: string;
  status: "completed" | "partial_failure" | "failed";
  actor: string;
  created_at: string;
  event_count: number;
  alert_count: number;
  persisted: boolean;
  detection_model: string;
  detection_model_version: string;
  steps: WorkflowAgentStep[];
  human_approval_required: true;
  execution_permitted: false;
}

export interface ModelMetrics {
  precision: number;
  recall: number;
  f1: number;
  roc_auc: number;
  samples: number;
}

export interface ModelProfile {
  id: string;
  name: string;
  version: string;
  kind: "deterministic_baseline" | "logistic_regression" | "graph_neural_network";
  deployment: "runtime" | "evaluated_offline";
  purpose: string;
  architecture: string;
  metrics: ModelMetrics | null;
}

export interface ModelCatalog {
  experiment_version: string;
  dataset_version: string;
  models: ModelProfile[];
  limitations: string[];
}

export type ThreatClassification = "attack" | "suspicious" | "benign";

export interface ThreatScenario {
  id: string;
  title: string;
  category: string;
  technique: string;
  description: string;
  expected_classification: ThreatClassification;
  severity: Severity;
  event_count: number;
  signals: string[];
  learning_points: string[];
}

export interface ScenarioRunResult {
  workflow: {
    workflow_id: string;
    status: "completed" | "partial_failure" | "failed";
    detection: {
      findings: Array<{
        event_id: string;
        classification: ThreatClassification;
        confidence: number;
        anomaly_score: number;
        model_name: string;
        model_version: string;
      }>;
    } | null;
    correlation: {
      incidents: Array<{ id: string; event_ids: string[] }>;
      attack_graph: AttackGraph;
    } | null;
    risk: {
      assessments: Array<{
        event_id: string;
        risk: { score: number; level: Severity; components: Record<string, number> };
      }>;
    } | null;
    explainability: {
      explanations: Array<{ event_id: string; summary: string; limitations: string }>;
    } | null;
    response: {
      recommendations: Array<{
        recommendation: Recommendation;
        supporting_event_ids: string[];
      }>;
    } | null;
    audit_trail: Array<{
      sequence: number;
      agent: string;
      status: "completed" | "failed" | "skipped";
      started_at: string;
      completed_at: string;
      detail: string;
    }>;
    human_approval: {
      required: true;
      approval_status: "pending";
      execution_permitted: false;
    };
  };
  stored_event_ids: string[];
  stored_alert_ids: string[];
}

export interface Explanation {
  id: string;
  alert_id: string;
  method: string;
  summary: string;
  evidence: {
    important_features?: Array<{ name: string; value: string | number }>;
    source_ip?: string;
    host?: string;
  };
  limitations: string | null;
  created_at: string;
}

export interface Recommendation {
  action: string;
  target: string;
  priority: Severity;
  rationale: string;
  requires_human_approval: true;
  automatic_execution: false;
}

export interface RecommendationResult {
  alert_id: string;
  recommendations: Recommendation[];
}

export interface Feedback {
  id: string;
  alert_id: string | null;
  incident_id: string | null;
  analyst: string;
  verdict: string;
  comment: string | null;
  created_at: string;
}

export interface AuditLog {
  id: string;
  actor_username: string;
  action: string;
  resource_type: string;
  resource_id: string | null;
  detail: Record<string, unknown>;
  ip_address: string | null;
  created_at: string;
}
