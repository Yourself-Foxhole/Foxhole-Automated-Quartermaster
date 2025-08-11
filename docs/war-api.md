Foxhole has an API called War API which can be found here: https://github.com/clapfoot/warapi

We use War API to get useful information about the War to avoid the user having to enter in as much data and to guard against data validation errors.


# War API Integration

We use [FoxAPI](https://github.com/ThePhoenix78/FoxAPI) to access the Foxhole War API. FoxAPI provides a robust, cached, and well-structured interface for all war, map, and report data. All code should use the data access functions in `data/warapi/war_api_client.py`.

Example usage:

```python
from data.warapi.war_api_client import get_hexagon_data
hex_data = get_hexagon_data('Deadlands')
print(hex_data.war_report)
print(hex_data.static)
print(hex_data.dynamic)
print(hex_data.captured_towns)
print(hex_data.casualty_rate)
```

## Endpoints and our analysis of them

* GET /worldconquest/war
  * This is useful for determining if we are in resistance phase and when a war starts. If it is before a war start time onboarding flow should include a warning as resources and even map factory layout can get rerolled and moved by the game's developers.
* GET /worldconquest/maps
  * This allows us to get a comprehensive list of game hexes that are active for a given war. However it does not include all information, like if the hex is predominantly islands or ocean (to the best of my knowledge). Thus we still require a mapping with additional hex metadata
* GET /worldconquest/warReport/:mapName
  * This is a very useful endpoint that we want to poll freuqently. This gives us the total number of casulities in a given hex. The data should be updated no more than once every 3 seconds.
  * A spike in enlistments or casulities is likely to result in a spike in consumption and depending on user configuerable settings we may want to trigger a notification if above a certain threshol.d
* GET /worldconquest/maps/:mapName/static
  * This contains map details and names and other useful information. It's useful to cache, but not needed on a regular basis. We only need to pull this once per war.
* GET /worldconquest/maps/:mapName/dynamic/public
  * This contains data like bunker bases known to both teams and locations of world structure buidlings. This is incredibly useful data as it drives the onboarding flow. We may want to pull this once per day, or a few times per day. It is per hex so it must be pulled mutliple times
