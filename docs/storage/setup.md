# ZODB Setup and Configuration Guide

## Installation

### Prerequisites

- Python 3.8 or higher
- NetworkX 3.0+
- Git (for development)

### Installing Dependencies

#### Using pip

```bash
# Install from requirements.txt
pip install -r requirements.txt

# Or install individual packages
pip install ZODB BTrees persistent transaction networkx
```

#### Using conda (optional)

```bash
# Create conda environment
conda create -n foxhole-quartermaster python=3.11
conda activate foxhole-quartermaster

# Install packages
conda install -c conda-forge zodb btrees networkx
pip install persistent transaction
```

### Verify Installation

```python
# Test ZODB installation
import ZODB
import BTrees
import persistent
import transaction
print("ZODB installation successful!")

# Test NetworkX integration
import networkx as nx
from services.storage import PersistentNetworkXGraph
print("NetworkX integration ready!")
```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Database configuration
ZODB_DATABASE_PATH=data/storage/foxhole_graphs.db
ZODB_CACHE_SIZE=10000
ZODB_POOL_SIZE=7

# Service configuration
GRAPH_SERVICE_CACHE_SIZE=1000
GRAPH_SERVICE_CACHE_TTL=3600

# Migration settings
MIGRATION_BACKUP_DIR=data/migration_backups
MIGRATION_LOG_LEVEL=INFO

# Performance tuning
BATCH_MODE_THRESHOLD=100
AUTO_PACK_ENABLED=true
AUTO_PACK_DAYS=30
```

### Database Configuration

#### Basic Setup

```python
from services.storage import ZODBManager

# Use default configuration
zodb_manager = ZODBManager()

# Custom database path
zodb_manager = ZODBManager("custom/path/graphs.db")
```

#### Advanced Configuration

```python
import ZODB
import ZODB.FileStorage

# Custom storage configuration
storage = ZODB.FileStorage.FileStorage(
    'data/graphs.db',
    create=True,
    read_only=False
)

# Custom database configuration
db = ZODB.DB(
    storage,
    cache_size=20000,  # Object cache size
    pool_size=10,      # Connection pool size
    cache_size_bytes=100*1024*1024  # Cache size in bytes (100MB)
)

# Use with ZODBManager
zodb_manager = ZODBManager()
zodb_manager.db = db
```

### Service Configuration

```python
from services.storage import PersistentGraphService

# Custom service configuration
service = PersistentGraphService(
    cache_size=2000,    # Maximum cached items
    cache_ttl=7200      # Cache time-to-live (2 hours)
)

# Configure logging
import logging
logging.getLogger('services.storage').setLevel(logging.DEBUG)
```

## Development Setup

### Project Structure

Create the following directory structure:

```
foxhole-quartermaster/
├── data/
│   ├── storage/          # ZODB database files
│   ├── migration_backups/ # Migration backups
│   └── cache/            # Legacy cache files
├── services/
│   └── storage/          # ZODB implementation
├── tests/                # Test files
├── docs/                 # Documentation
└── examples/             # Example scripts
```

### Initialize Storage

```python
from services.storage import zodb_manager, graph_service

# Initialize database (creates file if needed)
with zodb_manager.transaction() as root:
    if 'graph_storage' not in root:
        from services.storage import GraphStorage
        root['graph_storage'] = GraphStorage()
        print("Initialized graph storage")

# Verify setup
health = graph_service.health_check()
print(f"System health: {health['status']}")
```

### Development Tools

#### Auto-formatter Configuration

Create `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        additional_dependencies: [flake8-docstrings]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.3.0
    hooks:
      - id: mypy
        additional_dependencies: [types-requests]
```

#### Testing Configuration

Create `pytest.ini`:

```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --verbose
    --cov=services.storage
    --cov-report=html
    --cov-report=term-missing
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    unit: marks tests as unit tests
```

## Production Deployment

### Database Optimization

#### File System Considerations

```bash
# Use SSD storage for better performance
# Example mount options for better ZODB performance
/dev/ssd1 /data/storage ext4 defaults,noatime,barrier=0 0 2
```

#### Database Tuning

```python
# Production ZODB configuration
import ZODB
import ZODB.FileStorage

