# Foxhole Automated Quartermaster Discord Bot

This design document explains the goals and key features of this project.


## Introduction

The goal of this project is to facilitate information of human players via the chat platform discord. The bot should


## The Problem Space

The game Foxhole is a persistent third-person shooter wherein everything players interact with is player made (except basic items at the start of the game).

The wars in Foxhole are sequentially numbered as of July 2025 we are on War 126. Wars will typically last between 1-7 weeks with each war going until the other team has captured a certain number of victory points.

The only thing directly spawned into the world of Foxhole is raw resources. These materials are then made into one or more intermediate resource, before being made into a final item. Items must then be transported and delivered to the front.

This production phase creates 4 distinct phases of production.

1. Resource Gathering
2. Production
3. Midline Distribution
4. Frontline Distribution

These changes create a directed draft which goes from a raw resource node into a thing that can be directly used at a front (including infantry weapons, vehicles, ships, artillery, or other support items).

### Logistics and Production in Foxhole



### Logistics Density

There is a hierarchy of items in Foxhole primary centered around the concept of density. Items can exist in the following levels:

1. Shippable — There are 4 shippable. Shippable store items for transportation in bulk.
   1. Shipping Container (For Crates)
   2. Liquid Container (For Liquids)
   3. Resource Container (For loose resources)
   4. Material Pallet (For items)
   5. Vehicles
   6. Special Shippable (rare advanced manufacturing items or advanced manufacturing items)
2. Crates - store a variety of items in a more compact form.
3. Item - a single number of something
4. Sub-item Quantity - some items in the game (like magazines or gas mask filters) have shots or health which track before they are used.

For Foxhole logistical density is one of the single most important factors in efficiency and has the power to substantially increase output of the entire network.

#### Inventory

The inventory of items is kept in one of two configurations: slots or stockpiles.

Slots are the basic unit of space in Foxhole. All items in the game take a minimum of one slot. Depending on the item, items may stack allowing them to be stored more compactly. The game developers will set stack sizes depending on their desired role with more expensive items usually having lower stack sizes. The standard inventory size for most vehicles or buildings is 15 slots.

Stockpiles allow for a much greater quantity of items stored, however they bring additional restrictions on the state of the items. Items in a stockpile incur assembly times when they are removed from the stockpile called "pull times" by the player community. This is a game mechanic intended to avoid griefing, but it is in this author's opinion poorly designed and heavy-handed. It punishes all players in the game to only slightly mitigate the problem of bad actors. The more expensive the item is it generally has longer pull times. Most items will have between a 1-10 second pull time. With pull times for expensive or important items being long such as 30 seconds or longer.

Stockpiles have additional properties with restrictions depending on the type of stockpile. Generally items may only be added to a stockpile if they are good condition fully repaired, with empty inventories, and not connected to other things. Anything other than the base item will be deleted when something is added to a stockpile, such as fuel, ammunition, or anything in the item inventory.

Player characters also have additional slot. Players have 8 different inventory slots with specialized purposes regardless of the uniform type, however these slots are highly restricted with each being able to store only a certain type of item. Players also include an inventory with the number changing depending on the type of uniform or item type. The default uniform allows for 7 inventory slots, but some types, like the Gunner's Breastplate only allow 3. Others like the Engineering Uniform, allow 8.


For logistics purposes, the main types we care about are slots, stack sizes within slots, and stockpiles. Here is a breakdown by type:

##### Resource

For resource gathering we care about 4 different ways of storing items:

* Basic Truck
  * The base transport truck is the Dunne or R-5 Hauler. It is a quite useful general purpose vehicle but does not have a large inventory capacity. While it is possible to use it for resource gathering, you would have to make many trips, and could find a higher capacity vehicle making it only good for early war.
* Expanded Capacity Truck (e.g. Loadlugger)
  * Expanded capacity trucks are effectively dump trucks within the world of Foxhole. They carry a pretty notable advantage of being able to carry more items. For instance you may carry 20 stacks of items in a loadlugger, but only 15 in a base truck. The disadvantage of the loadlugger is they are not general purpose. You may only use a loadlugger for resource gathering and it can't store complex or finished products.
* Resource Container
  * A resource container has the advantage of being able to carry significantly more items with the item limit being 5,000 of an item type. The disadvantage is that you must have crane infrastructure available at a location. While there is a mobile crane that means you must have at a minimum two vehicles. This can be a major problem in the early war when cranes are not yet commonly at resource fields.
* Small guage train
  * A small guage train is the highest capacity way of transporting raw materials in the game other than a large guage train full of resource containers. THey are commonly used for transporting raw materials short distances.


##### Production

Transportation during production can take a variety of forms. Production is very different depending on if the player is doing it at world structures or player facilities.

For world structure production, it involves "Factory Dancing" wherein you transport things between buildings one after another and make different items.



##### Midline Distribution


Midline distribution is typically done with one of the following methods:

* Basic Truck
  * Much like for other parts of the supply chain the base truck can be useful as a general purpose thing that does almost anything, but is quite limited.
* Shipping Container
  * A shipping container is very useful for midline tranpsortation.


##### Frontline Distribution

For frontline distrbuution you may use any of the following methods:

* Basic Truck
* Uparmored Truck
* Material Pallet
* Trailer (Large Items Only)


## The Goal

The bot should facilitate all the different steps of production
