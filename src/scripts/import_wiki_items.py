"""
Script for importing item data from the Foxhole wiki.
"""

import asyncio
import logging
from typing import Dict, List, Optional
import aiohttp
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.database_manager import DatabaseManager
from src.models.item import Item, ItemBuildingTarget

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default configurations
DEFAULT_IMPORTANCE = {
    "Ammunition": 5,
    "Medical": 5,
    "Fuel": 4,
    "Heavy Arms": 4,
    "Supplies": 3,
    "Tools": 3,
    "Materials": 2,
    "Miscellaneous": 1
}

DEFAULT_TARGETS = {
    "Ammunition": {
        "Bunker": 1000,
        "Safehouse": 500,
        "Stockpile": 2000
    },
    "Medical": {
        "Bunker": 500,
        "Safehouse": 200,
        "Stockpile": 1000
    },
    "Fuel": {
        "Bunker": 2000,
        "Safehouse": 1000,
        "Stockpile": 5000
    },
    "Heavy Arms": {
        "Bunker": 100,
        "Safehouse": 50,
        "Stockpile": 200
    },
    "Supplies": {
        "Bunker": 500,
        "Safehouse": 200,
        "Stockpile": 1000
    }
}

async def fetch_wiki_data() -> List[Dict]:
    """Fetch item data from the Foxhole wiki."""
    url = "https://foxhole.wiki.gg/wiki/Items"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                raise Exception(f"Failed to fetch wiki data: {response.status}")
            
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            
            items = []
            # TODO: Implement wiki parsing logic
            # This is a placeholder for the actual parsing logic
            return items

def determine_importance(category: str, name: str) -> int:
    """Determine item importance based on category and name."""
    base_importance = DEFAULT_IMPORTANCE.get(category, 3)
    
    # Adjust importance based on item name keywords
    if any(keyword in name.lower() for keyword in ["critical", "essential", "vital"]):
        return min(base_importance + 1, 5)
    elif any(keyword in name.lower() for keyword in ["optional", "luxury"]):
        return max(base_importance - 1, 1)
    
    return base_importance

def get_building_targets(category: str) -> Dict[str, int]:
    """Get default building targets for an item category."""
    return DEFAULT_TARGETS.get(category, {
        "Bunker": 100,
        "Safehouse": 50,
        "Stockpile": 200
    })

async def import_items(session: AsyncSession, items_data: List[Dict]) -> None:
    """Import items into the database."""
    for item_data in items_data:
        try:
            # Create item
            item = Item(
                id=item_data["id"],
                name=item_data["name"],
                category=item_data["category"],
                description=item_data.get("description"),
                importance=determine_importance(item_data["category"], item_data["name"]),
                can_be_produced=item_data.get("can_be_produced", False),
                production_facility=item_data.get("production_facility")
            )
            
            # Add building targets
            building_targets = get_building_targets(item_data["category"])
            for building_type, target_quantity in building_targets.items():
                target = ItemBuildingTarget(
                    item_id=item.id,
                    building_type=building_type,
                    target_quantity=target_quantity
                )
                item.building_targets.append(target)
            
            session.add(item)
            logger.info(f"Added item: {item.name}")
            
        except Exception as e:
            logger.error(f"Failed to import item {item_data.get('name', 'unknown')}: {str(e)}")
            continue
    
    await session.commit()

async def main():
    """Main function to run the import process."""
    try:
        # Initialize database
        db_manager = DatabaseManager()
        await db_manager.initialize()
        
        # Fetch wiki data
        logger.info("Fetching wiki data...")
        items_data = await fetch_wiki_data()
        
        # Import items
        async with db_manager.get_session() as session:
            logger.info("Importing items...")
            await import_items(session, items_data)
        
        logger.info("Import completed successfully")
        
    except Exception as e:
        logger.error(f"Import failed: {str(e)}")
        raise
    finally:
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(main()) 