export type Role = "analyst" | "administrator";
export type Severity = "informational" | "low" | "medium" | "high" | "critical";

export interface User {
  id: string;
  username: string;
  full_name: string;
  role: Role;
  active: boolean;
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
