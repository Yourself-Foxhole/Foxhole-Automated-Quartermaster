# Foxhole Logistics Network Onboarding Workflow

## Overview

The Network Onboarding CLI provides an interactive way to set up and configure Foxhole logistics networks. This tool guides users through creating a supply chain graph with MPFs, refineries, factories, facilities, and their connections.

## Quick Start

### Interactive Onboarding
```bash
python3 onboard_network.py
```

### Load Existing Network
```bash
python3 onboard_network.py --load network.yaml
python3 onboard_network.py --status network.yaml
```

### Create Demo Network
```bash
python3 create_demo_network.py
```

## Onboarding Workflow

### Step 1: Mass Production Facilities (MPFs)
- Add MPFs by location/name
- MPFs provide bulk production discounts for vehicles, ships, and equipment
- Can skip if no MPF access

### Step 2: Refineries
- Add refineries by location and type:
  - Basic Materials Refinery
  - Explosive Materials Refinery
  - Fuel Refinery
  - Other/Custom
- Refineries process raw materials into BMats, EMats, fuel, etc.

### Step 3: Factories
- Add factories by location and type:
  - Small Arms Factory
  - Heavy Arms Factory
  - Ammunition Factory
  - Utility Factory
  - Medical Factory
  - Other/Custom
- Factories produce weapons, ammunition, and equipment

### Step 4: Other Facilities
- Add other logistics facilities:
  - Storage Depot
  - Seaport
  - Garage
  - Shipyard
  - Construction Yard
  - Other/Custom

### Step 5: Network Connections
- Connect facilities to define material flow
- Specify allowed items for each connection (optional)
- Creates directed edges in the logistics graph

### Step 6: Frontline Status
- Mark facilities as "frontline" for demo/testing
- Helps prioritize logistics in war scenarios
- Used for task prioritization and routing

## File Formats

### YAML Format (Recommended)
```yaml
metadata:
  version: '1.0'
  tool: Foxhole Automated Quartermaster - Network Onboarding
  description: Foxhole logistics network configuration
nodes:
  node_001:
    id: node_001
    location_name: Westgate Mass Production Factory
    unit_size: crate
    base_type: Production
    metadata:
      facility_type: MPF
      description: Main MPF for vehicle production
      hex: Westgate
      frontline: false
    inventory: {}
    delta: {}
    status: unknown
    production_type: MassProductionFactory
edges:
  - source: node_002
    target: node_001
    allowed_items:
      - bmats
      - emats
      - refined_materials
    production_process: null
    user_config: null
```

### JSON Format
Similar structure as YAML but in JSON format for programmatic access.

## Integration with Existing Systems

### Graph Classes
- Uses existing `InventoryGraph`, `InventoryNode` classes
- Leverages `ProductionNode` hierarchy (`FactoryNode`, `MassProductionFactoryNode`, etc.)
- Maintains compatibility with `FacilityNode` and `BaseType` enums
- No parallel graph structure - integrates directly with existing code

### Production Processes
- References `PRODUCTION_PROCESS_MAP` for valid production types
- Supports all facility types and process types from game data
- Maintains consistency with existing order and inventory systems

### Serialization
- Human-readable YAML/JSON format
- Preserves all node attributes and metadata
- Supports full round-trip save/load
- Compatible with existing graph validation logic

## Command Line Usage

```bash
# Interactive onboarding wizard
python3 onboard_network.py

# Load and display existing network
python3 onboard_network.py --load network.yaml
python3 onboard_network.py --status network.json

# Help
python3 onboard_network.py --help
```

## Example Networks

### Simple Production Chain
```
Refinery → Factory → Depot
```

### Complex Multi-Facility Network
```
Refinery → MPF → Depot
     ↓      ↓      ↓
  Factory → → → Seaport
```

### Demo Network
Run `python3 create_demo_network.py` to generate a complete example network with:
- 1 MPF (Westgate)
- 1 Refinery (Heartlands) 
- 1 Factory (Deadlands) - marked as frontline
- 1 Storage Depot (Westgate)
- 1 Seaport (Fisherman's Row)
- 6 connections showing material flow

## Testing and Validation

### Running Tests
```bash
python3 -m pytest test_onboard_network.py -v
```

### Test Coverage
- Node creation and type preservation
- Network serialization/deserialization
- YAML/JSON round-trip compatibility
- Graph integration and validation
- Error handling and edge cases

## Future Enhancements

- War API integration for auto-discovery of facilities
- Template networks for common scenarios
- Validation rules for logical connections
- Integration with Discord bot commands
- Automated network optimization suggestions

---

## Legacy Documentation (Discord Bot Workflow)

The following below includes an example exchange for a new war.

--Start of onboarding--

Welcome to the Foxhole Automated Quartermaster (FAQ). This bot aims to create and manage tasks in a ticketing system to
facilitate communication between players of Foxhole. By better communicating, it aims to answer the following questions:

* What can I do to help?
* What should I work on next?
* Why don't we have what we need?
* How much longer until we get x?

-- Query WarAPI @

Welcome to War {Number}

1. Proceeding with onboarding will delete and rebuild your database and require you to reenter all your setup
   information. This is intended to be done at the start of every war. Are you sure you want to continue?
    1. If you want to change only a single setting, you may do so with a command.
    2. If you would like a list of everything covered in onboarding react.
2. Which MPF do you want to use?
    1. List all MPFs
    2. List an option to not use an MPF
3. Do you want to add nearby buildings to the MPF to your logistics network?
    1. All Buildings
    2. Storage Depot / Seaport
    3. Factory
    4. Refinery
    5. Garage
    6. Shipyard
4. Do you want to add any additional refineries?
    1. Use War API to list all refineries
    2. Group by number of factories in hex
    3. Include an option to skip
5. Do you want to add nearby logistics buildings to your network? (same as MPF question, but filtered for what is inex)
6. Do you want to add any additional factories?
    1. Use War API to gather a list of all factories
    2. Group first by if there is a refinery present in the same hex
    3. Then group by the number of factories present in the hex, in descending order
    4. Always list island hexes within a group
7. 
