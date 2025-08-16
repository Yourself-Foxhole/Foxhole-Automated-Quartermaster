Player facilities introduce a large amount of complexity for the following reasons:

* Facilities include a high number of buildings, each with their own stockpiles
* Facilities may include duplicates of the same building type
* Facility production often involves significant more intermediate products
* Facility tasks involve moving things between different buildings over short distances, making them high repetition but low complexity tasks
* Facility storage is often difficult or complicated, with items being spread between the buildings and not collected until it leaves the facility
* Facilities require power, meaning production may go offline if power supply is disrupted
* Facilities require Maintenance Supplies, meaning that the facility may decay if not supplied
* Facilities have different designs and are not common with different production goals

 ## Architecture

Facilities must be built out and setup. They require certain inputs these are:

* The materials needed to build the actual facility
* The power grid for the facility
* Ongoing Maintenance Supplies

For facilities we are going to make use of the "using" part of the production chain. At least at the moment we need to store the following information about production.

"Using" is not calculated as an input because for the most part there are distinct phases of facilities:

* Facility Planning (what I will build?, where I will build it?, what the goals for the facility?)
* Facility Construction (is the facility actually built?, are we waiting on stuff? are we waiting on technology?)
* Facility Maintenance (do I have the stuff I need to make stuff? is there power? is there maintenance supplies (aka msupps)? is the facility defended?)
* Facility Operations (actually running the facility, which queues do I need to set?)

For the first phase, this is not a facility planning tool. There are dedicated web apps that aim to help plan facility layout with a drag and drop UI (Foxhole Planner) or map where stuff is across the world (Foxhole Stats). We don't need to implement facility planning tools because there are better tools than a discord bot.

For construction, we should implement this but really only for a list of planned buildings with orders queued up ready to go. This is so once something is actually available and comes online we should be able to instantly put those into the graph as soon as we are ready.

For facility maintenance, we do want to address this task. It's really important. Without the maintenance tasks the facility basically goes offline and decays or gets attacked by anti-facility partisans. But this task doesn't directly produce any outputs. Producing power or msupps does nothing for us in terms of total output. It's simply overhead. Depending on the player they may or may not want to track maintenance.

For facility operations, this is similar to other production in the game. But it differs in many key ways. For one facilities are unusual because they operate *entirely asynchronously* without player interaction. Unlike in the MPF, Factory, or any other world strucutre which effectively rely on batch processing Facilities have the power to basically set something and let it cook in large quantities.

Certain facility buildings involved in oil production are even fully automatic with pipes, requiring no player inputs at all other than transportation of outputs. Unfortunately at time of writing there are no conveyor belts in the game allowing for fully automated facilities.

Facilities can offer intermediate steps in complex development, advanced construction of high tech items, efficiency improvements on top of base processes, or the final finishing process of upgrades for tanks or other vehicles. The most complicated items in the game can only be built at facilities.


## Approach to Facilities

Instead of trying to generate tasks for facilities we instead approach the idea of a facility as a single entity.

### Core Requirements

At it's core a facility needs to monitor:

* Inputs
	* What is required
* Outputs
	* What we will get
* Using
	* What processes or other management things do we need to produce it
* MaintenanceStatus
	* Are the facility maintenance processes actually being done. We don't want to put a bunch of inputs into a decaying or abandoned facility.


### Facility Statusboard

The goal of the facility node is to capture everything on a single status board and leave it up to the user what they wish to track. Keep in mind at least for the first version of this tracking is going to be entirely manual, that shouldn't be *too* bad because facilities have relatively repetive inputs and only a few major critical things in the production cycle.

But it's also less convient than a Factory or MPF because you can't screenshot progress for everything, or just screenshot crates. A screenshot based utility would need to identify what building it's looking at and then add the totals together. Possibly doable, but not with existing Foxhole Inventory libarires. Due to the extra work this is left as a future possible feature, probably below tech unlock.

For the core of the dashboard we are providing:

