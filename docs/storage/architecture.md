# ZODB Integration Architecture Guide

## Overview

The Foxhole Automated Quartermaster has been upgraded with a modern ZODB-based persistent storage system that replaces the legacy Peewee/SQLite approach. This new system provides native NetworkX graph persistence, improved performance, and enhanced data integrity for complex logistics operations.

## Architecture Components

### Core Components

1. **ZODBManager** - Singleton database connection manager
2. **GraphStorage** - Organized container for different graph types
3. **PersistentNetworkXGraph** - ZODB-compatible NetworkX wrapper
4. **PersistentGraphService** - High-level API with caching
5. **Persistent Node Classes** - Specialized node types for different use cases

### System Architecture

```
┌─────────────────────────────────────────────────────┐
│                Application Layer                    │
├─────────────────────────────────────────────────────┤
│           PersistentGraphService                    │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │
│  │   Caching   │ │ Batch Ops   │ │ Performance │   │
│  └─────────────┘ └─────────────┘ └─────────────┘   │
├─────────────────────────────────────────────────────┤
│          PersistentNetworkXGraph                    │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │
│  │ NetworkX    │ │ ZODB Sync   │ │ Batch Mode  │   │
│  │ Compatibility│ │            │ │            │   │
│  └─────────────┘ └─────────────┘ └─────────────┘   │
├─────────────────────────────────────────────────────┤
│              Persistent Nodes                      │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │
│  │ Inventory   │ │ Production  │ │    Task     │   │
│  │    Node     │ │    Node     │ │    Node     │   │
│  └─────────────┘ └─────────────┘ └─────────────┘   │
├─────────────────────────────────────────────────────┤
│               GraphStorage                          │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │
│  │ Production  │ │ Task Graphs │ │ Inventory   │   │
│  │   Graphs    │ │            │ │  Networks   │   │
│  └─────────────┘ └─────────────┘ └─────────────┘   │
├─────────────────────────────────────────────────────┤
│                ZODBManager                          │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │
│  │ Connection  │ │Transaction  │ │ Maintenance │   │
│  │   Pool      │ │  Management │ │   Utils     │   │
│  └─────────────┘ └─────────────┘ └─────────────┘   │
├─────────────────────────────────────────────────────┤
│                    ZODB                             │
│              Object Database                        │
└─────────────────────────────────────────────────────┘
```

## Key Features

### 1. Native NetworkX Persistence

The `PersistentNetworkXGraph` class provides full NetworkX API compatibility while automatically persisting changes to ZODB:

```python
from services.storage import PersistentNetworkXGraph

# Create a persistent graph
graph = PersistentNetworkXGraph(
    graph_type="DiGraph",
    graph_id="production_network",
    graph_name="Main Production Network"
)

# Use standard NetworkX operations
graph.add_node("RefiningPost", type="refinery", capacity=1000)
graph.add_node("ComponentMine", type="mine", output="components")
graph.add_edge("ComponentMine", "RefiningPost", material="components")

# Changes are automatically persisted
```

### 2. Specialized Persistent Nodes

Different node types provide domain-specific functionality:

#### Inventory Nodes
```python
from services.storage.nodes import PersistentInventoryNode

storage = PersistentInventoryNode(
    name="Main Storage Depot",
    location="Loch Mor",
    max_capacity=10000,
    facility_type="storage"
)

# Inventory management
storage.add_inventory("bmats", 500, quality="standard")
storage.reserve_inventory("bmats", 100, "order_123")
available = storage.get_available_inventory("bmats")
```

#### Production Nodes
```python
from services.storage.nodes import PersistentProductionNode

factory = PersistentProductionNode(
    name="Weapons Factory",
    facility_type="factory",
    location="Tempest Island"
)

# Recipe management
recipe_id = factory.add_recipe({
    'inputs': {'bmats': 100, 'rmats': 25},
    'outputs': {'rifle': 1},
    'cycle_time': 300,
    'required_tier': 2
})

# Production operations
factory.start_production(recipe_id, cycles=5)
```

#### Task Nodes
```python
from services.storage.nodes import PersistentTaskNode

task = PersistentTaskNode(
    name="Transport BMATS",
    task_type="logistics",
    priority_level="high"
)

# Task lifecycle
task.start_task("user_123")
task.update_progress(50, "Loading materials")
task.complete_task(success=True, results={"delivered": 500})
```

### 3. High-Level Service API

The `PersistentGraphService` provides optimized operations with caching:

```python
from services.storage import graph_service

# Create and manage graphs
graph = graph_service.create_graph(
    graph_id="logistics_network",
    graph_type="DiGraph",
    metadata={"faction": "colonial", "region": "deadlands"}
)

# Node management
storage_node = graph_service.create_node(
    graph_id="logistics_network",
    node_type="inventory",
    name="Forward Base Storage",
    location="Deadlands Hub"
)

# Batch operations for performance
with graph_service.batch_operation("logistics_network") as graph:
    for i in range(100):
        graph.add_node(f"depot_{i}", type="storage")
        if i > 0:
            graph.add_edge(f"depot_{i-1}", f"depot_{i}", type="transport")
```

### 4. Transaction Management

All operations use ACID transactions for data integrity:

```python
from services.storage import zodb_manager

# Explicit transaction control
with zodb_manager.transaction() as root:
    storage = root['graph_storage']
    # Multiple operations in single transaction
    storage.register_graph("graph_1", "production", graph1)
    storage.register_graph("graph_2", "task", graph2)
    # Automatically commits on success, rolls back on error
```