storage = ZODB.FileStorage.FileStorage(
    '/data/storage/foxhole_graphs.db',
    create=False,
    read_only=False,
    blob_dir='/data/storage/blobs'  # Separate blob storage
)

db = ZODB.DB(
    storage,
    cache_size=50000,           # Larger cache for production
    pool_size=20,               # More connections
    cache_size_bytes=500*1024*1024,  # 500MB cache
    historical_pool_size=5,     # Historical connections
    historical_cache_size=10000,
    historical_timeout=300
)
```

### Monitoring Setup

#### Health Check Endpoint

```python
from flask import Flask, jsonify
from services.storage import graph_service, zodb_manager

app = Flask(__name__)

@app.route('/health')
def health_check():
    """Health check endpoint for monitoring."""
    zodb_health = zodb_manager.health_check()
    service_health = graph_service.health_check()
    
    overall_status = 'healthy'
    if zodb_health['status'] != 'healthy' or service_health['status'] != 'healthy':
        overall_status = 'unhealthy'
    
    return jsonify({
        'status': overall_status,
        'zodb': zodb_health,
        'service': service_health,
        'timestamp': time.time()
    })

@app.route('/metrics')
def metrics():
    """Metrics endpoint for monitoring."""
    service_stats = graph_service.get_service_statistics()
    zodb_stats = zodb_manager.get_statistics()
    
    return jsonify({
        'service': service_stats,
        'database': zodb_stats
    })
```

#### Logging Configuration

```python
import logging
import structlog

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(name)s %(levelname)s %(message)s'
)

# Configure ZODB logging
logging.getLogger('ZODB').setLevel(logging.WARNING)
logging.getLogger('ZEO').setLevel(logging.WARNING)

# Configure application logging
logging.getLogger('services.storage').setLevel(logging.INFO)
```

### Backup and Recovery

#### Automated Backup Script

```python
#!/usr/bin/env python3
"""
Automated backup script for ZODB database.
"""

import os
import time
import shutil
from datetime import datetime
from services.storage import zodb_manager

