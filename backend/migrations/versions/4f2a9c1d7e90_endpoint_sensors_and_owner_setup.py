"""endpoint sensors and owner setup

Revision ID: 4f2a9c1d7e90
Revises: bbfa5454db7e
Create Date: 2026-08-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "4f2a9c1d7e90"
down_revision: str | None = "bbfa5454db7e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "endpoint_sensors",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sensor_id", sa.String(length=100), nullable=False),
        sa.Column("hostname", sa.String(length=255), nullable=False),
        sa.Column("operating_system", sa.String(length=255), nullable=False),
        sa.Column("agent_version", sa.String(length=50), nullable=False),
        sa.Column("ip_addresses", sa.JSON(), nullable=False),
        sa.Column("capabilities", sa.JSON(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_event_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_endpoint_sensors_hostname"), "endpoint_sensors", ["hostname"], unique=False
    )
    op.create_index(
        op.f("ix_endpoint_sensors_last_event_at"),
        "endpoint_sensors",
        ["last_event_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_endpoint_sensors_last_seen_at"),
        "endpoint_sensors",
        ["last_seen_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_endpoint_sensors_sensor_id"),
        "endpoint_sensors",
        ["sensor_id"],
        unique=True,
    )

    op.create_table(
        "sensor_event_receipts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sensor_id", sa.String(length=100), nullable=False),
        sa.Column("event_key", sa.String(length=128), nullable=False),
        sa.Column("normalized_event_id", sa.Uuid(), nullable=True),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["normalized_event_id"], ["normalized_events.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["sensor_id"], ["endpoint_sensors.sensor_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sensor_id", "event_key", name="uq_sensor_event_receipt"),
    )
    op.create_index(
        op.f("ix_sensor_event_receipts_normalized_event_id"),
        "sensor_event_receipts",
        ["normalized_event_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_sensor_event_receipts_sensor_id"),
        "sensor_event_receipts",
        ["sensor_id"],
        unique=False,
    )

    # Remove only the deterministic Phase 6 demo identities. User-created accounts are untouched.
    op.execute(
        """
        DELETE FROM user_accounts
        WHERE id IN (
            'd45f0f63-7068-526a-a204-c72186ea2670',
            '7886032e-0e05-57b9-9647-481139cbd6bb'
        )
        """
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_sensor_event_receipts_sensor_id"), table_name="sensor_event_receipts")
    op.drop_index(
        op.f("ix_sensor_event_receipts_normalized_event_id"),
        table_name="sensor_event_receipts",
    )
    op.drop_table("sensor_event_receipts")
    op.drop_index(op.f("ix_endpoint_sensors_sensor_id"), table_name="endpoint_sensors")
    op.drop_index(op.f("ix_endpoint_sensors_last_seen_at"), table_name="endpoint_sensors")
    op.drop_index(op.f("ix_endpoint_sensors_last_event_at"), table_name="endpoint_sensors")
    op.drop_index(op.f("ix_endpoint_sensors_hostname"), table_name="endpoint_sensors")
    op.drop_table("endpoint_sensors")
