# Streamlit Logistics Prototype

## Overview

The Streamlit logistics prototype provides an interactive web interface for the Foxhole Automated Quartermaster system. It demonstrates core functionality through a user-friendly dashboard that allows users to visualize the logistics network, manage tasks, and upload inventory reports.

## Features

### 🗺️ Logistics Network Visualization
- Interactive network graph using Plotly showing facilities and transport routes
- Real Foxhole location names and regions (Deadlands, Heartlands, Basin Sionnach, etc.)
- Color-coded facility types (Factory, Refinery, Seaport, Storage Depot, etc.)
- Node size based on inventory levels
- Click-to-select locations for detailed information
- Real-time inventory status with capacity utilization

### 📋 Task Management System
- Integration with existing Task/TaskStatus classes from services/tasks/
- Task filtering by type (transportation, production, supply) and status
- Priority-based task sorting with visual indicators
- Task claiming and completion workflow
- Real-time task statistics dashboard

### 📸 Inventory Upload & OCR
- File upload interface for Foxhole Inventory Report screenshots
- Mock OCR parsing with realistic results
- Automatic inventory update workflow
- Support for multiple file formats (PNG, JPG, JPEG)

### 📈 Analytics Dashboard
- Facility type distribution charts
- Item type inventory analysis
- Low stock alerts and metrics
- Capacity utilization tracking

## Architecture Integration

The Streamlit prototype follows the 4-layer architecture defined in `docs/architecture.md`:

### Presentation Layer (This Implementation)
- Streamlit web interface (`streamlit_app.py`)
- User interaction handling
- Data visualization components

### Service Layer Integration
- Uses existing `services/tasks/task.py` for task management
- Fallback implementation for prototype operation
- Graph processing with NetworkX

### Data Layer Integration
- Designed to work with `data/db/db.py` database models
- Sample data structures compatible with existing schema
- Ready for future integration with War API data

### Data Pipeline (Future Enhancement)
- Mock OCR processing demonstrates screenshot parsing workflow
- Placeholder for future integration with Foxhole Inventory Report libraries

## Technical Implementation

### Dependencies
- **Streamlit**: Web application framework
- **Plotly**: Interactive graph visualization
- **NetworkX**: Graph data structure and algorithms
- **Pandas**: Data manipulation for analytics

### Data Models
Located in `presentation/streamlit/data_models.py`:
- `Item`: Represents Foxhole items with type categorization
- `Location`: Facility locations with inventory management
- `InventoryState`: Tracks item quantities and capacity utilization
- Sample data with realistic Foxhole game content

### Key Files
- `streamlit_app.py`: Main application entry point
- `data_models.py`: Data structures and sample game data
- `test_streamlit_app.py`: Comprehensive test suite

## Repository Standards Compliance

- **No f-strings**: Uses `.format()` for string formatting as required
- **Print parameters**: Follows repository print statement guidelines
- **Code quality**: Tested with comprehensive unit tests
- **Architecture**: Follows documented 4-layer design
- **Real game data**: Uses authentic Foxhole item and location names

## Usage

### Running the Application
```bash
cd presentation/streamlit
streamlit run streamlit_app.py
```

### Running Tests
```bash
python -m unittest tests.test_streamlit_app -v
```

## Future Enhancements

1. **Real OCR Integration**: Replace mock parsing with actual Foxhole Inventory Report processing
2. **Database Integration**: Connect to persistent storage using existing db.py models
3. **War API Integration**: Pull real-time game data from Foxhole War API
4. **Task Generation**: Integrate with existing graph processing and priority algorithms
5. **User Authentication**: Add user management and role-based access
6. **Real-time Updates**: WebSocket integration for live data updates

## Mock Data

The prototype includes realistic sample data:
- **8 locations** across different Foxhole regions
- **29 Foxhole items** with proper categorization
- **10 transport routes** between facilities
- **5 sample tasks** demonstrating different task types
- **Inventory states** with realistic capacity and quantity data

This provides a comprehensive demonstration of the system's capabilities while remaining true to the Foxhole game environment.