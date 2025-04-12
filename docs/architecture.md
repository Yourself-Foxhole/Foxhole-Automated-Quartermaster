# Application Architecture

## Overview

The application follows a layered architecture pattern, separating concerns and responsibilities into distinct layers. This design promotes maintainability, testability, and scalability.

## Layer Structure

```
┌─────────────────────────────────────────────────────────┐
│                      Presentation Layer                  │
│                    (Discord Bot Interface)              │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                      Service Layer                       │
│              (Business Logic & Orchestration)           │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                      Data Access Layer                   │
│              (Database Models & Operations)             │
└─────────────────────────────────────────────────────────┘
```

## Layer Details

### 1. Presentation Layer (Discord Bot Interface)
- **Location**: `src/bot/discord_bot.py`
- **Purpose**: Handles user interactions through Discord
- **Responsibilities**:
  - Command parsing and validation
  - User input handling
  - Response formatting
  - Event handling
  - Permission management
- **Dependencies**: Service Layer
- **Key Components**:
  - Command handlers
  - Event listeners
  - Message formatters
  - Permission checkers

### 2. Service Layer (Business Logic)
- **Location**: `src/services/`
- **Purpose**: Implements business logic and orchestrates operations
- **Components**:
  1. **Inventory Service** (`inventory.py`)
     - Inventory tracking
     - Stock level management
     - Resource allocation
     - Buffer management

  2. **Task Service** (`task.py`)
     - Task creation and management
     - Priority calculation
     - Task assignment
     - Status tracking
     - Automatic task generation

  3. **Recipe Service** (`recipe.py`)
     - Recipe management
     - Production planning
     - Resource requirements calculation
     - MPF optimization

- **Responsibilities**:
  - Business rule enforcement
  - Data validation
  - Complex operation orchestration
  - Transaction management
  - Error handling
- **Dependencies**: Data Access Layer

### 3. Data Access Layer
- **Location**: `src/database/`
- **Purpose**: Manages data persistence and retrieval
- **Components**:
  1. **Database Manager** (`database_manager.py`)
     - Connection management
     - Session handling
     - Transaction control
     - Database initialization

  2. **Models** (`models.py`)
     - Data structure definition
     - Relationship mapping
     - Constraint enforcement
     - Data validation

## Layer Interactions

### Flow Example: Creating a Logistics Task

1. **Presentation Layer**
   ```
   User Command → Command Parser → Input Validation
   ```

2. **Service Layer**
   ```
   Task Service
   ├── Validates requirements
   ├── Checks inventory availability
   ├── Calculates priority
   └── Orchestrates task creation
   ```

3. **Data Access Layer**
   ```
   Database Manager
   ├── Creates database session
   ├── Manages transaction
   └── Persists task data
   ```

## State Diagrams

### Task States
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Created   │────▶│  Assigned   │────▶│  In Progress│
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │                    │
       │                   │                    │
       ▼                   ▼                    ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Cancelled  │◀────│   Failed    │◀────│  Completed  │
└─────────────┘     └─────────────┘     └─────────────┘
```

**Task State Transitions:**
- Created → Assigned: When a task is assigned to a player
- Assigned → In Progress: When work begins on the task
- In Progress → Completed: When task requirements are met
- In Progress → Failed: When task cannot be completed
- Any State → Cancelled: When task is manually cancelled

### Location States
```
┌─────────────┐     ┌─────────────┐
│  Active     │────▶│  Understock │
└─────────────┘     └─────────────┘
       │                   │
       │                   │
       ▼                   ▼
┌─────────────┐     ┌─────────────┐
│  Inactive   │◀────│  Overstock  │
└─────────────┘     └─────────────┘
```

**Location State Transitions:**
- Active → Understock: When inventory falls below threshold
- Understock → Active: When inventory is replenished
- Active → Overstock: When inventory exceeds maximum
- Overstock → Active: When inventory is reduced
- Any State → Inactive: When location is disabled

### Inventory States
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Oversupply │◀────│   Normal    │────▶│    Low      │
└─────────────┘     └─────────────┘     └─────────────┘
       ▲                   │                   │
       │                   │                   │
       │                   ▼                   ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Reserved   │◀────│  Critical   │◀────│  Reserved   │
└─────────────┘     └─────────────┘     └─────────────┘
```

**Inventory State Color Coding:**
- 🔴 Critical (Red): Immediate attention required
- 🟡 Low (Yellow): Needs attention soon
- 🟢 Normal (Green): Healthy stock levels
- 💚 Oversupply (Flashing Green): Opportunity for redistribution
- ⚪ Reserved: Items allocated to tasks

