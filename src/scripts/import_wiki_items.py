"""
Script for importing item data from the Foxhole wiki.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple
import aiohttp
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import re
import json

from src.database.database_manager import DatabaseManager
from src.database.models import Item, ItemBuildingTarget, ItemProductionInput, ItemCategory

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

# Production facility mappings
PRODUCTION_FACILITIES = {
    "Factory": ["Factory", "Munitions Factory", "Light Arms Factory", "Heavy Arms Factory"],
    "Refinery": ["Refinery", "Oil Refinery", "Component Mine"],
    "Workshop": ["Workshop", "Engineering Center"],
    "Garrison": ["Garrison", "Barracks"],
    "Hospital": ["Hospital", "Medical Center"],
    "Other": ["Seaport", "Storage Depot", "Relic Vault"]
}

async def fetch_wiki_data() -> List[Dict]:
    """Fetch item data from the Foxhole wiki using the MediaWiki API."""
    base_url = "https://foxhole.wiki.gg/w/api.php"
    items = []
    
    # First, get the page content
    params = {
        "action": "parse",
        "page": "Items",
        "format": "json",
        "prop": "text"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(base_url, params=params) as response:
            if response.status != 200:
                raise Exception(f"Failed to fetch wiki data: {response.status}")
            
            data = await response.json()
            html = data["parse"]["text"]["*"]
            soup = BeautifulSoup(html, "html.parser")
            
            # Find all item tables
            tables = soup.find_all("table", class_="wikitable")
            for table in tables:
                # Process each row in the table
                for row in table.find_all("tr")[1:]:  # Skip header row
                    cols = row.find_all("td")
                    if len(cols) >= 3:
                        name = cols[0].get_text(strip=True)
                        category = cols[1].get_text(strip=True).lower()
                        description = cols[2].get_text(strip=True)
                        
                        # Create item dictionary
                        item = {
                            "name": name,
                            "category": category,
                            "description": description,
                            "production_inputs": []
                        }
                        
                        # Get production inputs for this item
                        inputs = await fetch_production_inputs(session, name)
                        item["production_inputs"] = inputs
                        
                        items.append(item)
    
    return items

async def fetch_production_inputs(session: aiohttp.ClientSession, item_name: str) -> List[Dict]:
    """Fetch production inputs for a specific item."""
    base_url = "https://foxhole.wiki.gg/w/api.php"
    inputs = []
    
    try:
        # Get the item's page content
        params = {
            "action": "parse",
            "page": item_name,
            "format": "json",
            "prop": "text"
        }
        
        async with session.get(base_url, params=params) as response:
            if response.status != 200:
                return inputs
            
            data = await response.json()
            html = data["parse"]["text"]["*"]
            soup = BeautifulSoup(html, "html.parser")
            
            # Find the production section
            production_section = soup.find("h2", string="Production")
            if production_section:
                # Find the recipe table
                recipe_table = production_section.find_next("table", class_="wikitable")
                if recipe_table:
                    # Process each row in the table
                    for row in recipe_table.find_all("tr")[1:]:  # Skip header row
                        cols = row.find_all("td")
                        if len(cols) >= 2:
                            input_name = cols[0].get_text(strip=True)
                            quantity = int(cols[1].get_text(strip=True))
                            inputs.append({
                                "name": input_name,
                                "quantity": quantity
                            })
    
    except Exception as e:
        logger.error(f"Error fetching production inputs for {item_name}: {e}")
    
    return inputs

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
            # Check if item already exists
            result = await session.execute(
                select(Item).where(Item.name == item_data["name"])
            )
            existing_item = result.scalar_one_or_none()
            
            if existing_item:
                # Update existing item
                for key, value in item_data.items():
                    if key != "production_inputs":
                        setattr(existing_item, key, value)
                item = existing_item
            else:
                # Create new item
                item = Item(
                    name=item_data["name"],
                    category=item_data["category"],
                    description=item_data["description"]
                )
                session.add(item)
            
            # Add production inputs
            for input_data in item_data["production_inputs"]:
                # Find the input item
                result = await session.execute(
                    select(Item).where(Item.name == input_data["name"])
                )
                input_item = result.scalar_one_or_none()
                
                if input_item:
                    # Create production input relationship
                    production_input = ItemProductionInput(
                        item=item,
                        input_item=input_item,
                        quantity=input_data["quantity"]
                    )
                    item.production_inputs.append(production_input)
            
            await session.commit()
            
        except Exception as e:
            logger.error(f"Failed to import item {item_data['name']}: {e}")
            await session.rollback()

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