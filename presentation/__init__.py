"""
Presentation layer for the Foxhole Automated Quartermaster.

This module provides Jinja2-based templating for Discord embeds and other
presentation components. It separates presentation logic from business logic,
making it easy to customize message formatting without changing core functionality.
"""

from .renderer import EmbedRenderer

__all__ = ["EmbedRenderer"]