# Slash Commands Workflow

The bot will use two different methods of interacting with the user.

The first is slash commands, this is the new and preferred method, supporting autocomplete if necessary and which does not require message content access in order to implement.

Slash Commands get implemented as a REST API to a bot defined API endpoint.

## Types of Commands

* task_status
    Displays the status of a task. Allows users to inspect and see why a task is stalled.
* inventory_update
    Updates the inventory at a node from a screenshot.
* alert
    Manually trigger a stock alert
* setup_network
    Administrator Only: Setup a new logistics network.
* settings
    Administrator Only: allows changing of settings for the bot.