Players in Foxhole often have questions on "how many of /x/ to do /y/"
and other questions that can be answered relatively easily from the
static data export.

While not a primary feature, we should include a feature which allows
easy natural language queries of the Static Data Export (SDE) from our
local DB.

As a first feature this should be the following:

* How much to kill?
* Relative Cost Effectivness
* Production Cost

## How Much to Kill

The goal of this bot is to find out how many things you need to kill
something in the game. This should take two formats.

1. A direct query lookup of "how many mammons do I need to kill a tank"
2. A option to give a thing and have an automatic report generated on 
what you need to kill it.
3. An option to do the same thing, but from the prospective of the weapon
   (i.e. I have 6 mammons what can I kill)

## Relative Cost Effectiveness

A person once asked for a list of how many bmats per item. We should be able
to generate a report like this pretty easily.

## Production Cost

This is built into the actual app, but we should have a simple calculator
for tallying the total production cost for various things, and be able
to generate a report, to interact with before locking it in to the
logistics system.