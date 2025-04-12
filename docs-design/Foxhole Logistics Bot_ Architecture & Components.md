## **Foxhole Logistics Bot: Software Architecture & Component Breakdown**

This document outlines a potential software architecture for the Foxhole Logistics Discord Bot, based on the provided design document. It focuses on a pull-based task management system integrated with Discord.

### **1\. High-Level Architecture**

The system can be conceptualized as follows:

1. **Discord Interface:** The primary user interaction point. It receives commands (\!command), displays task lists, sends notifications (pings, status updates), and provides feedback.  
2. **Command Parser:** Interprets user commands from Discord, validates syntax and permissions, and extracts relevant parameters.  
3. **Task Management Core:** The heart of the system. It manages the lifecycle of tasks (creation, assignment, status changes, timeouts), implements the pull-based logic across different levels (Forward Base \-\> Staging Hub \-\> Production \-\> Refinery \-\> Raw Materials), prioritizes tasks, and handles production location decisions (Factory vs. MPF vs. Facility).  
4. **Data Persistence Layer:** Stores the state of the system, including hub configurations, item priorities, current stock levels (as reported), active tasks, recipes, and global settings. This could be a database (SQL or NoSQL) or even structured files for simpler implementations.  
5. **Notification Engine:** Handles sending messages and pings to Discord users or roles based on events (task completion, critical stock levels, timeouts, MPF readiness).  
6. **Scheduler/Timer:** Manages time-based events, such as task expiration (claim timeouts, pending timeouts) and triggering actions when MPF/Refinery production is estimated to be complete.

graph TD  
    A\[Discord User\] \-- Command \--\> B(Discord Interface);  
    B \-- Raw Command \--\> C{Command Parser};  
    C \-- Parsed Action/Data \--\> D{Task Management Core};  
    D \-- Create/Update/Query \--\> E\[Data Persistence Layer\];  
    E \-- Data \--\> D;  
    D \-- Trigger Notification \--\> F{Notification Engine};  
    F \-- Send Message/Ping \--\> B;  
    D \-- Schedule/Check Time \--\> G{Scheduler/Timer};  
    G \-- Trigger Event \--\> D;

    subgraph Bot Backend  
        C; D; E; F; G;  
    end

*(Note: This Mermaid diagram provides a visual representation of the flow. Rendering may depend on the environment.)*

### **2\. Key Classes and Components**

Here's a potential breakdown into classes, their responsibilities, and key functions/methods:

**DiscordBot** / **CommandHandler**

* **Responsibility:** Interface with the Discord API, listen for messages, parse commands, delegate actions to other components, format and send responses/notifications.  
* **Key Functions:**  
  * on\_message(message): Entry point for incoming messages. Identifies potential commands.  
  * parse\_command(command\_string): Uses regex or string splitting to identify the command name and arguments. Handles validation.  
  * handle\_config\_command(user, args): Processes \!config subcommands. Requires admin checks. Delegates to ConfigManager.  
  * handle\_hub\_command(user, args): Processes \!hub config subcommands. Requires admin checks. Delegates to HubManager or ConfigManager.  
  * handle\_stock\_command(user, args): Processes \!stock report. Delegates to StockManager.  
  * handle\_request\_command(user, args): Processes \!request. Initiates the pull logic via TaskManager.  
  * handle\_tasks\_command(user, args): Processes \!tasks subcommands (list, find, claim, update, complete, abandon). Delegates to TaskManager.  
  * handle\_production\_command(user, args): Processes \!production calc. Delegates to RecipeManager or TaskManager.  
  * handle\_status\_command(user, args): Processes \!status. Delegates to HubManager or StockManager.  
  * handle\_dashboard\_command(user, args): Processes \!dashboard. Aggregates data from TaskManager and StockManager.  
  * send\_message(channel\_id, message\_content): Sends a standard message.  
  * send\_notification(user\_or\_role\_id, message\_content): Sends a targeted ping/notification.

**TaskManager**

