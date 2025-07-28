Goal of system:

We want to move away from predefined levels or hirearchies while still keeping the same style of flow that 


* Types of Nodes
    * Facility (player made, has production, but does not generally have detailed storage)
    * Crate (Storage Depot, Seaport, Bluefin, etc.)
    * Item (bunker base, town hall, relic)

* Destination
    * Type: Item/Crate
    * Quantity Desired <Hashmap <Items, InventoryPreference>>
    * Inventory <Hashmap <Items, int>> 
    * DownstreamOrders <List Orders>
    * UpstreamProvider <Map Destination, RouteSettings>
    * logistics hub: true/false

  * Item (has invidual uncrated goods)
  * Crate
    
    * Methods
        * generate order

Explaination:
    * Type: displays whether there is item or crate level logistics, this is important because all things should be converted into crates for size purposes. Crate quantities should be a float.
    * QuantityDesired - this stores how much of each item we should keep in the depot
    * 

* InventoryPreference
    * QuantityDesired: Int - Default: 0
    * ReserveQuantity: Int - Default: 0
    * HeldQuantity: Int - Default: 0
    * ComputedDemand: Int - Default: 0

Explaination:
    * This class's job is to store for a given item how much we should actually keep in stock.
    * QuantityDesired is the how much the bot should try to take in inventory. A Quantity desired is how much the logi person wants to be in that stockpile for that item.
    * ReserveQuantity is the amount that *should* be there, it adds on top of quantity desired, but is automatically lower priority than all quantity desired.
        * The goal of this amount is to be ready for quick delivery requests by creating a floor b. The behavior of this number is that it should generate an upstream order if the number drops below this amount, but not if it goes above it. 
        * For example, let's say for example we have 3 bunker bases we are tracking each of which store individual items. If we want 15 crates delivered, for a total of 45 items and we have set a reserve value of 70 crates. The current inventory is 20 crates. The calculated demand should be 45 crates on a normal priority basis + 50 crates on a low priority basis. This would allow us to get back to the reserve level and still fill all downstream demand.
        * If for any reason the amount goes over reserve + downstream orders, the order quantity should be 0.
        * The demand on  QuantityDesired creates an order which propogates backwards upstream. Reserve would add on top and send this up the chain, but as a lower priority. 
    * HeldQuantity indicates how much should be reserved for this and not sent downstream. This is for ops or planning where things should be held at a depot but not moved.
    * ComputedDemand represented the total amount to request from upstream


* Order
    * Origin
    * Destination
    * Items <Hashmap <Item, Int>>

Explaination:
    * This class stores 

* RouteSettings
    * RestrictedItems <List Items>
    * RestrictedCategories <List Categories>

Explaination:
    This class tells

Classes and properties:

* Node Properties
  * Item
  * Desired Quantites
  * Origin Node
  * Production


* Production <Object>
    * Categories
        * Small Arms
        * Explosives


* World Structure <Inherits from: Production>

* Factory <Inherits from: World Structure>
    * Queue size:
    * Categories Supported

* Mass Production Factory <Inherits from: World Structure>

* Construction Yard <Inherits from: World Structure>

* Garage <Inherits from: World Structure>

* Shipyard <Inherits from: World Structure>

* Facility <Inherits from: Production>

* Edge
  * Allowed Transportation List


* Item Class
  * Item Id
  * Item Name
  * Item Category
  * Item Cost
  * Item Quantity


* Crate
    * Item Class


 ## Data Model Inheritance & Relationships

The logistics system is modeled using class inheritance to represent the different types of objects and their relationships. This allows for flexible extension and clear mapping to in-game entities.

### Core Class Hierarchy

- **Node (Base Class)**
  - Represents any entity in the logistics network (facility, crate, item, etc.)
  - Common properties:
    - `id`, `name`, `type`
    - `origin_node` (optional)
    - `desired_quantities` (mapping of Item → InventoryPreference)
    - `inventory` (mapping of Item → int)
    - `downstream_orders` (list of Orders)
    - `upstream_providers` (mapping of Destination → RouteSettings)
    - `logistics_hub` (bool)

- **Production (Mixin/Object)**
  - For nodes that can produce items.
  - Properties:
    - `categories_supported` (e.g., Small Arms, Explosives)
    - `queue_size` (for factories)
    - `production_rate`
    - `current_queue` (list of Items)

- **WorldStructure (inherits Node)**
  - Represents map structures (factories, yards, etc.)
  - Subclasses:
    - `Factory` (inherits Production)
    - `MassProductionFactory` (inherits Production)
    - `ContainerYard`
    - `Garage`
    - `Shipyard`
    - `Facility` (inherits Production)

