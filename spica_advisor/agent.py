from dataclasses import dataclass

from pydantic import BaseModel


@dataclass(frozen=True)
class Agent:
    name: str
    instructions: str
    output_type: type[BaseModel]
