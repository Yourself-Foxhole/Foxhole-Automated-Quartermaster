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
- **Google Sheets Backend**: Optional persistent storage using st-gsheets-connection
- **OAuth Authentication**: Secure access to private Google Sheets
- Ready for future integration with War API data

### Data Pipeline
- Mock OCR processing demonstrates screenshot parsing workflow
- **Persistent Storage**: Automatic sync with Google Sheets for data persistence
- **Analytics Logging**: Track user interactions and system metrics
- Placeholder for future integration with Foxhole Inventory Report libraries

## Technical Implementation

### Dependencies
- **Streamlit**: Web application framework
- **Plotly**: Interactive graph visualization
- **NetworkX**: Graph data structure and algorithms
- **Pandas**: Data manipulation for analytics
- **st-gsheets-connection**: Google Sheets integration for persistent storage

### Data Models
Located in `presentation/streamlit/data_models.py`:
- `Item`: Represents Foxhole items with type categorization
- `Location`: Facility locations with inventory management
- `InventoryState`: Tracks item quantities and capacity utilization
- Sample data with realistic Foxhole game content

### Google Sheets Integration
Located in `presentation/streamlit/`:
- `gsheets_backend.py`: Data backend using Google Sheets for persistence
- `gsheets_config.py`: Configuration management for Google Sheets credentials
- `gsheets_ui.py`: UI components for connection status and data management

### Key Files
- `streamlit_app.py`: Main application entry point with Google Sheets integration
- `data_models.py`: Data structures and sample game data
- `test_streamlit_app.py`: Comprehensive test suite
- `test_gsheets_integration.py`: Google Sheets integration tests

## Repository Standards Compliance

- **No f-strings**: Uses `.format()` for string formatting as required
- **Print parameters**: Follows repository print statement guidelines
- **Code quality**: Tested with comprehensive unit tests
- **Architecture**: Follows documented 4-layer design
- **Real game data**: Uses authentic Foxhole item and location names

## Usage

### Google Sheets Setup (Optional)

For persistent data storage, configure Google Sheets integration:

#### 1. Google Cloud Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the following APIs:
   - Google Sheets API
   - Google Drive API

#### 2. Service Account Setup
1. Go to "APIs & Services > Credentials"
2. Click "Create credentials > Service account key"
3. Fill out the form and create the account
4. Download the JSON key file

#### 3. Spreadsheet Setup
1. Create a new Google Sheet or use existing one
2. Share it with the service account email (from JSON file)
3. Give "Editor" permissions
4. Copy the spreadsheet URL

#### 4. Configuration
1. Copy the secrets template:
   ```bash
   cp presentation/streamlit/.streamlit/secrets.toml.example presentation/streamlit/.streamlit/secrets.toml
   ```
2. Edit `presentation/streamlit/.streamlit/secrets.toml` with your values:
   - Replace `YOUR_SPREADSHEET_ID` with your spreadsheet ID from the URL
   - Copy service account values from your downloaded JSON file
   - **Important**: Never commit secrets.toml to git!

### Running the Application
```bash
cd presentation/streamlit
pip install -r ../../requirements.txt
streamlit run streamlit_app.py
```

The app will automatically:
- Connect to Google Sheets if configured
- Fall back to local data if not configured  
- Initialize required worksheets on first run
- Provide sync controls in the sidebar

### Running Tests
```bash
# Test the Streamlit app
python -m unittest tests.test_streamlit_app -v

# Test Google Sheets integration
python -m unittest tests.test_gsheets_integration -v

# Run all tests
python -m pytest tests/ -v
```

### Google Sheets Features

#### Connection Status
- Real-time connection status in sidebar
- Connection test functionality  
- Automatic initialization of required worksheets

#### Data Sync
- **Manual Sync**: Save/Load buttons in sidebar
- **Auto-sync**: Optional automatic saving of changes
- **Startup Load**: Automatically load data on app start
- **Analytics**: Track usage and sync patterns

#### Error Handling
- Graceful fallback to local data if connection fails
- Clear error messages for configuration issues
- Detailed connection status and diagnostics

## Future Enhancements

1. **Real OCR Integration**: Replace mock parsing with actual Foxhole Inventory Report processing
2. **War API Integration**: Pull real-time game data from Foxhole War API  
3. **Advanced Analytics**: Enhanced dashboards with trend analysis and predictions
4. **Task Generation**: Integrate with existing graph processing and priority algorithms
5. **User Authentication**: Add user management and role-based access
6. **Real-time Updates**: WebSocket integration for live data updates
7. **Mobile Optimization**: Responsive design for mobile logistics management
8. **Multi-Sheet Support**: Support for multiple Google Sheets per user/clan

## Google Sheets Data Schema

The integration creates the following worksheets:

### Inventory Sheet
| Column | Description |
|--------|-------------|
| location_name | Facility location name |
| item_name | Foxhole item name |
| item_type | Item category (material, ammunition, etc.) |
| quantity | Current inventory quantity |
| capacity | Storage capacity |
| last_updated | Timestamp of last update |

### Tasks Sheet  
| Column | Description |
|--------|-------------|
| task_id | Unique task identifier |
| name | Task description |
| task_type | Type (transportation, production, supply) |
| priority | Priority level (high, medium, low) |
| status | Current status (pending, in_progress, completed) |
| created_at | Task creation timestamp |
| updated_at | Last modification timestamp |
| assigned_to | User assigned to task |
| description | Detailed task description |

### Locations Sheet
| Column | Description |
|--------|-------------|
| name | Location name |
| region | Foxhole region |
| facility_type | Type of facility |
| position_x | X coordinate |
| position_y | Y coordinate |

### Analytics Sheet
| Column | Description |
|--------|-------------|
| metric_name | Name of the metric |
| metric_value | Metric value |
| timestamp | When the metric was recorded |
| metadata | Additional context (JSON) |

## Mock Data

The prototype includes realistic sample data:
- **8 locations** across different Foxhole regions
- **29 Foxhole items** with proper categorization
- **10 transport routes** between facilities
- **5 sample tasks** demonstrating different task types
- **Inventory states** with realistic capacity and quantity data

This provides a comprehensive demonstration of the system's capabilities while remaining true to the Foxhole game environment.