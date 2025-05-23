"""
Test suite for the wiki parsing functionality.
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from bs4 import BeautifulSoup
import json

from src.database.models import Item, ItemBuildingTarget, ItemProductionInput
from src.scripts.import_wiki_items import (
    fetch_wiki_data,
    fetch_production_inputs,
    determine_importance,
    get_building_targets,
    import_items,
    main,
    PRODUCTION_FACILITIES
)

# Sample HTML content for testing
SAMPLE_ITEMS_HTML = """
<table class="wikitable">
    <tr>
        <th>Name</th>
        <th>Category</th>
        <th>Description</th>
    </tr>
    <tr>
        <td>7.62mm</td>
        <td>Ammunition</td>
        <td>Standard rifle ammunition</td>
    </tr>
    <tr>
        <td>Bandages</td>
        <td>Medical</td>
        <td>Basic medical supplies</td>
    </tr>
    <tr>
        <td>Diesel</td>
        <td>Supply</td>
        <td>Fuel for vehicles</td>
    </tr>
    <tr>
        <td>Rifle</td>
        <td>Weapon</td>
        <td>Standard infantry weapon</td>
    </tr>
    <tr>
        <td>Shovel</td>
        <td>Tool</td>
        <td>Used for building</td>
    </tr>
</table>
"""

SAMPLE_ITEM_PAGE_HTML = """
<div class="mw-parser-output">
    <h2>Production</h2>
    <table class="wikitable">
        <tr>
            <th>Input</th>
            <th>Quantity</th>
        </tr>
        <tr>
            <td>Iron</td>
            <td>2</td>
        </tr>
        <tr>
            <td>Coal</td>
            <td>1</td>
        </tr>
    </table>