def backup_database():
    """Create database backup."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = '/backups/zodb'
    
    # Ensure backup directory exists
    os.makedirs(backup_dir, exist_ok=True)
    
    # Create backup
    backup_path = os.path.join(backup_dir, f'foxhole_graphs_{timestamp}.db')
    
    try:
        zodb_manager.backup(backup_path)
        print(f"Backup created: {backup_path}")
        
        # Compress backup
        import gzip
        with open(backup_path, 'rb') as f_in:
            with gzip.open(f"{backup_path}.gz", 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        # Remove uncompressed backup
        os.remove(backup_path)
        print(f"Compressed backup: {backup_path}.gz")
        
    except Exception as e:
        print(f"Backup failed: {e}")
        return False
    
    return True

if __name__ == '__main__':
    backup_database()
```

#### Cron Configuration

```bash
# Add to crontab for automated backups
# Run backup every 6 hours
0 */6 * * * /usr/bin/python3 /app/scripts/backup_database.py

# Pack database weekly (Sunday at 2 AM)
0 2 * * 0 /usr/bin/python3 -c "from services.storage import zodb_manager; zodb_manager.pack(days=30)"
```

### Performance Tuning

#### Cache Optimization

```python
# Monitor cache performance
def monitor_cache_performance():
    """Monitor and log cache performance metrics."""
    stats = graph_service.get_service_statistics()
    
    hit_rate = stats['cache_hit_rate_percent']
    if hit_rate < 70:  # Low hit rate threshold
        print(f"Warning: Low cache hit rate: {hit_rate}%")
        
        # Consider increasing cache size
        if stats['cache_size'] >= stats['cache_capacity'] * 0.9:
            print("Consider increasing cache size")
    
    return stats

# Schedule regular monitoring
import schedule
schedule.every(15).minutes.do(monitor_cache_performance)
```

#### Database Maintenance

```python
def maintenance_tasks():
    """Regular maintenance tasks."""
    
    # Pack database monthly
    zodb_manager.pack(days=30)
    
    # Clear old cache entries
    graph_service.clear_cache()
    
    # Validate integrity
    with zodb_manager.read_only_transaction() as root:
        storage = root.get('graph_storage')
        if storage:
            validation = storage.validate_integrity()
            if not validation['is_valid']:
                print(f"Integrity issues found: {validation['issues']}")

# Schedule monthly maintenance
schedule.every().month.do(maintenance_tasks)
```

## Security Configuration

### Access Control

```python
# Basic access control example
class SecureGraphService(PersistentGraphService):
    """Graph service with access control."""
    
    def __init__(self, auth_backend=None, **kwargs):
        super().__init__(**kwargs)
        self.auth_backend = auth_backend
    
    def _check_permission(self, user_id, operation, resource):
        """Check if user has permission for operation."""
        if self.auth_backend:
            return self.auth_backend.has_permission(user_id, operation, resource)
        return True  # Default allow for backwards compatibility
    
    def get_graph(self, graph_id, user_id=None):
        """Get graph with access control."""
        if not self._check_permission(user_id, 'read', graph_id):
            raise PermissionError(f"Access denied to graph {graph_id}")
        
        return super().get_graph(graph_id)
```

### Data Encryption

```python
# Example encryption configuration (requires additional libraries)
import cryptography
from cryptography.fernet import Fernet

class EncryptedZODBManager(ZODBManager):
    """ZODB manager with encryption support."""
    
    def __init__(self, db_path, encryption_key=None, **kwargs):
        self.cipher = None
        if encryption_key:
            self.cipher = Fernet(encryption_key)
        
        super().__init__(db_path, **kwargs)
    
    def _encrypt_data(self, data):
        """Encrypt data if cipher is available."""
        if self.cipher and isinstance(data, (str, bytes)):
            if isinstance(data, str):
                data = data.encode('utf-8')
            return self.cipher.encrypt(data)
        return data
    
    def _decrypt_data(self, data):
        """Decrypt data if cipher is available."""
        if self.cipher and isinstance(data, bytes):
            try:
                return self.cipher.decrypt(data)
            except:
                return data  # Not encrypted or invalid
        return data
```

## Troubleshooting

### Common Issues

#### Database Lock Issues

```python
# Check for stale connections
def check_database_locks():
    """Check for database lock issues."""
    try:
        with zodb_manager.read_only_transaction() as root:
            # Quick read test
            _ = list(root.keys())
        print("Database accessible")
    except Exception as e:
        print(f"Database lock issue: {e}")
        # Force close connections
        zodb_manager.close()
```

#### Memory Issues

```python
# Monitor memory usage
import psutil
import gc

def monitor_memory():
    """Monitor memory usage."""
    process = psutil.Process()
    memory_info = process.memory_info()
    
    print(f"RSS: {memory_info.rss / 1024 / 1024:.1f} MB")
    print(f"VMS: {memory_info.vms / 1024 / 1024:.1f} MB")
    
    # Force garbage collection if memory is high
    if memory_info.rss > 1024 * 1024 * 1024:  # 1GB threshold
        gc.collect()
        print("Forced garbage collection")
```

#### Performance Issues

```python
# Performance diagnostics
def diagnose_performance():
    """Diagnose performance issues."""
    stats = graph_service.get_service_statistics()
    
    print(f"Cache hit rate: {stats['cache_hit_rate_percent']}%")
    print(f"Total operations: {stats['total_operations']}")
    
    if stats['cache_hit_rate_percent'] < 70:
        print("Low cache hit rate - consider:")
        print("- Increasing cache size")
        print("- Increasing cache TTL")
        print("- Optimizing access patterns")
    
    db_stats = zodb_manager.get_statistics()
    print(f"Database size: {db_stats['db_size_mb']} MB")
    
    if db_stats['db_size_mb'] > 1000:  # 1GB threshold
        print("Large database - consider:")
        print("- Regular packing")
        print("- Archiving old data")
        print("- Database partitioning")
```

### Debug Mode

```python
# Enable debug mode
import os
os.environ['ZODB_DEBUG'] = '1'

# Detailed logging
import logging
logging.getLogger().setLevel(logging.DEBUG)

# Enable transaction logging
import transaction
transaction._manager.debug = True
```

This setup guide provides comprehensive configuration options for both development and production environments, ensuring optimal performance and reliability of the ZODB-based storage system.