"""
Jinja2-based presentation layer for Discord embeds.

This module provides the EmbedRenderer class which uses Jinja2 templates to render
Discord embeds for various message types (task updates, inventory deltas, alerts, etc.).
The renderer separates presentation logic from business logic, making it easy to
customize message formatting without changing core functionality.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import disnake
from jinja2 import Environment, FileSystemLoader, Template, TemplateNotFound, select_autoescape


class EmbedRenderer:
    """
    Renders Discord embeds using Jinja2 templates.
    
    This class provides a bridge between data objects (Tasks, inventory deltas, alerts)
    and Discord embeds by loading and rendering appropriate Jinja2 templates.
    Templates are expected to generate JSON that can be converted to Discord embed objects.
    """
    
    def __init__(self, templates_dir: Optional[Path] = None) -> None:
        """
        Initialize the EmbedRenderer.
        
        Args:
            templates_dir: Path to the templates directory. If None, uses default location.
        """
        self.logger = logging.getLogger(__name__)
        
        # Set up templates directory
        if templates_dir is None:
            templates_dir = Path(__file__).parent / "templates"
        
        self.templates_dir = Path(templates_dir)
        
        # Initialize Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Add custom filters
        self._register_filters()
        
        self.logger.info("EmbedRenderer initialized with templates directory: %s", self.templates_dir)
    
    def _register_filters(self) -> None:
        """Register custom Jinja2 filters for template use."""
        
        def datetime_format(value: datetime, format_string: str = "%Y-%m-%d %H:%M UTC") -> str:
            """Format datetime objects."""
            if isinstance(value, datetime):
                return value.strftime(format_string)
            return str(value)
        
        def item_emoji(item_name: str) -> str:
            """Add appropriate emoji for Foxhole items."""
            # Simple emoji mapping for common Foxhole items
            emoji_map = {
                "7.62mm": "🔫",
                "9mm": "🔫", 
                "40mm": "💥",
                "120mm": "💥",
                "150mm": "💥",
                "bandages": "🩹",
                "trauma kit": "🏥",
                "blood plasma": "🩸",
                "bmats": "🧱",
                "emats": "⚡",
                "hemats": "💎",
                "shirts": "👔",
                "diesel": "⛽",
                "petrol": "⛽",
                "coal": "⚫",
                "salvage": "🔧",
                "components": "⚙️",
                "sulfur": "🟡",
                "explosive materials": "💥",
                "refined materials": "🧱",
                "heavy explosive materials": "💎",
            }
            
            item_lower = item_name.lower()
            for key, emoji in emoji_map.items():
                if key in item_lower:
                    return f"{emoji} {item_name}"
            
            return item_name
        
        # Register the filters
        self.env.filters['datetime_format'] = datetime_format
        self.env.filters['item_emoji'] = item_emoji
    
    def render_task_update(self, task: Any) -> disnake.Embed:
        """
        Render a task update embed.
        
        Args:
            task: Task object with attributes like task_id, name, status, etc.
            
        Returns:
            Discord embed object ready for sending.
            
        Raises:
            TemplateNotFound: If the task_update template doesn't exist.
            ValueError: If template rendering fails or produces invalid JSON.
        """
        return self._render_template("task_update.jinja2", {"task": task})
    
    def render_inventory_delta(self, 
                             facility_name: str,
                             changes: Dict[str, int],
                             timestamp: Optional[datetime] = None,
                             delta_type: str = "change",
                             **kwargs: Any) -> disnake.Embed:
        """
        Render an inventory delta embed.
        
        Args:
            facility_name: Name of the facility where changes occurred.
            changes: Dictionary mapping item names to quantity changes.
            timestamp: When the change occurred (defaults to now).
            delta_type: Type of change ("increase", "decrease", "change").
            **kwargs: Additional context variables for the template.
            
        Returns:
            Discord embed object ready for sending.
            
        Raises:
            TemplateNotFound: If the inventory_delta template doesn't exist.
            ValueError: If template rendering fails or produces invalid JSON.
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        # Calculate total change and determine delta type if not specified
        total_change = sum(changes.values())
        if delta_type == "change":
            delta_type = "increase" if total_change > 0 else "decrease" if total_change < 0 else "neutral"
        
        context = {
            "facility_name": facility_name,
            "changes": changes,
            "timestamp": timestamp,
            "delta_type": delta_type,
            "total_change": total_change,
            **kwargs
        }
        
        return self._render_template("inventory_delta.jinja2", context)
    
    def render_alert(self,
                    alert_title: str,
                    alert_message: str,
                    alert_type: str = "info",
                    timestamp: Optional[datetime] = None,
                    **kwargs: Any) -> disnake.Embed:
        """
        Render an alert embed.
        
        Args:
            alert_title: Title of the alert.
            alert_message: Main alert message.
            alert_type: Type of alert ("critical", "warning", "info").
            timestamp: When the alert occurred (defaults to now).
            **kwargs: Additional context variables for the template.
            
        Returns:
            Discord embed object ready for sending.
            
        Raises:
            TemplateNotFound: If the alert template doesn't exist.
            ValueError: If template rendering fails or produces invalid JSON.
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        context = {
            "alert_title": alert_title,
            "alert_message": alert_message,
            "alert_type": alert_type,
            "timestamp": timestamp,
            **kwargs
        }
        
        return self._render_template("alert.jinja2", context)
    
    def render_custom(self, template_name: str, context: Dict[str, Any]) -> disnake.Embed:
        """
        Render a custom template with provided context.
        
        Args:
            template_name: Name of the template file (with .jinja2 extension).
            context: Dictionary containing template variables.
            
        Returns:
            Discord embed object ready for sending.
            
        Raises:
            TemplateNotFound: If the specified template doesn't exist.
            ValueError: If template rendering fails or produces invalid JSON.
        """
        return self._render_template(template_name, context)
    
    def _render_template(self, template_name: str, context: Dict[str, Any]) -> disnake.Embed:
        """
        Load and render a template with the given context.
        
        Args:
            template_name: Name of the template file.
            context: Dictionary containing template variables.
            
        Returns:
            Discord embed object.
            
        Raises:
            TemplateNotFound: If the template file doesn't exist.
            ValueError: If template rendering fails or produces invalid JSON.
        """
        try:
            # Load template
            template = self.env.get_template(template_name)
            
            # Render template
            rendered_json = template.render(**context)
            
            # Parse JSON
            embed_data = json.loads(rendered_json)
            
            # Create Discord embed
            embed = disnake.Embed(
                title=embed_data.get("title", ""),
                description=embed_data.get("description", ""),
                color=embed_data.get("color", 0x0099ff)
            )
            
            # Add fields
            for field in embed_data.get("fields", []):
                embed.add_field(
                    name=field.get("name", ""),
                    value=field.get("value", ""),
                    inline=field.get("inline", False)
                )
            
            # Add footer
            if "footer" in embed_data:
                footer = embed_data["footer"]
                embed.set_footer(
                    text=footer.get("text", ""),
                    icon_url=footer.get("icon_url")
                )
            
            # Add timestamp
            if "timestamp" in embed_data and embed_data["timestamp"]:
                try:
                    # Handle ISO format timestamp
                    timestamp_str = embed_data["timestamp"]
                    if timestamp_str:
                        embed.timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    self.logger.warning("Invalid timestamp format in template: %s", embed_data["timestamp"])
            
            # Add thumbnail
            if "thumbnail" in embed_data:
                embed.set_thumbnail(url=embed_data["thumbnail"])
            
            # Add image
            if "image" in embed_data:
                embed.set_image(url=embed_data["image"])
            
            # Add author
            if "author" in embed_data:
                author = embed_data["author"]
                embed.set_author(
                    name=author.get("name", ""),
                    url=author.get("url"),
                    icon_url=author.get("icon_url")
                )
            
            return embed
            
        except TemplateNotFound as e:
            self.logger.error("Template not found: %s", template_name)
            raise TemplateNotFound(f"Template '{template_name}' not found in {self.templates_dir}")
        
        except json.JSONDecodeError as e:
            self.logger.error("Failed to parse JSON from template %s: %s", template_name, e)
            raise ValueError(f"Template '{template_name}' produced invalid JSON: {e}")
        
        except Exception as e:
            self.logger.error("Failed to render template %s: %s", template_name, e)
            raise ValueError(f"Template rendering failed for '{template_name}': {e}")
    
    def list_templates(self) -> list[str]:
        """
        List all available templates.
        
        Returns:
            List of template filenames.
        """
        if not self.templates_dir.exists():
            return []
        
        return [f.name for f in self.templates_dir.glob("*.jinja2")]
    
    def template_exists(self, template_name: str) -> bool:
        """
        Check if a template exists.
        
        Args:
            template_name: Name of the template file.
            
        Returns:
            True if the template exists, False otherwise.
        """
        return (self.templates_dir / template_name).exists()