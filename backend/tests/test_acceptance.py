from pathlib import Path

from app.acceptance import run_acceptance

PROJECT_ROOT = Path(__file__).parents[2]


def test_raw_sample_reaches_explainable_visual_dashboard_contract() -> None:
    report = run_acceptance(
        PROJECT_ROOT / "data/samples/phase7-acceptance-events-v1.json",
        max_duration_ms=2000,
    )

    assert report["passed"] is True
    assert all(report["criteria"].values())
    assert report["counts"]["normalized_events"] == 3
    assert report["counts"]["graph_nodes"] > 0
    assert report["counts"]["graph_edges"] > 0
    assert report["human_approval"]["execution_permitted"] is False
