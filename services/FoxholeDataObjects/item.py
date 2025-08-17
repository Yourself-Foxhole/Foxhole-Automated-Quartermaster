from typing import Dict, List, Optional
from services.FoxholeDataObjects.enums import Faction

class Item:
    def __init__(
        self,
        Item_Id: str,
        Item_Name: str,
        Item_DisplayName: str,
        Faction: Faction = Faction.NEUTRAL,
        ItemCategory: str = "",
        ItemCost: Optional[Dict[str, float]] = None,
        CrateSize: int = 0,
        ProductionProcess: Optional[List[str]] = None,
        EquipmentSlot: str = "",
        ItemProfileType: str = "",
        UsedBy: Optional[List[str]] = None,
        FactoryProductionTime: float = 0.0,
        Encumberance: float = 0.0,
        SingleRetrieveTime: float = 0.0,
        CrateRetrieveTime: float = 0.0,
        TechId: str = "",
        IsLiquid: bool = False,
        PickupItemCapacity: int = 0
    ):
        self.Item_Id = Item_Id
        self.Item_Name = Item_Name
        self.Item_DisplayName = Item_DisplayName
        self.Faction = Faction
        self.ItemCategory = ItemCategory
        self.ItemCost = ItemCost if ItemCost is not None else {}
        self.CrateSize = CrateSize
        self.ProductionProcess = ProductionProcess if ProductionProcess is not None else []
        self.EquipmentSlot = EquipmentSlot
        self.ItemProfileType = ItemProfileType
        self.UsedBy = UsedBy if UsedBy is not None else []
        self.FactoryProductionTime = FactoryProductionTime
        self.Encumberance = Encumberance
        self.SingleRetrieveTime = SingleRetrieveTime
        self.CrateRetrieveTime = CrateRetrieveTime
        self.TechId = TechId
        self.IsLiquid = IsLiquid
        self.PickupItemCapacity = PickupItemCapacity

    def is_crateable(self) -> bool:
        return self.CrateSize >= 1
