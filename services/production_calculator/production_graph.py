import networkx as nx
from typing import Dict, Any, Tuple, List
import pickle
import os
import json
from typing import Optional
# Peewee DB integration for caching
from data.db.db import ProductionCalculationCache, initialize_db
import datetime
from services.inventory.production_nodes import OutputType, TechnologyLevel
from services.FoxholeDataObjects.recipe import Recipe

class ProductionNode:
    def __init__(self, name: str, recipes: List[Recipe] = None, category: str = None):
        """
        :param name: Name of the item/material
        :param recipes: List of Recipe objects
        :param category: Category of the node (resource, refined, material, product)
        """
        self.name = name
        self.recipes = recipes or []
        self.category = category

    def __repr__(self):
        return f"ProductionNode({self.name!r}, recipes={self.recipes!r}, category={self.category!r})"

    def get_unlocked_recipe_indices(self, unlocked_tiers: List[str]) -> List[int]:
        """
        Returns a list of indices for recipes that are unlocked given the unlocked_tiers.
        If a recipe has no 'tier', it is always unlocked.
        """
        unlocked = []
        for i, recipe in enumerate(self.recipes):
            tier = recipe.tier
            if tier is None or tier in unlocked_tiers:
                unlocked.append(i)
        return unlocked

class ProductionGraph:
    def __init__(self):
        self.graph = nx.DiGraph()

    def _subnode_name(self, parent_name: str, recipe_idx: int) -> str:
        return f"{parent_name}#r{recipe_idx}"

    def add_node(self, node: ProductionNode):
        if node.category not in {"resource", "refined", "material", "product"}:
            raise ValueError(f"Invalid category: {node.category}")
        # If only one recipe, behave as before
        if len(node.recipes) <= 1:
            self.graph.add_node(node.name, node=node)
            if node.recipes:
                for recipe in node.recipes:
                    for input_name, qty in recipe.inputs.items():
                        self.graph.add_edge(input_name, node.name, quantity=qty)
        else:
            # Multiple recipes: create parent and subnodes
            self.graph.add_node(node.name, node=node)
            for idx, recipe in enumerate(node.recipes):
                subnode_name = self._subnode_name(node.name, idx)
                # Subnode is a ProductionNode with only this recipe
                subnode = ProductionNode(subnode_name, [recipe], category=node.category)
                self.graph.add_node(subnode_name, node=subnode)
                # Connect parent to subnode
                self.graph.add_edge(node.name, subnode_name, is_subnode=True)
                # Handle multiple outputs: connect subnode to all outputs
                outputs = recipe.outputs or [node.name]
                if isinstance(outputs, str):
                    outputs = [outputs]
                for output in outputs:
                    self.graph.add_edge(subnode_name, output, is_recipe_output=True)
                # Connect subnode to its inputs
                for input_name, qty in recipe.inputs.items():
                    self.graph.add_edge(input_name, subnode_name, quantity=qty)

    def add_production(self, output: str, recipe: Recipe = None):
        node = self.graph.nodes[output].get('node')
        if node is None:
            raise ValueError(f"Node '{output}' does not exist in the graph.")
        if recipe:
            node.recipes.append(recipe)
            for input_name, qty in recipe.inputs.items():
                self.graph.add_edge(input_name, output, quantity=qty)
        elif node.recipes:
            # Add edges for the default recipe if not already present
            for input_name, qty in node.recipes[0].inputs.items():
                self.graph.add_edge(input_name, output, quantity=qty)

    def resolve_base_materials(self, node_name: str, amount: float = 1.0, visited=None
                               , recipe_index: int = 0, byproducts=None) -> dict:
        """
        Recursively compute total base material requirements for a given node, with cycle detection and recipe selection.
        Handles subnodes for multi-recipe nodes and tracks byproducts.
        Returns a dict with keys: 'materials', 'total_time', 'cycles', 'using', 'cycle_time', 'output_per_cycle', 'byproducts'.
        """
        if visited is None:
            visited = set()
        if byproducts is None:
            byproducts = {}
        if node_name in visited:
            print(f"Cycle detected at {node_name}, skipping to prevent infinite recursion.")
            return {"materials": {}, "total_time": 0, "cycles": 0, "byproducts": {}}
        visited = visited | {node_name}
        node = self.graph.nodes[node_name]['node']
        # If this is a parent node with multiple recipes, descend into the chosen subnode
        if len(node.recipes) > 1 and not node_name.endswith('#r' + str(recipe_index)):
            subnode_name = self._subnode_name(node_name, recipe_index)
            return self.resolve_base_materials(subnode_name, amount, visited, recipe_index=0, byproducts=byproducts)
        if not node.recipes or recipe_index >= len(node.recipes):
            return {"materials": {node_name: amount}, "total_time": 0, "cycles": 0, "byproducts": {}}
        recipe = node.recipes[recipe_index]
        inputs = recipe.inputs
        outputs = recipe.outputs or {node.name: getattr(recipe, 'output_per_cycle', 1)}
        if isinstance(outputs, list):
            # Convert list to dict with 1 per output
            outputs = {k: 1 for k in outputs}
        cycle_time = recipe.cycle_time
        using = recipe.using
        # Determine how many cycles are needed for the requested output, considering byproducts
        output_qty = outputs.get(node_name, getattr(recipe, 'output_per_cycle', 1))
        # Use byproducts if available
        used_byproduct = min(byproducts.get(node_name, 0), amount)
        amount_needed = amount - used_byproduct
        if used_byproduct > 0:
            byproducts[node_name] -= used_byproduct
        import math
        cycles = math.ceil(amount_needed / output_qty) if output_qty else 0
        total_time = cycles * cycle_time
        # Track all outputs produced
        produced = {k: v * cycles for k, v in outputs.items()}
        # Calculate new byproducts (including surplus of main output)
        new_byproducts = byproducts.copy()
        for out_name, produced_qty in produced.items():
            used = amount_needed if out_name == node_name else 0
            surplus = produced_qty - used if out_name == node_name else produced_qty
            if surplus > 0:
                new_byproducts[out_name] = new_byproducts.get(out_name, 0) + surplus
        total_materials = {}
        for input_name, qty in inputs.items():
            required = qty * cycles
            sub_result = self.resolve_base_materials(input_name, required, visited, recipe_index=0, byproducts=new_byproducts)
            for mat, sub_qty in sub_result['materials'].items():
                total_materials[mat] = total_materials.get(mat, 0) + sub_qty
            # Merge byproducts from subcalls
            for b, bqty in sub_result.get('byproducts', {}).items():
                new_byproducts[b] = new_byproducts.get(b, 0) + bqty
        return {
            "materials": total_materials,
            "total_time": total_time,
            "cycles": cycles,
            "using": using,
            "cycle_time": cycle_time,
            "output_per_cycle": output_qty,
            "byproducts": new_byproducts
        }

    def get_node(self, name: str) -> ProductionNode:
        return self.graph.nodes[name]['node']

    def all_nodes(self) -> List[str]:
        return list(self.graph.nodes)

    def get_nodes_by_category(self, category: str) -> list:
        """Return a list of node names in the given category."""
        return [n for n, d in self.graph.nodes(data=True) if d['node'].category == category]

    def is_resource_node(self, node_name: str) -> bool:
        """Return True if the node is a resource (no inputs)."""
        node = self.graph.nodes[node_name]['node']
        return node.category == 'resource'

    def save_to_disk(self, path: str):
        """Serialize the graph to disk using pickle."""
        with open(path, 'wb') as f:
            pickle.dump(self.graph, f)

    @classmethod
    def load_from_disk(cls, path: str) -> 'ProductionGraph':
        """Load the graph from disk using pickle."""
        with open(path, 'rb') as f:
            graph = pickle.load(f)
        obj = cls()
        obj.graph = graph
        return obj

    def cache_base_materials(self, node_name: str, amount: float = 1.0, cache_dir: Optional[str] = None):
        """Cache the resolved base materials for a node to disk as JSON."""
        result = self.resolve_base_materials(node_name, amount)
        cache_dir = cache_dir or os.path.join(os.path.dirname(__file__), 'cache')
        os.makedirs(cache_dir, exist_ok=True)
        cache_path = os.path.join(cache_dir, f'{node_name}_x{amount}.json')
        with open(cache_path, 'w') as f:
            json.dump(result, f)
        return cache_path

    def load_cached_base_materials(self, node_name: str, amount: float = 1.0, cache_dir: Optional[str] = None) -> Optional[dict]:
        """Load cached base materials from disk if available."""
        cache_dir = cache_dir or os.path.join(os.path.dirname(__file__), 'cache')
        cache_path = os.path.join(cache_dir, f'{node_name}_x{amount}.json')
        if os.path.exists(cache_path):
            with open(cache_path, 'r') as f:
                return json.load(f)
        return None

    # Peewee DB integration for caching
    def save_base_materials_to_db(self, node_name: str, amount: float = 1.0):
        """Save the resolved base materials for a node/amount to the database cache."""
        initialize_db()
        result = self.resolve_base_materials(node_name, amount)
        result_json = json.dumps(result)
        now = datetime.datetime.utcnow()
        query = ProductionCalculationCache.replace(
            node_name=node_name,
            amount=amount,
            result_json=result_json,
            last_updated=now
        )
        query.execute()
        return result

    def load_base_materials_from_db(self, node_name: str, amount: float = 1.0):
        """Load cached base materials from the database if available."""
        initialize_db()
        try:
            cache = ProductionCalculationCache.get(
                (ProductionCalculationCache.node_name == node_name) &
                (ProductionCalculationCache.amount == amount)
            )
            return json.loads(cache.result_json)
        except ProductionCalculationCache.DoesNotExist:
            return None

    def print_production_chain(self, node_name: str, amount: float = 1.0, indent: int = 0, visited=None, recipe_index: int = 0, _totals=None, byproducts=None):
        """
        Print the production chain for a given node, showing all dependencies recursively, including facility, cycle time, cycles, and byproducts.
        Handles subnodes for multi-recipe nodes.
        """
        if visited is None:
            visited = set()
        if _totals is None and indent == 0:
            _totals = {"materials": {}, "refined": {}}
        elif _totals is None:
            _totals = None
        if byproducts is None:
            byproducts = {}
        prefix = '    ' * indent
        node = self.graph.nodes[node_name]['node']
        # If this is a parent node with multiple recipes, descend into the chosen subnode
        if len(node.recipes) > 1 and not node_name.endswith('#r' + str(recipe_index)):
            subnode_name = self._subnode_name(node_name, recipe_index)
            self.print_production_chain(subnode_name, amount, indent, visited, recipe_index=0, _totals=_totals, byproducts=byproducts)
            return
        if not node.recipes or recipe_index >= len(node.recipes):
            print(f"{prefix}{node_name} (category: {node.category}, amount: {amount}) [NO RECIPE]")
            return
        recipe = node.recipes[recipe_index]
        inputs = recipe.inputs
        outputs = recipe.outputs or {node.name: recipe.get('output_per_cycle', 1)}
        if isinstance(outputs, list):
            outputs = {k: 1 for k in outputs}
        cycle_time = recipe.cycle_time
        output_per_cycle = outputs.get(node_name, recipe.get('output_per_cycle', 1))
        using = recipe.using
        import math
        # Use byproducts if available
        used_byproduct = min(byproducts.get(node_name, 0), amount)
        amount_needed = amount - used_byproduct
        if used_byproduct > 0:
            byproducts[node_name] -= used_byproduct
        cycles = math.ceil(amount_needed / output_per_cycle) if output_per_cycle else 0
        total_time = cycles * cycle_time
        using_str = f" using {using}" if using else ""
        # Track all outputs produced
        produced = {k: v * cycles for k, v in outputs.items()}
        # Calculate new byproducts (including surplus of main output)
        new_byproducts = byproducts.copy()
        byproduct_lines = []
        for out_name, produced_qty in produced.items():
            used = amount_needed if out_name == node_name else 0
            surplus = produced_qty - used if out_name == node_name else produced_qty
            if surplus > 0:
                new_byproducts[out_name] = new_byproducts.get(out_name, 0) + surplus
                if out_name != node_name:
                    byproduct_lines.append(f"{prefix}  Byproduct: {surplus}x {out_name}")
        print(f"{prefix}{node_name} (category: {node.category}, amount: {amount}, cycles: {cycles}, total_time: {total_time}s, cycle_time: {cycle_time}s, output/cycle: {output_per_cycle}{using_str})")
        for line in byproduct_lines:
            print(line)
        if not inputs:
            if _totals is not None and node.category in _totals:
                _totals[node.category][node_name] = _totals[node.category].get(node_name, 0) + amount
            return
        for input_name, qty in inputs.items():
            if input_name in visited or input_name == node_name:
                print("    " * (indent + 1) + f"{qty * cycles}x {input_name} (cycle detected)")
                continue
            self.print_production_chain(input_name, qty * cycles, indent + 1, visited | {node_name}, recipe_index=0, _totals=_totals, byproducts=new_byproducts)
        if indent == 0 and _totals is not None:
            if _totals["materials"]:
                print("\nTotal materials:")
                for k, v in _totals["materials"].items():
                    print(f"  {k}: {v}")
            if _totals["refined"]:
                print("\nTotal refined:")
                for k, v in _totals["refined"].items():
                    print(f"  {k}: {v}")
            if new_byproducts:
                print("\nByproducts:")
                for k, v in new_byproducts.items():
                    if v > 0:
                        print(f"  {k}: {v}")

    def check_all_nodes_reach_resource(self) -> List[str]:
        """
        Returns a list of node names that cannot be traced back to a resource node.
        """
        resource_nodes = set(self.get_nodes_by_category("resource"))
        unreachable = []
        for node in self.graph.nodes:
            if self.graph.nodes[node]['node'].category == 'resource':
                continue
            found_resource = False
            visited = set()
            stack = [node]
            while stack:
                current = stack.pop()
                if current in visited:
                    continue
                visited.add(current)
                if current in resource_nodes:
                    found_resource = True
                    break
                stack.extend(self.graph.predecessors(current))
            if not found_resource:
                unreachable.append(node)
        return unreachable

