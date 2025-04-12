"""
Script for importing item data from the Foxhole wiki.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple
import aiohttp
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession
import re
import json

from src.database.database_manager import DatabaseManager
from src.models.item import Item, ItemBuildingTarget, ItemProductionInput

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
            content = data["parse"]["text"]["*"]
            
            # Parse the content using BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            
            # Find the items table
            items_table = soup.find('table', {'class': 'wikitable'})
            if not items_table:
                raise Exception("Could not find items table in wiki content")
            
            # Process each row in the table
            for row in items_table.find_all('tr')[1:]:  # Skip header row
                cols = row.find_all(['td', 'th'])
                if len(cols) >= 3:  # Ensure we have enough columns
                    try:
                        # Extract item name and create ID
                        name = cols[0].get_text(strip=True)
                        item_id = name.lower().replace(' ', '_').replace('-', '_')
                        
                        # Extract category
                        category = cols[1].get_text(strip=True)
                        
                        # Extract description
                        description = cols[2].get_text(strip=True)
                        
                        # Extract stack size if available
                        stack_size = None
                        stack_size_match = re.search(r'stack size:?\s*(\d+)', description.lower())
                        if stack_size_match:
                            stack_size = int(stack_size_match.group(1))
                        
                        # Determine if item can be produced and extract production info
                        can_be_produced = False
                        production_facility = None
                        production_inputs = []
                        production_output = 1  # Default output is 1
                        
                        # Check for production information in description
                        if "produced" in description.lower():
                            can_be_produced = True
                            
                            # Try to extract production facility
                            for facility_type, facility_names in PRODUCTION_FACILITIES.items():
                                if any(name.lower() in description.lower() for name in facility_names):
                                    production_facility = facility_type
                                    break
                            
                            # If no specific facility found, use a generic one
                            if not production_facility:
                                production_facility = "Factory"
                            
                            # Try to extract production output quantity
                            output_match = re.search(r'produces (\d+)', description.lower())
                            if output_match:
                                production_output = int(output_match.group(1))
                        
                        # Try to find production inputs in the item's wiki page
                        inputs = await fetch_production_inputs(session, name)
                        if inputs:
                            production_inputs = inputs
                        
                        item_data = {
                            "id": item_id,
                            "name": name,
                            "category": category,
                            "description": description,
                            "stack_size": stack_size,
                            "can_be_produced": can_be_produced,
                            "production_facility": production_facility,
                            "production_inputs": production_inputs,
                            "production_output": production_output
                        }
                        
                        items.append(item_data)
                        logger.info(f"Parsed item: {name}")
                        
                    except Exception as e:
                        logger.error(f"Error parsing row: {str(e)}")
                        continue
    
    return items

async def fetch_production_inputs(session: aiohttp.ClientSession, item_name: str) -> List[Dict[str, int]]:
    """Fetch production inputs for an item from its wiki page."""
    base_url = "https://foxhole.wiki.gg/w/api.php"
    inputs = []
    
    # Get the item's page content
    params = {
        "action": "parse",
        "page": item_name,
        "format": "json",
        "prop": "text"
    }
    
    try:
        async with session.get(base_url, params=params) as response:
            if response.status != 200:
                return []
            
            data = await response.json()
            content = data["parse"]["text"]["*"]
            
            # Parse the content using BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            
            # Look for production recipe table
            recipe_table = soup.find('table', {'class': 'recipe'})
            if recipe_table:
                # Process each input row
                for row in recipe_table.find_all('tr')[1:]:  # Skip header row
                    cols = row.find_all(['td', 'th'])
                    if len(cols) >= 2:
                        input_name = cols[0].get_text(strip=True)
                        input_quantity = 1  # Default quantity
                        
                        # Try to extract quantity if available
                        quantity_match = re.search(r'(\d+)', cols[1].get_text())
                        if quantity_match:
                            input_quantity = int(quantity_match.group(1))
                        
                        inputs.append({
                            "item_name": input_name,
                            "quantity": input_quantity
                        })
    
    except Exception as e:
        logger.error(f"Error fetching production inputs for {item_name}: {str(e)}")
    
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
    # First pass: Create all items without relationships
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
                production_facility=item_data.get("production_facility"),
                stack_size=item_data.get("stack_size"),
                production_output=item_data.get("production_output", 1)
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
    
    # Commit to ensure all items exist before adding relationships
    await session.commit()
    
    # Second pass: Add production input relationships
    for item_data in items_data:
        if not item_data.get("production_inputs"):
            continue
            
        try:
            # Get the item
            item = await session.get(Item, item_data["id"])
            if not item:
                logger.error(f"Item not found: {item_data['id']}")
                continue
                
            # Add production inputs
            for input_data in item_data["production_inputs"]:
                input_item_name = input_data["item_name"]
                input_quantity = input_data["quantity"]
                
                # Find the input item by name
                input_item = await session.query(Item).filter(Item.name == input_item_name).first()
                if not input_item:
                    logger.warning(f"Input item not found: {input_item_name}")
                    continue
                
                # Create the production input relationship
                production_input = ItemProductionInput(
                    item_id=item.id,
                    input_item_id=input_item.id,
                    quantity=input_quantity
                )
                item.production_inputs.append(production_input)
                
            logger.info(f"Added production inputs for: {item.name}")
            
        except Exception as e:
            logger.error(f"Failed to add production inputs for {item_data.get('name', 'unknown')}: {str(e)}")
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