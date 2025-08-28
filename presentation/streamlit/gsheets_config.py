"""Configuration management for Google Sheets backend.

This module handles configuration of Google Sheets connection settings,
including credentials management and validation.
"""

import streamlit as st
from typing import Dict, Any, Optional
import os
import json


class GSheetsConfig:
    """Configuration manager for Google Sheets integration."""
    
    def __init__(self):
        """Initialize configuration manager."""
        self._config_cache = None
    
    @property
    def is_configured(self) -> bool:
        """Check if Google Sheets is properly configured."""
        try:
            config = self.get_config()
            required_fields = [
                'spreadsheet', 'type', 'project_id', 'private_key_id',
                'private_key', 'client_email', 'client_id'
            ]
            return all(field in config and config[field] for field in required_fields)
        except Exception:
            return False
    
    def get_config(self) -> Dict[str, Any]:
        """Get Google Sheets configuration."""
        if self._config_cache is not None:
            return self._config_cache
        
        try:
            # Try to get from Streamlit secrets first
            if 'connections' in st.secrets and 'gsheets' in st.secrets.connections:
                config = dict(st.secrets.connections.gsheets)
                self._config_cache = config
                return config
        except Exception:
            pass
        
        # Fallback to environment variables
        config = {
            'spreadsheet': os.getenv('GSHEETS_SPREADSHEET', ''),
            'inventory_worksheet': os.getenv('GSHEETS_INVENTORY_WORKSHEET', 'Inventory'),
            'tasks_worksheet': os.getenv('GSHEETS_TASKS_WORKSHEET', 'Tasks'),
            'analytics_worksheet': os.getenv('GSHEETS_ANALYTICS_WORKSHEET', 'Analytics'),
            'locations_worksheet': os.getenv('GSHEETS_LOCATIONS_WORKSHEET', 'Locations'),
            'type': os.getenv('GSHEETS_TYPE', 'service_account'),
            'project_id': os.getenv('GSHEETS_PROJECT_ID', ''),
            'private_key_id': os.getenv('GSHEETS_PRIVATE_KEY_ID', ''),
            'private_key': os.getenv('GSHEETS_PRIVATE_KEY', ''),
            'client_email': os.getenv('GSHEETS_CLIENT_EMAIL', ''),
            'client_id': os.getenv('GSHEETS_CLIENT_ID', ''),
            'auth_uri': os.getenv('GSHEETS_AUTH_URI', 'https://accounts.google.com/o/oauth2/auth'),
            'token_uri': os.getenv('GSHEETS_TOKEN_URI', 'https://oauth2.googleapis.com/token'),
            'auth_provider_x509_cert_url': os.getenv('GSHEETS_AUTH_PROVIDER_CERT_URL', 'https://www.googleapis.com/oauth2/v1/certs'),
            'client_x509_cert_url': os.getenv('GSHEETS_CLIENT_CERT_URL', ''),
            'cache_ttl': int(os.getenv('GSHEETS_CACHE_TTL', '600'))
        }
        
        self._config_cache = config
        return config
    
    def get_worksheet_name(self, worksheet_type: str) -> str:
        """Get worksheet name for a specific data type."""
        config = self.get_config()
        worksheet_map = {
            'inventory': config.get('inventory_worksheet', 'Inventory'),
            'tasks': config.get('tasks_worksheet', 'Tasks'),
            'analytics': config.get('analytics_worksheet', 'Analytics'),
            'locations': config.get('locations_worksheet', 'Locations')
        }
        return worksheet_map.get(worksheet_type, worksheet_type.title())
    
    def get_cache_ttl(self) -> int:
        """Get cache TTL in seconds."""
        return self.get_config().get('cache_ttl', 600)
    
    def validate_config(self) -> tuple[bool, Optional[str]]:
        """Validate the configuration."""
        if not self.is_configured:
            return False, "Google Sheets configuration is missing or incomplete. Please check your secrets.toml file."
        
        config = self.get_config()
        
        # Validate spreadsheet URL/ID
        spreadsheet = config.get('spreadsheet', '')
        if not spreadsheet:
            return False, "Spreadsheet URL or ID is required."
        
        # Validate service account fields
        if config.get('type') == 'service_account':
            required_sa_fields = ['project_id', 'private_key', 'client_email']
            missing_fields = [field for field in required_sa_fields if not config.get(field)]
            if missing_fields:
                return False, f"Missing service account fields: {', '.join(missing_fields)}"
        
        return True, None
    
    def create_streamlit_secrets_template(self) -> str:
        """Create a template for Streamlit secrets.toml file."""
        template = '''# .streamlit/secrets.toml
# Google Sheets Configuration for Foxhole Logistics

[connections.gsheets]
# Your Google Spreadsheet URL or ID
spreadsheet = "https://docs.google.com/spreadsheets/d/YOUR_SPREADSHEET_ID/edit"

# Worksheet names for different data types
inventory_worksheet = "Inventory"
tasks_worksheet = "Tasks"
analytics_worksheet = "Analytics" 
locations_worksheet = "Locations"

# Service Account Configuration
# Get these values from your Google Cloud Console service account JSON file
type = "service_account"
project_id = "your-project-id"
private_key_id = "your-private-key-id"
private_key = """-----BEGIN PRIVATE KEY-----
YOUR_PRIVATE_KEY_HERE
-----END PRIVATE KEY-----"""
client_email = "your-service-account@your-project.iam.gserviceaccount.com"
client_id = "your-client-id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/your-service-account%40your-project.iam.gserviceaccount.com"

# Optional settings
cache_ttl = 600  # Cache time in seconds (10 minutes)
'''
        return template


# Global configuration instance
_config_instance = None

def get_gsheets_config() -> GSheetsConfig:
    """Get the global Google Sheets configuration instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = GSheetsConfig()
    return _config_instance