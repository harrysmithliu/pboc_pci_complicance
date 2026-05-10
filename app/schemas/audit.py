from datetime import datetime

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    id: int
    actor: str
    actor_role: str
    action: str
    resource_type: str
    resource_id: str
    result: str
    trace_id: str
    metadata_json: dict[str, object]
    created_at: datetime

    model_config = {"from_attributes": True}

