"""
Streamlit prototype for Foxhole Automated Quartermaster.

This prototype provides an interactive logistics graph visualization and task management
interface for the Foxhole logistics system. It demonstrates core functionality including:
- Interactive logistics network graph
- Inventory upload and parsing (mock)
- Task management interface
- Real-time inventory tracking
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import networkx as nx
import pandas as pd
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import io
import random

# Import our data models
from data_models import (
    SAMPLE_LOCATIONS, LOGISTICS_GRAPH, FOXHOLE_ITEMS, FOXHOLE_REGIONS,
    Item, Location, InventoryState, ItemType, FacilityType
)

# Import existing task system components
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from services.tasks.task import Task, TaskStatus
    from data.db.db import setup as setup_db, initialize_db
except ImportError:
    # Fallback for prototype if imports fail
    from enum import Enum
    from dataclasses import dataclass, field
    
    class TaskStatus(Enum):
        PENDING = "pending"
        IN_PROGRESS = "in_progress" 
        COMPLETED = "completed"
        CANCELLED = "cancelled"
    
    @dataclass
    class Task:
        task_id: str
        name: str
        task_type: str
        status: TaskStatus = TaskStatus.PENDING
        base_priority: float = 1.0
        created_at: datetime = field(default_factory=datetime.now)
        metadata: Dict[str, Any] = field(default_factory=dict)


# Initialize Streamlit page config
st.set_page_config(
    page_title="Foxhole Automated Quartermaster",
    page_icon="🦊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
        margin: 5px 0;
    }
    .low-stock {
        background-color: #ffebee;
        border-left: 4px solid #f44336;
    }
    .high-stock {
        background-color: #e8f5e8;
        border-left: 4px solid #4caf50;
    }
    .normal-stock {
        background-color: #f0f2f6;
        border-left: 4px solid #2196f3;
    }
    .task-priority-high {
        background-color: #ffebee;
        border-left: 4px solid #f44336;
    }
    .task-priority-medium {
        background-color: #fff3e0;
        border-left: 4px solid #ff9800;
    }
    .task-priority-low {
        background-color: #e8f5e8;
        border-left: 4px solid #4caf50;
    }
</style>
""", unsafe_allow_html=True)


def initialize_session_state():
    """Initialize session state variables."""
    if 'locations' not in st.session_state:
        st.session_state.locations = SAMPLE_LOCATIONS.copy()
    if 'logistics_graph' not in st.session_state:
        st.session_state.logistics_graph = LOGISTICS_GRAPH.copy()
    if 'tasks' not in st.session_state:
        st.session_state.tasks = generate_sample_tasks()
    if 'selected_location' not in st.session_state:
        st.session_state.selected_location = None


def generate_sample_tasks() -> List[Task]:
    """Generate sample tasks for the prototype."""
    tasks = []
    
    # Transportation tasks
    tasks.append(Task(
        task_id="TRANS_001",
        name="Transport Basic Materials to Great March Base", 
        task_type="transportation",
        status=TaskStatus.PENDING,
        base_priority=0.8,
        metadata={
            "from_location": "Deadlands Factory",
            "to_location": "Great March Base", 
            "item": "Basic Materials",
            "quantity": 200,
            "urgency": "high"
        }
    ))
    
    tasks.append(Task(
        task_id="TRANS_002",
        name="Move Rifle Ammo to Basin Sionnach Depot",
        task_type="transportation", 
        status=TaskStatus.PENDING,
        base_priority=0.6,
        metadata={
            "from_location": "Deadlands Factory",
            "to_location": "Basin Sionnach Depot",
            "item": "Rifle Ammo", 
            "quantity": 500,
            "urgency": "medium"
        }
    ))
    
    # Production tasks  
    tasks.append(Task(
        task_id="PROD_001",
        name="Produce Refined Materials at Heartlands Refinery",
        task_type="production",
        status=TaskStatus.IN_PROGRESS,
        base_priority=0.9,
        metadata={
            "location": "Heartlands Refinery",
            "item": "Refined Materials", 
            "quantity": 400,
            "estimated_completion": datetime.now() + timedelta(hours=2),
            "urgency": "high"
        }
    ))
    
    tasks.append(Task(
        task_id="PROD_002", 
        name="Manufacture 40mm Rounds at Factory",
        task_type="production",
        status=TaskStatus.PENDING,
        base_priority=0.7,
        metadata={
            "location": "Deadlands Factory",
            "item": "40mm Rounds",
            "quantity": 300,
            "required_materials": {"Refined Materials": 150, "Heavy Explosive Materials": 50},
            "urgency": "medium"
        }
    ))
    
    # Supply tasks
    tasks.append(Task(
        task_id="SUPPLY_001",
        name="Resupply Medical Kits to Field Units", 
        task_type="supply",
        status=TaskStatus.PENDING,
        base_priority=0.85,
        metadata={
            "location": "Basin Sionnach Depot",
            "item": "Medic Kit",
            "quantity": 100,
            "destination": "frontline",
            "urgency": "high"
        }
    ))
    
    return tasks