* **Responsibility:** Core logic for task creation, lifecycle management, prioritization, and the pull-based supply chain simulation. Interacts heavily with StockManager, HubManager, and RecipeManager.  
* **Key Functions:**  
  * create\_task(task\_type, item, quantity, target\_hub, source\_location=None, priority\_score=None, production\_location=None, urgency=None, linked\_task\_id=None): Creates a new task object and saves it.  
  * process\_request(requester\_user, target\_location, requested\_items, urgency, preferred\_location): Initiates the Level 1 pull logic.  
  * trigger\_pull\_level\_1(target\_base, item, quantity\_needed): Checks base stock, potentially generates FRONTLINE\_DELIVERY task or triggers Level 2\.  
  * trigger\_pull\_level\_2(staging\_hub, item, quantity\_needed): Checks hub stock, potentially generates TRANSPORT\_MIDLINE\_PENDING task or triggers Level 3\.  
  * trigger\_pull\_level\_3(source\_hub, item, quantity\_needed): Checks source stockpile, potentially triggers Level 4 if manufacturing is needed.  
  * trigger\_pull\_level\_4(item, quantity\_needed, urgency, preferred\_location): Decides between Factory/MPF/Facility, generates MANUFACTURE\_PENDING or FACILITY\_PENDING tasks. Checks for required inputs and triggers Level 5 if needed.  
  * trigger\_pull\_level\_5(item, quantity\_needed): Checks refinery stock/queues, potentially generates REFINE\_IN\_PROGRESS or triggers Level 6\.  
  * trigger\_pull\_level\_6(resource, quantity\_needed): Generates RAW resource gathering task.  
  * calculate\_priority(item, deficit, urgency): Determines task priority score.  
  * find\_tasks(filters): Retrieves tasks based on criteria (type, location, status, etc.).  
  * claim\_task(user\_id, task\_id): Assigns a task to a user, sets timeout.  
  * update\_task\_status(task\_id, new\_status): Changes the status of a task (e.g., UNCLAIMED \-\> PENDING, PENDING \-\> IN\_PROGRESS).  
  * update\_mpf\_completion\_time(task\_id, user\_id, completion\_timestamp): Updates the EstimatedCompletionTime for an MPF task. Requires check that user claimed the task.  
  * complete\_task(user\_id, task\_id): Marks a task as COMPLETE. Triggers follow-up actions (e.g., generating pickup tasks).  
  * abandon\_task(user\_id, task\_id): Releases a claimed task back to UNCLAIMED.  
  * expire\_tasks(): Background process to check for timed-out claims/pending reservations and revert them to UNCLAIMED.  
  * check\_production\_completion(): Background process to check EstimatedCompletionTime for MPF/Refinery tasks and trigger status updates/notifications.  
  * get\_dashboard\_summary(): Provides data for the \!dashboard command.

**StockManager**

* **Responsibility:** Manages reported stock levels for hubs and bases.  
* **Key Functions:**  
  * report\_stock(location\_name, reported\_by\_user\_id, stock\_data): Updates the stored stock levels for a location based on user report. Records timestamp and reporter.  
  * get\_stock\_level(location\_name, item): Retrieves the last reported quantity of an item at a location.  
  * get\_stock\_status(location\_name): Retrieves the overall stock status for a location, comparing current levels to buffers.  
  * check\_critical\_stock(location\_name, item): Compares current stock against the critical threshold percentage.

**HubManager** / **LocationManager**

* **Responsibility:** Manages information about hubs, bases, and facilities (locations, types, configurations).  
* **Key Functions:**  
  * get\_hub\_config(hub\_name): Retrieves buffer levels, item priorities, critical ping settings for a hub.  
  * set\_hub\_buffer(hub\_name, item, target\_qty): Updates the target buffer for an item.  
  * set\_item\_priority(hub\_name, item, priority\_score, default\_prod, transport\_load): Updates item-specific settings for a hub.  
  * set\_critical\_ping(hub\_name, item, threshold\_percent, role\_or\_user): Updates critical stock alert settings.  
  * add\_facility(name, coordinates, managed\_by): Registers a new facility.  
  * get\_location\_info(location\_name): Returns details about a hub, base, or facility.  
  * get\_source\_for(location\_name): Returns the designated upstream source location(s).

**RecipeManager**

* **Responsibility:** Stores and provides information about item recipes (inputs, outputs, production locations).  
* **Key Functions:**  
  * get\_recipe(output\_item, production\_location=None): Returns the recipe(s) for an item, potentially filtered by Factory/MPF/Facility.  
  * calculate\_materials(item, quantity, production\_location): Calculates the raw/refined materials needed, considering potential MPF discounts.  
  * is\_factory\_only(item): Checks if an item must be made in a Factory.  
  * is\_facility\_only(item): Checks if an item must be made in a Facility.

**ConfigManager**

