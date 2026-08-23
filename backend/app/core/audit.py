from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog


async def record_audit(
    session: AsyncSession,
    *,
    actor_username: str,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    detail: dict[str, object] | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        actor_username=actor_username,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        detail=detail or {},
        ip_address=ip_address,
    )
    session.add(entry)
    await session.flush()
    return entry
