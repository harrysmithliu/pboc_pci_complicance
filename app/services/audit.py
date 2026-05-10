from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def write_audit_log(
    db: Session,
    *,
    actor: str,
    actor_role: str,
    action: str,
    resource_type: str,
    resource_id: str,
    result: str,
    trace_id: str,
    metadata: dict[str, object] | None = None,
) -> AuditLog:
    audit_log = AuditLog(
        actor=actor,
        actor_role=actor_role,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        result=result,
        trace_id=trace_id,
        metadata_json=metadata or {},
    )
    db.add(audit_log)
    return audit_log

