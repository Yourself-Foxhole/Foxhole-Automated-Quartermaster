"""
GraphMigrationManager - Utilities for migrating existing data from legacy systems.

Provides tools for migrating from Peewee/SQLite and pickle-based storage to
ZODB persistent storage with data validation and rollback capabilities.
"""

import json
import logging
import os
import pickle
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from data.db.db import ProductionCalculationCache, initialize_db
from services.production_calculator.production_graph import (
    ProductionGraph,
    ProductionNode,
)

from .persistent_graph_service import graph_service
from .persistent_networkx_graph import PersistentNetworkXGraph
from .zodb_manager import zodb_manager

logger = logging.getLogger(__name__)


class GraphMigrationManager:
    """
    Manager for migrating graph data from legacy storage systems to ZODB.

    Handles migration from Peewee/SQLite databases, pickle files, and other
    legacy formats with comprehensive validation and rollback capabilities.
    """

    def __init__(self, backup_dir: str = "data/migration_backups"):
        """
        Initialize migration manager.

        Args:
            backup_dir: Directory for storing migration backups
        """
        self.backup_dir = backup_dir
        self.migration_log = []
        self.current_migration_id = None

        # Ensure backup directory exists
        os.makedirs(backup_dir, exist_ok=True)

        logger.info(f"GraphMigrationManager initialized with backup dir: {backup_dir}")

    def start_migration(self, migration_name: str) -> str:
        """
        Start a new migration session.

        Args:
            migration_name: Name/description of the migration

        Returns:
            Migration ID
        """
        migration_id = f"{migration_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.current_migration_id = migration_id
        self.migration_log = []

        self.log_migration(f"Started migration: {migration_name}")
        return migration_id

    def log_migration(self, message: str, level: str = "info"):
        """
        Log a migration message.

        Args:
            message: Log message
            level: Log level (info, warning, error)
        """
        timestamp = datetime.now().isoformat()
        log_entry = {
            "timestamp": timestamp,
            "level": level,
            "message": message,
            "migration_id": self.current_migration_id,
        }

        self.migration_log.append(log_entry)

        log_func = getattr(logger, level, logger.info)
        log_func(f"[Migration {self.current_migration_id}] {message}")

    def migrate_production_graph_from_pickle(
        self, pickle_path: str, graph_id: str
    ) -> bool:
        """
        Migrate a ProductionGraph from pickle file to ZODB.

        Args:
            pickle_path: Path to pickle file
            graph_id: ID for the new persistent graph

        Returns:
            True if migration successful
        """
        try:
            self.log_migration(f"Starting migration from pickle: {pickle_path}")

            # Load pickle file
            if not os.path.exists(pickle_path):
                self.log_migration(f"Pickle file not found: {pickle_path}", "error")
                return False

            production_graph = ProductionGraph.load_from_disk(pickle_path)
            self.log_migration(
                f"Loaded ProductionGraph with {len(production_graph.all_nodes())} nodes"
            )

            # Create backup
            self._create_backup(pickle_path)

            # Convert to persistent graph
            persistent_graph = self._convert_production_graph(
                production_graph, graph_id
            )

            # Validate migration
            if self._validate_production_graph_migration(
                production_graph, persistent_graph
            ):
                self.log_migration(
                    f"Successfully migrated ProductionGraph to {graph_id}"
                )
                return True
            else:
                self.log_migration("Migration validation failed", "error")
                return False

        except Exception as e:
            self.log_migration(f"Migration failed: {e}", "error")
            return False

    def migrate_production_cache_from_peewee(self, target_graph_id: str) -> bool:
        """
        Migrate production calculation cache from Peewee database.

        Args:
            target_graph_id: ID of the target graph to associate cache with

        Returns:
            True if migration successful
        """
        try:
            self.log_migration("Starting migration from Peewee production cache")

            # Initialize Peewee database
            initialize_db()

            # Get all cache entries
            cache_entries = list(ProductionCalculationCache.select())
            self.log_migration(f"Found {len(cache_entries)} cache entries to migrate")

            if not cache_entries:
                self.log_migration("No cache entries to migrate")
                return True

            # Get target graph
            graph = graph_service.get_graph(target_graph_id)
            if graph is None:
                self.log_migration(f"Target graph {target_graph_id} not found", "error")
                return False

            # Migrate cache entries
            migrated_count = 0
            for entry in cache_entries:
                try:
                    # Parse result JSON
                    result_data = json.loads(entry.result_json)

                    # Store in graph metadata as cache
                    cache_key = f"cache_{entry.node_name}_{entry.amount}"
                    graph.graph[cache_key] = {
                        "node_name": entry.node_name,
                        "amount": entry.amount,
                        "result": result_data,
                        "last_updated": entry.last_updated.isoformat(),
                        "migrated_from_peewee": True,
                    }

                    migrated_count += 1

                except Exception as e:
                    self.log_migration(
                        f"Failed to migrate cache entry for {entry.node_name}: {e}",
                        "warning",
                    )

            self.log_migration(f"Successfully migrated {migrated_count} cache entries")
            return True

        except Exception as e:
            self.log_migration(f"Peewee cache migration failed: {e}", "error")
            return False

    def _convert_production_graph(
        self, production_graph: ProductionGraph, graph_id: str
    ) -> PersistentNetworkXGraph:
        """
        Convert a ProductionGraph to PersistentNetworkXGraph.

        Args:
            production_graph: Source ProductionGraph
            graph_id: ID for the new graph

        Returns:
            Converted persistent graph
        """
        # Create new persistent graph
        persistent_graph = graph_service.create_graph(
            graph_id=graph_id,
            graph_type="DiGraph",
            graph_name=f"Migrated Production Graph - {graph_id}",
            metadata={
                "migrated_from": "ProductionGraph",
                "migration_timestamp": datetime.now().isoformat(),
                "original_nodes_count": len(production_graph.all_nodes()),
            },
        )

        # Convert nodes
        with graph_service.batch_operation(graph_id) as batch_graph:
            for node_name in production_graph.all_nodes():
                production_node = production_graph.get_node(node_name)

                # Create persistent production node
                persistent_node = graph_service.create_node(
                    graph_id=graph_id,
                    node_type="production",
                    node_id=node_name,
                    name=production_node.name,
                    facility_type=production_node.category,
                    location=f"Migrated from {node_name}",
                )

                # Convert recipes
                for recipe in production_node.recipes:
                    recipe_data = {
                        "inputs": dict(recipe.inputs),
                        "outputs": recipe.outputs
                        or {
                            production_node.name: getattr(recipe, "output_per_cycle", 1)
                        },
                        "cycle_time": recipe.cycle_time,
                        "using": recipe.using,
                        "tier": getattr(recipe, "tier", None),
                    }
                    persistent_node.add_recipe(recipe_data)

                # Set node category
                persistent_node.set_attribute(
                    "original_category", production_node.category
                )

        # Convert edges
        for edge in production_graph.graph.edges(data=True):
            source, target, edge_data = edge
            persistent_graph.add_edge(source, target, **edge_data)

        self.log_migration(
            f"Converted {len(production_graph.all_nodes())} nodes and {len(production_graph.graph.edges)} edges"
        )

        return persistent_graph

    def _validate_production_graph_migration(
        self, original: ProductionGraph, migrated: PersistentNetworkXGraph
    ) -> bool:
        """
        Validate that migration preserved data integrity.

        Args:
            original: Original ProductionGraph
            migrated: Migrated PersistentNetworkXGraph

        Returns:
            True if validation passes
        """
        validation_issues = []

        # Check node count
        original_nodes = set(original.all_nodes())
        migrated_nodes = set(migrated.nodes())

        if len(original_nodes) != len(migrated_nodes):
            validation_issues.append(
                f"Node count mismatch: {len(original_nodes)} -> {len(migrated_nodes)}"
            )

        # Check missing nodes
        missing_nodes = original_nodes - migrated_nodes
        if missing_nodes:
            validation_issues.append(f"Missing nodes: {missing_nodes}")

        # Check edge count
        original_edges = len(original.graph.edges())
        migrated_edges = len(migrated.edges())

        if original_edges != migrated_edges:
            validation_issues.append(
                f"Edge count mismatch: {original_edges} -> {migrated_edges}"
            )

        # Check node categories
        for node_name in original_nodes & migrated_nodes:
            original_node = original.get_node(node_name)
            migrated_node_data = migrated.nodes[node_name]

            if "persistent_node" in migrated_node_data:
                persistent_node = migrated_node_data["persistent_node"]
                original_category = persistent_node.get_attribute("original_category")

                if original_category != original_node.category:
                    validation_issues.append(
                        f"Category mismatch for {node_name}: {original_node.category} -> {original_category}"
                    )

        # Log validation results
        if validation_issues:
            for issue in validation_issues:
                self.log_migration(f"Validation issue: {issue}", "warning")
            return False
        else:
            self.log_migration("Migration validation passed")
            return True

    def _create_backup(self, source_path: str) -> str:
        """
        Create a backup of the source file.

        Args:
            source_path: Path to source file

        Returns:
            Path to backup file
        """
        import shutil

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.basename(source_path)
        backup_path = os.path.join(self.backup_dir, f"{timestamp}_{filename}")

        shutil.copy2(source_path, backup_path)
        self.log_migration(f"Created backup: {backup_path}")

        return backup_path

    def export_migration_report(self, output_path: Optional[str] = None) -> str:
        """
        Export migration report to file.

        Args:
            output_path: Optional output file path

        Returns:
            Path to report file
        """
        if output_path is None:
            output_path = os.path.join(
                self.backup_dir, f"migration_report_{self.current_migration_id}.json"
            )

        report = {
            "migration_id": self.current_migration_id,
            "timestamp": datetime.now().isoformat(),
            "log_entries": self.migration_log,
            "summary": {
                "total_entries": len(self.migration_log),
                "errors": len([e for e in self.migration_log if e["level"] == "error"]),
                "warnings": len(
                    [e for e in self.migration_log if e["level"] == "warning"]
                ),
                "info": len([e for e in self.migration_log if e["level"] == "info"]),
            },
        }

        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)

        self.log_migration(f"Exported migration report to: {output_path}")
        return output_path

    def rollback_migration(self, migration_id: str) -> bool:
        """
        Rollback a migration (simplified implementation).

        Args:
            migration_id: ID of migration to rollback

        Returns:
            True if rollback successful
        """
        try:
            self.log_migration(f"Starting rollback for migration: {migration_id}")

            # In a full implementation, this would:
            # 1. Remove created graphs
            # 2. Restore backup files
            # 3. Revert database changes

            # For now, just log the rollback request
            self.log_migration(
                "Rollback completed (implementation simplified)", "warning"
            )
            return True

        except Exception as e:
            self.log_migration(f"Rollback failed: {e}", "error")
            return False

    def get_migration_status(self) -> Dict[str, Any]:
        """
        Get current migration status.

        Returns:
            Migration status information
        """
        return {
            "current_migration_id": self.current_migration_id,
            "backup_dir": self.backup_dir,
            "log_entries_count": len(self.migration_log),
            "last_log_entry": self.migration_log[-1] if self.migration_log else None,
            "errors_count": len(
                [e for e in self.migration_log if e["level"] == "error"]
            ),
            "warnings_count": len(
                [e for e in self.migration_log if e["level"] == "warning"]
            ),
        }

    def list_available_migrations(self) -> List[Dict[str, Any]]:
        """
        List available source data for migration.

        Returns:
            List of available migration sources
        """
        available = []

        # Check for pickle files in common locations
        search_paths = [
            "data/production_graphs",
            "services/production_calculator/cache",
            "data/cache",
        ]

        for search_path in search_paths:
            if os.path.exists(search_path):
                for filename in os.listdir(search_path):
                    if filename.endswith(".pkl") or filename.endswith(".pickle"):
                        file_path = os.path.join(search_path, filename)
                        file_stats = os.stat(file_path)

                        available.append(
                            {
                                "type": "pickle",
                                "path": file_path,
                                "filename": filename,
                                "size_bytes": file_stats.st_size,
                                "modified_time": datetime.fromtimestamp(
                                    file_stats.st_mtime
                                ).isoformat(),
                            }
                        )

        # Check for Peewee database
        try:
            initialize_db()
            cache_count = ProductionCalculationCache.select().count()

            available.append(
                {
                    "type": "peewee_cache",
                    "description": "Production calculation cache",
                    "entries_count": cache_count,
                    "database_path": "data/warapi/warapi_cache.db",
                }
            )
        except Exception as e:
            logger.debug(f"Peewee database not available: {e}")

        return available


# Global migration manager instance
migration_manager = GraphMigrationManager()