- **Crate (inherits Node)**
  - Storage depots, seaports, etc.
  - Properties:
    - `contained_items` (list of Item)
    - `capacity`
    - `is_logistics_hub` (bool)

- **Item (inherits Node)**
  - Represents individual items or uncrated goods.
  - Properties:
    - `item_id`, `item_name`, `item_category`, `item_cost`, `item_quantity`

### Inventory & Preferences

- **InventoryPreference**
  - For each item in a node’s inventory.
  - Properties:
    - `quantity_desired` (int, default 0)
    - `reserve_quantity` (int, default 0)
    - `held_quantity` (int, default 0)
    - `computed_demand` (int, default 0)
  - Behavior:
    - Drives order generation and prioritization.
    - Reserve is a lower-priority buffer for quick requests.
    - Held is for items not to be sent downstream.

### Orders & Routing

- **Order**
  - Represents a request for items from one node to another.
  - Properties:
    - `origin`, `destination`, `items` (mapping of Item → int)

- **RouteSettings**
  - Defines restrictions or preferences for routes.
  - Properties:
    - `restricted_items` (list of Items)
    - `restricted_categories` (list of Categories)

### Edges & Transportation

- **Edge**
  - Represents a connection between nodes.
  - Properties:
    - `allowed_transportation` (list of transport types, e.g., truck, ship)

### Example Inheritance Structure

```
Node (base)
  ├── WorldStructure (inherits Node)
  │     ├── Factory (Production)
  │     ├── MassProductionFactory (Production)
  │     ├── ContainerYard
  │     ├── Garage
  │     ├── Shipyard
  │     └── Facility (Production)
  ├── Crate (inherits Node)
  └── Item (inherits Node)
```


Data Model Inheritance & Relationships
1. Core Concepts
Node (Base Class)

Represents any entity in the logistics network.
Properties:
id
name
type (Facility, Crate, Item, etc.)
origin_node (optional)
desired_quantities (mapping of Item → InventoryPreference)
inventory (mapping of Item → int)
production (optional, for facilities)
downstream_orders (list of Orders)
upstream_providers (mapping of Destination → RouteSettings)
logistics_hub (bool)
Production (Mixin/Object)

For nodes that can produce items.
Properties:
categories_supported (e.g., Small Arms, Explosives)
queue_size (for factories)
production_rate
current_queue (list of Items)
WorldStructure (Node)

Inherits from Node, represents map structures.
Subclasses:
Factory
MassProductionFactory
ContainerYard
Garage
Shipyard
Facility
Facility (WorldStructure, Production)

Player-made, produces items, limited storage.
Crate (Node)

Storage depots, seaports, etc.
Properties:
contained_items (list of Item)
capacity
is_logistics_hub (bool)
Item (Node)

Represents individual items or uncrated goods.
Properties:
item_id
item_name
item_category
item_cost
item_quantity
2. Inventory & Preferences
InventoryPreference
For each item in a node’s inventory.
Properties:
quantity_desired (int, default 0)
reserve_quantity (int, default 0)
held_quantity (int, default 0)
computed_demand (int, default 0)
Behavior:
Drives order generation and prioritization.
Reserve is a lower-priority buffer for quick requests.
Held is for items not to be sent downstream.
3. Orders & Routing
Order

Represents a request for items from one node to another.
Properties:
origin
destination
items (mapping of Item → int)
RouteSettings

Defines restrictions or preferences for routes.
Properties:
restricted_items (list of Items)
restricted_categories (list of Categories)
4. Edges & Transportation
Edge
Represents a connection between nodes.
Properties:
allowed_transportation (list of transport types, e.g., truck, ship)
Example Inheritance Structure
Node (base)
WorldStructure (inherits Node)
Factory (inherits WorldStructure, Production)
MassProductionFactory (inherits WorldStructure, Production)
ContainerYard (inherits WorldStructure)
Garage (inherits WorldStructure)
Shipyard (inherits WorldStructure)
Facility (inherits WorldStructure, Production)
Crate (inherits Node)
Item (inherits Node)
Notes
All nodes can have inventory and desired quantities, but only some can produce.
Orders propagate upstream based on computed demand and reserve logic.
RouteSettings and Edges allow for flexible logistics pathing and restrictions.


Graph restrictions:

* The graph must go back to Raw Resources
* The graph must include at least one refinery
* The graph must include at least one production building.
* At least one basic factory setup is highly recommended item. This is:
    * Factory Setup (Immediate Construction/Higher Cost)
        * Factory
        * Garage
        * construction yard
        * Shipyard
