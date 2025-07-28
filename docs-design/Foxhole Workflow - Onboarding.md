oIntended Workflow:
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

2. Do you intend to use the Mass Production Factory for up to a 39% discount on crates and 30% discount on vehicles and shippables?
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

    You have added:

    * Seaport
    * Refinery
    * Factory/Factories
    * Garage
    * Shipyard

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

6. <If hex includes factory> Do you want to add the logistics buildings in this hex to your network? Yes / No

7. Which factories do you intend to use? You may choose to not include any factories, but this is not recommended.
    <Query from WarAPI and List, remove ones already added from MPF step>
    <Sort 
        Start with hexes that have a mass production factory, list that category first.
        Then count/list the number of refineries in the same hex. Group by each (will usually be 1 or 0 refineries)
        Then count/list by number of factories.
        Sort island hexes last in list
    >
    <Example From War 126 on Warden Side>

    You have already added the following factories:
        <List all factories in network>
        * None

    The following regions have a mass production factory *and* a refinery in the same hex:
        <Include, number of factories in same hex in parenthesis>
        * Clanshead Valley > The King (<Emoji MPF> + <Emoji refinery> + <Emoji garage> + <Emoji shipyard> + <Emoji construction yard>)
        * Basin Sinnoach > Cuttail Station (<Emoji mpf> + <Emoji refinery> + <Emoji garage> + <Emoji shipyard> + <Emoji construction yard>)
        * Reaching Trail > Brodytown (<Emoji mpf> + <Emoji refinery> + <Emoji garage> + <Emoji construction yard>)
        * Speaking Woods > Tine (<Emoji mpf> + <Emoji refinery> + <Emoji garage> + <Emoji shipyard> + <Emoji construction yard>)
        * Callum's Cape > Callum's Keep (<Emoji mpf> + <Emoji refinery> + <Emoji garage> + <Emoji shipyard> + <Emoji construction yard>)

    The following regions have *two* factories *and* a refinery in the same hex:
        * Howl County > Great Warden Dam (2 <Emoji factory> + <Emoji garage> + <Emoji shipyard> + <Emoji construction yard>)
        * Morgans Crossing > Allsight (2 <Emoji factory> + <Emoji garage> + <Emoji shipyard> + <Emoji construction yard>)
    
    The following regions have *one* factory *and* a refinery in the same hex:
        * Stonecradle > Fading Lights (1 <Emoji factory> + 1 <Emoji garage> + 4 <Emoji shipyard> + 2 <Emoji  construction yard>)
        * Godcrofts (Island) > Isawa (1 <Emoji factory> + 1 <Emoji garage> + 4 <Emoji shipyard> + 2 <Emoji  construction yard>)
        * Oarbreaker Isles (Island) > The Conclave (1 <Emoji factory> + 1 <Emoji garage> + <Emoji shipyard> + <Emoji construction yard>)
        * Stema Landing (Island) > Alchimeo Estate (1 <Emoji factory> + 1 <Emoji garage> + <Emoji shipyard> + <Emoji construction yard>)
    
    The following regions have *two* factories, but *no* refinery in the same hex:
        * Viper Pit > Kirknell (1 <Emoji garage> + <Emoji shipyard> + <Emoji construction yard>)
        * Kings Cage > The Manacle  (<Emoji garage> + <Emoji shipyard> + <Emoji construction yard>)
        * The Clastra > Treasury (<Emoji garage> + <Emoji shipyard> + <Emoji construction yard>)


    The following regions have *one* factories, but *no* refinery in the same hex:
        * Stilten Shelf > Breaker Town (<Emoji shipyard> + <Emoji construction yard>)
        * Linn of Mercy > Ulster Falls (<Emoji shipyard> + <Emoji construction yard>)
        * Farranac Coast > Huskhollow (<Emoji shipyard> + <Emoji construction yard>)
        * Nevish Line > The Scrying Belt (<Emoji shipyard> + <Emoji construction yard>)