def create_logistics_graph_plot(graph: nx.DiGraph, selected_node: Optional[str] = None) -> go.Figure:
    """Create an interactive plotly graph visualization."""
    # Get node positions
    pos = {}
    for node in graph.nodes():
        node_data = graph.nodes[node]
        pos[node] = node_data.get('position', (0, 0))
    
    # Create edge traces
    edge_x = []
    edge_y = []
    edge_info = []
    
    for edge in graph.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
        
        edge_data = graph.edges[edge]
        distance = edge_data.get('distance', 0)
        edge_info.append("{} → {}<br>Distance: {}".format(edge[0], edge[1], distance))
    
    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=2, color='#888'),
        hoverinfo='none',
        mode='lines'
    )
    
    # Create node traces
    node_x = []
    node_y = []
    node_text = []
    node_info = []
    node_colors = []
    node_sizes = []
    
    facility_color_map = {
        'factory': '#ff6b6b',
        'refinery': '#4ecdc4', 
        'seaport': '#45b7d1',
        'storage_depot': '#96ceb4',
        'bunker_base': '#feca57',
        'town_hall': '#ff9ff3',
        'vehicle_factory': '#fd79a8',
        'shipyard': '#74b9ff'
    }
    
    for node in graph.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        
        node_data = graph.nodes[node]
        facility_type = node_data.get('facility_type', 'unknown')
        region = node_data.get('region', 'Unknown')
        location = node_data.get('location')
        
        # Get inventory summary for hover info
        inventory_summary = ""
        if location and hasattr(location, 'inventory'):
            total_items = len(location.inventory)
            low_stock_items = sum(1 for inv in location.inventory.values() if inv.is_low_stock)
            inventory_summary = "<br>Total Items: {}<br>Low Stock: {}".format(total_items, low_stock_items)
        
        node_text.append(node)
        node_info.append("<b>{}</b><br>Region: {}<br>Type: {}{}".format(
            node, region, facility_type.replace('_', ' ').title(), inventory_summary))
        
        # Color based on facility type
        color = facility_color_map.get(facility_type, '#ddd')
        if node == selected_node:
            color = '#2d3748'  # Highlight selected node
        node_colors.append(color)
        
        # Size based on inventory level or importance
        size = 20
        if location and hasattr(location, 'inventory'):
            total_inventory = sum(inv.quantity for inv in location.inventory.values())
            size = max(15, min(30, 15 + total_inventory / 200))
        node_sizes.append(size)
    
    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        hoverinfo='text',
        text=node_text,
        textposition="middle center",
        hovertext=node_info,
        marker=dict(
            size=node_sizes,
            color=node_colors,
            line=dict(width=2, color='white')
        )
    )
    
    # Create the figure
    fig = go.Figure(data=[edge_trace, node_trace],
                   layout=go.Layout(
                       title="Foxhole Logistics Network",
                       titlefont_size=16,
                       showlegend=False,
                       hovermode='closest',
                       margin=dict(b=20,l=5,r=5,t=40),
                       annotations=[ dict(
                           text="Click on nodes to view detailed inventory",
                           showarrow=False,
                           xref="paper", yref="paper",
                           x=0.005, y=-0.002,
                           xanchor='left', yanchor='bottom',
                           font=dict(color="#888", size=12)
                       )],
                       xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                       yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                       plot_bgcolor='white'
                   ))
    
    return fig


