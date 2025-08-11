
The bot should be a 4-layer architecture.

The layers should be organized as follows:

* Model - Data Layer
  * Database ORM
    * Peewee
  * War API
    * FoxAPI (see `data/warapi/war_api_client.py`)
  * Discord Presence
    * dissnake
* Service Layer
  * Graph Processing
  * State Management
  * Queries
  * OCR (outsourced to Foxhole Inventory Report / FIR)
* Data Pipeline
  * Screenshot Parsing
    * Generates FIR data
  * Updates front node
  * Enqueues update of entire chain
  * event driven
* Presentation
  * Specific messages
  * Reactions
  * Cards


This should work as follows:

The Model is responsible for both maintaining continuous connection to discord and to the database. Models, database, Discord client, external APIs. Stores inventory, tasks, unit states, etc.

The Service layer is responsible for maintaining the actual graph. This involves the different nodes,
what should appear in each node. Contains domain-specific services.

The data pipeline is responsible for handling events and calling the necessary tools from the service layer. Such as parsing and processing images, getting totals, updating the node, triggering the update of the system, and then generating dashboards and task boards. Does batch analysis, image parsing, graph updates, or derived computations.  Coordinates complex flows: Screenshot → parsed text → inventory delta → production target → task list

The Presentation layer strictly contains message and interaction-based logic. This is responsible for handling any output, initial input, Posts dashboards, responds to commands, manages embeds/buttons, etc.