8. Would you like to add nearyby logistics buildings to the factories you have added? Yes/No
    <If Yes>
    <Loop through each factory, present list, ask which buildings they'd like to add to the network>

9. Would you like to add a garage to your network?

10. Would you like to add nearby logistics buildings to the garages you have added?

11. Do you intend to add or use any facilities? Yes / No

    Facilities allow you to:
        * Make and use advanced fuels (Petrol, Heavy Oil, Enriched Oil - Refinery)
        * Upgrade vehicles (Small Assembly Bay)
        * Make trains and advanced armored vehicles (Large Assembly Bay)
        * Make ammunition (Ammunition Factory)
        * Make Infantry Crate items in large quantities (Infantry Kit Factory)
        * Passively Harvest Resources (Stationary Harvesters)
        * Make sandbags, barbwire, and metal beams in large quantities (Assembly Bay)
        * Make additional componets or processed construction materials (Recycler)
        * Make concrete without using components (Coal Liquifier)
        * Make mounted weapons very inexpensively (Tripod Factory)

    The advantages of facilites are:
        * You may place a facility close to the frontline or resources
        * You may harvest additional resources
        * You may do advanced production, required for high tech items
        * You may do production continiously 24/7, producing signfigantly more than world structures
        * In some cases, items may be cheaper at facilities

    The disadvantages of facilities are:
        * They require you to negotiate and secure land to build the facility on
        * They require large amounts of ongoing maintenance supplies
        * They require defenses and bunker bases to be built
        * They may become subject to partisan attacks, requiring active QRFs
        * They require power to operate, and may require manual refueling

12. <If yes to 11> Which Tier of facilities is currently unlocked?
        * Tier 1
        * Tier 2
        * Tier 3

<Loop until all facilities have been added, repeat here if necessary>
13. <If yes to 11> Please name your facility. <Enter string>

14. <If yes to 11> Which hex will your facility be in? 

15. <If yes to 11> Which buildings do you have in your facility?
    You may change this later, only include the buildings currently in the tech level.

    <Remove buildings that have not yet teched>
    * Power
        * Diseal Power Plant
            * Petrol Power Plant
            * Coal Power Plant
        * Power Station
            * Sulfuric Reactor
    * Resource
        * Oil Pump
            * Electric Oil Well
            * Fracker
        * Stationary Harvester
            * Extractor
        * Water Pump
    * Coal Refinery
		* Coal Liquifier
		* Advanced Coal Liquifer
		* Smelter
    * Oil Refinery
        * Reformer
        * Petrol
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
    * Vehicle
        * Small Assembly Station
            * Motor Pool
            * Battery Line
            * Field Station
            * Tank Factory
            * Weapons Platform
            * Navy Works
            * Advanced Structure Manufactory
        * Large Assembly Station
            * Train Assembly
            * Heavy Tank Assembly
        * Field Modification Center
    * Advanced Structures
        * Dry Dock
        * A0E-9 Rocket Platform

