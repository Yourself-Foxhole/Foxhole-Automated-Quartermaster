import sys
from pathlib import Path
# Ensure project root is in sys.path for imports
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

import logging
from datetime import datetime, timezone
from presentation.renderer import EmbedRenderer

# Set up logging to print to console
logging.basicConfig(level=logging.INFO)

# Instantiate the renderer
renderer = EmbedRenderer()

print("--- Renderer Demo Script Start ---")

# List available templates
print("Available templates:", renderer.list_templates())

# Check if specific templates exist
for template in ["task_update.jinja2", "inventory_delta.jinja2", "alert.jinja2"]:
    print(f"Template '{template}' exists:", renderer.template_exists(template))

# Sample data for rendering
class DummyTask:
    def __init__(self):
        self.task_id = 123
        self.name = "Deliver BMats"
        self.status = "in_progress"
        self.assigned_to = "QuartermasterBot"
        self.created_at = datetime(2025, 8, 25, 12, 0, tzinfo=timezone.utc)
        self.updated_at = datetime(2025, 8, 25, 13, 0, tzinfo=timezone.utc)

task = DummyTask()

# Render task update
try:
    embed = renderer.render_task_update(task)
    print("Task Update Embed:", embed.to_dict())
except Exception as e:
    print("Error rendering task update:", e)

# Render inventory delta
try:
    changes = {"BMats": 100, "EMats": -50}
    embed = renderer.render_inventory_delta("Factory Alpha", changes)
    print("Inventory Delta Embed:", embed.to_dict())
except Exception as e:
    print("Error rendering inventory delta:", e)

# Render alert
try:
    embed = renderer.render_alert(
        alert_title="Critical Stockpile Low",
        alert_message="BMats below threshold at Factory Alpha!",
        alert_type="critical"
    )
    print("Alert Embed:", embed.to_dict())
except Exception as e:
    print("Error rendering alert:", e)

# Render custom template (if exists)
try:
    if renderer.template_exists("production_report.jinja2"):
        context = {"report_title": "Production Report", "items": ["BMats", "EMats"]}
        embed = renderer.render_custom("production_report.jinja2", context)
        print("Production Report Embed:", embed.to_dict())
except Exception as e:
    print("Error rendering custom template:", e)

print("--- Renderer Demo Script End ---")
