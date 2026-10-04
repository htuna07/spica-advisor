from typing import Literal

from pydantic import BaseModel


class MethodRisk(BaseModel):
    name: str
    risk_level: Literal["low", "medium", "high"]
    reason: str


class FunctionRisk(BaseModel):
    function_id: str
    methods: list[MethodRisk]


class FunctionRiskResponse(BaseModel):
    functions: list[FunctionRisk]
