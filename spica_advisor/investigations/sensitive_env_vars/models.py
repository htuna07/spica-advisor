from typing import Literal

from pydantic import BaseModel


class EnvVarSensitiveness(BaseModel):
    name: str
    sensitiveness_level: Literal["low", "medium", "high"]
    reason: str


class SensitivenessResponse(BaseModel):
    env_vars: list[EnvVarSensitiveness]
