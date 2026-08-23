import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

from app.agents import WorkflowCoordinator
from app.ingestion.adapters import ingest_json
from app.schemas.workflow import WorkflowRequest


def run_acceptance(sample_path: Path, *, max_duration_ms: float = 2000) -> dict[str, object]:
    started = perf_counter()
    ingestion = ingest_json(sample_path, log_source="phase7-acceptance")
    if ingestion.errors:
        messages = "; ".join(error.message for error in ingestion.errors)
        raise ValueError(f"acceptance input was not fully normalized: {messages}")

    events = [item.normalized for item in ingestion.accepted]
    workflow = WorkflowCoordinator().run(
        WorkflowRequest(
            events=events,
            window_minutes=15,
            asset_criticality=0.9,
            attack_stage=0.7,
            anomaly_level=0.8,
            as_of=datetime(2026, 1, 1, 1, tzinfo=timezone.utc),
            confirmed_malicious_ips=["192.0.2.44"],
            vulnerability_id="CVE-DEMO-0001",
        )
    )
    duration_ms = (perf_counter() - started) * 1000
    findings = workflow.detection.findings if workflow.detection else []
    graph = workflow.correlation.attack_graph if workflow.correlation else None
    explanations = workflow.explainability.explanations if workflow.explainability else []
    assessments = workflow.risk.assessments if workflow.risk else []
    recommendations = workflow.response.recommendations if workflow.response else []
    criteria = {
        "all_sample_logs_normalized": len(events) == 3,
        "attack_alert_created": any(item.classification == "attack" for item in findings),
        "correlated_incident_created": bool(
            workflow.correlation and workflow.correlation.incidents
        ),
        "risk_score_created": bool(assessments),
        "explanation_created": bool(explanations),
        "visual_attack_path_created": bool(graph and graph.nodes and graph.edges),
        "recommendations_are_advisory": bool(recommendations)
        and all(
            item.recommendation.requires_human_approval
            and not item.recommendation.automatic_execution
            for item in recommendations
        ),
        "completed_within_limit": duration_ms <= max_duration_ms,
    }
    return {
        "acceptance_version": "phase7-synthetic-v1",
        "sample_sha256": hashlib.sha256(sample_path.read_bytes()).hexdigest(),
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "max_duration_ms": max_duration_ms,
        "observed_duration_ms": duration_ms,
        "counts": {
            "normalized_events": len(events),
            "findings": len(findings),
            "incidents": len(workflow.correlation.incidents) if workflow.correlation else 0,
            "graph_nodes": len(graph.nodes) if graph else 0,
            "graph_edges": len(graph.edges) if graph else 0,
            "explanations": len(explanations),
            "recommendations": len(recommendations),
        },
        "criteria": criteria,
        "passed": workflow.status == "completed" and all(criteria.values()),
        "workflow_contract_version": workflow.contract_version,
        "human_approval": workflow.human_approval.model_dump(mode="json"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Phase 7 synthetic acceptance path")
    parser.add_argument("--sample", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-duration-ms", type=float, default=2000)
    args = parser.parse_args()
    result = run_acceptance(args.sample, max_duration_ms=args.max_duration_ms)
    serialized = json.dumps(result, indent=2, sort_keys=True) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(serialized, encoding="utf-8")
    print(serialized, end="")
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