* **Responsibility:** Manages global bot settings.  
* **Key Functions:**  
  * get\_setting(setting\_name): Retrieves a global setting value (e.g., TaskTimeoutHours).  
  * set\_setting(setting\_name, value): Updates a global setting (Admin only).

**Task** (Data Class/Object)

* **Responsibility:** Represents a single task unit.  
* **Attributes:** TaskID, TargetHub, TaskType (enum: RAW, REFINE\_IN\_PROGRESS, REFINE\_WAITING\_PICKUP, MANUFACTURE\_PENDING, MANUFACTURE\_IN\_PROGRESS, MANUFACTURE\_COMPLETE, FACILITY\_PENDING, FACILITY\_COMPLETE, TRANSPORT\_MIDLINE\_PENDING, TRANSPORT\_FRONTLINE\_STAGED, FRONTLINE\_DELIVERY), Item, Quantity, PriorityScore, Status (enum: UNCLAIMED, PENDING, IN\_PROGRESS, COMPLETE), ClaimedByUserID, SourceLocation, CreatedAt, CompletedAt, ClaimTimeoutTimestamp, PendingTimeoutTimestamp, LinkedQueueTaskID, ProductionLocationType (enum: Factory, MPF, Facility), EstimatedCompletionTime.

### **3\. Data Structures (Conceptual Model from Document)**

* **Hubs:** Information about each logistics hub.  
* **HubStockStatus:** Tracks current vs. target stock for items at hubs.  
* **ItemPriorities:** Defines priority, default production, and transport load for items.  
* **Tasks:** The central table/collection holding all task details (as described in the Task class).  
* **Recipes:** Defines input/output for manufacturing.  
* **GlobalConfig:** Key-value store for global settings.

### **4\. Key Parameters (Examples)**

* **Commands:** hub\_name, base\_name, item\_name, quantity, task\_id, user\_id, role\_id, duration, timestamp, urgency\_level, preference (Factory/MPF).  
* **Internal Functions:** Parameters will mirror the attributes of the data structures (Task, Hub, Item, etc.) and command inputs needed to perform the logic (e.g., deficit\_quantity, is\_critical, calculated\_priority).

This breakdown provides a structural foundation for building the Discord bot described in the design document. The actual implementation would involve choosing specific technologies (programming language, database, Discord library) and refining these components further.

Based on the design document, here's a high-level technical architecture for the Foxhole Logistics system:

**Core Components:**

1. **Discord Bot:** The central interface for users. It handles:  
   * **Command Processing:** Receives and interprets user commands like `!stock report`, `!request`, `!tasks`, `!config`, etc..    
   *   
   * **Task Management Interface:** Displays tasks, allows users to claim, update (especially MPF completion times), complete, or abandon tasks.    
   *   
   * **Notifications:** Pings users/roles for critical stock levels or MPF task completions.    
   *   
   * **Information Display:** Shows hub status, production calculations, and high-level dashboards.    
   *   
2.    
3.   
4. **Task Management System:** The engine driving the logistics workflow. It:  
   * **Generates Tasks:** Creates tasks based on demand signals (stock levels vs. buffers, explicit requests) across different logistics levels (Frontline, Staging Hubs, Production).    
   *   
   * **Manages Task Lifecycle:** Tracks task status (UNCLAIMED, PENDING, IN\_PROGRESS, COMPLETE) and ownership, handling timeouts and expirations.    
   *   
   * **Prioritizes Tasks:** Assigns priority based on item type, deficit severity, urgency, and potentially queue position.    
   *   
   * **Handles Dependencies:** Links production tasks to pickup tasks and tracks the flow from raw materials to final delivery.    
   *   
5.    
6.   
7. **Pull-Based Logic Engine:** Implements the core demand-driven workflow. It operates in levels:  
   * **Level 1 (Forward Base Demand):** Triggers last-mile delivery tasks (`FRONTLINE_DELIVERY`) based on forward base needs vs. staging hub stock.    
   *   
   * **Level 2 (Staging Hub Demand):** Triggers midline transport tasks based on staging hub needs vs. source stockpile stock.    
   *   
   * **Level 3 (Source Stockpile Check):** Checks backline stock and triggers production if needed.    
   *   
   * **Level 4 (Production):** Manages Factory/MPF/Facility task generation based on item type, urgency, cost, and stock levels. Handles production queueing, pickup, and user updates for MPF timings.    
   *   
   * **Level 5 (Refinery):** Manages refinery tasks (in-progress, waiting pickup) based on needed manufacturing inputs.    
   *   
   * **Level 6 (Raw Materials):** Generates tasks for raw material gathering when upstream resources are insufficient.    
   *   
