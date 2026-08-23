from pathlib import Path

from ecti_ml.experiment import run_experiment

PROJECT_ROOT = Path(__file__).parents[2]


def test_phase7_experiment_records_reproducible_evaluation_evidence() -> None:
    record = run_experiment(
        PROJECT_ROOT / "data/samples/synthetic-events-v1.csv",
        PROJECT_ROOT / "ml/configs/preprocessing-v1.json",
        PROJECT_ROOT / "ml/configs/phase7-evaluation-v1.json",
    )

    assert record["experiment_version"] == "phase7-evaluation-v1"
    assert record["features"]
    assert record["parameters"]["decision_threshold"] == 0.5
    for model_name in ("logistic_regression", "graphsage"):
        metrics = record["models"][model_name]["test"]
        assert (
            metrics["true_negative"]
            + metrics["false_positive"]
            + metrics["false_negative"]
            + metrics["true_positive"]
            == metrics["samples"]
        )
        assert isinstance(record["observed_failure_cases"][model_name], list)