def display_location_details(location: Location):
    """Display detailed information about a selected location."""
    st.subheader("📍 {}".format(location.name))
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.write("**Region:** {}".format(location.region))
        st.write("**Facility Type:** {}".format(location.facility_type.value.replace('_', ' ').title()))
        st.write("**Position:** ({}, {})".format(location.position[0], location.position[1]))
        
    with col2:
        total_items = len(location.inventory)
        total_capacity = sum(inv.capacity for inv in location.inventory.values())
        total_quantity = sum(inv.quantity for inv in location.inventory.values())
        
        st.metric("Total Item Types", total_items)
        st.metric("Total Capacity", "{:,}".format(total_capacity))
        st.metric("Current Stock", "{:,}".format(total_quantity))
    
    # Inventory details
    if location.inventory:
        st.subheader("📦 Inventory Status")
        
        # Create inventory dataframe
        inventory_data = []
        for item_name, inv_state in location.inventory.items():
            inventory_data.append({
                'Item': item_name,
                'Quantity': inv_state.quantity,
                'Capacity': inv_state.capacity,
                'Utilization': "{:.1%}".format(inv_state.capacity_ratio),
                'Status': 'Low Stock' if inv_state.is_low_stock else 'High Stock' if inv_state.is_high_stock else 'Normal'
            })
        
        df = pd.DataFrame(inventory_data)
        
        # Color code the dataframe
        def color_status(val):
            if val == 'Low Stock':
                return 'background-color: #ffebee; color: #c62828'
            elif val == 'High Stock':
                return 'background-color: #e8f5e8; color: #2e7d32'
            else:
                return 'background-color: #f0f2f6; color: #1565c0'
        
        styled_df = df.style.map(color_status, subset=['Status'])
        st.dataframe(styled_df, use_container_width=True)
        
        # Quick actions
        st.subheader("⚡ Quick Actions")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📊 Generate Resupply Tasks"):
                st.success("Resupply tasks generated for low stock items!")
        
        with col2:
            if st.button("🚛 Plan Transportation"):
                st.info("Transportation planning interface would open here")
        
        with col3:
            if st.button("📈 View Trends"):
                st.info("Historical inventory trends would be displayed")


def display_task_management():
    """Display the task management interface."""
    st.header("📋 Task Management")
    
    tasks = st.session_state.get('tasks', [])
    
    # Task statistics
    col1, col2, col3, col4 = st.columns(4)
    
    pending_tasks = [t for t in tasks if t.status == TaskStatus.PENDING]
    in_progress_tasks = [t for t in tasks if t.status == TaskStatus.IN_PROGRESS]
    completed_tasks = [t for t in tasks if t.status == TaskStatus.COMPLETED]
    
    with col1:
        st.metric("Pending Tasks", len(pending_tasks))
    with col2:
        st.metric("In Progress", len(in_progress_tasks))
    with col3:
        st.metric("Completed", len(completed_tasks))
    with col4:
        high_priority = [t for t in tasks if t.base_priority > 0.8]
        st.metric("High Priority", len(high_priority))
    
    # Filter options
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        task_type_filter = st.selectbox(
            "Filter by Type",
            ["All", "transportation", "production", "supply"]
        )
    
    with col2:
        status_filter = st.selectbox(
            "Filter by Status", 
            ["All", "pending", "in_progress", "completed"]
        )
    
    with col3:
        priority_threshold = st.slider(
            "Minimum Priority",
            min_value=0.0,
            max_value=1.0,
            value=0.0,
            step=0.1
        )
    
    # Filter tasks
    filtered_tasks = tasks
    if task_type_filter != "All":
        filtered_tasks = [t for t in filtered_tasks if t.task_type == task_type_filter]
    if status_filter != "All":
        filtered_tasks = [t for t in filtered_tasks if t.status.value == status_filter]
    filtered_tasks = [t for t in filtered_tasks if t.base_priority >= priority_threshold]
    
    # Sort by priority
    filtered_tasks.sort(key=lambda x: x.base_priority, reverse=True)
    
    # Display tasks
    st.subheader("Tasks ({} shown)".format(len(filtered_tasks)))
    
    for task in filtered_tasks:
        # Determine priority level for styling
        if task.base_priority > 0.8:
            priority_class = "task-priority-high"
            priority_label = "🔴 High"
        elif task.base_priority > 0.6:
            priority_class = "task-priority-medium" 
            priority_label = "🟡 Medium"
        else:
            priority_class = "task-priority-low"
            priority_label = "🟢 Low"
        
        with st.container():
            st.markdown('<div class="metric-card {}">'.format(priority_class), unsafe_allow_html=True)
            
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            
            with col1:
                st.write("**{}**".format(task.name))
                st.write("Type: {}".format(task.task_type.title()))
                
                # Display metadata
                if task.metadata:
                    metadata_str = ""
                    for key, value in task.metadata.items():
                        if key in ['item', 'quantity', 'from_location', 'to_location', 'location']:
                            metadata_str += "{}: {} | ".format(key.replace('_', ' ').title(), value)
                    if metadata_str:
                        st.write("Details: {}".format(metadata_str.rstrip(' | ')))
            
            with col2:
                st.write("**Priority:** {}".format(priority_label))
                st.write("**Status:** {}".format(task.status.value.title()))
            
            with col3:
                st.write("**Created:** {}".format(task.created_at.strftime('%m/%d %H:%M')))
                if 'estimated_completion' in task.metadata:
                    eta = task.metadata['estimated_completion']
                    st.write("**ETA:** {}".format(eta.strftime('%m/%d %H:%M')))
            
            with col4:
                if task.status == TaskStatus.PENDING:
                    if st.button("Claim", key="claim_{}".format(task.task_id)):
                        task.status = TaskStatus.IN_PROGRESS
                        st.rerun()
                elif task.status == TaskStatus.IN_PROGRESS:
                    if st.button("Complete", key="complete_{}".format(task.task_id)):
                        task.status = TaskStatus.COMPLETED
                        st.rerun()
                else:
                    st.write("✅ Done")
            
            st.markdown('</div>', unsafe_allow_html=True)


