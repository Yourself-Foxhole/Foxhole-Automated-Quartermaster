The Foxhole developers update the game roughly
3-7 times per year with various updates.

At the time of writing the most important update
of the year 2025 is the Airborne Update that will
add planes to the game.

Each update usually contains minor gameplay and balance
changes between different minor version of the game.
A true expansion only comes once every 2-3 years.

Foxhole is an MMO-like Third-Person Shooter wherein
players fight for areas in a persistent global war.
Like EVE Online each item in the game is made by
a human player and do logistics.

When game updates are released this gets distributed via
the steam distribution, and new application binaries
get produced.

The player modding community produces a community generated
"Player Data Mine" of this data. Which includes exported
Unreal Engine 4 scripts and data that is stored directly
in a .pak Unreal Engine binary file.

This can be extracted with scripts and tools like FModel,
which allow unpacking of these back to their original format.
From here the mod community has produced an entity extraction
into a data mine with all major variables and constants in the
game. This is what we have in the data/static-game-data/ folder.

As of writing the current update is Update 61. Update 62 is due
sometime in August 2025 or September 2025.

## The Static Data Export

The static data is important for us because it is how we calculate
the proper production times and ratios. The static data export
contains values for the production costs of various things.