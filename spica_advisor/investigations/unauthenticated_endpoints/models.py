from typing import Literal

from pydantic import BaseModel


RiskLevel = Literal["low", "medium", "high"]


class MethodRisk(BaseModel):
    name: str
    risk_level: RiskLevel
    reason: str


class FunctionRisk(BaseModel):
    function_id: str
    methods: list[MethodRisk]


class FunctionRiskResponse(BaseModel):
    functions: list[FunctionRisk]