* What the category is that's being tracked
* The status (red - need more /yellow - in between/green - sufficient)
* Quantity (optional)
* Who is working on that section

The goal of the status board is to be like a tag-in/tag-out board seen in industrial settings, allowing one to quickly see the status of the entire facility and what needs to be done just by looking at the board.

For example, if cmats are red I know I need to go make more cmats. If I'm told I need at least 25,000, then I know exactly what to do.

### What users can choose to track

On the one hand users could track everything. Inputs, Outputs, Needed "Using" facilitated inputs, and maintenance status (which could go so far as to include periodic site inspections or anti-partisan patrols).

On the other hand users could cut down on data entry substantially by eliminating all data entry entirely (i.e. only tracking orders from other nodes. The next step up would be to only track outputs ready for delivery.

By having separate sections, and perhaps even custom fields, we can allow the board to be configurable to suit the needs of that facility.

### Facility Tasks

Facilities often have recurring items that need to be done, there should be a reccuring tasks feature available for msupps, facility reservations (click a button or things go public), or other time based things that need to be done. This can be another embed below the statusboard that effectively has a reaction and when clicked updates the time. If close to expiry send a notificaiton.


## Facility Buildings


* Power
    * Diesel Power Plant
    * Power Station
      * Sulfuric Reactor
* Resource
  * Oil Well
    * Electric Oil Well
    * Fracker
  * Stationary Harvesters
    * Extractor
  * Water Pump
* Ammo Factory
* Concrete Mixer
* Infantry Kit Factory
* Materials Factory
* Metalworks Factory
* Coal Refinery
* Oil Refinery
* Vehicle
  * Small Assembly Bay
    * Tank Factory
  * Large Assembly Bay
    * Train Upgrade
* Advanced Manufacturing


## Class List Pre-Combination


* BaseNode
	* ProductionNode
		* WorldStructureNode
			* QueueableProductionNode
				* RefineryNode
				* FactoryNode
				* MassProductionFactoryNode
			* CharacterProductionNode
				* GarageNode
				* ShipyardNode
				* ConstructionYardNode
		* FacilityNode
			* PowerBuilding
				* DieselPowerPlant
				* PowerStationBuilding
			* ResourceBuilding
				* OilWell
				* WaterPump
				* StationaryHarvester
			* FacilityRefinery
				* CoalRefinery
				* OilRefinery
				* ConcreteMixer
			* ItemProductionBuilding
				* AmmoFactory
					* RocketBatteryWorkshop
					* LargeShellFactory
					* TripodFactory
				* InfantryKitFactory
					* SpecialIssueFirearmsAssembly
					* SmallArmsWorkshop
					* HeavyMunitionsFoundry
				* MaterialsFactory
					* AssemblyBay
					* Forge
					* MetalPress
					* Smelter
				* MetalworksFactory
					* Recycler
					* Blast Furnace
					* EngineeringStation
				* FacilityStorage
					* ResourceTransferStation
					* LiquidTransferStation
					* MaterialTransferStation
					* CrateTransferStation
				* FacilityVehicleBuilding
					* SmallAssemblyStation
					* LargeAssemblyStation
					* DryDock
					* FieldModificationCenter
					* A0E-9 Rocket Platform
				* FacilityUtility  (These are primarily player actions that represent maintenance activities, i.e. did you put something away or check this.)
					* MaintenanceTunnel
					* PowerSwitch
					* SmallGaugeTrain
					* LargeGaugeTrain
					* CraneStorage
					* SiteInspection
	


## Combined Class List

* BaseNode
	* ProductionNode
		* QueueableProductionNode
			* RefineryNode
			* FactoryNode
			* MassProductionFactoryNode
		* CharacterProductionNode
		* FacilityNode
			* PowerBuilding
			* LiquidBuilding
			* RawResourceBuilding
			* MaterialBuilding
			* CrateBuilding
			* VehicleBuilding
			* FacilityUtility