"""
PersistentProductionNode - Production nodes with recipe management.

Specialized persistent node for production facilities with recipe management,
efficiency tracking, tech tiers, and production planning for Foxhole manufacturing.
"""

import logging
from typing import Any, Dict, List, Optional, Union

from persistent.list import PersistentList
from persistent.mapping import PersistentMapping

from .base_node import PersistentBaseNode

logger = logging.getLogger(__name__)


class PersistentProductionNode(PersistentBaseNode):
    """
    Persistent node for production facility management.

    Extends PersistentBaseNode with production-specific functionality including
    recipe management, efficiency tracking, tech tiers, and production scheduling.
    """

    def __init__(
        self,
        node_id: Optional[str] = None,
        name: str = "",
        facility_type: str = "factory",
        **kwargs,
    ):
        """
        Initialize production node.

        Args:
            node_id: Unique identifier for the node
            name: Human-readable name for the node
            facility_type: Type of production facility
            **kwargs: Additional attributes
        """
        super().__init__(node_id=node_id, name=name, node_type="production", **kwargs)

        # Facility information
        self.facility_type = facility_type  # factory, refinery, mpf, etc.
        self.location = kwargs.get("location", "")
        self.region = kwargs.get("region", "")
        self.coordinates = PersistentMapping(kwargs.get("coordinates", {}))

        # Production recipes and capabilities
        self.recipes = PersistentList()
        self.active_recipes = PersistentMapping()  # Currently running recipes
        self.recipe_queue = PersistentList()  # Queued production orders

        # Technology and upgrades
        self.tech_tier = kwargs.get("tech_tier", 1)
        self.unlocked_tiers = PersistentList(kwargs.get("unlocked_tiers", []))
        self.available_upgrades = PersistentList()
        self.applied_upgrades = PersistentList()

        # Efficiency and performance
        self.base_efficiency = kwargs.get("base_efficiency", 1.0)
        self.current_efficiency = kwargs.get("current_efficiency", 1.0)
        self.efficiency_modifiers = PersistentMapping()
        self.production_multiplier = kwargs.get("production_multiplier", 1.0)

        # Resource management
        self.input_storage = PersistentMapping()  # Current input materials
        self.output_storage = PersistentMapping()  # Produced outputs
        self.storage_capacity = kwargs.get("storage_capacity", 1000)

        # Power and utilities
        self.power_requirement = kwargs.get("power_requirement", 0.0)
        self.power_consumption = kwargs.get("power_consumption", 0.0)
        self.fuel_type = kwargs.get("fuel_type", None)
        self.fuel_consumption = kwargs.get("fuel_consumption", 0.0)

        # Operational status
        self.is_operational = kwargs.get("is_operational", True)
        self.is_powered = kwargs.get("is_powered", True)
        self.maintenance_level = kwargs.get("maintenance_level", 100.0)
        self.last_maintenance = kwargs.get("last_maintenance", None)

        # Workers and staffing
        self.required_workers = kwargs.get("required_workers", 0)
        self.current_workers = kwargs.get("current_workers", 0)
        self.worker_efficiency = kwargs.get("worker_efficiency", 1.0)

        # Production statistics
        self.total_production_cycles = 0
        self.successful_cycles = 0
        self.failed_cycles = 0
        self.total_uptime = 0.0
        self.total_downtime = 0.0

        logger.debug(
            f"Created production node: {self.node_id} ({facility_type}) at {self.location}"
        )

    def add_recipe(self, recipe_data: Dict[str, Any]) -> str:
        """
        Add a production recipe to the node.

        Args:
            recipe_data: Dictionary containing recipe information

        Returns:
            Recipe ID
        """
        recipe = PersistentMapping(recipe_data)

        # Generate recipe ID if not provided
        if "recipe_id" not in recipe:
            recipe["recipe_id"] = f"recipe_{len(self.recipes)}"

        # Set default values
        recipe.setdefault("inputs", PersistentMapping())
        recipe.setdefault("outputs", PersistentMapping())
        recipe.setdefault("cycle_time", 60.0)
        recipe.setdefault("required_tier", 1)
        recipe.setdefault("power_requirement", 0.0)
        recipe.setdefault("worker_requirement", 0)
        recipe.setdefault("efficiency_factor", 1.0)

        self.recipes.append(recipe)
        self.update_modified_time()

        logger.debug(f"Added recipe {recipe['recipe_id']} to {self.name}")
        return recipe["recipe_id"]

    def remove_recipe(self, recipe_id: str) -> bool:
        """
        Remove a recipe from the node.

        Args:
            recipe_id: ID of the recipe to remove

        Returns:
            True if recipe was removed
        """
        for i, recipe in enumerate(self.recipes):
            if recipe.get("recipe_id") == recipe_id:
                del self.recipes[i]

                # Remove from active recipes if running
                if recipe_id in self.active_recipes:
                    del self.active_recipes[recipe_id]

                self.update_modified_time()
                logger.debug(f"Removed recipe {recipe_id} from {self.name}")
                return True

        return False

    def get_recipe(self, recipe_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a recipe by ID.

        Args:
            recipe_id: ID of the recipe

        Returns:
            Recipe data or None if not found
        """
        for recipe in self.recipes:
            if recipe.get("recipe_id") == recipe_id:
                return dict(recipe)
        return None

    def get_available_recipes(self) -> List[Dict[str, Any]]:
        """
        Get recipes that can be executed with current tech tier and resources.

        Returns:
            List of available recipe data
        """
        available = []

        for recipe in self.recipes:
            # Check tech tier requirement
            required_tier = recipe.get("required_tier", 1)
            if (
                required_tier not in self.unlocked_tiers
                and required_tier > self.tech_tier
            ):
                continue

            # Check if we have inputs (basic check)
            inputs = recipe.get("inputs", {})
            can_produce = True

            for input_item, required_qty in inputs.items():
                available_qty = self.input_storage.get(input_item, 0.0)
                if available_qty < required_qty:
                    can_produce = False
                    break

            if can_produce:
                available.append(dict(recipe))

        return available

    def start_production(
        self, recipe_id: str, cycles: int = 1, priority: str = "normal"
    ) -> bool:
        """
        Start production using a recipe.

        Args:
            recipe_id: ID of the recipe to use
            cycles: Number of production cycles
            priority: Production priority level

        Returns:
            True if production started successfully
        """
        recipe = self.get_recipe(recipe_id)
        if not recipe:
            logger.warning(f"Recipe {recipe_id} not found at {self.name}")
            return False

        # Check if facility is operational
        if not self.is_operational:
            logger.warning(f"Production facility {self.name} is not operational")
            return False

        # Check tech tier
        required_tier = recipe.get("required_tier", 1)
        if required_tier not in self.unlocked_tiers and required_tier > self.tech_tier:
            logger.warning(
                f"Tech tier {required_tier} not unlocked for recipe {recipe_id}"
            )
            return False

        # Check input materials
        inputs = recipe.get("inputs", {})
        for input_item, required_qty in inputs.items():
            available_qty = self.input_storage.get(input_item, 0.0)
            total_needed = required_qty * cycles

            if available_qty < total_needed:
                logger.warning(
                    f"Insufficient {input_item} for production: {available_qty} < {total_needed}"
                )
                return False

        # Reserve input materials
        for input_item, required_qty in inputs.items():
            total_needed = required_qty * cycles
            self.input_storage[input_item] -= total_needed

        # Create production order
        production_order = PersistentMapping(
            {
                "recipe_id": recipe_id,
                "cycles": cycles,
                "cycles_completed": 0,
                "priority": priority,
                "started_at": self.modified_at,
                "estimated_completion": None,  # Should calculate based on cycle time
                "status": "active",
            }
        )

        self.active_recipes[recipe_id] = production_order
        self.update_modified_time()

        logger.info(
            f"Started production of {recipe_id} for {cycles} cycles at {self.name}"
        )
        return True

    def complete_production_cycle(self, recipe_id: str) -> bool:
        """
        Complete one production cycle for a recipe.

        Args:
            recipe_id: ID of the recipe

        Returns:
            True if cycle completed successfully
        """
        if recipe_id not in self.active_recipes:
            return False

        production_order = self.active_recipes[recipe_id]
        recipe = self.get_recipe(recipe_id)

        if not recipe:
            return False

        # Add outputs to storage
        outputs = recipe.get("outputs", {})
        efficiency_factor = recipe.get("efficiency_factor", 1.0)
        total_efficiency = self.current_efficiency * efficiency_factor

        for output_item, base_qty in outputs.items():
            actual_qty = base_qty * total_efficiency
            current_output = self.output_storage.get(output_item, 0.0)
            self.output_storage[output_item] = current_output + actual_qty

        # Update production order
        production_order["cycles_completed"] += 1

        # Check if production is complete
        if production_order["cycles_completed"] >= production_order["cycles"]:
            production_order["status"] = "completed"
            self.successful_cycles += 1
            logger.info(f"Completed production of {recipe_id} at {self.name}")

        self.total_production_cycles += 1
        self.update_modified_time()

        return True

    def cancel_production(self, recipe_id: str) -> bool:
        """
        Cancel active production.

        Args:
            recipe_id: ID of the recipe to cancel

        Returns:
            True if production was cancelled
        """
        if recipe_id not in self.active_recipes:
            return False

        # Return unused input materials (simplified)
        production_order = self.active_recipes[recipe_id]
        recipe = self.get_recipe(recipe_id)

        if recipe:
            remaining_cycles = (
                production_order["cycles"] - production_order["cycles_completed"]
            )
            inputs = recipe.get("inputs", {})

            for input_item, required_qty in inputs.items():
                return_qty = required_qty * remaining_cycles
                current_input = self.input_storage.get(input_item, 0.0)
                self.input_storage[input_item] = current_input + return_qty

        del self.active_recipes[recipe_id]
        self.failed_cycles += 1
        self.update_modified_time()

        logger.info(f"Cancelled production of {recipe_id} at {self.name}")
        return True

    def add_input_material(self, material_name: str, quantity: float) -> bool:
        """
        Add input material to storage.

        Args:
            material_name: Name of the material
            quantity: Quantity to add

        Returns:
            True if material was added
        """
        current_total = sum(self.input_storage.values())
        if current_total + quantity > self.storage_capacity:
            logger.warning(f"Storage capacity exceeded at {self.name}")
            return False

        current_qty = self.input_storage.get(material_name, 0.0)
        self.input_storage[material_name] = current_qty + quantity
        self.update_modified_time()

        return True

    def remove_output_material(self, material_name: str, quantity: float) -> bool:
        """
        Remove output material from storage.

        Args:
            material_name: Name of the material
            quantity: Quantity to remove

        Returns:
            True if material was removed
        """
        current_qty = self.output_storage.get(material_name, 0.0)

        if current_qty < quantity:
            logger.warning(
                f"Insufficient {material_name} in output storage: {current_qty} < {quantity}"
            )
            return False

        self.output_storage[material_name] = current_qty - quantity

        # Remove entry if quantity reaches zero
        if self.output_storage[material_name] <= 0:
            del self.output_storage[material_name]

        self.update_modified_time()
        return True

    def set_efficiency_modifier(self, modifier_name: str, value: float):
        """
        Set an efficiency modifier.

        Args:
            modifier_name: Name of the modifier
            value: Modifier value (1.0 = no change, > 1.0 = improvement, < 1.0 = penalty)
        """
        self.efficiency_modifiers[modifier_name] = value
        self._recalculate_efficiency()

    def _recalculate_efficiency(self):
        """Recalculate current efficiency based on modifiers."""
        efficiency = self.base_efficiency

        for modifier_value in self.efficiency_modifiers.values():
            efficiency *= modifier_value

        # Factor in maintenance level
        maintenance_factor = self.maintenance_level / 100.0
        efficiency *= maintenance_factor

        # Factor in worker efficiency
        if self.required_workers > 0:
            worker_factor = min(1.0, self.current_workers / self.required_workers)
            efficiency *= worker_factor * self.worker_efficiency

        self.current_efficiency = max(0.0, efficiency)
        self.update_modified_time()

    def unlock_tech_tier(self, tier: int):
        """
        Unlock a technology tier.

        Args:
            tier: Technology tier to unlock
        """
        if tier not in self.unlocked_tiers:
            self.unlocked_tiers.append(tier)
            self.tech_tier = max(self.tech_tier, tier)
            self.update_modified_time()
            logger.info(f"Unlocked tech tier {tier} at {self.name}")

    def get_production_statistics(self) -> Dict[str, Any]:
        """
        Get production statistics.

        Returns:
            Dictionary with production statistics
        """
        total_cycles = self.successful_cycles + self.failed_cycles
        success_rate = (
            (self.successful_cycles / total_cycles * 100) if total_cycles > 0 else 0
        )

        return {
            "total_cycles": total_cycles,
            "successful_cycles": self.successful_cycles,
            "failed_cycles": self.failed_cycles,
            "success_rate_percent": success_rate,
            "current_efficiency": self.current_efficiency,
            "active_recipes_count": len(self.active_recipes),
            "available_recipes_count": len(self.get_available_recipes()),
            "tech_tier": self.tech_tier,
            "unlocked_tiers": list(self.unlocked_tiers),
            "maintenance_level": self.maintenance_level,
            "is_operational": self.is_operational,
            "is_powered": self.is_powered,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert node to dictionary representation."""
        base_dict = super().to_dict()

        production_dict = {
            "facility_type": self.facility_type,
            "location": self.location,
            "region": self.region,
            "coordinates": dict(self.coordinates),
            "recipes_count": len(self.recipes),
            "active_recipes": {k: dict(v) for k, v in self.active_recipes.items()},
            "tech_tier": self.tech_tier,
            "unlocked_tiers": list(self.unlocked_tiers),
            "current_efficiency": self.current_efficiency,
            "input_storage": dict(self.input_storage),
            "output_storage": dict(self.output_storage),
            "storage_capacity": self.storage_capacity,
            "power_requirement": self.power_requirement,
            "is_operational": self.is_operational,
            "is_powered": self.is_powered,
            "maintenance_level": self.maintenance_level,
            "required_workers": self.required_workers,
            "current_workers": self.current_workers,
            "production_statistics": self.get_production_statistics(),
        }

        base_dict.update(production_dict)
        return base_dict