16. Which outputs do you wish to track in the logistics network that are made at this facility?

    Facilties can make a wide range of items, some items may be low production and you may not want to use this bot to track everything. 

    The more things you track, the more data entry you will have to do to keep everything up to date.

    It is recommended to only track high volume outputs or outputs you will be doing a lot of work on.

    * Resources
        * Coal Products
        * Oil Products
        * Sulfur
        * Components
        * Salvage
    * Vehicles
    * Infantry Items
    * Ammunition
    * Tanks
    * Advanced Manufacturing
        * Trains
        * Advanced Tanks (BT, SPG, SHT)
        * Large Ships
        * Rockets (Nuke)
   
   17. <If yes to Advanced Manufacturing> You have selected that you wish to track and make advanced manufacturing items.

        Keep in mind that advanced manufacturing adds a signifigantly larger base footprint and thus requires substantially more Maintenance Supplies.

        Additionally, advanced manufacturing will require signfignatly more security as your base will become a high value target. Expect to need to have daily active factory staff, with active QRF supplies available in the base.

        Keep in mind you may be able to purchase these items instead of making them through war-eco for less than it would cost to make them on your own. <If Warden> See Warden Trading Guild at warden.store discord link for details on current war-eco.

        Please consider the following for each of the production chains:

        * <If trains is true> Trains are the easiest advanced manufacturing item to produce. They have a short print time, but you must determine how to store a train when not in use. The locomotives in particular are sought after partisan targets as are any advanced cars (BMS Bloodtender, Tempest Cannon)
        * <If Advanced Tanks is true> Main Battle Tanks, Self Propelled Guns, and Super Heavy Tanks are high value targets with relatively long print times. You will need to secure your base for the entire print time, which can be up to 2 days. You must also store your tanks and keep them secure.
        
        Expect partisan interest and attacks. It is recommended to have multiple layers of defense, a base that is out of range of water attacks (partsians may use gunboats), good intel coverage, and dry concrete foundations. It is best if the base is large enough that the pads are out of view of partisans.
        * <If Large Ships is true> Large ships require large numbers of rare metals, a material that only spawns in small drop chances from salavage fields. Rare metal can be highly contested and time consuming to gather. It is recommended to have an anchored ship providing security (like a Longhook), good intel, quick QRFs, and good base defenses.
        * <If Rockets is true> The rocket requires large amounts of rare metal and long production times. It is typically a faction wide effort. It is recommended you make the rocket parts in a separate location than the rocket launch pad. Rockets will be very high value targets that may invite a faction-wide push to destroy your facility.
   
 18. How much detail do you want to track in your facility?

    * I only want to track facility outputs (what is ready to be picked up)
        This option tells what needs to be made, and how much is ready to go, but does not track anything beyond this basic information. It is ideal if you want to add outputs ready for pickup at a facility without having to do data entry or maintain inventories.
    * I want to track facility inputs and facility outputs
        This option allows you to specify inputs as well as outputs. For instance you may be able to track that you need salvage, sulfur, or coal and how much you need. You may also track outputs. By default the facility is treated like a black box and the inner workings are not tracked at all.

    Exclusive Or Reaction - O or I
    
19. Do you want to track any additional facility information on specifics inside your facility?

    Facilities operate under a different tracking model than those for world structures. Because facilites do not have a mouse hover over information and do not have map information collecting reliable inventory data is significantly more complicated.

    Facilities do not support screenshot entry at this time, and instead stocks must be manually updated. Be careful on how much detail you want to include from facilites, as too much data entry will mean that the bot will not be used or the data will be stale.

    Facility data entry is simplified to include a status board and a green/yellow/red on inventory in each category. Facilites do not have tasks, as the invidual effort required and distances traveled are too short to be relevant. 

    Instead the board would simply show "The facility is red on coal" and you can then gather more coal.

    Please select all you'd like to track:

    * I want to track facility reservations
        This option is recommended, and can be used for making sure reservations don't expire.
    * I want to track intermediate items
        This option allows intermediate components such as Construction Materials, Processed Construction Materials, and Assembly Materials to be tracked.
    * I want to track power
        This is typically useful for Tier 1 before pipes, for isolated facilities not connected to an oil field, or for coal plants. Enter the quantity and recipie and calculate time to empty.
    * I want to track maintenance supplies
        This option allows you to specify maintenance supplies overall for your facility as a category 
    * I want to track production queues
        This option allows you to reflect which specific queues have been set on buildings inside your facility and optionally provide estimates on cook time based on production
    * I want to track facility inventory
        This option allows you to track the total inventory of items at your facility. Be aware this effectively makes your facility a storage depot for tracking purposes in the bot and substantially increases data entry. It is recommended you only use this track items which you will be using or exporting.



    <Loop Through Each Building Type>
	* Which recipies do you intend to run from each building type?





   * How do you intend to make vehicles? <Garage/MPF>
	* Do you intend to use full MPF queues?
		* Yes - Go for Maximum Efficiency when producing, but risk overproducing items
		* No - Make only what is needed
  	* What is the threshold for when something should be manfuactured in the MPF?