import time
from typing import Dict, Union
from services.FoxholeDataObjects.recipe import Recipe

def calculate_completion_time(production_rates: Dict[str, float], recipe: str, quantity: int) -> float:
    """Calculate when a recipe will be completed given current production rate."""
    if recipe not in production_rates:
        return 0.0
    rate = production_rates[recipe]  # items per hour
    if rate <= 0:
        return float('inf')
    hours_needed = quantity / rate
    return time.time() + (hours_needed * 3600)

def calculate_output_at_time(recipe: Recipe, duration_or_timestamp: Union[float, int]) -> Dict[str, int]:
    """
    Calculate the output of a recipe at a given duration (seconds) or timestamp (epoch seconds).
    If a timestamp is provided, duration is calculated as timestamp - now.
    Returns a dict of output item -> quantity produced.
    """
    now = time.time()
    # If duration_or_timestamp is in the future, treat as timestamp
    if duration_or_timestamp > now + 1:  # allow for small rounding
        duration = duration_or_timestamp - now
    else:
        duration = duration_or_timestamp
    if duration <= 0:
        return {item: 0 for item in recipe.outputs}
    cycles = duration / recipe.cycle_time
    output = {item: int(cycles * qty) for item, qty in recipe.outputs.items()}
    return output