**Inventory State Transitions:**
- Normal → Low: When stock falls below warning threshold
- Low → Critical: When stock falls below critical threshold
- Critical → Low: When stock is partially replenished
- Low → Normal: When stock is fully replenished
- Normal → Oversupply: When stock exceeds optimal levels
- Oversupply → Normal: When excess stock is redistributed
- Any State → Reserved: When items are allocated to tasks

### Recipe States
```
┌─────────────┐     ┌─────────────┐
│  Available  │────▶│  In Use     │
└─────────────┘     └─────────────┘
       │                   │
       │                   │
       ▼                   ▼
┌─────────────┐     ┌─────────────┐
│  Disabled   │◀────│  Updating   │
└─────────────┘     └─────────────┘
```

**Recipe State Transitions:**
- Available → In Use: When recipe is selected for production
- In Use → Available: When production is complete
- Available → Updating: When recipe is being modified
- Updating → Available: When recipe update is complete
- Any State → Disabled: When recipe is temporarily disabled

### State Management Rules

1. **Task State Management**
   - Only authorized users can change task states
   - State changes must be logged
   - Failed tasks require reason documentation
   - Cancelled tasks can be reactivated if needed

2. **Location State Management**
   - State changes trigger notifications
   - Understock state generates automatic tasks
   - Overstock state triggers resource redistribution
   - Inactive state prevents new task assignment

3. **Inventory State Management**
   - State changes update buffer calculations
   - Critical state (🔴) triggers emergency tasks
   - Low state (🟡) generates warning notifications
   - Normal state (🟢) indicates healthy inventory
   - Oversupply state (💚) suggests redistribution opportunities
   - Reserved state (⚪) prevents double allocation
   - State changes affect priority calculations
   - Color coding helps quick visual status assessment

4. **Recipe State Management**
   - State changes require version control
   - Updating state prevents concurrent modifications
   - Disabled state maintains historical data
   - State changes affect task generation

## Desired State Configuration

### Building-Based Stockpile Configuration
```
┌─────────────────────────────────────────────────────────┐
│                Building Type Defaults                    │
├─────────────────────────────────────────────────────────┤
│ Building: Bunker Base / Front Line Base                 │
│ ├── Critical Threshold: 1000                            │
│ ├── Low Threshold: 2000                                 │
│ ├── Normal Range: 2000-5000                             │
│ ├── Oversupply Threshold: 5000                          │
│ ├── Buffer Size: 500                                    │
│ └── Priority Score: 10                                  │
│                                                         │
│ Building: Logistics Building                            │
│ ├── Critical Threshold: 5000                            │
│ ├── Low Threshold: 10000                                │
│ ├── Normal Range: 10000-20000                           │
│ ├── Oversupply Threshold: 20000                         │
│ ├── Buffer Size: 2000                                   │
│ └── Priority Score: 8                                   │
│                                                         │
│ Building: Production Building                           │
│ ├── Critical Threshold: 2000                            │
│ ├── Low Threshold: 5000                                 │
│ ├── Normal Range: 5000-10000                            │
│ ├── Oversupply Threshold: 10000                         │
│ ├── Buffer Size: 1000                                   │
│ └── Priority Score: 7                                   │
└─────────────────────────────────────────────────────────┘
```

### Building Types and Roles

1. **Bunker Bases / Front Line Bases**
   - Primary combat support locations
   - Highest priority for critical supplies
   - Smaller storage capacity
   - Focus on combat essentials
   - High priority score for task generation

2. **Logistics Buildings**
   - Seaports and Storage Depots
   - Large storage capacity
   - Regional distribution hubs
   - Medium priority score
   - Focus on bulk storage

3. **Production Buildings**
   - Factories
   - Mass Production Factories
   - Facilities
   - Production-focused storage
   - Lower priority score
   - Focus on production materials

### Location-Specific Overrides
```
┌─────────────────────────────────────────────────────────┐
│                Location Override Example                 │
├─────────────────────────────────────────────────────────┤
│ Location: Frontline Bunker Base                         │
│ Building Type: Bunker Base                              │
│ ├── Critical Threshold: 1500 (Override: +500)           │
│ ├── Low Threshold: 2500 (Override: +500)                │
│ ├── Normal Range: 2500-6000 (Override: +1000)           │
│ ├── Oversupply Threshold: 6000 (Override: +1000)        │
│ ├── Buffer Size: 750 (Override: +250)                   │
│ └── Priority Score: 10 (Override: +0)                   │
└─────────────────────────────────────────────────────────┘
```

### Configuration Management
1. **Default Settings**
   - Based on building type and role
   - Configured at system level
   - Can be modified by administrators
   - Used as base for all locations

