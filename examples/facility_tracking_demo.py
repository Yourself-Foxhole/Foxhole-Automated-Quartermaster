"""
Demonstration of the Facility Tracking Mode system.

This example shows how different tracking modes affect what data is captured
and how the system responds to user configuration choices.
"""


from services.inventory.facility_node import (
    FacilityNode, FacilityBuilding,
    FacilityTrackingMode, FacilityTrackingFeatures, FacilityTrackingConfig,
    OutputType, TechnologyLevel, OperationalStatus
)
import json


def demo_tracking_modes():
    """Demonstrate the different tracking modes and their behaviors."""

    print("=== Facility Tracking Mode Demonstration ===\n")

    # Create different tracking configurations
    untracked_config = FacilityTrackingConfig(
        mode=FacilityTrackingMode.UNTRACKED
    )

    outputs_only_config = FacilityTrackingConfig(
        mode=FacilityTrackingMode.OUTPUTS_ONLY,
        enabled_features=[FacilityTrackingFeatures.RESERVATIONS]
    )

    full_tracking_config = FacilityTrackingConfig(
        mode=FacilityTrackingMode.INPUTS_AND_OUTPUTS,
        enabled_features=[
            FacilityTrackingFeatures.POWER,
            FacilityTrackingFeatures.LIQUIDS,
            FacilityTrackingFeatures.RESERVATIONS
        ]
    )

    # Create facilities with different tracking modes
    facilities = []

    # 1. Untracked Facility - Minimal overhead
    untracked_facility = FacilityNode(
        node_id="fac_001",
        location_name="Remote Production Outpost",
        tracking_config=untracked_config
    )

    factory_building = FacilityNode(
        node_id="build_001",
        location_name="Basic Materials Factory",
        tracking_config=untracked_config
    )
    factory_building.building_type = "BasicMaterialsFactory"
    factory_building.base_recipes = ["rifle", "basic_materials"]
    factory_building.facility_stockpile = {"rifle": 500, "basic_materials": 1000}

    untracked_facility.add_building(factory_building)
    facilities.append(("Untracked", untracked_facility))

    # 2. Outputs Only Facility - Good for pickup coordination
    outputs_facility = FacilityNode(
        node_id="fac_002",
        location_name="Main Distribution Hub",
        tracking_config=outputs_only_config
    )

    distribution_building = FacilityNode(
        node_id="build_002",
        location_name="Distribution Center",
        tracking_config=outputs_only_config
    )
    distribution_building.building_type = "AssemblyStation"
    distribution_building.base_recipes = ["equipment", "vehicles"]
    distribution_building.facility_stockpile = {"equipment": 200, "vehicles": 50}

    outputs_facility.add_building(distribution_building)
    facilities.append(("Outputs Only", outputs_facility))

    # 3. Full Tracking Facility - Maximum visibility
    full_facility = FacilityNode(
        node_id="fac_003",
        location_name="Advanced Production Complex",
        tracking_config=full_tracking_config
    )

    advanced_building = FacilityNode(
        node_id="build_003",
        location_name="Advanced Assembly",
        tracking_config=full_tracking_config
    )
    advanced_building.building_type = "AdvancedAssemblyStation"
    advanced_building.base_recipes = ["heavy_equipment", "advanced_materials"]
    advanced_building.facility_stockpile = {"heavy_equipment": 100, "advanced_materials": 300}
    advanced_building.facility_inventory = {"components": 50, "tools": 25}

    full_facility.add_building(advanced_building)
    facilities.append(("Full Tracking", full_facility))

    # Demonstrate tracking behaviors
    for config_name, facility in facilities:
        print(f"--- {config_name} Facility ---")

        # Show tracking summary
        tracking_summary = facility.get_tracking_summary()
        print(f"Tracking Mode: {tracking_summary['facility_tracking_mode']}")
        print(f"Enabled Features: {tracking_summary['facility_enabled_features']}")

        # Show what inventory is visible based on tracking mode
        visible_inventory = facility.aggregate_inventory()
        print(f"Visible Inventory: {visible_inventory}")

        # Show what each building should track
        for building_info in tracking_summary['buildings']:
            print(f"  Building {building_info['building_type']}:")
            print(f"    - Should track inputs: {building_info['should_track_inputs']}")
            print(f"    - Should track outputs: {building_info['should_track_outputs']}")

        print()


def demo_request_driven_tracking():
    """Demonstrate how untracked facilities respond to requests from other nodes."""

    print("=== Request-Driven Tracking (Untracked Mode) ===\n")

    # Create an untracked facility
    untracked_config = FacilityTrackingConfig(mode=FacilityTrackingMode.UNTRACKED)
    supplier_facility = FacilityNode(
        node_id="supplier_001",
        location_name="Remote Supplier",
        tracking_config=untracked_config
    )

    # Add a production building
    production_building = FacilityNode(
        node_id="prod_001",
        location_name="Material Producer",
        tracking_config=untracked_config
    )
    production_building.building_type = "MaterialFactory"
    production_building.base_recipes = ["basic_materials", "components", "fuel"]
    production_building.facility_stockpile = {
        "basic_materials": 2000,
        "components": 500,
        "fuel": 1000,
        "other_stuff": 300  # This won't be visible until requested
    }

    supplier_facility.add_building(production_building)

    print("Initial state (no requests):")
    print(f"Visible inventory: {supplier_facility.aggregate_inventory()}")
    print(f"Actual stockpile: {production_building.facility_stockpile}")
    print()

    # Simulate requests from other facilities
    print("Adding requests from other facilities...")
    supplier_facility.add_cross_facility_request("basic_materials", 500, "consumer_facility_001")
    supplier_facility.add_cross_facility_request("fuel", 200, "consumer_facility_002")

    # Show how requests affect visibility
    requests = production_building.get_output_requests()
    print(f"Active requests: {requests}")

    # In a full implementation, the _get_requested_outputs method would
    # use these requests to determine what to show
    print("\nNote: In full implementation, visible inventory would now include requested items only")
    print()