## Migration from Legacy Systems

### Automatic Migration Tools

The `GraphMigrationManager` handles migration from legacy formats:

```python
from services.storage.migration_manager import migration_manager

# Start migration session
migration_id = migration_manager.start_migration("Legacy Production Graph")

# Migrate from pickle files
success = migration_manager.migrate_production_graph_from_pickle(
    pickle_path="data/legacy_production.pkl",
    graph_id="migrated_production"
)

# Migrate cached calculations from Peewee
success = migration_manager.migrate_production_cache_from_peewee(
    target_graph_id="migrated_production"
)

# Generate migration report
report_path = migration_manager.export_migration_report()
```

### Migration Process

1. **Backup Creation** - Automatic backups of source data
2. **Data Conversion** - Convert legacy formats to persistent objects
3. **Validation** - Verify data integrity after migration
4. **Report Generation** - Detailed migration logs and statistics

## Performance Characteristics

### Caching Strategy

The service layer implements intelligent caching:

- **LRU Cache** - Least recently used eviction
- **TTL-based Expiration** - Time-based cache invalidation
- **Pattern-based Invalidation** - Smart cache clearing on updates
- **Cache Hit Rate Monitoring** - Performance metrics

### Batch Operations

Optimize bulk operations:

```python
# Batch mode prevents individual sync operations
graph.start_batch_mode()
# ... perform many operations ...
graph.end_batch_mode()  # Single sync at the end
```

### Memory Management

ZODB provides efficient memory usage:

- **Lazy Loading** - Objects loaded on demand
- **Automatic Persistence** - Changes tracked and persisted
- **Connection Pooling** - Efficient database connections
- **Garbage Collection** - Automatic cleanup of unused objects

## Configuration and Setup

### Database Configuration

Configure ZODB storage location:

```python
# Default configuration
zodb_manager = ZODBManager("data/storage/foxhole_graphs.db")

# Custom configuration
zodb_manager = ZODBManager(
    db_path="/custom/path/graphs.db"
)
```

### Service Configuration

Customize service behavior:

```python
# Custom cache settings
service = PersistentGraphService(
    cache_size=2000,  # Maximum cached items
    cache_ttl=7200    # Cache TTL in seconds
)
```

## Monitoring and Maintenance

### Health Checks

Monitor system health:

```python
# ZODB health
zodb_health = zodb_manager.health_check()

# Service health
service_health = graph_service.health_check()

# Storage integrity
with zodb_manager.read_only_transaction() as root:
    storage = root['graph_storage']
    integrity = storage.validate_integrity()
```

### Performance Metrics

Track performance:

```python
# Service statistics
stats = graph_service.get_service_statistics()
print(f"Cache hit rate: {stats['cache_hit_rate_percent']}%")
print(f"Total operations: {stats['total_operations']}")

# Database statistics
db_stats = zodb_manager.get_statistics()
print(f"Database size: {db_stats['db_size_mb']} MB")
```

### Maintenance Operations

Regular maintenance:

```python
# Pack database (remove old revisions)
zodb_manager.pack(days=30)

# Clear service cache
graph_service.clear_cache()

# Backup database
zodb_manager.backup("backups/graphs_backup.db")
```

## Best Practices

### 1. Transaction Boundaries

- Use transactions for multi-step operations
- Keep transactions short and focused
- Let context managers handle commit/rollback

### 2. Batch Operations

- Use batch mode for bulk graph modifications
- Disable auto-sync during large operations
- End batch mode to persist changes

### 3. Error Handling

- Transactions automatically rollback on exceptions
- Validate data before committing
- Use try-catch for operation-specific error handling

### 4. Performance Optimization

- Use caching for frequently accessed data
- Monitor cache hit rates
- Pack database regularly
- Use read-only transactions when possible

### 5. Data Modeling

- Use appropriate node types for different domains
- Leverage persistent collections for complex data
- Design for change with extensible attributes

## Integration with Existing Code

### Backward Compatibility

The system maintains compatibility during transition:

```python
# Legacy code can still use ProductionGraph
from services.production_calculator.production_graph import ProductionGraph

# New code uses persistent graphs
from services.storage import graph_service

# Migration bridges the gap
legacy_graph = ProductionGraph.load_from_disk("legacy.pkl")
persistent_graph = migration_manager.migrate_production_graph_from_pickle(
    "legacy.pkl", "new_persistent_graph"
)
```

### Gradual Migration

1. **Phase 1** - New features use ZODB
2. **Phase 2** - Migrate existing data
3. **Phase 3** - Deprecate legacy systems
4. **Phase 4** - Remove legacy code

## Troubleshooting

### Common Issues

1. **Database Lock Issues** - Ensure proper connection management
2. **Memory Usage** - Monitor object loading and caching
3. **Performance Degradation** - Check cache hit rates and database size
4. **Migration Failures** - Validate source data and check migration logs

### Debug Tools

```python
# Enable detailed logging
import logging
logging.getLogger('services.storage').setLevel(logging.DEBUG)

# Validate graph integrity
validation = persistent_graph.validate_integrity()
if not validation['is_valid']:
    print("Issues:", validation['issues'])

# Check service health
health = graph_service.health_check()
if health['status'] != 'healthy':
    print("Health issues:", health['issues'])
```

This architecture provides a robust foundation for persistent NetworkX graphs with excellent performance, data integrity, and scalability for complex Foxhole logistics operations.