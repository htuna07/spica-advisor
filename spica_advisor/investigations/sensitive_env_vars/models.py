from typing import Literal

from pydantic import BaseModel


SensitivenessLevel = Literal["low", "medium", "high"]


class EnvVarSensitiveness(BaseModel):
    name: str
    sensitiveness_level: SensitivenessLevel
    reason: str


class SensitivenessResponse(BaseModel):
    env_vars: list[EnvVarSensitiveness]
