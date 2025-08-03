The following below includes an example exchange for a new war.

<Start of onboarding>

Welcome to the Foxhole Automated Quartermaster (FAQ). This bot aims to create and manage tasks in a ticketing system to facilitate communication between players of Foxhole. By better communicating it aims to answer the following questions:

* What can I do to help?
* What should I work on next?
* Why don't we have what we need?
* How much longer until we get x?

-- Query WarAPI @ 

Welcome to War {Number}

1. Proceeding with onboarding will delete and rebuild your database and require you to reenter all your setup information. This is intended to be done at the start of every war. Are you sure you want to continue?
   2. If you want to change only a single setting you may do so with a command.
   3. If you would like a list of everything covered in onboarding react.
2. Which MPF do you want to use? 
   3. List all MPFs
   4. List an option to not use an MPF
5. Do you want to add nearby buildings to the MPF to your logistics network?
   6. All Buidlings
   7. Storage Depot / Seaport
   8. Factory
   9. Refinery
   10. Garage
   11. Shipyard
12. Do you want to add any additional refineries
    13. Use War API to list all refineries
    14. Group by number of factories in hex
    14. Include an option to skip
15. Do you want to add nearby logistics buildings to your network? (same as MPF question, but filtered for what is inex)
15. Do you want to add any additional factories?
    16. Use War API to gather a list of all factories
    17. Group first by if there is a refinery present in the same hex
    18. Then group by the number of factories present in the hex, in descending order
    19. Always list island hexes within a group
20. 