8.    
9.   
10. **Data Store:** Persists the system's state. Key data models include:  
    * **Hubs:** Information about logistics hubs.    
    *   
    * **HubStockStatus:** Current and target inventory levels per item at each hub.    
    *   
    * **ItemPriorities:** Configuration for item importance, default production, and transport types.    
    *   
    * **Tasks:** Detailed information about each task, including type, status, item, quantity, priority, owner, locations, timestamps, production specifics (Factory/MPF, completion time), etc..    
    *   
    * **Recipes:** Item production requirements for Factory/MPF.    
    *   
    * **GlobalConfig:** System-wide settings like timeouts and notification roles.    
    * 

**Information Flow:**

* Demand originates from the front lines (Forward Bases or Staging Hubs) via stock reports or explicit requests.    
*   
* The Pull-Based Logic Engine propagates this demand backward through the supply chain levels (Transport \-\> Production \-\> Refining \-\> Gathering), generating tasks at each stage where deficits exist.    
*   
* The Discord Bot mediates all user interaction, presenting tasks, accepting commands, and providing feedback/notifications.    
*   
* Inventory levels are updated based on user-submitted `!stock report` commands, representing the state *after* a delivery or *before* a pickup. The bot doesn't track items "in transit" as a separate inventory pool.    
*   
* MPF task completion relies heavily on users updating the estimated completion time via the `!tasks update` command. The system then uses this time to trigger notifications and generate pickup tasks.    
* 

This architecture aims to automate and optimize the logistics workflow by translating player-reported needs into a prioritized, managed task list accessible via Discord, considering the specific mechanics and efficiencies of different production methods (Factory vs. MPF) within Foxhole.

Based on the architecture and components described in the "Foxhole Logistics: Pull-Based Design Doc", here is a suggested list of files and directories for the project, assuming a common structure (e.g., for a Python project):

Core Bot & Application:

bot.py / main.py: The main entry point for the Discord bot application. Handles bot initialization, connection to Discord, and loading of modules/cogs.

config.py / .env: Stores configuration variables like the Discord bot token, database connection details, default settings, and potentially API keys if external services were used.   

requirements.txt: Lists Python package dependencies (e.g., discord.py, database drivers).

Modules/Components (often in subdirectories):

cogs/ or commands/ (Directory): For organizing Discord command groups (Discord.py Cogs).

task\_commands.py: Handles commands like \!tasks list, \!tasks claim, \!tasks complete, \!tasks update, \!tasks abandon, \!tasks find.   

stock\_commands.py: Handles \!stock report, \!request.   

config\_commands.py: Handles \!config and \!hub config commands.   

info\_commands.py: Handles \!status, \!dashboard, \!production calc.   

refinery\_commands.py: (If specific commands exist for refinery interaction ).   

resource\_commands.py: (If specific commands exist for raw material gathering ).   

logic/ or core/ (Directory): Contains the core business logic.

pull\_model.py: Implements the multi-level pull logic (Levels 1-6).   

task\_manager.py: Handles task creation, state transitions, prioritization, timeouts, and ownership.   

production\_logic.py: Contains logic for deciding between Factory/MPF/Facility, batching rules, and handling production timings.   

priority\_queue.py: Implements the task prioritization logic.   

database/ or models/ (Directory): Handles data storage and retrieval.

db\_connection.py: Manages the connection to the database.

models.py: Defines the data structures/schemas (e.g., for Hubs, HubStockStatus, ItemPriorities, Tasks, Recipes, GlobalConfig).   

crud.py / db\_operations.py: Functions for creating, reading, updating, and deleting data in the database.

utils/ (Directory): Utility functions used across the project.

helpers.py: General helper functions (e.g., parsing commands, formatting output).

time\_utils.py: Functions for handling timestamps, calculating expirations, checking completion times.   

Other Potential Files/Directories:

README.md: Project description, setup instructions, usage guide.

tests/ (Directory): Unit and integration tests for various components.

docs/ (Directory): More detailed documentation (potentially including the original design doc).

This structure separates concerns, making the codebase easier to manage, maintain, and test as described in the design document. 


Sources and related content