def display_inventory_upload():
    """Display the inventory upload and parsing interface."""
    st.header("📸 Inventory Upload")
    
    st.write("""
    Upload Foxhole Inventory Report screenshots to automatically update inventory levels.
    The system will parse the screenshots and extract item quantities.
    """)
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Choose screenshot file(s)",
        type=['png', 'jpg', 'jpeg'],
        accept_multiple_files=True
    )
    
    if uploaded_file:
        st.subheader("📊 Processing Results")
        
        for i, file in enumerate(uploaded_file):
            with st.expander("Processing {}".format(file.name), expanded=True):
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    st.image(file, caption="Uploaded: {}".format(file.name), width=300)
                
                with col2:
                    # Mock OCR parsing results
                    st.write("**Mock OCR Parsing Results:**")
                    
                    # Generate mock parsed data
                    mock_results = generate_mock_ocr_results()
                    
                    st.write("Detected Location:", mock_results['location'])
                    st.write("Detected Items:")
                    
                    for item, quantity in mock_results['items'].items():
                        st.write("- {}: {}".format(item, quantity))
                    
                    # Apply to inventory button
                    if st.button("Apply to Inventory", key="apply_{}".format(i)):
                        # Find the location and update inventory
                        location_name = mock_results['location']
                        location = next((loc for loc in st.session_state.locations if loc.name == location_name), None)
                        
                        if location:
                            for item_name, quantity in mock_results['items'].items():
                                # Find the item
                                item = next((item for item in FOXHOLE_ITEMS if item.name == item_name), None)
                                if item:
                                    location.add_inventory(item, quantity)
                            
                            st.success("Inventory updated for {}!".format(location_name))
                            st.rerun()
                        else:
                            st.error("Location {} not found!".format(location_name))


def generate_mock_ocr_results() -> Dict[str, Any]:
    """Generate mock OCR parsing results for demonstration."""
    # Use session state locations if available, otherwise use sample locations
    try:
        locations = [loc.name for loc in st.session_state.locations]
    except (AttributeError, KeyError):
        # Fallback for testing or when running outside streamlit context
        locations = [loc.name for loc in SAMPLE_LOCATIONS]
    
    selected_location = random.choice(locations)
    
    # Generate random items and quantities
    available_items = [item.name for item in FOXHOLE_ITEMS]
    num_items = random.randint(3, 8)
    selected_items = random.sample(available_items, num_items)
    
    items = {}
    for item in selected_items:
        items[item] = random.randint(50, 950)
    
    return {
        'location': selected_location,
        'items': items,
        'confidence': random.uniform(0.85, 0.98)
    }


