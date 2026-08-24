from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Literal

from app.models.entities import Severity
from app.schemas.events import NormalizedEventCreate
from app.schemas.platform import AnalysisRunRequest, ThreatScenarioRead


@dataclass(frozen=True)
class ScenarioSpec:
    id: str
    title: str
    category: str
    technique: str
    description: str
    expected_classification: Literal["attack", "suspicious", "benign"]
    severity: Severity
    signals: tuple[str, ...]
    learning_points: tuple[str, ...]
    events: tuple[dict[str, Any], ...]
    asset_criticality: float
    attack_stage: float
    anomaly_level: float
    malicious_source: str | None = None

    def public(self) -> ThreatScenarioRead:
        return ThreatScenarioRead(
            id=self.id,
            title=self.title,
            category=self.category,
            technique=self.technique,
            description=self.description,
            expected_classification=self.expected_classification,
            severity=self.severity,
            event_count=len(self.events),
            signals=list(self.signals),
            learning_points=list(self.learning_points),
        )


def _event(
    offset_minutes: int,
    event_type: str,
    severity: str,
    action: str,
    anomaly_score: float,
    *,
    source_ip: str,
    destination_ip: str,
    user: str,
    host: str,
    protocol: str = "tcp",
) -> dict[str, Any]:
    return {
        "offset_minutes": offset_minutes,
        "source_ip": source_ip,
        "destination_ip": destination_ip,
        "user": user,
        "host": host,
        "protocol": protocol,
        "action": action,
        "severity": severity,
        "event_type": event_type,
        "attributes": {"anomaly_score": anomaly_score},
    }


