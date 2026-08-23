import app.models  # noqa: F401
from app.db.base import Base
from app.models import NormalizedEvent


def test_initial_schema_contains_required_tables() -> None:
    expected_tables = {
        "asset_hosts",
        "raw_events",
        "normalized_events",
        "alerts",
        "incidents",
        "indicators_of_compromise",
        "attack_graph_nodes",
        "attack_graph_edges",
        "model_runs",
        "explanations",
        "analyst_feedback",
        "user_accounts",
        "audit_logs",
    }

    assert expected_tables == set(Base.metadata.tables)


def test_normalized_event_contract_and_model_use_timestamp() -> None:
    assert hasattr(NormalizedEvent, "timestamp")
    assert NormalizedEvent.timestamp.property.columns[0].name == "event_timestamp"
