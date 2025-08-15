When adding a new production calculation we are looking at a specific event
or item delta.

The way this should work is:

* Inventory Update
  * New screenshot or manual update of inventory, this triggers a comparison
    to the desired state and a delta calculation
* Delta for Node
  * The delta represents what the node needs in order to achieve the desired
    configuration state
* Production Decision for Delta
  * We have two options for a delta item:
    * Transport the Item (incurs transport cost)
    * Produce the Item (incurs production + manu cost)
  * If we are going to transport the item we need to "order" the item, by
    putting it into the queue to be transported and creating a task
  * If we are going to make the item, likewise we need to reserve or order
    the materials/inputs needed to make it. These inputs then propogate for 
    every level of the supply chain back to the resource nodes.
* Resource Nodes
  * Resource is a special graph type, it has no source and represents the end
    of the graph. All resources needed to make things get summed and displayed
    similar to a facility card.
  * A resource card tells you how much is in what state, and what it will be
    used for, but it does not actually track individual bulk resources.
* Common "Currency" for all tasks
  * One of the goals of the bot is to answer the question "should I bother 
    getting this from the backline or is it faster to just make it here?"
  * If something is the same or close to the same cost it's obviously much
    better to just make more
  * For more expensive items (nukes for instance) it will always be worth it
    to transport them
  * The bot needs to consider the time needed for scrooping and the scroop rate
    per hour vs. the time needed to transport and the equivalent amount of salvage
    moved per hour.
  * There are additional complexities in this problem because not all fields are
    available. Depending on the hex there may be a surplus of resources with low
    competition, or highly contested resources with low individual output per hour


Delta For Node > Production Decision for Delta > Orders > Tasks

The way the algorithm could work is a recurisve inspection of the tasks. For instance
if I want 1 Callahan battleship the first thing I need to know is what production process
does this require.

It turns out this requires a dry dock. If I do not have the item and the node is not a
production node, then I have no choice. I *must* order it.

This then gets redistributed down the chain for each subproblem. 1 callahan battleship'
requires 20 naval hull segments, 20 naval shell plating, and 4 turbine components.

These in turn require their own decisions to be made, deliver or produce.

Each node only has the connections specifically specified by the logistics manager, so
this is a relatively simple calculation. 

We continue until we get a list of orders, find a building that can do the production,
or find a resource node that can give us the raw materials.
