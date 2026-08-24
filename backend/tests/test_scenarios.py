from datetime import datetime, timezone

import pytest

from app.agents import WorkflowCoordinator
from app.scenarios import SCENARIOS, build_scenario_request, list_scenarios
from app.schemas.workflow import WorkflowRequest


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda scenario: scenario.id)
def test_scenario_primary_classification_matches_documented_expectation(scenario) -> None:
    payload = build_scenario_request(
        scenario.id,
        datetime(2026, 8, 24, 12, 0, tzinfo=timezone.utc),
    )
    result = WorkflowCoordinator().run(
        WorkflowRequest.model_validate(payload.model_dump(exclude={"persist"}))
    )
    rank = {"benign": 0, "suspicious": 1, "attack": 2}
    classifications = [finding.classification for finding in result.detection.findings]
    primary = max(classifications, key=rank.__getitem__)

    assert primary == scenario.expected_classification
    assert result.status == "completed"
    assert [record.status for record in result.audit_trail] == ["completed"] * 5
    if scenario.expected_classification == "benign":
        assert result.correlation.incidents == []
        assert result.correlation.attack_graph.nodes == []
        assert result.response.recommendations == []
    else:
        assert result.correlation.incidents
        assert result.correlation.attack_graph.nodes
    assert result.human_approval.required is True
    assert result.human_approval.execution_permitted is False


def test_scenarios_are_simulated_and_never_persist_by_default() -> None:
    observed_at = datetime(2026, 8, 24, 12, 0, tzinfo=timezone.utc)
    for scenario in SCENARIOS:
        payload = build_scenario_request(scenario.id, observed_at)
        assert payload.persist is False
        assert all(event.log_source == "ecti-scenario-lab" for event in payload.events)
        assert all(event.attributes["simulation"] is True for event in payload.events)
        assert all(event.attributes["scenario_id"] == scenario.id for event in payload.events)


def test_scenario_catalog_covers_attack_suspicious_and_benign_outcomes() -> None:
    catalog = list_scenarios()
    assert len(catalog) == 7
    assert {item.expected_classification for item in catalog} == {
        "attack",
        "suspicious",
        "benign",
    }
    assert len({item.id for item in catalog}) == len(catalog)
