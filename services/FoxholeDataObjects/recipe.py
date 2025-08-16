from enum import Enum
from typing import Dict, Any, Optional

class OutputType(Enum):
    CRATES = "crates"
    ITEM = "item"
    RESOURCE = "resource"
    LIQUID = "liquid"

class TechnologyLevel(Enum):
    NONE = "none"
    TIER2 = "Tier2"
    TIER3 = "Tier3"

class Recipe:
    def __init__(self, inputs: Dict[str, int], outputs: Dict[str, int], using: Dict[str, Any], cycle_time: float,
                 tier: Optional[str] = None, output_type: OutputType = OutputType.CRATES,
                 technology_level: TechnologyLevel = TechnologyLevel.NONE):
        self.inputs = inputs
        self.outputs = outputs
        self.using = using
        self.cycle_time = cycle_time
        self.tier = tier
        self.output_type = output_type
        self.technology_level = technology_level

    def __repr__(self):
        return (f"Recipe(inputs={self.inputs!r}, outputs={self.outputs!r}, using={self.using!r}, "
                f"cycle_time={self.cycle_time!r}, tier={self.tier!r}, output_type={self.output_type!r}, technology_level={self.technology_level!r})")

