Most items in the game can be produced via multiple production processes. This leaves an open question of which process to prefer. This document outlines the production preference system and how it should be implemented in the bot.


## Cost

Item cost is one of the most important factors for the bot. The primary advantage of using a bot instead of having players manually manage production is that the bot can effectively manage lead times and coordinate team members across different production queues. Preventing over production at certain levels of the supply chain and shortages at others.

Cost is a complicated metric, because it is not simply the price of the item. It involves:

* The time required to harvest raw materials
* The availability of raw resources in a hex
* The time required to transport the materials to a refinery
* The time required to refine the materials
* The time required to transport the finished intermediate products to a storage and production facility
* The time required actually producing the item
* The time required to transport the finished item to a frontline depot or storage facility
* The time required to transport the item to the frontline or end user

When considering cost, the bot should primarily be attempting to convert cost into a time-based metric. A constant question is it better to simply mine more resources or spend time transporting an item from further in the backline.

In the backlines where scrap is scarce and the MPF close by it is likely better to set additional MPF queues and produce items there. In the frontline where resources are plentiful, it is likely better to simply mine more resources and produce items at a factory or other production facility.

Facilities add another layer of complexity to the cost metric. They have a fixed cost in terms of resources to build and can often can produce items at a lower cost total time cost than the MPF plus a higher volume of total product. However, they also require extensive planning, coordination, and management to ensure their security and prevent decay from lack of Maintenance Supplies.

If you add in the cost of maintenance supplies and the time required to transport them plus the inital pcmats used in production facilities often only pay off if they are used for a long period of time.

## Material Types

Not all material types are created equal. Anything component based is extensively more expensive than salvage-based items. Rmats in particular have a very slow refine time at 2.7 days for a full refinery queue of 6,000 rmats. There is no direct conversion rate between bmats and rmats, but the bot will need to answer the question of "how many bmats is an rmat worth?"

Sulfur and high explosive powder also effectively represent a hard wall against mass volumes of artillery by the game's developers. By design, they are intended to be slow to produce and challenging to acquire in large quantities. This means that the bot should always prioritize production of these items over things that have shorter lead times.


## Availability

Availability refers to the amount of space available in the Mass Production Factory (MPF) or other production facilities. If the MPF is full, it is often better to produce items at a factory or other production facility instead. The bot must monitor the MPF queue size and adjust production preferences accordingly.

## Density

Density is a critical factor in production preferences. Higher density items are preferred over lower density items. This means that crates of shippables should always be preferred over individual items. The bot should prioritize producing items that can be packed into crates or shippables to maximize the efficiency of transportation and storage.

## Transportation

Midline transportation is usually the bottleneck in the Foxhole supply chain. The bot should consider the transportation time and cost when determining production preferences. If an item is challenging to transport or is not getting transported, it may be better to produce it at a facility or factory closer to the frontline.

## Overproduction

In general, the bot should prefer intentional overproduction of certain items within reason. Generally, it is better to always take advantage of full production queues at a factory or MPF, even if it means producing more than is immediately needed.

This is because:

* it allows for a buffer of items that can be used in the future, especially for items that are critical to the frontline or in which full MPF queues are not available.
* the man-hours required to set up a production queue are the same for a full queue as they are for a partial queue. Factory dancing is often a time-consuming process, and it is often more efficient to produce a full queue of items rather than setting up multiple smaller queues.
* Certain queues at factories or the MPF are underutilized. For example, the MPF maintenance supply queue is almost never full, as is the uniform queue. Setting a queue in this category is effectively "free" as it does not take any additional factory dancing time, only additional resources.

If an item is expensive to produce, the bot should be more cautious about overproducing it. The bot should also consider the availability of resources and the cost of production when determining whether to overproduce an item.

Regiments in general tend towards overproduction of items. Most players are focused on either focused on backline production or frontline distribution. The ones in backline production tend to overproduce items and may not fully understand what is needed on the front. While the ones in frontline distribution tend to prefer traveling excessively long distances for items over taking the time to production. The bot should try to balance this out by generally preferring transportation tasks to prevent things from piling up in the backline.

## Lead Times

The bot should consider the lead times for production when determining production preferences. If there is a large shortage of an item, the bot should prioritize producing that item as soon as possible.

For the most part, the bot should prefer efficient production unless the priority has explicitly been raised by a user and approved by a logistics officer. This is because at the end of the day, the bot is simply a task board, and players retain the ability to override the bot's decisions. If something is truly in shortage, it may not need to be communicated explicitly through the bot, having adequate up ot date dashboards to maintain situational awareness is often enough.

Communicating lead times to people further down the supply chain is one of the biggest value adds the bot can do. Especially when factoring in cook times or when something will be available.

Players lean towards being impatient, so the bot preferring efficient production is often
