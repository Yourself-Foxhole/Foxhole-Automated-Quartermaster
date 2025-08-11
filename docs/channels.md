This document details the layout of various channels for users to interact with the logistics network.

## Types of Channels

* Dashboard
    * The purpose of a dashboard channel is to give an overview of things that are occurring. A dashboard should be done
      to do the following:
        * System Overview
            * The System Overview is responsible for displaying in a single page or screen what the status of everything
              is.
              It should report an overall inventory status for each major hub in the network. It should also show a
              summary and rollup of major KPIs for the given system to give an idea of health. With a focus on
              Resources, Production, Facilities, Frontline Depots, and Bunker Bases.
        * Stockpile
            * This dashboard should display all stockpiles, their expiration timers, allow the refresh of timers, and
              have a list of applicable stockpile codes
        * Resource
            * This dashboard should have detailed information on scroop totals with the seven amounts of all raw
              material needed, how much is currently stored or pending transport, how much is in transport, and who is
              currently on the tasks.
        * Production
            * This dashboard should show the different regions we have production in and their overall status and
              health, especially of critical or high demand areas within the network.
        * Production - Location
            * Production - Refine
                * This dashboard should display the total amount of materials that need to be refined, how long it will
                  take, how many refinery queues, how much material is pending, and how much is waiting pickup.
            * Production - Mass Production Factory
                * This dashboard should display the number of items waiting pickup at the MPF, the number that need to
                  be made, the ones currently in progress, and an overview of approsimately when each order will be
                  ready.
            * Production - Factory
                * This dashboard should contain the number of needed
            * Production - Individual items
                * This dashboard should have a list and statistics ov items that need to be made at the garage,
                  construction yard, or shipyard.
        * Transportation
            * This dashboard should show the total number of things waiting to be transported at the different stages of
              the supply chain, broken down by number of containers or truckloads.
        * Frontline
            * This dashboard should show the different regional stockpiles, their overall stocks of critical items, and
              statistics of the fulfillment and consumption rates
        * Frontline - Location
            * This should show thesame as frontline, but on a per hex basis for invidiual places within a hex.
        * Leaderboard
            * This dashboard should display the logistical output of the top players to foster friendly competition.
* Stockpiles
    * Stockpile Codes
    * Resrvations
    * Maintenance Supplies
* Stock Update
    * Stock Update channels specifically are for updating and running inventory reports against a given stockpile. They
      are fairly boring, containing only screenshots and the bots most recent parsed output. Perhaps a usage rate over
      change. Every location in the network should have a thread for screenshot updates.
* Tasks
    * Prioritized
        * The prioritized task board should be the both's priority algorithm for what needs to be done. This is
          described in detail in other documentation steps, but generally this includes the proprity and a bubble up
          mode wherein things are elevated based on the number and severity of downstream blocking tasks that exist.
    * Resource
        * The Resource Taskboard duplicates some of what we have in the resource dashboard, but allows users to track
          container loads, truck loads, or small train loads worth of resources and to
    * Production - Location - MPF
        * The MPF task board should contain a recommended list of needed items by item category with a button at the top
          to automatically grab an MPF queue.
        * Grab MPF queues, if clicked the bot will automatically populate a ticket telling which queues you should make
          and the number of material crates you need to be able to make it, along with the recommended transportation
          method.
        * Individual MPF queue, if the user wishes to only ake a certain category or item, they may click a button to
          react and make that given item.
    * Production - Location - Factory
        * The Factory task board should be similar to the MPF one. It should contain a list of items to be made
          prioritized by category. It should also include a button to automatically pull the highest priority thing from
          all categories.
    * Production - Location - Other Buildings
        * The shipyard, garage, and construction yard should all be combined. ANy things to be produced or done should
          be listed with reacts to make an item and mark it as done.
    * Facility
        * Facility tasks should be a customizable status board. See the facility documentation for more info.
    * Transportation
        * The transportation section should primarily include a list of how many truck or container loads of stuff is
          waiting to be moved and the general need for items before and after the change.
        * A transportation ticket should be prioritized, this section should be entirely focused on midline logi, with
          frontline distribution getting it's own section.
    * Frontline—Location
    * Regiment Requests
        * Regiment requests contain exclusively requests put in by players within the regiment. They can be filfulled
          and marked as done, but serve almost like a custom field.
        * Regiment requests are divided into three categories, high priority requests for esxisting items, user defined
          tasks, and recurring tasks.

* Tickets
    * Tickets channels should be effectively an event log. They should exist per location, per edge, and per user. They
      should mirror data in other views.
    * Location ticket channels
        * For a given frontline bb or delivery edge, there should be a thread allowing communication
        * For a given task it should be able to be unclaimed and returned to the pool or the actions undone
    * THe intended use case is that a screenshot is uploaded, the network quantities uploaded, a task seen on the task
      board, claimed, the event logged in a ticket channel, and then the task is removed from the task board.
    * Tickets should show a post within a thread of who is doing a ticket and details, and the thread itself should
      contain a channel history of everyone doing that ticket.

## Intended hierarchy

The entire bot should ideally run within a single channel group. The bot should ask for permissions to manage channels
and groups.

Individual channels should be used as broad categories for different areas of the app.

Actual data should be stored in threads, especially if it is ephemeral. For instance we can have a single channel for
Dashboard with a high level overview with links to the actual dashboards which themselves are text and image posts
within threads.
