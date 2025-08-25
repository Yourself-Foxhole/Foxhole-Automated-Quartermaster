
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
  * Jinja2 Template System
    * Template-based message rendering
    * Customizable Discord embeds
    * Separation of presentation and business logic
  * Specific messages
  * Reactions
  * Cards


This should work as follows:

The Model is responsible for both maintaining continuous connection to discord and to the database. Models, database, Discord client, external APIs. Stores inventory, tasks, unit states, etc.

The Service layer is responsible for maintaining the actual graph. This involves the different nodes,
what should appear in each node. Contains domain-specific services.

The data pipeline is responsible for handling events and calling the necessary tools from the service layer. Such as parsing and processing images, getting totals, updating the node, triggering the update of the system, and then generating dashboards and task boards. Does batch analysis, image parsing, graph updates, or derived computations.  Coordinates complex flows: Screenshot → parsed text → inventory delta → production target → task list

The Presentation layer strictly contains message and interaction-based logic. This is responsible for handling any output, initial input, Posts dashboards, responds to commands, manages embeds/buttons, etc.

## Presentation Layer - Jinja2 Template System

The presentation layer now includes a Jinja2-based templating system for Discord embeds that separates presentation logic from business logic. This system provides:

### Core Components

#### EmbedRenderer (`src/presentation/renderer.py`)
- **Purpose**: Bridge between data objects and Discord embeds
- **Features**: 
  - Template loading and rendering
  - JSON-to-embed conversion
  - Custom Jinja2 filters for Foxhole-specific formatting
  - Error handling for missing templates and invalid JSON
- **Usage**: `renderer.render_task_update(task)`, `renderer.render_inventory_delta(...)`, `renderer.render_alert(...)`

#### Template Directory (`src/presentation/templates/`)
Contains Jinja2 templates that generate JSON for Discord embeds:
- **`task_update.jinja2`**: Formats task status updates with priority, dependencies, and order associations
- **`inventory_delta.jinja2`**: Displays stockpile changes with facility information and impact analysis  
- **`alert.jinja2`**: Renders logistics alerts with severity levels, recommendations, and frontline impact

### Template Features

#### Dynamic Fields
Templates support conditional rendering based on data availability:
```jinja2
{% if task.upstream_dependencies or task.downstream_dependents %}
{
  "name": "🔗 Dependencies",
  "value": "{% if task.upstream_dependencies %}**Upstream:** {{ task.upstream_dependencies|list|join(', ') }}{% endif %}"
}
{% endif %}
```

#### Foxhole-Specific Formatting
- **Item Emojis**: Automatic emoji assignment for Foxhole items (🔫 for 7.62mm, 🧱 for BMats, etc.)
- **Status Colors**: Color coding based on task status, alert severity, and delta types
- **Real Foxhole Data**: Templates use actual item names, facility types, and game terminology

#### Custom Filters
- **`datetime_format`**: Formats datetime objects with custom format strings
- **`item_emoji`**: Adds appropriate emojis to Foxhole item names

### Integration Points

#### Bot Commands (`src/bot.py`)
The bot demonstrates integration with slash commands:
```python
@commands.slash_command(name="task_status")
async def task_status(self, inter, task_id: str):
    task = get_task(task_id)
    embed = self.embed_renderer.render_task_update(task)
    await inter.followup.send(embed=embed)
```

#### Error Handling
- Template not found errors are caught and logged
- Invalid JSON templates raise descriptive errors
- Graceful fallbacks for missing data fields

### Workflow Example

1. **Business Logic**: Task status changes in the service layer
2. **Data Pipeline**: Triggers presentation update
3. **Template Rendering**: `EmbedRenderer.render_task_update(task)` loads `task_update.jinja2`
4. **JSON Generation**: Template renders with task data to produce Discord embed JSON
5. **Discord Output**: JSON converted to `disnake.Embed` and sent to Discord

### Benefits

- **Maintainability**: Non-developers can update message formatting by editing templates
- **Consistency**: All Discord messages follow standardized template structures
- **Extensibility**: Easy to add new message types by creating new templates
- **Testability**: Template rendering can be unit tested independently of Discord API
- **Customization**: Different message styles can be achieved without code changes
