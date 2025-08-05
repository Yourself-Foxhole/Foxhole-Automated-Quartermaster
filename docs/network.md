The network is a directed graph. At the current point in time everything in the network flows unidirectionally from the front to the back.

The network operates similar to a tree data structure, wherein items "flow" from a source to a destination.

Demand and orders can be calculated using any method, but starting from "Demand/Consumption" nodes at the front should be considered.


## Algorithm

The proposed algorithm is as follows.

* The network is entirely event driven. We get updates from image data and can only process a single update at time.
* When a new image is added, traverse the graph following the directions until you arrive at the resource node
* Foreach intermediate node update the demand for the network starting from the frontline node that was updated
  * The calculation should add all the sum of all downstream nodes, plus factor in any demand for the node itself, before recording the demand as an order from it's own upstream node.
  * If the node is the resouce node, it should update the totals required for all raw materials.

## Nodes

Nodes are anything on the graph which has an inventory. They can be one of 5 types:

1. Resource Nodes
2. Refinery
3. Production Building
   1. Factory
   2. Mass Production Factory (MPF)
   3. Manual Build
      3. Garage
      4. Construction Yard
      5. Shipyard
4. Logistics Hub  (Storage Depot/Seaport/Bluefin Large Ship)
5. Facility

Items flow from raw materials


## Edges

Each node should have at least one directed connection from it's upstream node.

An edge or node should contain information about what is to move along it.

For example, let's say you have a Supply Depot in the frontline that is pulling from 3 sources:

* Vehicles, crates of items using refined materials (rmats), and more expensive infantry items (grenades, rifles, etc.) can be made at the mass production factory, and perhaps associated factories in a hex.
* Items from a frontline factory get pulled as it's own source, but the factory has no refinery with which to convert raw materials into intermediate components.
* Some items (upgraded tanks, ammunition, crate ammo focused items) might come from a facility with appropiate production capabilities that can be built anywhere, but usually they will want to be built close to a resource or close to the point of use.

Thus routing the order to the correct edge may involve multiple paths. There may even be multiple orders. In this example let's say that while someone is at the Mass Production Factory they also happen to stop by the factory to produce shirts. It is more transport efficient to produce shirts and ammunition on the frontline, but it is more man-hour efficient to consolidate them into a single location which might even have a double factory.

In such an example it might be desirable to split the route, pulling the extra shirts from the backline while still queueing up frontline production orders. Certain categories of items may be desired or restricted. For instance you may want frontline production of ammunition and medical supplies, but not gernades, shells, and vehicles which are more costly to produce.

At other times a regiment may max out the capacity of what can reasonably be produced at a single mass production factory, and it may become desirable to open a second MPF town up as a stockpile for manufacturing.

Because of all these scenarios, edges preferences and data need to be stored somewhere. While you could simply store this in objects for the nodes themselves the edge seems a good place to stick an object containing a filter.

## Reverse Logistics

At the current type we are simplifing the network by ignoring reverse logistics. For example redistribution of items to another frontline base. For the most part this because things in Foxhole tend to only flow one direction and once uncrated most items can't be uncrated again.

For example, if you were to redistribute Solider's Supplies (Shirts) the slow pull time means you can only store a stack size of 1 with each shirt taking an inventory slot. So whereas a Dunne hauler could carry 15 crates of 10 shirts (150 shirts) it would take 10 round trips of 15 shirts to carry the same quantity once uncrated.

This makes redistribution unappealing for all but the most expensive items and not something which needs to be tracked en mass.

However, the architecture should not be so limited as to prevent all forms of future expansion into reverse logistics. For now, such things would be best implemented as a manual task rather than automatically managed.