def demo_progressive_tracking_adoption():
    """Show how a user can progressively adopt more tracking features."""

    print("=== Progressive Tracking Adoption ===\n")

    # Start with minimal tracking
    facility = FacilityNode(
        node_id="progressive_001",
        location_name="User-Friendly Facility",
        tracking_config=FacilityTrackingConfig(mode=FacilityTrackingMode.UNTRACKED)
    )

    building = FacilityNode(
        node_id="prog_build_001",
        location_name="Flexible Factory",
        tracking_config=FacilityTrackingConfig(mode=FacilityTrackingMode.UNTRACKED)
    )
    building.building_type = "AdaptiveFactory"
    facility.add_building(building)

    print("Phase 1 - Starting with untracked mode:")
    print(f"Current mode: {facility.tracking_config.mode.value}")
    print(f"Features: {[f.value for f in facility.tracking_config.enabled_features]}")
    print()

    # User gets comfortable, adds output tracking
    print("Phase 2 - User adds output tracking for pickup coordination:")
    new_config = FacilityTrackingConfig(mode=FacilityTrackingMode.OUTPUTS_ONLY)
    facility.update_facility_tracking_config(new_config)
    print(f"Current mode: {facility.tracking_config.mode.value}")
    print()

    # User wants reservation tracking
    print("Phase 3 - User enables reservation tracking:")
    facility.tracking_config.enable_feature(FacilityTrackingFeatures.RESERVATIONS)
    facility.update_facility_tracking_config(facility.tracking_config)
    print(f"Features: {[f.value for f in facility.tracking_config.enabled_features]}")
    print()

    # User goes full tracking
    print("Phase 4 - User upgrades to full input/output tracking:")
    advanced_config = FacilityTrackingConfig(
        mode=FacilityTrackingMode.INPUTS_AND_OUTPUTS,
        enabled_features=[
            FacilityTrackingFeatures.POWER,
            FacilityTrackingFeatures.LIQUIDS,
            FacilityTrackingFeatures.RESERVATIONS,
            FacilityTrackingFeatures.MAINTENANCE_SUPPLIES
        ]
    )
    facility.update_facility_tracking_config(advanced_config)

    summary = facility.get_tracking_summary()
    print(f"Final mode: {summary['facility_tracking_mode']}")
    print(f"Final features: {summary['facility_enabled_features']}")
    print()


def demo_mixed_facility_tracking():
    """Show how different buildings in the same facility can have different tracking."""

    print("=== Mixed Building Tracking ===\n")

    # Create facility with default tracking
    facility = FacilityNode(
        node_id="mixed_001",
        location_name="Mixed Tracking Facility",
        tracking_config=FacilityTrackingConfig(mode=FacilityTrackingMode.OUTPUTS_ONLY)
    )

    # Building 1: Uses facility default
    building1 = FacilityNode(
        node_id="mixed_build_001",
        location_name="Standard Factory",
        tracking_config=FacilityTrackingConfig(mode=FacilityTrackingMode.OUTPUTS_ONLY)
    )
    building1.building_type = "StandardFactory"

    # Building 2: Has custom tracking config
    building2 = FacilityNode(
        node_id="mixed_build_002",
        location_name="High-Detail Factory",
        tracking_config=FacilityTrackingConfig(
            mode=FacilityTrackingMode.INPUTS_AND_OUTPUTS,
            enabled_features=[FacilityTrackingFeatures.POWER, FacilityTrackingFeatures.LIQUIDS]
        )
    )
    building2.building_type = "PrecisionFactory"

    # Building 3: Minimal tracking override
    building3 = FacilityNode(
        node_id="mixed_build_003",
        location_name="Simple Factory",
        tracking_config=FacilityTrackingConfig(mode=FacilityTrackingMode.UNTRACKED)
    )
    building3.building_type = "SimpleFactory"

    facility.add_building(building1)
    facility.add_building(building2)
    facility.add_building(building3)

    summary = facility.get_tracking_summary()
    print("Facility with mixed building tracking configurations:")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    demo_tracking_modes()
    demo_request_driven_tracking()
    demo_progressive_tracking_adoption()
    demo_mixed_facility_tracking()

    print("=== Summary ===")
    print("""
    The facility tracking system provides:
    
    1. GRADUATED COMPLEXITY: Users start simple and add features as needed
    2. DEMAND-DRIVEN DATA: Untracked facilities only show what's requested
    3. FLEXIBLE CONFIGURATION: Different buildings can have different tracking levels
    4. LOW BARRIER TO ENTRY: Default untracked mode requires minimal user input
    5. SCALABLE FEATURES: Additional capabilities (power, liquids, etc.) can be enabled independently
    
    This design prioritizes user adoption while maintaining the ability to scale up
    to full facility management when users are ready and willing to provide more data.
    """)