2. **Location Overrides**
   - Inherit from building type defaults
   - Can modify any threshold
   - Supports additive or absolute changes
   - Maintains override history

3. **Threshold Types**
   - Critical Threshold: Minimum acceptable quantity
   - Low Threshold: Warning level for low stock
   - Normal Range: Optimal operating range
   - Oversupply Threshold: Maximum desired quantity
   - Buffer Size: Safety stock level
   - Priority Score: Importance for task generation

### Task Generation Based on Desired State

1. **Gap Analysis**
   ```
   For each item at each building:
   ├── Calculate Current State
   │   └── Actual Stockpile Quantity - Reserved Amount
   ├── Determine Desired State
   │   ├── Get Building Type Default
   │   └── Apply Location Override
   ├── Calculate Gap
   │   └── Desired State - Current State
   └── Determine Action Required
       ├── If Gap > 0: Need More Items
       └── If Gap < 0: Have Excess Items
   ```

2. **Task Priority Calculation**
   ```
   Priority Score = Base Priority
   ├── + (Gap Size * Priority Multiplier)
   ├── + (Location Importance * Location Multiplier)
   ├── + (Item Criticality * Criticality Multiplier)
   └── + (Time Sensitivity * Time Multiplier)
   ```

3. **Task Generation Rules**
   - **Critical State (🔴)**
     ```
     If Current < Critical Threshold:
     ├── Generate Emergency Task
     ├── Highest Priority
     └── Notify All Available Players
     ```
   
   - **Low State (🟡)**
     ```
     If Current < Low Threshold:
     ├── Generate Warning Task
     ├── Medium Priority
     └── Notify Logistics Players
     ```
   
   - **Normal State (🟢)**
     ```
     If Current in Normal Range:
     ├── No Action Required
     └── Monitor for Changes
     ```
   
   - **Oversupply State (💚)**
     ```
     If Current > Oversupply Threshold:
     ├── Generate Redistribution Task
     ├── Low Priority
     └── Suggest Optimal Distribution
     ```

4. **Task Assignment Logic**
   ```
   For each Generated Task:
   ├── Calculate Required Resources
   │   ├── Items Needed
   │   ├── Transport Capacity
   │   └── Time Estimate
   ├── Find Suitable Players
   │   ├── Check Availability
   │   ├── Check Skills
   │   └── Check Location
   ├── Assign Task
   │   ├── Set Priority
   │   ├── Set Deadline
   │   └── Set Rewards
   └── Monitor Progress
       ├── Track Completion
       ├── Adjust Priority
       └── Handle Failures
   ```

### Configuration Interface
```
/configure
├── building <building_type>
│   ├── set critical <value>
│   ├── set low <value>
│   ├── set normal <min> <max>
│   ├── set oversupply <value>
│   ├── set buffer <value>
│   └── set priority <score>
└── location <location_name> <building_type>
    ├── override critical <value>
    ├── override low <value>
    ├── override normal <min> <max>
    ├── override oversupply <value>
    ├── override buffer <value>
    └── override priority <score>
```

### Benefits of Desired State Configuration

1. **Flexibility**
   - Each item can be tuned to specific needs
   - Different locations can have different requirements
   - Easy to adjust based on changing conditions

2. **Automation**
   - System automatically maintains desired state
   - Reduces manual monitoring
   - Proactive task generation

3. **Optimization**
   - Resources allocated based on priorities
   - Prevents over/under stocking
   - Efficient resource distribution

4. **Visibility**
   - Clear view of desired vs. actual state
   - Easy to identify gaps
   - Simple to adjust thresholds

## Benefits of Layered Architecture

1. **Separation of Concerns**
   - Each layer has a specific responsibility
   - Changes in one layer don't affect others
   - Easier to maintain and modify

2. **Testability**
   - Layers can be tested independently
   - Mock dependencies easily
   - Clear boundaries for unit tests

3. **Scalability**
   - Layers can be scaled independently
   - Easy to add new features
   - Simple to modify business logic

4. **Security**
   - Clear access control points
   - Data validation at multiple levels
   - Controlled data flow

## Best Practices

1. **Dependency Direction**
   - Dependencies flow downward
   - Upper layers depend on lower layers
   - No circular dependencies

2. **Data Transfer**
   - Use DTOs (Data Transfer Objects) between layers
   - Validate data at layer boundaries
   - Transform data as needed

3. **Error Handling**
   - Each layer handles its specific errors
   - Propagate errors appropriately
   - Maintain error context

4. **Testing Strategy**
   - Unit test each layer independently
   - Integration test layer interactions
   - Mock external dependencies 