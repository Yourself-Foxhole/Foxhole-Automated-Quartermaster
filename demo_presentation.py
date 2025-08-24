"""
Demo script to test the Jinja2 presentation layer functionality.
This script demonstrates the EmbedRenderer without requiring a Discord connection.
"""

from datetime import datetime, timezone
from src.presentation import EmbedRenderer
from services.tasks.task import Task, TaskStatus


def demo_presentation_layer():
    """Demonstrate the presentation layer functionality."""
    print("🎯 Foxhole Automated Quartermaster - Presentation Layer Demo")
    print("=" * 60)
    
    # Initialize the renderer
    renderer = EmbedRenderer()
    
    # Demo 1: Task Update
    print("\n📋 Demo 1: Task Update Rendering")
    print("-" * 40)
    
    task = Task(
        task_id="PROD-042",
        name="Produce 40mm for Frontline",
        task_type="production",
        status=TaskStatus.IN_PROGRESS,
        base_priority=3.5,
        created_at=datetime(2024, 1, 15, 14, 30, tzinfo=timezone.utc),
        metadata={
            "facility": "Safe House Assembly",
            "target_quantity": 500,
            "current_progress": 325,
            "estimated_completion": "25 minutes"
        }
    )
    task.add_order("ORD-789")
    task.add_order("ORD-790")
    
    try:
        embed = renderer.render_task_update(task)
        print(f"✅ Task embed created: {embed.title}")
        print(f"   Description: {embed.description}")
        print(f"   Fields: {len(embed.fields)} fields")
        print(f"   Color: #{embed.color.value:06x}")
    except Exception as e:
        print(f"❌ Task rendering failed: {e}")
    
    # Demo 2: Inventory Delta
    print("\n📊 Demo 2: Inventory Delta Rendering")
    print("-" * 40)
    
    changes = {
        "7.62mm": -250,
        "40mm": +100,
        "Bandages": +75,
        "BMats": -400,
        "Diesel": +150,
        "Shirts": -50
    }
    
    try:
        embed = renderer.render_inventory_delta(
            facility_name="Reaching Trail Depot", 
            changes=changes,
            region="Deadlands",
            critical_items=["7.62mm", "BMats"],
            production_impact="Ammunition production may be affected by low BMats"
        )
        print(f"✅ Inventory embed created: {embed.title}")
        print(f"   Description: {embed.description}")
        print(f"   Fields: {len(embed.fields)} fields")
        print(f"   Color: #{embed.color.value:06x}")
    except Exception as e:
        print(f"❌ Inventory rendering failed: {e}")
    
    # Demo 3: Critical Alert
    print("\n🚨 Demo 3: Critical Alert Rendering")
    print("-" * 40)
    
    try:
        embed = renderer.render_alert(
            alert_title="Critical Supply Shortage",
            alert_message="Multiple critical supply shortages detected at frontline bases",
            alert_type="critical",
            location="Deadlands - Multiple FOBs",
            priority="urgent",
            affected_items=["7.62mm", "40mm", "Bandages", "Shirts"],
            supply_shortage={"7.62mm": 800, "40mm": 300, "Bandages": 200},
            recommended_actions=[
                "Immediate logi run from Westgate depot",
                "Redirect production from Safe House facility",
                "Contact clan logistics team for emergency resupply"
            ],
            frontline_impact="Critical operations will be compromised within 1 hour",
            estimated_resolution="30-45 minutes with immediate action",
            assigned_to="Logistics Team Alpha",
            alert_id="FAQ-2024-CRIT-001"
        )
        print(f"✅ Alert embed created: {embed.title}")
        print(f"   Description: {embed.description}")
        print(f"   Fields: {len(embed.fields)} fields")
        print(f"   Color: #{embed.color.value:06x}")
    except Exception as e:
        print(f"❌ Alert rendering failed: {e}")
    
    # Demo 4: Template Management
    print("\n📁 Demo 4: Template Management")
    print("-" * 40)
    
    templates = renderer.list_templates()
    print(f"Available templates: {len(templates)}")
    for template in templates:
        print(f"  • {template}")
    
    # Demo 5: Custom Filters
    print("\n🎨 Demo 5: Custom Filter Testing")
    print("-" * 40)
    
    # Test the item emoji filter in a simple template
    try:
        simple_template_content = '''
        {
          "title": "{{ item_name | item_emoji }}",
          "description": "Testing custom filters",
          "color": 3066993,
          "fields": [
            {
              "name": "Item",
              "value": "{{ item_name | item_emoji }}",
              "inline": true
            },
            {
              "name": "Formatted Date",
              "value": "{{ test_date | datetime_format('%B %d, %Y') }}",
              "inline": true
            }
          ]
        }
        '''
        
        # Write temporary template for testing
        temp_template_path = renderer.templates_dir / "temp_test.jinja2"
        temp_template_path.write_text(simple_template_content)
        
        test_context = {
            "item_name": "7.62mm",
            "test_date": datetime(2024, 1, 15, 14, 30, tzinfo=timezone.utc)
        }
        
        embed = renderer.render_custom("temp_test.jinja2", test_context)
        print(f"✅ Custom template test: {embed.title}")
        print(f"   Item field: {embed.fields[0].value}")
        print(f"   Date field: {embed.fields[1].value}")
        
        # Clean up
        temp_template_path.unlink()
        
    except Exception as e:
        print(f"❌ Custom filter test failed: {e}")
    
    print("\n🎉 Presentation layer demo completed!")
    print(f"   Templates directory: {renderer.templates_dir}")
    print(f"   Ready for Discord integration via src/bot.py")


if __name__ == "__main__":
    demo_presentation_layer()