* The graph may optionally include more efficent production processes these are:
    * Mass Production Factory (Long Term Construction/Lower Cost)
        * MPF grants a 39% discount on crate logistics and a 30% discount on vehicles
        * MPF takes several hours to compelte items
        * MPF requires queues to be set, a waiting time, and final production
    * Facility
        * Facilities can be used to produce items closer to their final destination, or for some advanced items it is the only way to produce them. (e.g. Rockets, Large Ship, Battle Tank, 300mm ammunition)
* An item must be able to be manufactured at a building in the graph or it may not be ordered
* The item must be teched in order for the order to be active. <Disabled until we have tech scanner working>

Intended Workflow:
    * Start from the resource

* Base Node: Resource



* Add a Node
    * Type: Storage Depot
    * Supply Source: 


Intended onboarding of network:

At the start of war we want to do a setup of the bot with essential information.



<Query WarAPI and import data for entire map>

<Welcome Information> 
Welcome to War <Import from War API>

1. First off, which team are you on?
    * Warden
    * Colonial

<Onboard help> This bot is intened to help you optimize your logisitics route. The bot works by scanning images of a stockpile and telling what is intended at the end, the bot will then calculate orders upstream for things to be delievered or made.

To start, we need to know where you intend to produce items and what production methods you intend to use. Keep in mind you can make any changes you'd like to your network later if needed, however we do not recommend rerunning onboarding unless you want to delete everything and start over from scratch.


# Ask about Production Preferences

2. Do you intend to use the Mass Production Factory for up to a 39% discount on crates and 30% discount on vehicles?
    * Yes, include the Mass Production Factory
    * No, do not include the Mass Production Factory 

3. <If Yes to 2> Which Mass Production Factory(s) do you intend to use?
    <Query List from War API>
    Example List for Warden as of War 126 (July 2025):
    * Clanshead Valley > The King
    * Basin Sinnoach > Cuttail Station
    * Reaching Trail > Brodytown
    * Speaking Woods > Tine
    * Callum's Cape > Callum's Keep
 
    - Reaction. Should include number for each option.

4. <If Yes to 2> Mass Production Factory towns often have the full set of logisitcs buildings and a nearby included seaport or storage depot. This includes:

    * A refinery
    * One or More Factories for quick production.
    * A seaport or storage depot
    * A garage
    * A construction yard
    * A shipyard for production of basic small ships (if near water)

    Would you like to add this full set of buildings to your logistics network? Y emoji for Yes , N emoji for No

    - Reaction. Y or N.

    <If Yes:
        Parse previously queried WarAPI for hex information
        Add refinery, factory, storage depot/seaport, construction yard, shipyard (if applicable)
    >

    <If No:
        Skip to next question, ask separately later
    >

5. Which refineries do you intend to use? You must pick at least one refinery.

    <Query from WarAPI and List, remove ones already added from MPF step>
    <Sort 
        Start with hexes that have a mass production factory, list that category first.
        Then count/list the number of factories in same hex, group by number of factories
        Sort island hexes last in list
    >
    <Example From War 126 on Warden Side>

    You have added the following refineries:
        <List all refineries in network>
        * None

    The following refineries have a mass production factory in the same hex:
        <Include, number of factories in same hex in parenthesis>
        * Clanshead Valley > The King (<Emoji MPF> + 2 <Emoji factory> + <Emoji garage> + <Emoji shipyard> + <Emoji construction yard>)
        * Basin Sinnoach > Cuttail Station (<Emoji mpf> + 2 <Emoji factory> + <Emoji garage> + <Emoji shipyard> + <Emoji construction yard>)
        * Reaching Trail > Brodytown (<Emoji mpf> + 2 <Emoji factory> + <Emoji garage> + <Emoji construction yard>)
        * Speaking Woods > Tine (<Emoji mpf> + 2 <Emoji factory> + <Emoji garage> + <Emoji shipyard> + <Emoji construction yard>)
        * Callum's Cape > Callum's Keep (<Emoji mpf> + 2 <Emoji factory> + <Emoji garage> + <Emoji shipyard> + <Emoji construction yard>)

    The following refineries have *two* factories in the same hex:
        * Howl County > Great Warden Dam (2 <Emoji factory> + <Emoji garage> + <Emoji shipyard> + <Emoji construction yard>)
        * Morgans Crossing > Allsight (2 <Emoji factory> + <Emoji garage> + <Emoji shipyard> + <Emoji construction yard>)
    
    The following refineries have *one* factory in the same hex:
        * Stonecradle > Fading Lights (1 <Emoji factory> + 1 <Emoji garage> + 4 <Emoji shipyard> + 2 <Emoji  construction yard>)
        * Godcrofts (Island) > Isawa (1 <Emoji factory> + 1 <Emoji garage> + 4 <Emoji shipyard> + 2 <Emoji  construction yard>)
        * Oarbreaker Isles (Island) > The Conclave (1 <Emoji factory> + 1 <Emoji garage> + <Emoji shipyard> + <Emoji construction yard>)
        * Stema Landing (Island) > Alchimeo Estate (1 <Emoji factory> + 1 <Emoji garage> + <Emoji shipyard> + <Emoji construction yard>)

    The following refineries have *zero* factories in the same hex:
        * Callahans Passage > Crumbling Post (<Emoji shipyard>)
        * Weathered Expanse > Foxcatcher (<Emoji shipyard> + <Emoji construction yard>)