def display_analytics():
    """Display analytics and metrics dashboard."""
    st.header("📈 Analytics Dashboard")
    
    # Summary metrics
    locations = st.session_state.locations
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_locations = len(locations)
        st.metric("Total Locations", total_locations)
    
    with col2:
        total_items = sum(len(loc.inventory) for loc in locations)
        st.metric("Total Item Types", total_items)
    
    with col3:
        low_stock_count = sum(
            sum(1 for inv in loc.inventory.values() if inv.is_low_stock)
            for loc in locations
        )
        st.metric("Low Stock Alerts", low_stock_count, delta=-3, delta_color="inverse")
    
    with col4:
        total_capacity = sum(
            sum(inv.capacity for inv in loc.inventory.values())
            for loc in locations
        )
        st.metric("Total Capacity", "{:,}".format(total_capacity))
    
    # Inventory by facility type
    st.subheader("📊 Inventory by Facility Type")
    
    facility_data = {}
    for location in locations:
        facility_type = location.facility_type.value
        if facility_type not in facility_data:
            facility_data[facility_type] = {'total_items': 0, 'total_capacity': 0, 'total_quantity': 0}
        
        facility_data[facility_type]['total_items'] += len(location.inventory)
        facility_data[facility_type]['total_capacity'] += sum(inv.capacity for inv in location.inventory.values())
        facility_data[facility_type]['total_quantity'] += sum(inv.quantity for inv in location.inventory.values())
    
    # Create bar chart
    facility_df = pd.DataFrame.from_dict(facility_data, orient='index')
    facility_df.index.name = 'Facility Type'
    facility_df.reset_index(inplace=True)
    
    fig_bar = px.bar(
        facility_df,
        x='Facility Type',
        y='total_quantity',
        title='Total Inventory by Facility Type',
        labels={'total_quantity': 'Total Quantity', 'Facility Type': 'Facility Type'}
    )
    st.plotly_chart(fig_bar, use_container_width=True)
    
    # Item distribution pie chart
    st.subheader("🥧 Item Type Distribution")
    
    item_type_data = {}
    for location in locations:
        for item_name, inv_state in location.inventory.items():
            # Find the item to get its type
            item = next((item for item in FOXHOLE_ITEMS if item.name == item_name), None)
            if item:
                item_type = item.item_type.value
                if item_type not in item_type_data:
                    item_type_data[item_type] = 0
                item_type_data[item_type] += inv_state.quantity
    
    if item_type_data:
        fig_pie = px.pie(
            values=list(item_type_data.values()),
            names=list(item_type_data.keys()),
            title='Inventory Distribution by Item Type'
        )
        st.plotly_chart(fig_pie, use_container_width=True)


def main():
    """Main Streamlit application."""
    
    # Initialize session state
    initialize_session_state()
    
    # Sidebar navigation
    st.sidebar.title("🦊 Foxhole Automated Quartermaster")
    st.sidebar.markdown("---")
    
    page = st.sidebar.selectbox(
        "Navigate",
        ["🗺️ Logistics Network", "📋 Task Management", "📸 Inventory Upload", "📈 Analytics"]
    )
    
    # Display current war information (mock)
    st.sidebar.markdown("### 🌐 War Status")
    st.sidebar.write("**War #105** - Resistance Phase")
    st.sidebar.write("**Duration:** Day 23")
    st.sidebar.write("**Active Regions:** 18")
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔧 Quick Actions")
    if st.sidebar.button("🔄 Refresh Data"):
        st.rerun()
    
    if st.sidebar.button("📊 Generate Report"):
        st.sidebar.success("Report generated!")
    
    # Main content area
    if page == "🗺️ Logistics Network":
        st.title("🗺️ Foxhole Logistics Network")
        
        # Graph visualization
        col1, col2 = st.columns([2, 1])
        
        with col1:
            graph = st.session_state.logistics_graph
            selected_node = st.session_state.selected_location
            
            fig = create_logistics_graph_plot(graph, selected_node)
            
            # Handle node clicks
            clicked_data = st.plotly_chart(fig, use_container_width=True, on_select="rerun")
            
            # Node selection dropdown as fallback
            location_names = [loc.name for loc in st.session_state.locations]
            selected_location_name = st.selectbox(
                "Select Location for Details:",
                ["None"] + location_names,
                index=0 if not st.session_state.selected_location else location_names.index(st.session_state.selected_location) + 1
            )
            
            if selected_location_name != "None":
                st.session_state.selected_location = selected_location_name
            else:
                st.session_state.selected_location = None
        
        with col2:
            if st.session_state.selected_location:
                location = next(
                    (loc for loc in st.session_state.locations if loc.name == st.session_state.selected_location),
                    None
                )
                if location:
                    display_location_details(location)
            else:
                st.info("Select a location on the map or from the dropdown to view details.")
                
                # Show network summary
                st.subheader("🌐 Network Summary")
                total_nodes = len(st.session_state.logistics_graph.nodes())
                total_edges = len(st.session_state.logistics_graph.edges())
                
                st.write("**Total Locations:** {}".format(total_nodes))
                st.write("**Total Routes:** {}".format(total_edges))
                
                # Show facility types
                facility_counts = {}
                for location in st.session_state.locations:
                    facility_type = location.facility_type.value
                    facility_counts[facility_type] = facility_counts.get(facility_type, 0) + 1
                
                st.write("**Facility Distribution:**")
                for facility_type, count in facility_counts.items():
                    st.write("- {}: {}".format(facility_type.replace('_', ' ').title(), count))
    
    elif page == "📋 Task Management":
        display_task_management()
    
    elif page == "📸 Inventory Upload":
        display_inventory_upload()
    
    elif page == "📈 Analytics":
        display_analytics()


if __name__ == "__main__":
    main()
