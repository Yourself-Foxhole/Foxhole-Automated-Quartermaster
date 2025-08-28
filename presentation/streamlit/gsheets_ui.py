"""UI components for Google Sheets integration.

This module provides Streamlit UI components for managing Google Sheets
connection status, configuration, and error handling.
"""

import streamlit as st
import pandas as pd
from typing import Optional
import json

from gsheets_config import get_gsheets_config
from gsheets_backend import get_gsheets_backend


def show_connection_status():
    """Show Google Sheets connection status in the sidebar."""
    config = get_gsheets_config()
    backend = get_gsheets_backend()
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("📊 Google Sheets Backend")
    
    # Configuration status
    if config.is_configured:
        st.sidebar.success("✅ Configuration loaded")
    else:
        st.sidebar.error("❌ Configuration missing")
        if st.sidebar.button("Show Setup Instructions"):
            st.session_state.show_config_help = True
    
    # Connection status
    status = backend.connection_status
    if status == "connected":
        st.sidebar.success("✅ Connected to Google Sheets")
        
        # Test connection button
        if st.sidebar.button("Test Connection"):
            with st.sidebar:
                with st.spinner("Testing connection..."):
                    if backend.test_connection():
                        st.success("✅ Connection test passed")
                    else:
                        st.error("❌ Connection test failed")
                        if backend.last_error:
                            st.error(f"Error: {backend.last_error}")
    
    elif status == "error":
        st.sidebar.error("❌ Connection error")
        if backend.last_error:
            st.sidebar.error(f"Error: {backend.last_error}")
    else:
        st.sidebar.warning("⚠️ Not connected")
    
    # Initialize sheets button
    if status == "connected":
        if st.sidebar.button("Initialize Sheets"):
            with st.sidebar:
                with st.spinner("Initializing Google Sheets..."):
                    if backend.initialize_sheets():
                        st.success("✅ Sheets initialized successfully")
                        st.rerun()
                    else:
                        st.error("❌ Failed to initialize sheets")
                        if backend.last_error:
                            st.error(f"Error: {backend.last_error}")


def show_configuration_help():
    """Show configuration help modal."""
    if st.session_state.get('show_config_help', False):
        config = get_gsheets_config()
        
        st.markdown("## 🔧 Google Sheets Setup Instructions")
        
        st.markdown("""
        ### Prerequisites
        
        1. **Create a Google Cloud Project**
           - Go to [Google Cloud Console](https://console.cloud.google.com/)
           - Create a new project or select existing one
        
        2. **Enable Required APIs**
           - Search for "Google Sheets API" and enable it
           - Search for "Google Drive API" and enable it
        
        3. **Create Service Account**
           - Go to "APIs & Services > Credentials"
           - Click "Create credentials > Service account key"
           - Fill out the form and create the account
           - Download the JSON key file
        
        4. **Share Your Spreadsheet**
           - Create a new Google Sheet or use existing one
           - Share it with the service account email (from JSON file)
           - Give "Editor" permissions
        """)
        
        st.markdown("### Configuration Template")
        st.markdown("Copy this template to `.streamlit/secrets.toml`:")
        
        template = config.create_streamlit_secrets_template()
        st.code(template, language='toml')
        
        st.markdown("""
        ### Important Notes
        
        - **Never commit secrets.toml to git!** Add it to your .gitignore
        - Replace `YOUR_SPREADSHEET_ID` with your actual spreadsheet ID from the URL
        - Copy the service account values exactly from your downloaded JSON file
        - Make sure the spreadsheet is shared with the service account email
        """)
        
        if st.button("Close Instructions"):
            st.session_state.show_config_help = False
            st.rerun()


def show_data_management_panel():
    """Show data management panel in the sidebar."""
    backend = get_gsheets_backend()
    
    if backend.connection_status != "connected":
        return
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("💾 Data Management")
    
    # Sync controls
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        if st.button("💾 Save All", help="Save current data to Google Sheets"):
            with st.spinner("Saving to Google Sheets..."):
                success = True
                
                # Save locations and inventory
                if 'locations' in st.session_state:
                    if not backend.save_inventory_data(st.session_state.locations):
                        success = False
                
                # Save tasks
                if 'tasks' in st.session_state:
                    if not backend.save_tasks(st.session_state.tasks):
                        success = False
                
                if success:
                    st.success("✅ Data saved successfully")
                    # Log analytics
                    backend.log_analytics_metric("manual_save", 1)
                else:
                    st.error("❌ Failed to save data")
                    if backend.last_error:
                        st.error(f"Error: {backend.last_error}")
    
    with col2:
        if st.button("🔄 Load All", help="Load data from Google Sheets"):
            with st.spinner("Loading from Google Sheets..."):
                # Load locations and inventory
                locations = backend.load_inventory_data()
                if locations:
                    st.session_state.locations = locations
                
                # Load tasks
                tasks = backend.load_tasks()
                if tasks:
                    st.session_state.tasks = tasks
                
                st.success("✅ Data loaded successfully")
                # Log analytics
                backend.log_analytics_metric("manual_load", 1)
                st.rerun()
    
    # Auto-save toggle
    auto_save = st.sidebar.checkbox(
        "🔄 Auto-save changes",
        value=st.session_state.get('auto_save_enabled', False),
        help="Automatically save changes to Google Sheets"
    )
    st.session_state.auto_save_enabled = auto_save