</div>
"""

# Sample items data for testing
SAMPLE_ITEMS_DATA = [
    {
        "name": "7.62mm",
        "category": "ammunition",
        "description": "Standard rifle ammunition",
        "production_inputs": []
    },
    {
        "name": "Bandages",
        "category": "medical",
        "description": "Basic medical supplies",
        "production_inputs": []
    },
    {
        "name": "Diesel",
        "category": "supply",
        "description": "Fuel for vehicles",
        "production_inputs": []
    },
    {
        "name": "Rifle",
        "category": "weapon",
        "description": "Standard infantry weapon",
        "production_inputs": []
    },
    {
        "name": "Shovel",
        "category": "tool",
        "description": "Used for building",
        "production_inputs": []
    }
]

# Sample items data with production inputs
SAMPLE_ITEMS_DATA_WITH_INPUTS = [
    {
        "name": "Rifle",
        "category": "weapon",
        "description": "Standard infantry weapon",
        "production_inputs": [
            {
                "name": "Iron",
                "quantity": 2
            }
        ]
    }
]

@pytest.mark.asyncio
async def test_fetch_wiki_data():
    """Test fetching and parsing wiki data."""
    # Mock the API response
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={
        "parse": {
            "text": {
                "*": SAMPLE_ITEMS_HTML
            }
        }
    })
    
    # Mock the session and its get method
    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=mock_response)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()
    
    # Mock aiohttp.ClientSession
    with patch('aiohttp.ClientSession', return_value=mock_session):
        # Mock the fetch_production_inputs function
        with patch('src.scripts.import_wiki_items.fetch_production_inputs', new_callable=AsyncMock) as mock_fetch_inputs:
            mock_fetch_inputs.return_value = []
            
            # Call the function
            items = await fetch_wiki_data()
            
            # Verify the results
            assert len(items) == 5
            
            # Check the first item (7.62mm)
            ammo = next(item for item in items if item["name"] == "7.62mm")
            assert ammo["name"] == "7.62mm"
            assert ammo["category"] == "ammunition"
            assert "Standard rifle ammunition" in ammo["description"]
            
            # Check the last item (Shovel)
            shovel = next(item for item in items if item["name"] == "Shovel")
            assert shovel["name"] == "Shovel"
            assert shovel["category"] == "tool"
            assert "Used for building" in shovel["description"]

@pytest.mark.asyncio
async def test_fetch_production_inputs():
    """Test fetching production inputs for an item."""
    # Mock the API response
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={
        "parse": {
            "text": {
                "*": SAMPLE_ITEM_PAGE_HTML
            }
        }
    })
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock()
    
    # Mock the session and its get method
    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=mock_response)
    
    # Call the function
    inputs = await fetch_production_inputs(mock_session, "Test Item")
    
    # Verify the results
    assert len(inputs) == 2
    
    # Check the first input
    assert inputs[0]["name"] == "Iron"
    assert inputs[0]["quantity"] == 2
    
    # Check the second input
    assert inputs[1]["name"] == "Coal"
    assert inputs[1]["quantity"] == 1

@pytest.mark.asyncio
async def test_fetch_production_inputs_no_recipe():
    """Test fetching production inputs when no recipe table exists."""
    # Mock the API response with HTML that doesn't contain a recipe table
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={
        "parse": {
            "text": {
                "*": "<div class='mw-parser-output'></div>"
            }
        }
    })
    
    # Mock the session and its get method
    mock_session = MagicMock()
    mock_session.get = AsyncMock(return_value=mock_response)
    
    # Call the function
    inputs = await fetch_production_inputs(mock_session, "Test Item")
    
    # Verify the results
    assert len(inputs) == 0

@pytest.mark.asyncio
async def test_fetch_production_inputs_api_error():
    """Test fetching production inputs when the API returns an error."""
    # Mock the API response with an error
    mock_response = MagicMock()
    mock_response.status = 404
    
    # Mock the session and its get method
    mock_session = MagicMock()
    mock_session.get = AsyncMock(return_value=mock_response)
    
    # Call the function
    inputs = await fetch_production_inputs(mock_session, "Test Item")
    
    # Verify the results
    assert len(inputs) == 0

def test_determine_importance():
    """Test determining item importance based on category and name."""
    # Test with default category importance
    assert determine_importance("Ammunition", "7.62mm") == 5
    assert determine_importance("Medical", "Bandages") == 5
    assert determine_importance("Fuel", "Diesel") == 4
    assert determine_importance("Heavy Arms", "Rifle") == 4
    assert determine_importance("Supplies", "Rations") == 3
    assert determine_importance("Tools", "Shovel") == 3
    assert determine_importance("Materials", "Iron") == 2
    assert determine_importance("Miscellaneous", "Map") == 1
    
    # Test with importance adjustment based on name
    assert determine_importance("Ammunition", "Critical Ammunition") == 5  # Already at max
    assert determine_importance("Medical", "Essential Medical Supply") == 5  # Already at max
    assert determine_importance("Fuel", "Vital Fuel") == 5  # Increased from 4
    assert determine_importance("Supplies", "Optional Supply") == 2  # Decreased from 3
    assert determine_importance("Tools", "Luxury Tool") == 2  # Decreased from 3

def test_get_building_targets():
    """Test getting building targets for an item category."""
    # Test with known categories
    ammo_targets = get_building_targets("Ammunition")
    assert ammo_targets["Bunker"] == 1000
    assert ammo_targets["Safehouse"] == 500
    assert ammo_targets["Stockpile"] == 2000
    
    medical_targets = get_building_targets("Medical")
    assert medical_targets["Bunker"] == 500
    assert medical_targets["Safehouse"] == 200
    assert medical_targets["Stockpile"] == 1000
    
    # Test with unknown category
    unknown_targets = get_building_targets("Unknown")
    assert unknown_targets["Bunker"] == 100
    assert unknown_targets["Safehouse"] == 50
    assert unknown_targets["Stockpile"] == 200

def test_production_facility_mapping():
    """Test the production facility mapping."""
    # Test each facility type
    for facility_type, facility_names in PRODUCTION_FACILITIES.items():
        for name in facility_names:
            assert facility_type in PRODUCTION_FACILITIES
            assert name in PRODUCTION_FACILITIES[facility_type]
    
    # Test that all facility types are covered
    assert "Factory" in PRODUCTION_FACILITIES
    assert "Refinery" in PRODUCTION_FACILITIES
    assert "Workshop" in PRODUCTION_FACILITIES
    assert "Garrison" in PRODUCTION_FACILITIES
    assert "Hospital" in PRODUCTION_FACILITIES
    assert "Other" in PRODUCTION_FACILITIES

@pytest.mark.asyncio
async def test_import_items():
    """Test importing items into the database."""
    # Create a mock session
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.execute.return_value.scalar_one_or_none = AsyncMock(return_value=None)
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    
    # Call the function
    await import_items(mock_session, SAMPLE_ITEMS_DATA)
    
    # Verify that execute was called for each item
    assert mock_session.execute.call_count == len(SAMPLE_ITEMS_DATA)
    
    # Verify that commit was called for each item
    assert mock_session.commit.call_count == len(SAMPLE_ITEMS_DATA)

@pytest.mark.asyncio
async def test_import_items_with_production_inputs():
    """Test importing items with production inputs into the database."""
    # Create a mock session
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.execute.return_value.scalar_one_or_none = AsyncMock(return_value=None)
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    
    # Call the function
    await import_items(mock_session, SAMPLE_ITEMS_DATA_WITH_INPUTS)
    
    # Verify that execute was called for each item
    assert mock_session.execute.call_count == 2  # Once for the item, once for the input item
    
    # Verify that commit was called
    assert mock_session.commit.call_count == 1

@pytest.mark.asyncio
async def test_main():
    """Test the main function that orchestrates the entire import process."""
    # Mock the DatabaseManager
    mock_db_manager = MagicMock()
    mock_db_manager.initialize = AsyncMock()
    mock_db_manager.get_session = MagicMock()
    mock_db_manager.close = AsyncMock()
    
    # Create a mock session
    mock_session = MagicMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()
    mock_db_manager.get_session.return_value = mock_session
    
    # Mock the fetch_wiki_data function
    with patch('src.scripts.import_wiki_items.fetch_wiki_data', new_callable=AsyncMock) as mock_fetch_data:
        mock_fetch_data.return_value = SAMPLE_ITEMS_DATA
        
        # Mock the import_items function
        with patch('src.scripts.import_wiki_items.import_items', new_callable=AsyncMock) as mock_import:
            # Mock the DatabaseManager constructor
            with patch('src.scripts.import_wiki_items.DatabaseManager', return_value=mock_db_manager):
                # Call the main function
                await main()
                
                # Verify that the database was initialized
                mock_db_manager.initialize.assert_called_once()
                
                # Verify that wiki data was fetched
                mock_fetch_data.assert_called_once()
                
                # Verify that items were imported
                mock_import.assert_called_once_with(mock_session, SAMPLE_ITEMS_DATA)
                
                # Verify that the database was closed
                mock_db_manager.close.assert_called_once() 