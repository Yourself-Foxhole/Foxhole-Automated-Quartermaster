Priority Calculation: The "Bubble Up" System
Task priority is not a simple linear scale. It dynamically escalates based on the severity of the deficit and the cumulative demand from downstream nodes. This creates a "bubble up" effect, where critical shortages at the frontline rapidly elevate the priority of all blocking tasks further up the supply chain.

The priority of a task is calculated using the following formula:

Task Priority=(Base Item Priority×Deficit Multiplier)+Urgency Bonus+Cumulative Downstream Priority
Base Item Priority: A static value assigned to each item type, reflecting its general importance (e.g., Shirts > Bmats > Grenades). Configurable via !hub config set_item_priority.

Deficit Multiplier: This is the non-linear scaling factor. As the current stock of an item at a location drops further below its target buffer, the multiplier increases exponentially. This ensures that the last few items needed to fill a critical gap receive a disproportionately high priority.

Example: If "Soldier's Supplies" (Shirts) have a base priority of 10, and a target buffer of 200:

Having 190 shirts (deficit of 10) might yield a small multiplier (e.g., 1.1x).

Having 10 shirts (deficit of 190) might yield a much larger multiplier (e.g., 10x), making the priority of getting those last shirts extremely high.

This multiplier ensures that the closer a location is to running out, the more urgent the task becomes.

Urgency Bonus: A flat bonus applied if the initial !request included an Urgency=High flag.

Cumulative Downstream Priority: This is the "bubble up" component. When a task is generated due to a deficit, it inherits a portion of the priority of all downstream tasks that are blocked by its completion.

Mechanism:

When a TRANSPORT_LAST_MILE task is generated for a Forward Base, its priority is calculated based on the base's deficit and the item's base priority.

If this task cannot be fulfilled (e.g., STORED_FRONTLINE_HUB is insufficient), it triggers a Level 2 pull. The resulting Level 2 task (TRANSPORT or QUEUE_PRODUCTION) will then inherit a portion (e.g., 50%) of the TRANSPORT_LAST_MILE task's calculated priority.

This continues up the chain: if a QUEUE_PRODUCTION task is blocked by REFINED_STORED materials, the TRANSPORT_REFINED or QUEUE_REFINING task generated will inherit a portion of the QUEUE_PRODUCTION task's priority, and so on, all the way to GATHER_RESOURCE.

This ensures that a single critical shortage at the frontline can rapidly elevate the priority of a raw resource gathering task deep in the backline, making it visible and actionable.

Default Task Priority Tiers (Long Lead Time Bias)
In scenarios where no critical shortages are actively "bubbling up" priority, the default task priority tiers favor tasks with longer lead times, optimizing for continuous flow and preventing future bottlenecks.

Long Lead Time Manufacturing

a. Mass Production Factory (MPF)

b. Facility (shells, vehicles, etc.)

Long Lead Time Refining

a. Components > Refined Materials (Rmats) - (2.7 days for full queue of 6000)

b. Sulfur > High Explosive Powder - 24 hours for full queue

c. Salvage > Explosive Materials - 24 hours for full queue, but much higher capacity

Hard to Find Resource Acquisition

a. Component (6-8 hours to gather a significant amount)

b. Sulfur (4-6 hours to gather a significant amount)

Midline Transport (Bulk)

a. Train (Highest volume, longest setup)

b. Freighter (High volume, ocean transport)

c. Flatbed (Container/Vehicle transport)

Raw Resource Gathering (Common)

Refinery Pickup/Transport (Short Lead Time)

Factory Production (Short Lead Time)

Front Line Delivery (Last Mile)

Note: This tier can be dynamically upgraded to a priority of 5 or higher based on the "bubble up" system if the item is critically needed at the frontline.