6. <If hex includes factory> Do you want to add the factories in this hex to your network? Yes / No

7. Which factories do you intend to use? You may choose to not include any factories, but this is not recommended.
    <Query from WarAPI and List, remove ones already added from MPF step>
    <Sort 
        Start with hexes that have a mass production factory, list that category first.
        Then count/list the number of refineries in same hex, group by number of refineries, usually there will be only one
        Sort island hexes last in list
    >
    <Example From War 126 on Warden Side>

    You have added the following factories:
        <List all factories in network>
        * None

    The following factories also have a mass production factory in the same hex:
        <Include, number of factories in same hex in parenthesis>
        * Clanshead Valley > The King (<Emoji MPF> + <Emoji refinery> + <Emoji garage> + <Emoji shipyard> + <Emoji construction yard>)
        * Basin Sinnoach > Cuttail Station (<Emoji mpf> + <Emoji refinery> + <Emoji garage> + <Emoji shipyard> + <Emoji construction yard>)
        * Reaching Trail > Brodytown (<Emoji mpf> + <Emoji refinery> + <Emoji garage> + <Emoji construction yard>)
        * Speaking Woods > Tine (<Emoji mpf> + <Emoji refinery> + <Emoji garage> + <Emoji shipyard> + <Emoji construction yard>)
        * Callum's Cape > Callum's Keep (<Emoji mpf> + <Emoji refinery> + <Emoji garage> + <Emoji shipyard> + <Emoji construction yard>)

    The following refineries have *two* refineries  in the same hex:
        * Howl County > Great Warden Dam (2 <Emoji factory> + <Emoji garage> + <Emoji shipyard> + <Emoji construction yard>)
        * Morgans Crossing > Allsight (2 <Emoji factory> + <Emoji garage> + <Emoji shipyard> + <Emoji construction yard>)
    
    The following refineries have *one* factory in the same hex:
        * Stonecradle > Fading Lights (1 <Emoji factory> + 1 <Emoji garage> + 4 <Emoji shipyard> + 2 <Emoji  construction yard>)
        * Godcrofts (Island) > Isawa (1 <Emoji factory> + 1 <Emoji garage> + 4 <Emoji shipyard> + 2 <Emoji  construction yard>)
        * Oarbreaker Isles (Island) > The Conclave (1 <Emoji factory> + 1 <Emoji garage> + <Emoji shipyard> + <Emoji construction yard>)
        * Stema Landing (Island) > Alchimeo Estate (1 <Emoji factory> + 1 <Emoji garage> + <Emoji shipyard> + <Emoji construction yard>)

    The following refineries have *zero* factories in the same hex:
        * Callahans Passage > Crumbling Post (<Emoji shipyard>)
        * Weathered Expanse > Foxcatcher (<Emoji shipyard> + <Emoji construction yard>)



   * Do you intend to use a facility for ease of large volume manufacturing, savings in logistics, savings in resources, or advanced manufacturing?
   * How many of each building will you have in your facility?
	* Coal Refinery
		* Coal Liquifier
		* Advanced Coal Liquifer
		* Smelter
	* Ammunition Factory
		* Large Shell Factory
		* Rocket Workshop
		* Tripod Factory
	* Concrete Mixer
	* Infantry Kit Factory
		* Small Arms Workshop
		* Heavy Munitions Foundry
		* Special Weapons
	* Materials Factory
		* Assembly Bay
		* Forge
		* Metal Press (Oil)
		* Smelter
   * <Loop Through Each Building Type>
	* Which recipies do you intend to run from each building type?
   * How do you intend to make vehicles? <Garage/MPF>
	* Do you intend to use full MPF queues?
		* Yes - Go for Maximum Efficiency when producing, but risk overproducing items
		* No - Make only what is needed
  	* What is the threshold for when something should be manfuactured in the MPF?