SCENARIOS = (
    ScenarioSpec(
        id="credential-attack",
        title="Credential attack",
        category="Credential access",
        technique="Repeated failure followed by credential attack",
        description="An external address repeatedly targets a privileged account.",
        expected_classification="attack",
        severity=Severity.critical,
        signals=("Authentication failure", "Credential attack"),
        learning_points=("Shared user/IP correlation", "Critical account-risk escalation"),
        events=(
            _event(
                -4,
                "authentication_failure",
                "high",
                "failed",
                0.85,
                source_ip="192.0.2.44",
                destination_ip="198.51.100.10",
                user="sample-admin",
                host="sample-workstation",
            ),
            _event(
                -1,
                "credential_attack",
                "critical",
                "denied",
                0.96,
                source_ip="192.0.2.44",
                destination_ip="198.51.100.10",
                user="sample-admin",
                host="sample-workstation",
            ),
        ),
        asset_criticality=0.95,
        attack_stage=0.75,
        anomaly_level=0.9,
        malicious_source="192.0.2.44",
    ),
    ScenarioSpec(
        id="malware-execution",
        title="Malware execution",
        category="Execution",
        technique="Suspicious process followed by Defender detection",
        description="A high-risk process signal is followed by a malware detection.",
        expected_classification="attack",
        severity=Severity.critical,
        signals=("Suspicious process", "Malware detected"),
        learning_points=("Host-based correlation", "Defender evidence prioritization"),
        events=(
            _event(
                -3,
                "suspicious_process",
                "high",
                "observed",
                0.92,
                source_ip="192.0.2.51",
                destination_ip="198.51.100.20",
                user="sample-user",
                host="sample-laptop",
            ),
            _event(
                -1,
                "malware_detected",
                "critical",
                "detected",
                1.0,
                source_ip="192.0.2.51",
                destination_ip="198.51.100.20",
                user="sample-user",
                host="sample-laptop",
            ),
        ),
        asset_criticality=0.85,
        attack_stage=0.8,
        anomaly_level=0.95,
    ),
    ScenarioSpec(
        id="network-reconnaissance",
        title="Network reconnaissance",
        category="Discovery",
        technique="Port scan followed by blocked connection",
        description="One source probes a workstation before a firewall block.",
        expected_classification="attack",
        severity=Severity.high,
        signals=("Port scan", "Blocked network connection"),
        learning_points=("Source-IP correlation", "Attack-graph relationship"),
        events=(
            _event(
                -5,
                "port_scan",
                "high",
                "blocked",
                0.9,
                source_ip="203.0.113.25",
                destination_ip="198.51.100.30",
                user="sample-user",
                host="sample-server",
            ),
            _event(
                -2,
                "network_connection_blocked",
                "high",
                "blocked",
                0.72,
                source_ip="203.0.113.25",
                destination_ip="198.51.100.30",
                user="sample-user",
                host="sample-server",
            ),
        ),
        asset_criticality=0.7,
        attack_stage=0.35,
        anomaly_level=0.8,
    ),
    ScenarioSpec(
        id="lateral-movement",
        title="Lateral movement",
        category="Lateral movement",
        technique="Remote authentication followed by host pivot",
        description="A compromised identity appears across related internal hosts.",
        expected_classification="attack",
        severity=Severity.critical,
        signals=("Authentication failure", "Lateral movement"),
        learning_points=("Identity-to-host graph path", "Late-stage risk weighting"),
        events=(
            _event(
                -6,
                "authentication_failure",
                "high",
                "failed",
                0.8,
                source_ip="192.0.2.60",
                destination_ip="198.51.100.40",
                user="sample-operator",
                host="sample-host-a",
            ),
            _event(
                -1,
                "lateral_movement",
                "critical",
                "observed",
                0.94,
                source_ip="192.0.2.60",
                destination_ip="198.51.100.41",
                user="sample-operator",
                host="sample-host-a",
            ),
        ),
        asset_criticality=0.9,
        attack_stage=0.85,
        anomaly_level=0.9,
        malicious_source="192.0.2.60",
    ),
    ScenarioSpec(
        id="data-exfiltration",
        title="Data exfiltration",
        category="Exfiltration",
        technique="Large outbound transfer followed by exfiltration signal",
        description="An unusual outbound transfer escalates into an exfiltration finding.",
        expected_classification="attack",
        severity=Severity.critical,
        signals=("Large outbound transfer", "Data exfiltration"),
        learning_points=("Multi-event risk escalation", "Containment recommendations"),
        events=(
            _event(
                -4,
                "large_outbound_transfer",
                "high",
                "allowed",
                0.82,
                source_ip="198.51.100.50",
                destination_ip="203.0.113.77",
                user="sample-service",
                host="sample-database",
            ),
            _event(
                -1,
                "data_exfiltration",
                "critical",
                "observed",
                0.98,
                source_ip="198.51.100.50",
                destination_ip="203.0.113.77",
                user="sample-service",
                host="sample-database",
            ),
        ),
        asset_criticality=1.0,
        attack_stage=1.0,
        anomaly_level=0.98,
    ),
    ScenarioSpec(
        id="suspicious-tool",
        title="Suspicious tool activity",
        category="Behavioral anomaly",
        technique="Unusual unsigned process sequence",
        description=(
            "Medium-severity process anomalies require review but do not cross "
            "the attack threshold."
        ),
        expected_classification="suspicious",
        severity=Severity.medium,
        signals=("Unusual process", "Unsigned tool execution"),
        learning_points=("Suspicious versus attack threshold", "False-positive review"),
        events=(
            _event(
                -3,
                "unusual_process",
                "medium",
                "allowed",
                0.45,
                source_ip="192.0.2.80",
                destination_ip="198.51.100.80",
                user="sample-developer",
                host="sample-devbox",
            ),
            _event(
                -1,
                "unsigned_tool_execution",
                "medium",
                "allowed",
                0.4,
                source_ip="192.0.2.80",
                destination_ip="198.51.100.80",
                user="sample-developer",
                host="sample-devbox",
            ),
        ),
        asset_criticality=0.45,
        attack_stage=0.25,
        anomaly_level=0.45,
    ),
    ScenarioSpec(
        id="benign-activity",
        title="Normal system activity",
        category="Benign baseline",
        technique="Heartbeat and successful authentication",
        description="Routine low-risk activity demonstrates that not every event becomes an alert.",
        expected_classification="benign",
        severity=Severity.low,
        signals=("System heartbeat", "Authentication success"),
        learning_points=("Benign classification", "No response recommendation"),
        events=(
            _event(
                -3,
                "heartbeat",
                "informational",
                "allowed",
                0.0,
                source_ip="192.0.2.90",
                destination_ip="198.51.100.90",
                user="sample-user",
                host="sample-office-pc",
            ),
            _event(
                -1,
                "authentication_success",
                "low",
                "allowed",
                0.05,
                source_ip="192.0.2.90",
                destination_ip="198.51.100.90",
                user="sample-user",
                host="sample-office-pc",
            ),
        ),
        asset_criticality=0.3,
        attack_stage=0.1,
        anomaly_level=0.1,
    ),
)
SCENARIO_BY_ID = {scenario.id: scenario for scenario in SCENARIOS}


def list_scenarios() -> list[ThreatScenarioRead]:
    return [scenario.public() for scenario in SCENARIOS]


def build_scenario_request(scenario_id: str, observed_at: datetime) -> AnalysisRunRequest:
    scenario = SCENARIO_BY_ID[scenario_id]
    events: list[NormalizedEventCreate] = []
    for template in scenario.events:
        values = dict(template)
        offset = values.pop("offset_minutes")
        attributes = {
            **values.pop("attributes"),
            "simulation": True,
            "scenario_id": scenario.id,
        }
        events.append(
            NormalizedEventCreate(
                timestamp=observed_at + timedelta(minutes=offset),
                log_source="ecti-scenario-lab",
                attributes=attributes,
                **values,
            )
        )
    return AnalysisRunRequest(
        events=events,
        window_minutes=15,
        asset_criticality=scenario.asset_criticality,
        attack_stage=scenario.attack_stage,
        anomaly_level=scenario.anomaly_level,
        as_of=observed_at,
        confirmed_malicious_ips=([scenario.malicious_source] if scenario.malicious_source else []),
        persist=False,
    )
