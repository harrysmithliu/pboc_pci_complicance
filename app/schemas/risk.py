from datetime import datetime

from pydantic import BaseModel


class RiskResultResponse(BaseModel):
    id: int
    transaction_id: int
    decision: str
    triggered_rules: list[str]
    details_json: dict[str, object]
    source: str
    created_at: datetime

    model_config = {"from_attributes": True}

