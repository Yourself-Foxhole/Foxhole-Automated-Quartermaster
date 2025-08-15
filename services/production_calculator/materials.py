from enum import Enum

class Material(Enum):
    BMAT = "Basic Material"
    RMAT = "Refined Material"
    EMAT = "Explosive Powder"
    HEMAT = "High Explosive Powder"
    PCMAT = "Processed Construction Material"
    CMAT = "Construction Material"
    AMAT1 = "Assembly Material I"
    AMAT2 = "Assembly Material II"
    AMAT3 = "Assembly Material III"
    AMAT4 = "Assembly Material IV"
    AMAT5 = "Assembly Material V"
    RARE = "Rare Alloy"
    HULL_SEGMENT = "Naval Hull Segment"
    SHELL_PLATING = "Naval Shell Plating"
    TURB_COMP = "Naval Turbine Components"

class RawResource(Enum):
    ALUMINUM = "Aluminum"
    SALVAGE = "Salvage"
    COPPER = "Copper"
    IRON = "Iron"
    OIL = "Oil"
    COAL = "Coal"
    SULFUR = "Sulfur"
    IRON = "Iron"
    COMPONENTS = "Components"
    WRECKAGE = "Wreckage"

class ResourceField(Enum):
    COAL_FIELD = "Coal Field"
    COMPONENT_FIELD = "Component Field"
    OIL_FIELD = "Oil Field"
    SALVAGE_FIELD = "Salvage Field"
    SULFUR_FIELD = "Sulfur Field"
