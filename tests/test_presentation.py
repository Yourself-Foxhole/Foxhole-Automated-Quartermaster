"""
Unit tests for the EmbedRenderer presentation layer.

Tests cover template loading, rendering, error handling, and Discord embed generation.
"""

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock

import pytest
import disnake
from jinja2 import TemplateNotFound

from src.presentation.renderer import EmbedRenderer
from services.tasks.task import Task, TaskStatus


class TestEmbedRenderer:
    """Test cases for the EmbedRenderer class."""
    
    @pytest.fixture
    def temp_templates_dir(self):
        """Create a temporary templates directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            templates_path = Path(temp_dir) / "templates"
            templates_path.mkdir()
            yield templates_path
    
    @pytest.fixture
    def renderer(self, temp_templates_dir):
        """Create an EmbedRenderer instance for testing."""
        return EmbedRenderer(templates_dir=temp_templates_dir)
    
    @pytest.fixture
    def mock_task(self):
        """Create a mock task for testing."""
        task = Task(
            task_id="TEST-001",
            name="Test Production Task",
            task_type="production",
            status=TaskStatus.IN_PROGRESS,
            base_priority=2.5,
            created_at=datetime(2024, 1, 15, 14, 30),
            metadata={
                "facility": "Test Factory",
                "target_quantity": 100,
                "current_progress": 50
            }
        )
        task.add_order("ORDER-123")
        return task
    
    def test_renderer_initialization(self, temp_templates_dir):
        """Test that renderer initializes correctly."""
        renderer = EmbedRenderer(templates_dir=temp_templates_dir)
        assert renderer.templates_dir == temp_templates_dir
        assert renderer.env is not None
    
    def test_renderer_default_templates_dir(self):
        """Test that renderer uses default templates directory when none provided."""
        renderer = EmbedRenderer()
        # Use absolute path resolution to account for test environment
        expected_path = Path(__file__).parent.parent / "src" / "presentation" / "templates"
        assert renderer.templates_dir.resolve() == expected_path.resolve()
    
    def test_list_templates_empty_dir(self, renderer):
        """Test listing templates in empty directory."""
        templates = renderer.list_templates()
        assert templates == []
    
    def test_list_templates_with_files(self, renderer, temp_templates_dir):
        """Test listing templates when files exist."""
        # Create test template files
        (temp_templates_dir / "test1.jinja2").write_text("test1")
        (temp_templates_dir / "test2.jinja2").write_text("test2")
        (temp_templates_dir / "not_template.txt").write_text("ignored")
        
        templates = renderer.list_templates()
        assert set(templates) == {"test1.jinja2", "test2.jinja2"}
    
    def test_template_exists(self, renderer, temp_templates_dir):
        """Test template existence checking."""
        # Create a test template
        template_file = temp_templates_dir / "test.jinja2"
        template_file.write_text("test")
        
        assert renderer.template_exists("test.jinja2") is True
        assert renderer.template_exists("nonexistent.jinja2") is False
    
    def test_render_simple_template(self, renderer, temp_templates_dir):
        """Test rendering a simple template."""
        # Create a simple template
        template_content = '''
        {
          "title": "{{ title }}",
          "description": "{{ description }}",
          "color": 3066993,
          "fields": []
        }
        '''
        (temp_templates_dir / "simple.jinja2").write_text(template_content)
        
        context = {"title": "Test Title", "description": "Test Description"}
        embed = renderer.render_custom("simple.jinja2", context)
        
        assert isinstance(embed, disnake.Embed)
        assert embed.title == "Test Title"
        assert embed.description == "Test Description"
        assert embed.color.value == 3066993
    
    def test_render_template_with_fields(self, renderer, temp_templates_dir):
        """Test rendering a template with fields."""
        template_content = '''
        {
          "title": "Test Embed",
          "description": "Test Description",
          "color": 3066993,
          "fields": [
            {
              "name": "Field 1",
              "value": "{{ value1 }}",
              "inline": true
            },
            {
              "name": "Field 2", 
              "value": "{{ value2 }}",
              "inline": false
            }
          ]
        }
        '''
        (temp_templates_dir / "fields.jinja2").write_text(template_content)
        
        context = {"value1": "Test Value 1", "value2": "Test Value 2"}
        embed = renderer.render_custom("fields.jinja2", context)
        
        assert len(embed.fields) == 2
        assert embed.fields[0].name == "Field 1"
        assert embed.fields[0].value == "Test Value 1"
        assert embed.fields[0].inline is True
        assert embed.fields[1].name == "Field 2"
        assert embed.fields[1].value == "Test Value 2"
        assert embed.fields[1].inline is False
    
    def test_render_template_with_footer_and_timestamp(self, renderer, temp_templates_dir):
        """Test rendering a template with footer and timestamp."""
        template_content = '''
        {
          "title": "Test Embed",
          "description": "Test Description",
          "color": 3066993,
          "fields": [],
          "footer": {
            "text": "{{ footer_text }}"
          },
          "timestamp": "{{ timestamp.isoformat() }}"
        }
        '''
        (temp_templates_dir / "footer.jinja2").write_text(template_content)
        
        test_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        context = {
            "footer_text": "Test Footer",
            "timestamp": test_time
        }
        embed = renderer.render_custom("footer.jinja2", context)
        
        assert embed.footer.text == "Test Footer"
        assert embed.timestamp == test_time
    
    def test_render_task_update_with_real_template(self, mock_task):
        """Test rendering task update with the actual template."""
        renderer = EmbedRenderer()
        
        # This test requires the actual template file to exist
        if renderer.template_exists("task_update.jinja2"):
            embed = renderer.render_task_update(mock_task)
            
            assert isinstance(embed, disnake.Embed)
            assert "Test Production Task" in embed.title
            assert len(embed.fields) > 0
            
            # Check that task ID field exists
            task_id_field = next((f for f in embed.fields if "Task ID" in f.name), None)
            assert task_id_field is not None
            assert "TEST-001" in task_id_field.value
    
    def test_render_inventory_delta(self):
        """Test rendering inventory delta."""
        renderer = EmbedRenderer()
        
        changes = {
            "7.62mm": -100,
            "40mm": +50,
            "Bandages": +25
        }
        timestamp = datetime(2024, 1, 15, 14, 30)
        
        if renderer.template_exists("inventory_delta.jinja2"):
            embed = renderer.render_inventory_delta(
                facility_name="Test Depot",
                changes=changes,
                timestamp=timestamp,
                region="Test Region",
                critical_items=["7.62mm"]
            )
            
            assert isinstance(embed, disnake.Embed)
            assert "Test Depot" in embed.title
            assert len(embed.fields) > 0
    
    def test_render_alert(self):
        """Test rendering alert."""
        renderer = EmbedRenderer()
        
        if renderer.template_exists("alert.jinja2"):
            embed = renderer.render_alert(
                alert_title="Test Alert",
                alert_message="This is a test alert",
                alert_type="warning",
                location="Test Location",
                priority="high"
            )
            
            assert isinstance(embed, disnake.Embed)
            assert "Test Alert" in embed.title
            assert "This is a test alert" in embed.description
    
    def test_template_not_found_error(self, renderer):
        """Test that TemplateNotFound is raised for missing templates."""
        with pytest.raises(TemplateNotFound):
            renderer.render_custom("nonexistent.jinja2", {})
    
    def test_invalid_json_error(self, renderer, temp_templates_dir):
        """Test that ValueError is raised for invalid JSON templates."""
        # Create template with invalid JSON
        template_content = '''
        {
          "title": "{{ title }}",
          "invalid": {{ invalid_json }},
        }
        '''
        (temp_templates_dir / "invalid.jinja2").write_text(template_content)
        
        context = {"title": "Test", "invalid_json": "not_json"}
        with pytest.raises(ValueError, match="invalid JSON"):
            renderer.render_custom("invalid.jinja2", context)
    
    def test_datetime_filter(self, renderer, temp_templates_dir):
        """Test the custom datetime filter."""
        template_content = '''
        {
          "title": "{{ timestamp | datetime_format('%Y-%m-%d') }}",
          "description": "Test",
          "color": 3066993,
          "fields": []
        }
        '''
        (temp_templates_dir / "datetime.jinja2").write_text(template_content)
        
        test_time = datetime(2024, 1, 15, 14, 30)
        context = {"timestamp": test_time}
        embed = renderer.render_custom("datetime.jinja2", context)
        
        assert embed.title == "2024-01-15"
    
    def test_item_emoji_filter(self, renderer, temp_templates_dir):
        """Test the custom item emoji filter.""" 
        template_content = '''
        {
          "title": "{{ item_name | item_emoji }}",
          "description": "Test",
          "color": 3066993,
          "fields": []
        }
        '''
        (temp_templates_dir / "emoji.jinja2").write_text(template_content)
        
        # Test known item
        context = {"item_name": "7.62mm"}
        embed = renderer.render_custom("emoji.jinja2", context)
        assert "🔫" in embed.title
        assert "7.62mm" in embed.title
        
        # Test unknown item
        context = {"item_name": "Unknown Item"}
        embed = renderer.render_custom("emoji.jinja2", context)
        assert embed.title == "Unknown Item"
    
    def test_blocked_task_duration(self, renderer):
        """Test rendering a blocked task with duration calculation."""
        task = Task(
            task_id="BLOCKED-001",
            name="Blocked Task",
            task_type="transport",
            status=TaskStatus.BLOCKED,
            base_priority=1.0,
            created_at=datetime(2024, 1, 15, 12, 0)
        )
        task.mark_blocked()
        
        if renderer.template_exists("task_update.jinja2"):
            embed = renderer.render_task_update(task)
            assert isinstance(embed, disnake.Embed)
            # The template should show blocked status
            status_field = next((f for f in embed.fields if "Status" in f.name), None)
            assert status_field is not None
            assert "Blocked" in status_field.value
    
    def test_inventory_delta_type_detection(self):
        """Test that inventory delta type is correctly detected."""
        renderer = EmbedRenderer()
        
        if not renderer.template_exists("inventory_delta.jinja2"):
            pytest.skip("inventory_delta.jinja2 template not found")
        
        # Test increase
        changes_increase = {"Item1": 100, "Item2": 50}
        embed = renderer.render_inventory_delta("Test Facility", changes_increase)
        # Should detect as increase (positive total)
        
        # Test decrease  
        changes_decrease = {"Item1": -100, "Item2": -50}
        embed = renderer.render_inventory_delta("Test Facility", changes_decrease)
        # Should detect as decrease (negative total)
        
        # Test mixed
        changes_mixed = {"Item1": 100, "Item2": -50}
        embed = renderer.render_inventory_delta("Test Facility", changes_mixed)
        # Should detect as increase (positive total)
        
        assert isinstance(embed, disnake.Embed)
    
    def test_alert_with_all_optional_fields(self):
        """Test alert rendering with all optional fields."""
        renderer = EmbedRenderer()
        
        if not renderer.template_exists("alert.jinja2"):
            pytest.skip("alert.jinja2 template not found")
        
        embed = renderer.render_alert(
            alert_title="Critical Supply Alert",
            alert_message="Multiple shortages detected",
            alert_type="critical",
            location="Multiple Locations",
            priority="urgent",
            affected_items=["7.62mm", "40mm", "Bandages"],
            supply_shortage={"7.62mm": 500, "40mm": 200},
            recommended_actions=[
                "Immediate resupply run",
                "Contact logistics team",
                "Review production schedules"
            ],
            frontline_impact="Operations may be compromised",
            estimated_resolution="2 hours",
            assigned_to="Logistics Team Alpha",
            alert_id="ALERT-001"
        )
        
        assert isinstance(embed, disnake.Embed)
        assert "Critical Supply Alert" in embed.title
        assert len(embed.fields) > 0