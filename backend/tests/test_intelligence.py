from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.intelligence.correlation import correlate_events
from app.intelligence.graph import build_attack_graph, explain_graph_node
from app.intelligence.response import recommend_actions
from app.intelligence.risk import calculate_risk
from app.main import app
from app.schemas.events import EventSeverity, NormalizedEventCreate
from app.schemas.intelligence import ResponseContext, RiskInput

client = TestClient(app)


def event(
    minute: int,
    *,
    source_ip: str = "192.0.2.10",
    destination_ip: str = "198.51.100.20",
    host: str = "demo-host",
    user: str = "demo-user",
) -> NormalizedEventCreate:
    return NormalizedEventCreate(
        timestamp=datetime(2026, 1, 1, 0, minute, tzinfo=timezone.utc),
        source_ip=source_ip,
        destination_ip=destination_ip,
        host=host,
        user=user,
        protocol="tcp",
        action="denied",
        severity=EventSeverity.high,
        log_source="test",
        event_type="authentication_failure",
    )


def test_rule_correlation_groups_shared_entities_inside_window() -> None:
    events = [
        event(2),
        event(0),
        event(
            40,
            source_ip="192.0.2.99",
            destination_ip="198.51.100.99",
            host="other-host",
            user="other-user",
        ),
    ]

    incidents = correlate_events(events, window=timedelta(minutes=15))

    assert len(incidents) == 1
    assert len(incidents[0].event_ids) == 2
    assert incidents[0].started_at.minute == 0
    assert {link.relationship for link in incidents[0].links} == {
        "shared_host",
        "shared_ip",
        "shared_user",
    }


def test_attack_graph_is_deterministic_and_has_evidence_paths() -> None:
    events = [event(0), event(1)]

    graph = build_attack_graph(events)
    reversed_graph = build_attack_graph(list(reversed(events)))

    assert graph == reversed_graph
    assert {node.entity_type for node in graph.nodes} == {"host", "ip", "user"}
    assert {edge.relationship for edge in graph.edges} == {
        "network_connection",
        "source_observed_on_host",
        "user_activity",
    }
    evidence = explain_graph_node(graph, graph.nodes[0].id)
    assert evidence.supporting_event_ids
    assert "does not prove causality" in evidence.limitations


def test_risk_formula_is_transparent_and_time_aware() -> None:
    observed = datetime(2026, 1, 1, tzinfo=timezone.utc)
    result = calculate_risk(
        RiskInput(
            threat_confidence=0.8,
            asset_criticality=0.6,
            attack_stage=0.5,
            anomaly_level=0.7,
            observed_at=observed,
            as_of=observed + timedelta(hours=24),
        )
    )

    assert result.formula_version == "risk-v1"
    assert result.components == {
        "threat_confidence": 28.0,
        "asset_criticality": 15.0,
        "attack_stage": 7.5,
        "anomaly_level": 10.5,
        "recency": 5.0,
    }
    assert result.score == 66
    assert result.level == "high"


def test_response_catalog_never_auto_executes() -> None:
    recommendations = recommend_actions(
        ResponseContext(
            risk_score=90,
            confidence=0.9,
            event_type="authentication_failure",
            host="demo-host",
            user="demo-user",
            source_ip="192.0.2.44",
            malicious_ip_confirmed=True,
            vulnerability_id="CVE-DEMO-0001",
        )
    )

    assert {item.action for item in recommendations} == {
        "block_ip",
        "isolate_host",
        "reset_credentials",
        "investigate_endpoint",
        "patch_vulnerability",
    }
    assert all(item.requires_human_approval for item in recommendations)
    assert not any(item.automatic_execution for item in recommendations)


def test_intelligence_api_exposes_graph_risk_and_recommendations() -> None:
    payload = [item.model_dump(mode="json") for item in (event(0), event(1))]
    graph_response = client.post(
        "/api/v1/intelligence/attack-graphs/build", json={"events": payload}
    )
    assert graph_response.status_code == 200
    assert graph_response.json()["nodes"]

    risk_response = client.post(
        "/api/v1/intelligence/risk/score",
        json={
            "threat_confidence": 1,
            "asset_criticality": 1,
            "attack_stage": 1,
            "anomaly_level": 1,
            "observed_at": "2026-01-01T00:00:00Z",
            "as_of": "2026-01-01T00:00:00Z",
        },
    )
    assert risk_response.status_code == 200
    assert risk_response.json()["score"] == pytest.approx(100)

    recommendation_response = client.post(
        "/api/v1/intelligence/recommendations",
        json={
            "risk_score": 20,
            "confidence": 0.2,
            "event_type": "heartbeat",
        },
    )
    assert recommendation_response.status_code == 200
    assert recommendation_response.json()[0]["action"] == "monitor"