# Example usage (remove or comment out in production):
if __name__ == "__main__":
    g = ProductionGraph()
    g.add_node(ProductionNode("Salvage", category="resource"))
    g.add_node(ProductionNode("Sulfur", category="resource"))
    g.add_node(ProductionNode("Components", category="resource"))
    g.add_node(ProductionNode("Oil", category="resource"))
    g.add_node(ProductionNode("Coal", category="resource"))
    g.add_node(ProductionNode("Rare Metal", category="resource"))
    g.add_node(ProductionNode("Power", category="resource"))
    g.add_node(ProductionNode("BMAT", [Recipe(inputs={"Salvage": 2}, outputs={"BMAT": 1}, using={}, cycle_time=60)], category="refined"))
    g.add_node(ProductionNode("RMAT", [Recipe(inputs={"Components": 20}, outputs={"RMAT": 1}, using={}, cycle_time=60)], category="refined"))
    g.add_node(ProductionNode("Coke", [Recipe(inputs={"Coal": 200}, outputs={"Coke": 1}, using={}, cycle_time=60)], category="refined"))
    g.add_node(ProductionNode("Petrol", [Recipe(inputs={"Oil": 50}, outputs={"Petrol": 1}, using={}, cycle_time=60)], category="refined"))
    g.add_node(ProductionNode("Heavy Oil", [Recipe(inputs={"Oil": 50, "Power": 1.5}, outputs={"Heavy Oil": 1}, using={}, cycle_time=60)], category="refined"))
    g.add_node(ProductionNode("CMAT", [Recipe(inputs={"Salvage": 10, "Power": 2}, outputs={"CMAT": 1}, using={}, cycle_time=60)], category="material"))
    g.add_node(ProductionNode("Metal Beam", [Recipe(inputs={"Salvage": 25, "Power": 2}, outputs={"Metal Beam": 1}, using={}, cycle_time=60)], category="material"))
    g.add_node(ProductionNode("PCMAT", [Recipe(inputs={"CMAT": 15, "Metal Beam": 1, "Heavy Oil": 10}, outputs={"PCMAT": 1}, using={}, cycle_time=60)], category="material"))
    g.add_node(ProductionNode("RMAT", [Recipe(inputs={"Components": 20}, outputs={"RMAT": 1}, using={}, cycle_time=60)], category="material"))
    g.add_node(ProductionNode("AMAT1", [Recipe(inputs={"Salvage": 15, "Coke": 75, "Power": 2}, outputs={"AMAT1": 1}, using={}, cycle_time=60)], category="material"))
    g.add_node(ProductionNode("AMAT2", [Recipe(inputs={"Salvage": 15, "Petrol": 50, "Power": 2}, outputs={"AMAT2": 1}, using={}, cycle_time=60)], category="material"))
    g.add_node(ProductionNode("AMAT3", [Recipe(inputs={"CMAT": 3, "Sulfur": 20, "Power": 5}, outputs={"AMAT3": 1}, using={}, cycle_time=60)], category="material"))
    g.add_node(ProductionNode("AMAT4", [Recipe(inputs={"PCMAT": 1, "Heavy Oil": 66, "Power": 5}, outputs={"AMAT4": 1}, using={}, cycle_time=60)], category="material"))
    g.add_node(ProductionNode("AMAT5", [Recipe(inputs={"Steel": 3, "Coke": 245, "AMAT1": 10, "AMAT2": 10, "Power": 8}, outputs={"AMAT5": 1}, using={}, cycle_time=60)], category="material"))
    g.add_node(ProductionNode("Steel", [Recipe(inputs={"PCMAT": 3, "Coke": 200, "Sulfur": 65, "Heavy Oil": 35, "Power": 9}, outputs={"Steel": 1}, using={}, cycle_time=60)], category="material"))
    g.add_node(ProductionNode("Rare Alloy", [Recipe(inputs={"Rare Metal": 20, "PCMAT": 5, "Coke": 60, "Power": 10}, outputs={"Rare Alloy": 1}, using={}, cycle_time=60)], category="material"))
    g.add_node(ProductionNode("Thermal Shielding", [Recipe(inputs={"CMAT": 2, "AMAT4": 5, "Power": 4}, outputs={"Thermal Shielding": 1}, using={}, cycle_time=60)], category="material"))
    g.add_node(ProductionNode("Naval Hull Segments", [Recipe(inputs={"PCMAT": 60, "AMAT1": 2, "AMAT2": 2, "AMAT4": 10, "Rare Alloy": 4, "Thermal Shielding": 4, "Power": 2}, outputs={"Naval Hull Segments": 1}, using={}, cycle_time=60)], category="material"))
    g.add_node(ProductionNode("Naval Shell Plating", [Recipe(inputs={"CMAT": 2, "Thermal Shielding": 1, "Power": 2}, outputs={"Naval Shell Plating": 1}, using={}, cycle_time=60)], category="material"))
    g.add_node(ProductionNode("Naval Turbine Components", [Recipe(inputs={"AMAT5": 20, "Rare Alloy": 20, "Power": 2}, outputs={"Naval Turbine Components": 1}, using={}, cycle_time=60)], category="material"))
    g.add_node(ProductionNode("Gallagher Outlaw Mk. II", [Recipe(inputs={"PCMAT": 10, "AMAT1": 10, "AMAT4": 10, "Gallagher Brigand Mk. I": 1}, outputs={"Gallagher Outlaw Mk. II": 1}, using={}, cycle_time=60)], category="product"))
    g.add_node(ProductionNode("Gallagher Brigand Mk. I", [Recipe(inputs={"RMAT": 150}, outputs={"Gallagher Brigand Mk. I": 1}, using={}, cycle_time=60)], category="product"))
    g.add_node(ProductionNode("Callahan", [Recipe(inputs={"Naval Hull Segments": 20, "Naval Shell Plating": 20, "Naval Turbine Components": 4}, outputs={"Callahan": 1}, using={}, cycle_time=60)], category="product"))
    # Add production relationships
    g.add_production("Gallagher Outlaw Mk. II")
    print(
        g.resolve_base_materials("Gallagher Outlaw Mk. II", 2)
    )  # Should show total BMATS and RMATS needed for 2 TANKs
    g.print_production_chain("Gallagher Outlaw Mk. II", 2)  # Print the production chain for 'Silverhand - Mk. IV'

    g.add_production("Callahan")
    print(g.resolve_base_materials("Callahan", 1)) # Should show total BMATS and RMATS needed for 2 TANKs
    g.print_production_chain('Callahan', 1)  # Print the production chain for 'Silverhand - Mk. IV'

    unreachable_nodes = g.check_all_nodes_reach_resource()
    if unreachable_nodes:
        print("Unreachable nodes (cannot be traced back to a resource):", unreachable_nodes)
    else:
        print("All nodes can be traced back to a resource.")
