from pydantic import BaseModel, Field
from typing import List, Optional

class DesignSpec(BaseModel):
    category: str = Field(default="spaceship")
    length_studs: int = Field(default=16, ge=4, le=64)
    width_studs: int = Field(default=8, ge=4, le=64)
    height_layers: int = Field(default=6, ge=2, le=64)
    palette: List[str] = Field(default_factory=lambda: ["red","black","light_gray"])
    part_cap: int = Field(default=200, ge=1, le=5000)
    style: str = Field(default="sleek")
    symmetry: Optional[str] = Field(default="bilateral")
    stability_target: Optional[str] = Field(default="basic")
    seed: int = Field(default=42)
