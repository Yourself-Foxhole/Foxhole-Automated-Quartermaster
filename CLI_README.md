# Network Onboarding CLI

A robust CLI tool for onboarding and configuring Foxhole logistics networks. This tool guides users through setting up core supply chain components (MPFs, refineries, factories, facilities) and their connections, stores networks in human-readable format, and supports loading/saving for debugging and simulation.

## Features

- ✅ **Interactive CLI Onboarding** - Step-by-step wizard for network setup
- ✅ **Multiple Node Types** - MPFs, refineries, factories, facilities
- ✅ **Network Connections** - Define material flow between facilities
- ✅ **Frontline Status** - Mark facilities for demo/testing scenarios
- ✅ **Human-Readable Storage** - Save networks as YAML or JSON
- ✅ **Load/Save Support** - Full round-trip serialization
- ✅ **Graph Integration** - Uses existing inventory/production graph classes
- ✅ **Comprehensive Tests** - Full test suite with 17 test cases

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
python3 onboard_network.py --status demo_foxhole_network.yaml
```

## Usage Examples

### 1. Create a Simple Network
```bash
$ python3 onboard_network.py
============================================================
Foxhole Automated Quartermaster - Network Onboarding
============================================================

Welcome to the network onboarding wizard!
This tool will guide you through setting up your logistics network.

You'll be prompted to add:
  1. MPF (Mass Production Facility)
  2. Refineries
  3. Factories
  4. Other Facilities
  5. Network connections

Ready to begin? (y/n): y

==================================================
STEP 1: Mass Production Facilities (MPFs)
==================================================
# ... follow prompts
```

### 2. Load and Inspect Network
```bash
$ python3 onboard_network.py --status demo_foxhole_network.yaml
Loading network status from: demo_foxhole_network.yaml

============================================================
NETWORK STATUS
============================================================
Nodes: 5
Edges: 6

Nodes:
  node_001: Westgate Mass Production Factory (MPF)
  node_002: Heartlands Basic Materials Refinery (Refinery)
  node_003: Deadlands Arms Factory (Factory) 🔥
  node_004: Westgate Supply Depot (Storage Depot)
  node_005: Fisherman's Row Seaport (Seaport)

Edges:
  node_002 → node_001
    Items: bmats, emats, refined_materials
  # ... more connections
```

## File Format

Networks are saved in human-readable YAML or JSON format:

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

## Architecture Integration

This tool integrates seamlessly with the existing codebase:

- **Uses Existing Classes**: `InventoryGraph`, `InventoryNode`, `ProductionNode` hierarchy
- **No Parallel Structure**: Creates the same graph objects as the rest of the system
- **Type Preservation**: Maintains `FactoryNode`, `MassProductionFactoryNode`, `RefineryNode`, `FacilityNode` types
- **Metadata Support**: Stores frontline status and facility descriptions
- **Production Compatibility**: Uses `PRODUCTION_PROCESS_MAP` for valid processes

## Node Types Supported

| Type | Class | Description |
|------|-------|-------------|
| MPF | `MassProductionFactoryNode` | Mass production facilities with bulk discounts |
| Refinery | `RefineryNode` | Basic/explosive materials refineries |
| Factory | `FactoryNode` | Small arms, heavy arms, ammunition factories |
| Facility | `FacilityNode` | Storage depots, seaports, garages, shipyards |

## Testing

Run the comprehensive test suite:

```bash
python3 -m pytest test_onboard_network.py -v
```

Test coverage includes:
- Node creation and type preservation
- Network serialization/deserialization  
- YAML/JSON round-trip compatibility
- Graph integration validation
- Error handling and edge cases

### Test Results
```
17 passed, 2 warnings in 0.05s
```

## Command Line Options

```bash
usage: onboard_network.py [-h] [--load FILE] [--status FILE]

Foxhole Automated Quartermaster - Network Onboarding CLI

options:
  -h, --help     show this help message and exit
  --load FILE    Load an existing network from file
  --status FILE  Load network and display status

Examples:
  python onboard_network.py                    # Interactive onboarding
  python onboard_network.py --load network.yaml  # Load and display network
  python onboard_network.py --status network.yaml # Show network status
```

## Implementation Details

### Key Features
- **Step-by-Step Workflow**: Guides users through MPF → Refinery → Factory → Facility → Connections → Frontline
- **Input Validation**: Validates user choices and prevents invalid configurations
- **Flexible Connections**: Supports specifying allowed items or allowing all items
- **Metadata Rich**: Stores facility types, descriptions, hex locations, frontline status
- **Error Handling**: Graceful handling of file errors, invalid inputs, interrupted workflows

### Class Structure
```python
class NetworkOnboardingCLI:
    def __init__(self):
        self.graph = InventoryGraph()          # Main graph object
        self.nodes = {}                        # Node registry
        self.next_node_id = 1                  # Auto-incrementing IDs
    
    def run(self):                             # Main interactive workflow
    def load_network(self, filepath):          # Load from YAML/JSON
    def _serialize_network(self):              # Convert to dict
    def _save_yaml(self, filepath):            # Save as YAML
    def _save_json(self, filepath):            # Save as JSON
```

## Future Enhancements

- **War API Integration**: Auto-discover facilities from game API
- **Network Templates**: Predefined templates for common scenarios
- **Validation Rules**: Logical connection validation
- **Discord Integration**: Connect with bot commands
- **Network Analysis**: Optimization and bottleneck detection

## Files

| File | Description |
|------|-------------|
| `onboard_network.py` | Main CLI tool (executable) |
| `test_onboard_network.py` | Comprehensive test suite |
| `create_demo_network.py` | Demo network generator |
| `demo_foxhole_network.yaml` | Sample network (YAML format) |
| `demo_foxhole_network.json` | Sample network (JSON format) |

## Dependencies

- Python 3.12+
- `pyyaml` - YAML file support
- `pytest` - Testing framework
- Existing project modules (inventory, production nodes, etc.)

## License

Same as parent project.