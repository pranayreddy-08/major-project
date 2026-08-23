import pytest

from app.db.base import Base
from app.db.migrate import ALEMBIC_TABLE, baseline_required


def test_empty_and_versioned_databases_do_not_require_baseline() -> None:
    assert baseline_required(set(), "development") is False
    assert baseline_required({ALEMBIC_TABLE}, "production") is False


def test_complete_legacy_schema_can_be_baselined_only_outside_production() -> None:
    tables = set(Base.metadata.tables)

    assert baseline_required(tables, "development") is True
    assert baseline_required(tables, "staging") is True
    with pytest.raises(RuntimeError, match="explicit operator review"):
        baseline_required(tables, "production")


def test_partial_legacy_schema_fails_closed() -> None:
    partial = set(Base.metadata.tables) - {"alerts"}

    with pytest.raises(RuntimeError, match="missing: alerts"):
        baseline_required(partial, "development")
