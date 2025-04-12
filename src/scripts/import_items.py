"""
Script to import item data from the Foxhole wiki.

This script fetches item data from the Foxhole wiki and imports it into the database.
It handles:
- Fetching item data from the wiki
- Parsing item information
- Setting default importance values
- Setting default target quantities for different building types
- Importing the data into the database
"""

import asyncio
import json
from typing import Dict, List, Optional
import requests
from bs4 import BeautifulSoup
from loguru import logger

from src.database.database_manager import DatabaseManager
from src.models.item import Item, ItemBuildingTarget

# Default importance values by category
DEFAULT_IMPORTANCE = {
    "Ammunition": 5,  # Critical for combat
    "Medical": 5,     # Critical for survival
    "Supplies": 4,    # Important for logistics
    "Resources": 3,   # Basic resources
    "Equipment": 4,   # Important equipment
    "Vehicles": 4,    # Important vehicles
    "Structures": 3,  # Basic structures
    "Other": 2        # Miscellaneous items
}

# Default target quantities by building type
DEFAULT_TARGETS = {
    "Bunker": {
        "Ammunition": 1000,
        "Medical": 100,
        "Supplies": 500
    },
    "Safehouse": {
        "Medical": 200,
        "Supplies": 1000
    },
    "Factory": {
        "Resources": 5000,
        "Supplies": 2000
    },
    "Refinery": {
        "Resources": 10000
    }
}

async def fetch_wiki_data() -> List[Dict]:
    """Fetch item data from the Foxhole wiki.
    
    Returns:
        List of dictionaries containing item data
    """
    # URL of the items page on the wiki
    url = "https://foxhole.wiki.gg/wiki/Items"
    
    try:
        # Fetch the page
        response = requests.get(url)
        response.raise_for_status()
        
        # Parse the HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the items table
        items_table = soup.find('table', {'class': 'wikitable'})
        if not items_table:
            raise ValueError("Could not find items table on wiki page")
        
        # Parse the table rows
        items = []
        for row in items_table.find_all('tr')[1:]:  # Skip header row
            cols = row.find_all('td')
            if len(cols) >= 3:
                item = {
                    'id': cols[0].text.strip().lower().replace(' ', '_'),
                    'name': cols[0].text.strip(),
                    'category': cols[1].text.strip(),
                    'description': cols[2].text.strip()
                }
                items.append(item)
        
        return items
    
    except Exception as e:
        logger.error(f"Error fetching wiki data: {e}")
        raise

def determine_importance(item: Dict) -> int:
    """Determine the importance value for an item.
    
    Args:
        item: Dictionary containing item data
        
    Returns:
        Importance value (1-5)
    """
    category = item['category']
    
    # Check for specific high-importance items
    if any(keyword in item['name'].lower() for keyword in ['bmat', 'rmat', 'hemat', 'diesel', 'petrol']):
        return 5
    
    # Use default importance for category
    return DEFAULT_IMPORTANCE.get(category, 3)

def get_building_targets(item: Dict) -> Dict[str, int]:
    """Get target quantities for different building types.
    
    Args:
        item: Dictionary containing item data
        
    Returns:
        Dictionary mapping building types to target quantities
    """
    category = item['category']
    targets = {}
    
    # Add default targets based on category
    for building_type, category_targets in DEFAULT_TARGETS.items():
        if category in category_targets:
            targets[building_type] = category_targets[category]
    
    return targets

async def import_items(db: DatabaseManager):
    """Import items from the wiki into the database.
    
    Args:
        db: Database manager instance
    """
    try:
        # Fetch items from wiki
        items = await fetch_wiki_data()
        logger.info(f"Fetched {len(items)} items from wiki")
        
        # Create database session
        async with db.get_session() as session:
            # Import each item
            for item_data in items:
                # Create item
                item = Item(
                    id=item_data['id'],
                    name=item_data['name'],
                    category=item_data['category'],
                    description=item_data['description'],
                    importance=determine_importance(item_data)
                )
                
                # Add building targets
                for building_type, target_quantity in get_building_targets(item_data).items():
                    target = ItemBuildingTarget(
                        item_id=item.id,
                        building_type=building_type,
                        target_quantity=target_quantity
                    )
                    item.building_targets.append(target)
                
                # Add to session
                session.add(item)
            
            # Commit changes
            await session.commit()
            logger.info("Successfully imported items into database")
    
    except Exception as e:
        logger.error(f"Error importing items: {e}")
        raise

async def main():
    """Main function to run the import script."""
    # Initialize database
    db = DatabaseManager()
    await db.initialize()
    
    try:
        # Import items
        await import_items(db)
    
    finally:
        # Close database connection
        await db.close()

if __name__ == "__main__":
    asyncio.run(main()) 