## 

## Understanding the Domain

Before diving into code, it's important to understand what we're building:

* This is a Discord bot for the game Foxhole that helps coordinate logistics operations  
* It uses a "pull-based" model where demands at the frontline generate upstream tasks  
* The system tracks inventories, creates tasks, and helps players coordinate activities  
* It distinguishes between different production methods (Factory, MPF, Facility)  
* Tasks have various states and follow a workflow from resource gathering to frontline delivery

## **Technology Stack**

Based on the requirements, I recommend the following technologies:

1. Programming Language: Python 3.9+ (compatible with Discord.py)  
2. Discord Library: Discord.py (or Pycord/Disnake if Discord.py isn't maintained)  
3. Database: SQLite  
4. ORM: SQLAlchemy (for database abstraction)  
5. Task Scheduling: APScheduler (for handling timeouts and time-based events)  
6. Testing: pytest for unit and integration testing  
7. Deployment: Docker (for easy deployment and environment consistency)  
8. Container Orchestration: Kubernetes

## Command Parser System

The bot requires robust command parsing to handle the complex command syntax shown in the design documents:

\!hub config \[HubName\] set\_buffer \[Item\] \[TargetQty\]  
\!stock report \[HubNameOrBaseName\] \[--source FrontlineHubName\] \[Item1\]=\[Qty1\] ...  
This suggests the need for:

A command argument parser that can handle positional and named arguments  
Support for optional flags (like \--source)  
Type conversion for numerical values  
Validation logic for command syntax and parameters

## Asynchronous Processing Model

The bot will need to handle multiple concurrent operations:

Responding to Discord commands while processing logistics calculations  
Running background tasks for checking timeouts and completion times  
Managing database operations without blocking the main event loop

This suggests implementing:

Proper async/await patterns throughout the codebase  
Task queues for background processing  
Connection pooling for database interactions

State Management

The bot tracks complex state across multiple entities:

Task lifecycle states (UNCLAIMED, PENDING, IN\_PROGRESS, COMPLETE)  
Inventory levels at multiple locations  
Production status at factories, MPFs, and facilities

This requires:

Well-designed state machines for transitions  
Database transactions to ensure consistency  
Locking mechanisms to prevent race conditions

### **Error Handling**

The bot should implement robust error handling:

* Graceful handling of Discord API rate limits and outages  
* Database connection error recovery  
* Input validation with helpful error messages  
* Exception tracking and logging

A structured logging system should capture:

* Command invocations with parameters  
* State transitions  
* Error conditions with stack traces  
* Performance metrics

### **Testing Strategy**

For this bot, a comprehensive testing strategy should include:

* Unit tests for core logic components (pull model, task prioritization)  
* Integration tests for database interactions  
* Mock-based tests for Discord API interactions  
* End-to-end tests simulating complete workflows

### **Deployment Pipeline**

A proper CI/CD pipeline would be beneficial:

* Automated testing on code commits  
* Docker image building and versioning  
* Deployment to staging environment for verification  
* Controlled rollout to production

### **Performance Considerations**

To ensure responsive performance:

* Database indices on frequently queried fields (task status, hub names, etc.)  
* Connection pooling for database access  
* Caching of frequently accessed data (recipes, hub configurations)  
* Query optimization for task listing operations

### **Security Measures**

Since this is a Discord bot handling game logistics:

* Role-based access control for administrative commands  
* Input sanitization to prevent injection attacks  
* Secure storage of Discord token and other credentials  
* Rate limiting for commands to prevent abuse

## 

## Data Model

The data model needs to capture several key aspects of the logistics system:

* Locations (hubs, bases, facilities)  
* Inventory tracking  
* Tasks and their lifecycle  
* Production recipes  
* User configurations and permissions

Let's break down each entity in detail:

### Core Entities

### **1\. Location**

This represents any physical location in the game where items can be stored or produced.

class Location:  
    id: str  \# Unique identifier  
    name: str  \# Human-readable name  
    type: LocationType  \# Enum: FORWARD\_BASE, FRONTLINE\_HUB, BACKLINE\_HUB, REFINERY, FACTORY, MPF, FACILITY  
    coordinates: str  \# In-game coordinates  
    managed\_by\_role: str  \# Discord role ID that manages this location  
    source\_location\_ids: List\[str\]  \# IDs of upstream locations that supply this location  
    created\_at: datetime  
    updated\_at: datetime

### **2\. Item**

Represents any item in the game that can be produced, transported or consumed.

class Item:  
    id: str  \# Unique identifier (might be game's internal ID)  
    name: str  \# Human-readable name  
    category: ItemCategory  \# Enum: WEAPON, AMMUNITION, VEHICLE, MEDICAL, UNIFORM, BUILDING, RAW\_RESOURCE, REFINED\_RESOURCE, etc.  
    is\_crate\_packable: bool  \# Can this item be packaged into crates?  
    crate\_size: float  \# How many can fit in a standard transport unit  
    created\_at: datetime  
    updated\_at: datetime

### **3\. Recipe**

Defines how items are produced and what input materials are required.

class Recipe:  
    id: str  \# Unique identifier  
    output\_item\_id: str  \# What item is produced  
    output\_quantity: int  \# How many are produced  
    production\_location\_type: ProductionLocationType  \# Enum: FACTORY, MPF, FACILITY, REFINERY  
    production\_time: int  \# Time in minutes to produce  
    mpf\_discount\_eligible: bool  \# Can benefit from MPF batch discounts  
    created\_at: datetime  
    updated\_at: datetime

### **4\. Recipe Ingredient**

Many-to-many relationship between Recipes and Items that are used as inputs.

class RecipeIngredient:  
    recipe\_id: str  \# Reference to Recipe  
    ingredient\_item\_id: str  \# Reference to Item used as input  
    quantity: int  \# How many of this item are needed  
    created\_at: datetime  
    updated\_at: datetime

### **5\. Inventory**

Tracks the last reported inventory level of an item at a specific location.

class Inventory:  
    location\_id: str  \# Reference to Location  
    item\_id: str  \# Reference to Item  
    quantity: int  \# Current quantity as last reported  
    last\_updated: datetime  \# When this was last reported  
    reported\_by\_user\_id: str  \# Discord user ID who reported this  
    created\_at: datetime  
    updated\_at: datetime

### **6\. Task**

The central entity that represents a specific logistics task to be completed.

class Task:  
    id: str  \# Unique identifier  
    task\_type: TaskType  \# One of the task types defined in the design doc (RAW, REFINE\_IN\_PROGRESS, etc.)  
    item\_id: str  \# Reference to Item  
    quantity: int  \# How many of the item  
    status: TaskStatus  \# Enum: UNCLAIMED, PENDING, IN\_PROGRESS, COMPLETE  
    priority\_score: int  \# Calculated priority  
    source\_location\_id: str  \# Where the item should come from  
    target\_location\_id: str  \# Where the item should go  
    claimed\_by\_user\_id: str  \# Discord user ID who claimed the task, null if unclaimed  
    linked\_task\_id: str  \# Optional reference to a parent task  
    production\_location\_type: ProductionLocationType  \# Enum: FACTORY, MPF, FACILITY, null if not applicable  
    estimated\_completion\_time: datetime  \# When production is expected to finish  
    claim\_timeout: datetime  \# When the claim expires  
    pending\_timeout: datetime  \# When the pending status expires  
    urgency: UrgencyLevel  \# Enum: LOW, MEDIUM, HIGH  
    created\_at: datetime  
    updated\_at: datetime  
    completed\_at: datetime  \# When the task was marked complete

### **7\. LocationBuffer**

Defines the desired buffer levels for items at specific locations.

class LocationBuffer:  
    location\_id: str  \# Reference to Location  
    item\_id: str  \# Reference to Item  
    target\_quantity: int  \# Desired buffer level  
    critical\_threshold\_percent: int  \# Percentage below which alerts are triggered  
    alert\_role\_id: str  \# Discord role ID to ping when critical  
    default\_production\_location: ProductionLocationType  \# Where this should typically be produced  
    default\_transport\_load\_type: TransportLoadType  \# Enum: FTL, FCL  
    priority\_score: int  \# Base priority for this item at this location  
    created\_at: datetime  
    updated\_at: datetime

### **8\. User**

Tracks user preferences and permissions for the Discord bot.

class User:  
    id: str  \# Discord user ID  
    roles: List\[str\]  \# Discord role IDs  
    is\_admin: bool  \# Whether user has admin privileges  
    notification\_preferences: dict  \# JSON of notification settings  
    current\_pending\_tasks: int  \# Count of tasks in PENDING status  
    created\_at: datetime  
    updated\_at: datetime  
    last\_active: datetime

### **9\. Config**

Global configuration settings for the bot.

class Config:  
    key: str  \# Setting name  
    value: str  \# Setting value  
    description: str  \# Human-readable description  
    created\_at: datetime  
    updated\_at: datetime

### **10\. TaskHistory**

Audit log of task state changes.

class TaskHistory:  
    id: str  \# Unique identifier  
    task\_id: str  \# Reference to Task  
    previous\_status: TaskStatus  \# Previous state  
    new\_status: TaskStatus  \# New state  
    changed\_by\_user\_id: str  \# Discord user ID who made the change  
    timestamp: datetime  \# When the change occurred  
    notes: str  \# Optional notes about the change

### Enumerations

class LocationType(Enum):  
    FORWARD\_BASE \= "forward\_base"  
    FRONTLINE\_HUB \= "frontline\_hub"  
    BACKLINE\_HUB \= "backline\_hub"  
    REFINERY \= "refinery"  
    FACTORY \= "factory"  
    MPF \= "mpf"  
    FACILITY \= "facility"  
    RESOURCE\_FIELD \= "resource\_field"

class TaskType(Enum):  
    RAW \= "raw"  
    REFINE\_IN\_PROGRESS \= "refine\_in\_progress"  
    REFINE\_WAITING\_PICKUP \= "refine\_waiting\_pickup"  
    MANUFACTURE\_PENDING \= "manufacture\_pending"  
    MANUFACTURE\_IN\_PROGRESS \= "manufacture\_in\_progress"  
    MANUFACTURE\_COMPLETE \= "manufacture\_complete"  
    FACILITY\_PENDING \= "facility\_pending"  
    FACILITY\_COMPLETE \= "facility\_complete"  
    TRANSPORT\_MIDLINE\_PENDING \= "transport\_midline\_pending"  
    TRANSPORT\_FRONTLINE\_STAGED \= "transport\_frontline\_staged"  
    FRONTLINE\_DELIVERY \= "frontline\_delivery"

class TaskStatus(Enum):  
    UNCLAIMED \= "unclaimed"  
    PENDING \= "pending"  
    IN\_PROGRESS \= "in\_progress"  
    COMPLETE \= "complete"

class ProductionLocationType(Enum):  
    FACTORY \= "factory"  
    MPF \= "mpf"  
    FACILITY \= "facility"  
    REFINERY \= "refinery"

class UrgencyLevel(Enum):  
    LOW \= "low"  
    MEDIUM \= "medium"  
    HIGH \= "high"

class TransportLoadType(Enum):  
    FTL \= "ftl"  \# Full Truck Load (15 crates)  
    FCL \= "fcl"  \# Full Container Load (60 crates)  
    LIQUID \= "liquid"  \# Liquid Container (100 cans)  
    SHIPPABLE \= "shippable"  \# Pre-packaged shippable (3 vehicles)

## **Key Relationships**

1. **Location → Location**: Self-referential relationship for source\_location\_ids (where supplies come from)  
2. **Recipe → Item**: Each recipe produces one type of item  
3. **RecipeIngredient → Recipe**: Each recipe has multiple ingredients  
4. **RecipeIngredient → Item**: Each ingredient can be made into multiple items.  
5. **Inventory → Location**: Each inventory entry belongs to a location  
6. **Inventory → Item**: Each inventory entry tracks a specific item  
7. **Task → Item**: Each task involves at least one specific item, but may include multiple different items.  
8. **Task → Location**: Each task has source and target locations  
9. **Task → Task**: Tasks can be linked (parent-child relationship)  
10. **LocationBuffer → Location**: Buffer settings for a specific location  
11. **LocationBuffer → Item**: Buffer settings for a specific item  
12. **TaskHistory → Task**: History entries relate to a specific task

## **Indexing**:

Critical fields to index would include:

* Task status and priority (for quick querying of active tasks)  
* Location names (for quick lookup)  
* Item names (for quick lookup)  
* User IDs (for authentication and task claiming)  
* Task completion time estimates (for timer checks)

## **Entity Descriptions and Relationships**

### **Core Entities**

1. **Location**  
   * Represents any physical location in the game where items can be stored or produced  
   * Types include FORWARD\_BASE, FRONTLINE\_HUB, BACKLINE\_HUB, REFINERY, FACTORY, MPF, FACILITY, RESOURCE\_FIELD  
   * Has many Inventory records, LocationBuffer settings, and can be source/target for Tasks  
   * Can have multiple source locations through LocationSource relationship  
2. **Item**  
   * Represents any item in the game that can be produced, transported, or consumed  
   * Has attributes like category, whether it can be packaged into crates, and crate size  
   * Used in Recipes, RecipeIngredients, Inventory, Tasks, and LocationBuffer settings  
3. **Recipe**  
   * Defines how items are produced and what input materials are required  
   * Has a production location type (FACTORY, MPF, FACILITY, REFINERY)  
   * Records production time and whether item is eligible for MPF batch discounts  
   * Contains one output Item and multiple RecipeIngredients  
4. **RecipeIngredient**  
   * Many-to-many relationship between Recipes and Items used as inputs  
   * Stores the quantity of each ingredient needed for a recipe  
5. **Inventory**  
   * Tracks the last reported inventory level of an item at a specific location  
   * Includes who reported it and when it was last updated  
   * Composite primary key on location\_id and item\_id  
6. **Task**  
   * The central entity representing a specific logistics task to be completed  
   * Has a task\_type corresponding to the game's logistics workflow stages  
   * States include UNCLAIMED, PENDING, IN\_PROGRESS, COMPLETE  
   * Has source and target locations, an item being moved/produced  
   * Includes timeouts, priority scoring, and ownership information  
   * Can be linked to parent tasks (forming task chains)  
7. **LocationBuffer**  
   * Defines desired buffer/stock levels for items at specific locations  
   * Includes critical threshold percentages that trigger alerts  
   * Specifies default production location and transport load type for the item at that location  
   * Has priority score used in task generation  
8. **User**  
   * Represents Discord users interacting with the bot  
   * Tracks admin status, notification preferences, and task counts  
   * Connected to roles through the UserRole table  
9. **Config**  
   * Global configuration settings for the bot  
   * Simple key-value store with descriptions  
10. **TaskHistory**  
    * Audit log of task state changes  
    * Records who made changes and when  
    * Allows tracking the complete lifecycle of tasks  
11. **LocationSource**  
    * Many-to-many relationship showing which locations supply other locations  
    * Essential for implementing the pull-based model's flow  
12. **UserRole**  
    * Many-to-many relationship between Users and their Discord roles  
    * Used for permission checks and notifications

## **Key Design Considerations**

1. **Hierarchical Task System**  
   * Tasks can be linked to "parent" tasks, enabling the representation of complex workflows  
   * The linked\_task\_id in the Task entity creates this hierarchy  
2. **Location Supply Chain**  
   * LocationSource table establishes the supply chain hierarchy, defining where each location gets its supplies from  
   * Critical for implementing the multi-level pull model described in the documents  
3. **Buffer Management**  
   * LocationBuffer defines target stock levels and thresholds for each item at each location  
   * This drives the pull-based request generation system  
4. **Production Differentiation**  
   * Tasks track production\_location\_type to distinguish between Factory, MPF, and Facility production methods  
   * This affects batching, timing, and resource calculations  
5. **Task Status Management**  
   * Task entity includes timeout fields for claim and pending statuses  
   * TaskHistory provides an audit trail of state changes

erDiagram

    Location {

        string id PK

        string name

        enum location\_type

        string coordinates

        string managed\_by\_role

        datetime created\_at

        datetime updated\_at

    }

    

    Item {

        string id PK

        string name

        enum category

        boolean is\_crate\_packable

        int crate\_size

        datetime created\_at

        datetime updated\_at

    }

    

    Recipe {

        string id PK

        string output\_item\_id FK

        int output\_quantity

        enum production\_location\_type

        int production\_time

        boolean mpf\_discount\_eligible

        datetime created\_at

        datetime updated\_at

    }

    

    RecipeIngredient {

        string recipe\_id PK,FK

        string ingredient\_item\_id PK,FK

        int quantity

        datetime created\_at

        datetime updated\_at

    }

    

    Inventory {

        string location\_id PK,FK

        string item\_id PK,FK

        int quantity

        datetime last\_updated

        string reported\_by\_user\_id FK

        datetime created\_at

        datetime updated\_at

    }

    

    Task {

        string id PK

        enum task\_type 

        string item\_id FK

        int quantity

        enum status

        int priority\_score

        string source\_location\_id FK

        string target\_location\_id FK

        string claimed\_by\_user\_id FK

        string linked\_task\_id FK

        enum production\_location\_type

        datetime estimated\_completion\_time

        datetime claim\_timeout

        datetime pending\_timeout

        enum urgency

        datetime created\_at

        datetime updated\_at

        datetime completed\_at

    }

    

    LocationBuffer {

        string location\_id PK,FK

        string item\_id PK,FK

        int target\_quantity

        int critical\_threshold\_percent

        string alert\_role\_id

        enum default\_production\_location

        enum default\_transport\_load\_type

        int priority\_score

        datetime created\_at

        datetime updated\_at

    }

    

    User {

        string id PK

        boolean is\_admin

        json notification\_preferences

        int current\_pending\_tasks

        datetime created\_at

        datetime updated\_at

        datetime last\_active

    }

    

    UserRole {

        string user\_id PK,FK

        string role\_id PK

        datetime created\_at

    }

    

    Config {

        string key PK

        string value

        string description

        datetime created\_at

        datetime updated\_at

    }

    

    TaskHistory {

        string id PK

        string task\_id FK

        enum previous\_status

        enum new\_status

        string changed\_by\_user\_id FK

        datetime timestamp

        string notes

    }

    

    LocationSource {

        string location\_id PK,FK

        string source\_location\_id PK,FK

        datetime created\_at

    }

    

    Location ||--o{ LocationSource : "has\_source"

    Location ||--o{ Inventory : "stores"

    Location ||--o{ Task : "is\_source\_for"

    Location ||--o{ Task : "is\_target\_for"

    Location ||--o{ LocationBuffer : "has\_buffer"

    

    Item ||--o{ Recipe : "is\_output\_of"

    Item ||--o{ RecipeIngredient : "is\_ingredient\_in"

    Item ||--o{ Inventory : "is\_stored\_as"

    Item ||--o{ Task : "is\_required\_in"

    Item ||--o{ LocationBuffer : "has\_buffer\_for"

    

    Recipe ||--o{ RecipeIngredient : "requires"

    

    User ||--o{ UserRole : "has"

    User ||--o{ Task : "claims"

    User ||--o{ Inventory : "reports"

    User ||--o{ TaskHistory : "makes\_changes\_to"

    

    Task ||--o{ TaskHistory : "has\_history"

    Task ||--o{ Task : "links\_to"

## Python Class Considerations

## **Core Classes**

### **1\. `DiscordBot`**

**Responsibilities:**

* Initialize and maintain the connection to Discord  
* Register commands and event handlers  
* Route messages to appropriate command handlers

**Design Considerations:**

* Should use Discord.py or a similar library (Pycord/Disnake)  
* Should implement proper error handling for Discord API rate limits and outages  
* Should separate the Discord interface from the core business logic

### **2\. `CommandHandler`**

**Responsibilities:**

* Parse incoming Discord messages into structured commands  
* Validate command syntax and user permissions  
* Delegate to appropriate handlers for specific command types  
* Format and return command responses

**Design Considerations:**

* Should support complex command syntaxes like `!hub config [HubName] set_buffer [Item] [TargetQty]`  
* Should handle positional and named arguments  
* Should support optional flags (like `--source`)  
* Should support type conversion for numerical values

### **3\. `TaskManager`**

**Responsibilities:**

* Create, update, and track tasks throughout their lifecycle  
* Implement the multi-level pull model logic  
* Handle task assignment, timeouts, and completions  
* Prioritize tasks based on urgency, item type, deficit severity

**Design Considerations:**

* Should implement proper state machines for task transitions  
* Should use database transactions to ensure consistency  
* Should use locking mechanisms to prevent race conditions  
* Should handle task linkages (e.g., when one task completion triggers another)

### **4\. `StockManager`**

**Responsibilities:**

* Track and update inventory levels at various locations  
* Compare current stock levels to target buffer levels  
* Identify critical shortages and trigger alerts

**Design Considerations:**

* Should handle the fact that inventory is only updated by user reports  
* Should track when inventory was last reported and by whom  
* Should implement proper validation for stock reports

### **5\. `HubManager` (or `LocationManager`)**

**Responsibilities:**

* Manage information about game locations (hubs, bases, facilities)  
* Track configuration settings for each location  
* Handle relationships between locations (source/destination)

**Design Considerations:**

* Should support different location types:  
  * RAW\_MATERIAL  
  * Production Buildings:  
    * REFINERY  
    * FACTORY  
    * FACILITY  
  * SOURCE\_HUB  
  * FORWARD\_BASE  
  * FRONTLINE\_HUB  
* Should maintain hierarchical relationships between locations  
* Should track which Discord roles manage each location  
* Some locations (such as FACILITY) may contain relationships where they serve as a SOURCE\_HUB as they can be built anywhere on the map.  
  * A decision on whether to store in SOURCE\_HUB should be made based on the item need

### **6\. `RecipeManager`**

**Responsibilities:**

* Store and provide information about item recipes  
* Calculate resource requirements for production tasks  
* Handle production location specificities (Factory vs. MPF vs. Facility)

**Design Considerations:**

* Should account for different production methods and their efficiencies  
* Should handle MPF batch discounts and minimum batch sizes  
* Should handle the requirements for different items (some can only be made in specific locations)

### **7\. `ConfigManager`**

**Responsibilities:**

* Manage global bot settings  
* Store and retrieve configuration values  
* Handle permission checks for configuration changes

**Design Considerations:**

* Should use a key-value store approach for flexibility  
* Should validate configuration values  
* Should restrict access to admin-only settings

### **8\. `NotificationEngine`**

**Responsibilities:**

* Send alerts to users or roles in Discord  
* Handle notifications for critical stock levels  
* Send notifications for task completions, particularly MPF productions

**Design Considerations:**

* Should avoid notification fatigue with appropriate throttling  
* Should respect user notification preferences  
* Should format messages appropriately for different notification types

### **9\. `TaskScheduler`**

**Responsibilities:**

* Manage time-based events such as task timeouts  
* Check for MPF/refinery completion based on estimated times  
* Trigger events when time thresholds are reached

**Design Considerations:**

* Should use an efficient scheduling mechanism (e.g., APScheduler)  
* Should handle task priority queues  
* Should recover gracefully if the bot restarts

### **10\. `DatabaseManager`**

**Responsibilities:**

* Handle database connections and transactions  
* Provide an abstraction layer for database operations  
* Implement data models and mappings

**Design Considerations:**

* Should use a proper ORM (SQLAlchemy recommended)  
* Should implement connection pooling for efficiency  
* Should handle transaction isolation properly

## **Data Model Classes**

### **11\. `Task`**

**Responsibilities:**

* Represent a single logistics task in the system  
* Track its state, assignments, and relationships

**Design Considerations:**

* Should implement proper state transitions  
* Should track history of changes  
* Should handle linkages to related tasks

### **12\. `Location`**

**Responsibilities:**

* Represent a location in the game (hub, base, facility)  
* Track its relationships with other locations

### **13\. `Item`**

**Responsibilities:**

* Represent an item in the game  
* Track its characteristics and relationships

### **14\. `Inventory`**

**Responsibilities:**

* Track the current inventory level of an item at a location  
* Record when and by whom the inventory was reported

### **15\. `LocationBuffer`**

**Responsibilities:**

* Define the desired buffer levels for items at locations  
* Track critical thresholds and alert settings

The following is a possible draft KML diagram for the above problem.

classDiagram  
  *%% Core System Classes*  
  class DiscordBot {  
    \-token: str  
    \-command\_prefix: str  
    \+on\_message(message)  
    \+register\_commands()  
    \+send\_message(channel, content)  
    \+send\_notification(role\_or\_user, content)  
  }  
    
  class CommandHandler {  
    \+parse\_command(command\_string)  
    \+handle\_config\_command(user, args)  
    \+handle\_hub\_command(user, args)  
    \+handle\_stock\_command(user, args)  
    \+handle\_request\_command(user, args)  
    \+handle\_tasks\_command(user, args)  
    \+handle\_production\_command(user, args)  
    \+handle\_status\_command(user, args)  
    \+handle\_dashboard\_command(user, args)  
  }  
    
  class TaskManager {  
    \+create\_task(task\_type, item, quantity, target\_hub)  
    \+process\_request(requester, target, items, urgency)  
    \+trigger\_pull\_level\_1(base, item, quantity)  
    \+trigger\_pull\_level\_2(hub, item, quantity)  
    \+trigger\_pull\_level\_3(source, item, quantity)  
    \+trigger\_pull\_level\_4(item, quantity, urgency)  
    \+trigger\_pull\_level\_5(item, quantity)  
    \+trigger\_pull\_level\_6(resource, quantity)  
    \+calculate\_priority(item, deficit, urgency)  
    \+find\_tasks(filters)  
    \+claim\_task(user\_id, task\_id)  
    \+update\_task\_status(task\_id, status)  
    \+update\_mpf\_completion\_time(task\_id, time)  
    \+complete\_task(user\_id, task\_id)  
    \+abandon\_task(user\_id, task\_id)  
    \+expire\_tasks()  
    \+check\_production\_completion()  
  }  
    
  class StockManager {  
    \+report\_stock(location, user\_id, stock\_data)  
    \+get\_stock\_level(location, item)  
    \+get\_stock\_status(location)  
    \+check\_critical\_stock(location, item)  
  }  
    
  class LocationManager {  
    \+get\_hub\_config(hub\_name)  
    \+set\_hub\_buffer(hub\_name, item, target\_qty)  
    \+set\_item\_priority(hub, item, priority, prod, load)  
    \+set\_critical\_ping(hub, item, threshold, role)  
    \+add\_facility(name, coords, manager)  
    \+get\_location\_info(location\_name)  
    \+get\_source\_for(location\_name)  
  }  
    
  class RecipeManager {  
    \+get\_recipe(output\_item, production\_location)  
    \+calculate\_materials(item, quantity, location)  
    \+is\_factory\_only(item)  
    \+is\_facility\_only(item)  
  }  
    
  class ConfigManager {  
    \+get\_setting(setting\_name)  
    \+set\_setting(setting\_name, value)  
  }  
    
  class Scheduler {  
    \+schedule\_task\_expiration(task\_id, expiration\_time)  
    \+schedule\_production\_completion(task\_id, completion\_time)  
    \+check\_scheduled\_events()  
  }  
    
  *%% Data Models*  
  class Location {  
    \+id: str  
    \+name: str  
    \+type: LocationType  
    \+coordinates: str  
    \+managed\_by\_role: str  
    \+source\_location\_ids: List\[str\]  
    \+created\_at: datetime  
    \+updated\_at: datetime  
  }  
    
  class Item {  
    \+id: str  
    \+name: str  
    \+category: ItemCategory  
    \+is\_crate\_packable: bool  
    \+crate\_size: float  
    \+created\_at: datetime  
    \+updated\_at: datetime  
  }  
    
  class Recipe {  
    \+id: str  
    \+output\_item\_id: str  
    \+output\_quantity: int  
    \+production\_location\_type: ProductionLocationType  
    \+production\_time: int  
    \+mpf\_discount\_eligible: bool  
    \+created\_at: datetime  
    \+updated\_at: datetime  
  }  
    
  class RecipeIngredient {  
    \+recipe\_id: str  
    \+ingredient\_item\_id: str  
    \+quantity: int  
    \+created\_at: datetime  
    \+updated\_at: datetime  
  }  
    
  class Inventory {  
    \+location\_id: str  
    \+item\_id: str  
    \+quantity: int  
    \+last\_updated: datetime  
    \+reported\_by\_user\_id: str  
    \+created\_at: datetime  
    \+updated\_at: datetime  
  }  
    
  class Task {  
    \+id: str  
    \+task\_type: TaskType  
    \+item\_id: str  
    \+quantity: int  
    \+status: TaskStatus  
    \+priority\_score: int  
    \+source\_location\_id: str  
    \+target\_location\_id: str  
    \+claimed\_by\_user\_id: str  
    \+linked\_task\_id: str  
    \+production\_location\_type: ProductionLocationType  
    \+estimated\_completion\_time: datetime  
    \+claim\_timeout: datetime  
    \+pending\_timeout: datetime  
    \+urgency: UrgencyLevel  
    \+created\_at: datetime  
    \+updated\_at: datetime  
    \+completed\_at: datetime  
  }  
    
  class LocationBuffer {  
    \+location\_id: str  
    \+item\_id: str  
    \+target\_quantity: int  
    \+critical\_threshold\_percent: int  
    \+alert\_role\_id: str  
    \+default\_production\_location: ProductionLocationType  
    \+default\_transport\_load\_type: TransportLoadType  
    \+priority\_score: int  
    \+created\_at: datetime  
    \+updated\_at: datetime  
  }  
    
  class User {  
    \+id: str  
    \+roles: List\[str\]  
    \+is\_admin: bool  
    \+notification\_preferences: dict  
    \+current\_pending\_tasks: int  
    \+created\_at: datetime  
    \+updated\_at: datetime  
    \+last\_active: datetime  
  }  
    
  class Config {  
    \+key: str  
    \+value: str  
    \+description: str  
    \+created\_at: datetime  
    \+updated\_at: datetime  
  }  
    
  class TaskHistory {  
    \+id: str  
    \+task\_id: str  
    \+previous\_status: TaskStatus  
    \+new\_status: TaskStatus  
    \+changed\_by\_user\_id: str  
    \+timestamp: datetime  
    \+notes: str  
  }  
    
  *%% Enums*  
  class LocationType {  
    \<\<enumeration\>\>  
    FORWARD\_BASE  
    FRONTLINE\_HUB  
    BACKLINE\_HUB  
    REFINERY  
    FACTORY  
    MPF  
    FACILITY  
    RESOURCE\_FIELD  
  }  
    
  class TaskType {  
    \<\<enumeration\>\>  
    RAW  
    REFINE\_IN\_PROGRESS  
    REFINE\_WAITING\_PICKUP  
    MANUFACTURE\_PENDING  
    MANUFACTURE\_IN\_PROGRESS  
    MANUFACTURE\_COMPLETE  
    FACILITY\_PENDING  
    FACILITY\_COMPLETE  
    TRANSPORT\_MIDLINE\_PENDING  
    TRANSPORT\_FRONTLINE\_STAGED  
    FRONTLINE\_DELIVERY  
  }  
    
  class TaskStatus {  
    \<\<enumeration\>\>  
    UNCLAIMED  
    PENDING  
    IN\_PROGRESS  
    COMPLETE  
  }  
    
  class ProductionLocationType {  
    \<\<enumeration\>\>  
    FACTORY  
    MPF  
    FACILITY  
    REFINERY  
  }  
    
  class UrgencyLevel {  
    \<\<enumeration\>\>  
    LOW  
    MEDIUM  
    HIGH  
  }  
    
  class TransportLoadType {  
    \<\<enumeration\>\>  
    FTL  
    FCL  
    LIQUID  
    SHIPPABLE  
  }  
    
  *%% Database Manager*  
  class DatabaseManager {  
    \-connection  
    \+connect()  
    \+disconnect()  
    \+execute\_query(query, params)  
    \+fetch\_all(query, params)  
    \+fetch\_one(query, params)  
    \+commit()  
    \+rollback()  
  }  
    
  *%% Relationships*  
  DiscordBot \--\> CommandHandler  
  CommandHandler \--\> TaskManager  
  CommandHandler \--\> StockManager  
  CommandHandler \--\> LocationManager  
  CommandHandler \--\> RecipeManager  
  CommandHandler \--\> ConfigManager  
    
  TaskManager \--\> StockManager  
  TaskManager \--\> LocationManager  
  TaskManager \--\> RecipeManager  
  TaskManager \--\> Scheduler  
  TaskManager \--\> DatabaseManager  
    
  StockManager \--\> DatabaseManager  
  LocationManager \--\> DatabaseManager  
  RecipeManager \--\> DatabaseManager  
  ConfigManager \--\> DatabaseManager  
    
  Location \--\> LocationType  
  Task \--\> TaskType  
  Task \--\> TaskStatus  
  Task \--\> ProductionLocationType  
  Task \--\> UrgencyLevel  
  LocationBuffer \--\> ProductionLocationType  
  LocationBuffer \--\> TransportLoadType  
    
  Recipe \--\> "1" Item : produces  
  RecipeIngredient \--\> "1" Recipe : belongs to  
  RecipeIngredient \--\> "1" Item : requires  
  Inventory \--\> "1" Location : stored at  
  Inventory \--\> "1" Item : tracks  
  Task \--\> "1" Item : involves  
  Task \--\> "2" Location : has source and target  
  Task \--\> "0..1" Task : linked to  
  LocationBuffer \--\> "1" Location : configured for  
  LocationBuffer \--\> "1" Item : manages stock of  
  TaskHistory \--\> "1" Task : references

## 