def show_sync_indicator():
    """Show sync indicator in the main content area."""
    backend = get_gsheets_backend()
    
    if backend.connection_status == "connected":
        if st.session_state.get('auto_save_enabled', False):
            st.info("🔄 Auto-sync with Google Sheets enabled", icon="📊")
        else:
            st.info("📊 Connected to Google Sheets - use sidebar to sync data", icon="💾")
    elif backend.connection_status == "error":
        st.error(f"❌ Google Sheets connection error: {backend.last_error}", icon="🚨")
    else:
        st.warning("⚠️ Google Sheets not configured - using local data only", icon="📊")


def auto_save_data():
    """Auto-save data if enabled."""
    if not st.session_state.get('auto_save_enabled', False):
        return
    
    backend = get_gsheets_backend()
    if backend.connection_status != "connected":
        return
    
    try:
        # Save locations and inventory
        if 'locations' in st.session_state:
            backend.save_inventory_data(st.session_state.locations)
        
        # Save tasks  
        if 'tasks' in st.session_state:
            backend.save_tasks(st.session_state.tasks)
        
        # Log auto-save
        backend.log_analytics_metric("auto_save", 1)
        
    except Exception as e:
        st.warning(f"Auto-save failed: {str(e)}")


def load_data_on_startup():
    """Load data from Google Sheets on app startup."""
    backend = get_gsheets_backend()
    
    # Only load if not already loaded and connection is available
    if (backend.connection_status == "connected" and 
        'data_loaded_from_sheets' not in st.session_state):
        
        try:
            # Load locations and inventory
            locations = backend.load_inventory_data()
            if locations:
                st.session_state.locations = locations
            
            # Load tasks
            tasks = backend.load_tasks()
            if tasks is not None:  # Allow empty list
                st.session_state.tasks = tasks
            
            # Mark as loaded
            st.session_state.data_loaded_from_sheets = True
            
            # Log startup load
            backend.log_analytics_metric("startup_load", 1)
            
        except Exception as e:
            st.warning(f"Failed to load data from Google Sheets: {str(e)}")


def show_sheets_analytics():
    """Show Google Sheets analytics."""
    backend = get_gsheets_backend()
    
    if backend.connection_status != "connected":
        st.warning("Connect to Google Sheets to see analytics")
        return
    
    st.subheader("📊 Google Sheets Analytics")
    
    # Get analytics data
    analytics_df = backend.get_analytics_metrics(hours_back=24)
    
    if analytics_df.empty:
        st.info("No analytics data available")
        return
    
    # Show metrics summary
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        saves = len(analytics_df[analytics_df['metric_name'].isin(['manual_save', 'auto_save'])])
        st.metric("Saves (24h)", saves)
    
    with col2:
        loads = len(analytics_df[analytics_df['metric_name'] == 'manual_load'])
        st.metric("Loads (24h)", loads)
    
    with col3:
        startup_loads = len(analytics_df[analytics_df['metric_name'] == 'startup_load'])
        st.metric("Startup Loads", startup_loads)
    
    with col4:
        last_activity = analytics_df['timestamp'].max() if not analytics_df.empty else None
        if last_activity:
            st.metric("Last Activity", last_activity.strftime("%H:%M"))
        else:
            st.metric("Last Activity", "Never")
    
    # Show activity timeline
    if len(analytics_df) > 0:
        st.subheader("Activity Timeline")
        
        # Group by hour for chart
        analytics_df['hour'] = analytics_df['timestamp'].dt.floor('H')
        hourly_activity = analytics_df.groupby(['hour', 'metric_name']).size().reset_index(name='count')
        
        if not hourly_activity.empty:
            # Create pivot for better visualization
            hourly_pivot = hourly_activity.pivot(index='hour', columns='metric_name', values='count').fillna(0)
            st.bar_chart(hourly_pivot)
        
        # Show raw data
        with st.expander("Raw Analytics Data"):
            st.dataframe(analytics_df.sort_values('timestamp', ascending=False))