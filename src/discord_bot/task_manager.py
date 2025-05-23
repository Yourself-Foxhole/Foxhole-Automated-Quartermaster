import discord
from discord.ext import commands, tasks
from typing import Dict, List, Optional
import asyncio
from datetime import datetime, timedelta

class TaskManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.task_boards = {}  # message_id -> {task_id -> emoji}
        self.task_threads = {}  # task_id -> thread_id
        
        # Configurable limits
        self.max_tasks_per_board = 20  # Maximum tasks per embed
        self.max_embeds_per_thread = 5  # Maximum embeds per thread
        self.max_total_tasks = 200  # Maximum total outstanding tasks
        
        # Task organization
        self.task_types = ['resource', 'backline', 'midline', 'frontline', 'facility']
        self.task_statuses = ['pending', 'claimed', 'completed', 'cancelled']
        self.task_priorities = ['highest', 'expedited', 'normal']
        
        # Board types and their mutual exclusivity rules
        self.board_types = {
            'type': {
                'name': 'Task Type',
                'values': self.task_types,
                'mutually_exclusive': True
            },
            'status': {
                'name': 'Status',
                'values': self.task_statuses,
                'mutually_exclusive': True
            },
            'priority': {
                'name': 'Priority',
                'values': self.task_priorities,
                'mutually_exclusive': True
            },
            'region': {
                'name': 'Region',
                'values': [],  # Will be populated from game data
                'mutually_exclusive': True
            }
        }
        
        self.cleanup_tasks.start()

    def set_limits(self, tasks_per_board: int = None, embeds_per_thread: int = None, max_total_tasks: int = None):
        """Update the configurable limits."""
        if tasks_per_board is not None:
            self.max_tasks_per_board = min(tasks_per_board, 20)  # Discord's reaction limit
        if embeds_per_thread is not None:
            self.max_embeds_per_thread = embeds_per_thread
        if max_total_tasks is not None:
            self.max_total_tasks = max_total_tasks

    @tasks.loop(minutes=5)
    async def cleanup_tasks(self):
        """Clean up expired tasks and update task boards."""
        self.bot.scanner.cleanup_expired_tasks()
        await self.update_all_task_boards()

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """Handle task claiming via reactions."""
        if user.bot:
            return
            
        if str(reaction.emoji) in self.task_boards:
            task_id = self.task_boards[str(reaction.emoji)]
            await self.claim_task(task_id, user)

    def _should_task_appear_on_board(self, task: dict, board_type: str, board_value: str) -> bool:
        """
        Determine if a task should appear on a specific board.
        Respects mutual exclusivity rules.
        """
        if board_type not in self.board_types:
            return False
            
        # Get the task's value for this board type
        task_value = None
        if board_type == 'type':
            task_value = task['type']
        elif board_type == 'status':
            task_value = task['status']
        elif board_type == 'priority':
            task_value = task['details'].get('priority', 'normal')
        elif board_type == 'region':
            task_value = task['details'].get('region')
            
        # If the board type is mutually exclusive, task must match exactly
        if self.board_types[board_type]['mutually_exclusive']:
            return task_value == board_value
            
        # For non-mutually exclusive boards, check if the task has this attribute
        return task_value is not None

    async def _create_task_board_embed(self, board_type: str, board_value: str) -> discord.Embed:
        """Create an embed for the task board with proper task filtering."""
        board_info = self.board_types[board_type]
        embed = discord.Embed(
            title=f"{board_info['name']}: {board_value.title()}",
            description="React to claim a task",
            color=self._get_priority_color(board_value if board_type == 'priority' else 'normal')
        )
        
        # Get all tasks that should appear on this board
        tasks = [
            task for task in self.bot.scanner.active_tasks.values()
            if self._should_task_appear_on_board(task, board_type, board_value)
        ]
        
        if not tasks:
            embed.add_field(
                name="No Tasks",
                value=f"No tasks for {board_value} {board_type}.",
                inline=False
            )
            return embed
            
        # Sort tasks by priority first, then creation time
        def task_sort_key(task):
            priority_order = {'highest': 0, 'expedited': 1, 'normal': 2}
            return (
                priority_order.get(task['details'].get('priority', 'normal'), 2),
                task['created_at']
            )
            
        tasks.sort(key=task_sort_key)
        
        # Add tasks to embed
        for i, task in enumerate(tasks[:self.max_tasks_per_board]):
            emoji = self._get_task_emoji(i)
            self.task_boards[task['id']] = emoji
            
            # Format task details
            details = task['details']
            value = f"**Type:** {task['type']}\n"
            value += f"**Priority:** {details.get('priority', 'normal')}\n"
            value += f"**Location:** {details.get('location', 'N/A')}\n"
            value += f"**Created:** {task['created_at'].strftime('%H:%M:%S')}\n"
            
            if task['expires_at']:
                value += f"**Expires:** {task['expires_at'].strftime('%H:%M:%S')}\n"
                
            embed.add_field(
                name=f"{emoji} {details.get('title', 'Untitled Task')}",
                value=value,
                inline=False
            )
            
        return embed

    async def create_task_organization(self, channel: discord.TextChannel) -> None:
        """Create the initial task organization structure."""
        # Create single category for the bot
        category = await channel.guild.create_category("FAQ Bot")
        
        # Create channels for different purposes
        channels = {
            'task-board': await category.create_text_channel("task-board"),
            'resource-tasks': await category.create_text_channel("resource-tasks"),
            'backline-tasks': await category.create_text_channel("backline-tasks"),
            'midline-tasks': await category.create_text_channel("midline-tasks"),
            'frontline-tasks': await category.create_text_channel("frontline-tasks"),
            'facility-tasks': await category.create_text_channel("facility-tasks"),
            'task-status': await category.create_text_channel("task-status"),
            'task-priority': await category.create_text_channel("task-priority"),
            # Dashboard channels
            'system-overview': await category.create_text_channel("system-overview"),
            'backline-dashboard': await category.create_text_channel("backline-dashboard"),
            'midline-dashboard': await category.create_text_channel("midline-dashboard"),
            'frontline-dashboard': await category.create_text_channel("frontline-dashboard"),
            'activity-logs': await category.create_text_channel("activity-logs"),
            'tech-dashboard': await category.create_text_channel("tech-dashboard")
        }
        
        # Create task type boards
        for task_type in self.task_types:
            channel = channels[f'{task_type}-tasks']
            embed = await self._create_task_board_embed('type', task_type)
            message = await channel.send(embed=embed)
            self.task_boards[message.id] = {}
            
            # Add reactions for tasks
            for task_id, emoji in self.task_boards[message.id].items():
                await message.add_reaction(emoji)
        
        # Create status overview
        status_channel = channels['task-status']
        for status in self.task_statuses:
            embed = await self._create_task_board_embed('status', status)
            message = await status_channel.send(embed=embed)
            self.task_boards[message.id] = {}
            
            # Add reactions for tasks
            for task_id, emoji in self.task_boards[message.id].items():
                await message.add_reaction(emoji)
        
        # Create priority overview
        priority_channel = channels['task-priority']
        for priority in self.task_priorities:
            embed = await self._create_task_board_embed('priority', priority)
            message = await priority_channel.send(embed=embed)
            self.task_boards[message.id] = {}
            
            # Add reactions for tasks
            for task_id, emoji in self.task_boards[message.id].items():
                await message.add_reaction(emoji)
        
        # Create main task board
        main_board = channels['task-board']
        embed = discord.Embed(
            title="Task Board Overview",
            description="Welcome to the FAQ Bot Task Board!\n\n" +
                       "**Available Task Types:**\n" +
                       "• Resource Tasks - Raw material gathering\n" +
                       "• Backline Tasks - Production and manufacturing\n" +
                       "• Midline Tasks - Transport between depots\n" +
                       "• Frontline Tasks - Frontline supply delivery\n" +
                       "• Facility Tasks - Facility management\n\n" +
                       "Use the channels above to view specific task types.\n" +
                       "React to a task to claim it.",
            color=discord.Color.blue()
        )
        await main_board.send(embed=embed)
        
        # Initialize dashboards
        await self.initialize_dashboards(channels)

    async def initialize_dashboards(self, channels: dict) -> None:
        """Initialize all dashboard channels with their initial embeds."""
        # System Overview Dashboard
        system_overview = await self._create_system_overview_embed()
        await channels['system-overview'].send(embed=system_overview)
        
        # Backline Dashboard
        backline_dashboard = await self._create_backline_dashboard_embed()
        await channels['backline-dashboard'].send(embed=backline_dashboard)
        
        # Midline Dashboard
        midline_dashboard = await self._create_midline_dashboard_embed()
        await channels['midline-dashboard'].send(embed=midline_dashboard)
        
        # Frontline Dashboard
        frontline_dashboard = await self._create_frontline_dashboard_embed()
        await channels['frontline-dashboard'].send(embed=frontline_dashboard)
        
        # Tech Dashboard
        tech_dashboard = await self._create_tech_dashboard_embed()
        await channels['tech-dashboard'].send(embed=tech_dashboard)

    async def _create_system_overview_embed(self) -> discord.Embed:
        """Create the system overview dashboard embed."""
        tasks = self.bot.scanner.active_tasks.values()
        
        # Count tasks by type and status
        task_counts = {
            'backline': {'pending': 0, 'in_progress': 0, 'completed': 0},
            'midline': {'pending': 0, 'in_progress': 0, 'completed': 0},
            'frontline': {'pending': 0, 'in_progress': 0, 'completed': 0}
        }
        
        for task in tasks:
            if task['type'] in task_counts:
                status = 'in_progress' if task['status'] == 'claimed' else task['status']
                task_counts[task['type']][status] += 1
        
        embed = discord.Embed(
            title="System Overview",
            description="Network health metrics and request distribution",
            color=discord.Color.blue()
        )
        
        # Add task distribution
        for task_type, counts in task_counts.items():
            value = f"Pending: {counts['pending']}\n"
            value += f"In Progress: {counts['in_progress']}\n"
            value += f"Completed: {counts['completed']}"
            embed.add_field(
                name=f"{task_type.title()} Tasks",
                value=value,
                inline=True
            )
        
        return embed

    async def _create_backline_dashboard_embed(self) -> discord.Embed:
        """Create the backline dashboard embed."""
        tasks = [t for t in self.bot.scanner.active_tasks.values() if t['type'] == 'backline']
        
        # Group tasks by production state
        production_states = {
            'waiting_resources': [],
            'in_production': [],
            'completed': []
        }
        
        for task in tasks:
            if task['status'] == 'completed':
                production_states['completed'].append(task)
            elif task['details'].get('has_resources', False):
                production_states['in_production'].append(task)
            else:
                production_states['waiting_resources'].append(task)
        
        embed = discord.Embed(
            title="Backline Production Dashboard",
            description="Current production status and queues",
            color=discord.Color.green()
        )
        
        for state, tasks in production_states.items():
            value = "\n".join([f"• {t['details'].get('title', 'Untitled')}" for t in tasks[:5]])
            if len(tasks) > 5:
                value += f"\n... and {len(tasks) - 5} more"
            embed.add_field(
                name=state.replace('_', ' ').title(),
                value=value or "No tasks",
                inline=False
            )
        
        return embed

    async def _create_midline_dashboard_embed(self) -> discord.Embed:
        """Create the midline dashboard embed."""
        tasks = [t for t in self.bot.scanner.active_tasks.values() if t['type'] == 'midline']
        
        # Group by transport type
        transport_types = {
            'trucks': [],
            'containers': [],
            'ships': [],
            'trains': []
        }
        
        for task in tasks:
            transport_type = task['details'].get('transport_type', 'trucks')
            if transport_type in transport_types:
                transport_types[transport_type].append(task)
        
        embed = discord.Embed(
            title="Midline Transport Dashboard",
            description="Pending movements and vehicle allocation",
            color=discord.Color.orange()
        )
        
        for transport_type, tasks in transport_types.items():
            value = "\n".join([f"• {t['details'].get('title', 'Untitled')}" for t in tasks[:5]])
            if len(tasks) > 5:
                value += f"\n... and {len(tasks) - 5} more"
            embed.add_field(
                name=transport_type.title(),
                value=value or "No tasks",
                inline=True
            )
        
        return embed

    async def _create_frontline_dashboard_embed(self) -> discord.Embed:
        """Create the frontline dashboard embed."""
        tasks = [t for t in self.bot.scanner.active_tasks.values() if t['type'] == 'frontline']
        
        # Group by region
        regions = {}
        for task in tasks:
            region = task['details'].get('region', 'Unknown')
            if region not in regions:
                regions[region] = []
            regions[region].append(task)
        
        embed = discord.Embed(
            title="Frontline Supply Dashboard",
            description="Supply/demand by region and shortage alerts",
            color=discord.Color.red()
        )
        
        for region, tasks in regions.items():
            value = "**Shortages:**\n"
            shortages = [t for t in tasks if t['details'].get('is_shortage', False)]
            value += "\n".join([f"• {t['details'].get('title', 'Untitled')}" for t in shortages[:3]])
            
            value += "\n\n**Usage Rates:**\n"
            for task in tasks[:3]:
                rate = task['details'].get('usage_rate', 'Unknown')
                value += f"• {task['details'].get('item', 'Unknown')}: {rate}\n"
            
            embed.add_field(
                name=region,
                value=value,
                inline=True
            )
        
        return embed

    async def _create_tech_dashboard_embed(self) -> discord.Embed:
        """Create the tech dashboard embed."""
        # This would be populated from your tech tracking system
        embed = discord.Embed(
            title="Tech Research Dashboard",
            description="Research progress and production unlock predictions",
            color=discord.Color.purple()
        )
        
        # Add placeholder fields
        embed.add_field(
            name="Current Research",
            value="No active research",
            inline=False
        )
        
        embed.add_field(
            name="Upcoming Unlocks",
            value="No upcoming unlocks",
            inline=False
        )
        
        return embed

    @tasks.loop(minutes=5)
    async def update_dashboards(self):
        """Update all dashboard embeds periodically."""
        for guild in self.bot.guilds:
            for channel in guild.text_channels:
                if channel.name == 'system-overview':
                    embed = await self._create_system_overview_embed()
                    await self._update_channel_embed(channel, embed)
                elif channel.name == 'backline-dashboard':
                    embed = await self._create_backline_dashboard_embed()
                    await self._update_channel_embed(channel, embed)
                elif channel.name == 'midline-dashboard':
                    embed = await self._create_midline_dashboard_embed()
                    await self._update_channel_embed(channel, embed)
                elif channel.name == 'frontline-dashboard':
                    embed = await self._create_frontline_dashboard_embed()
                    await self._update_channel_embed(channel, embed)
                elif channel.name == 'tech-dashboard':
                    embed = await self._create_tech_dashboard_embed()
                    await self._update_channel_embed(channel, embed)

    async def _update_channel_embed(self, channel: discord.TextChannel, new_embed: discord.Embed):
        """Update the first embed in a channel."""
        async for message in channel.history(limit=1):
            if message.author == self.bot.user:
                await message.edit(embed=new_embed)
                break

    async def create_task_thread(self, task: dict, user: discord.User) -> discord.Thread:
        """Create a detailed task thread when a task is claimed."""
        # Find the appropriate task channel
        task_channel = None
        for channel in self.bot.get_all_channels():
            if channel.name == f"{task['type']}-tasks" and isinstance(channel, discord.TextChannel):
                task_channel = channel
                break
                
        if not task_channel:
            return None
            
        # Create thread for the task
        thread = await task_channel.create_thread(
            name=f"Task {task['id'][:8]} - {task['type']}",
            auto_archive_duration=1440
        )
        
        # Create initial task details embed
        embed = discord.Embed(
            title=f"Task {task['id'][:8]}",
            description=task['details'].get('description', 'No description'),
            color=self._get_priority_color(task['details'].get('priority', 'normal'))
        )
        
        # Add task details
        embed.add_field(name="Type", value=task['type'])
        embed.add_field(name="Status", value=task['status'])
        embed.add_field(name="Priority", value=task['details'].get('priority', 'normal'))
        embed.add_field(name="Created", value=task['created_at'].strftime("%Y-%m-%d %H:%M:%S"))
        embed.add_field(name="Assigned To", value=user.mention)
        
        if task['expires_at']:
            embed.add_field(name="Expires", value=task['expires_at'].strftime("%Y-%m-%d %H:%M:%S"))
            
        # Add task-specific details
        if task['type'] == 'midline':
            embed.add_field(name="Vehicle Type", value="Please specify your vehicle type")
            embed.add_field(name="Capacity", value="Please specify your available capacity")
        elif task['type'] == 'frontline':
            embed.add_field(name="Data Freshness", value="Please verify data is less than 15 minutes old")
            embed.add_field(name="Usage Rate", value="Please provide current usage rate")
        elif task['type'] == 'backline':
            embed.add_field(name="Production Queue", value="Please specify your production queue")
            embed.add_field(name="Input Resources", value="Please verify input resources")
        elif task['type'] == 'facility':
            embed.add_field(name="Building", value="Please specify the building")
            embed.add_field(name="Queue Type", value="Please specify if this is a public or private queue")
            
        await thread.send(embed=embed)
        
        # Add task tracking message
        tracking_msg = await thread.send("Task progress will be tracked here...")
        self.task_threads[task['id']] = {
            'thread_id': thread.id,
            'tracking_msg_id': tracking_msg.id
        }
        
        return thread

    async def update_task_thread(self, task_id: str, update_type: str, details: str) -> None:
        """Update a task thread with new information."""
        if task_id not in self.task_threads:
            return
            
        thread_info = self.task_threads[task_id]
        thread = self.bot.get_channel(thread_info['thread_id'])
        if not thread:
            return
            
        # Update tracking message
        tracking_msg = await thread.fetch_message(thread_info['tracking_msg_id'])
        current_content = tracking_msg.content
        
        # Add new update
        timestamp = datetime.now().strftime("%H:%M:%S")
        new_content = f"{current_content}\n[{timestamp}] {update_type}: {details}"
        
        await tracking_msg.edit(content=new_content)

    async def claim_task(self, task_id: str, user: discord.User) -> None:
        """Create a thread for a claimed task."""
        task = self.bot.scanner.get_task_details(task_id)
        if not task:
            return
            
        # Create task thread
        thread = await self.create_task_thread(task, user)
        if not thread:
            return
            
        # Update task status
        self.bot.scanner.update_task_status(task_id, 'claimed', str(user.id))
        
        # Update all task boards
        await self.update_all_task_boards()
        
        # Send confirmation
        await thread.send(f"{user.mention} has claimed this task. Please provide any required information.")

    @commands.command()
    async def task(self, ctx, action: str, task_id: Optional[str] = None, *args):
        """Task management commands."""
        if action == "list":
            # List tasks
            tasks = self.bot.scanner.active_tasks.values()
            if not tasks:
                await ctx.send("No active tasks.")
                return
                
            embed = discord.Embed(
                title="Active Tasks",
                color=discord.Color.blue()
            )
            
            for task in tasks:
                value = f"**Type:** {task['type']}\n"
                value += f"**Status:** {task['status']}\n"
                value += f"**Created:** {task['created_at'].strftime('%Y-%m-%d %H:%M:%S')}\n"
                
                if task['expires_at']:
                    value += f"**Expires:** {task['expires_at'].strftime('%Y-%m-%d %H:%M:%S')}\n"
                    
                embed.add_field(
                    name=f"Task {task['id'][:8]}",
                    value=value,
                    inline=False
                )
                
            await ctx.send(embed=embed)
            
        elif action == "claim" and task_id:
            # Claim task
            await self.claim_task(task_id, ctx.author)
            
        elif action == "complete" and task_id:
            # Complete task
            if self.bot.scanner.update_task_status(task_id, 'completed'):
                await ctx.send(f"Task {task_id} marked as completed.")
                await self.update_all_task_boards()
            else:
                await ctx.send("Task not found or already completed.")
                
        elif action == "cancel" and task_id:
            # Cancel task
            if self.bot.scanner.update_task_status(task_id, 'cancelled'):
                await ctx.send(f"Task {task_id} cancelled.")
                await self.update_all_task_boards()
            else:
                await ctx.send("Task not found or already cancelled.")
                
        elif action == "update" and task_id:
            # Update task details
            if not args:
                await ctx.send("Please provide update details.")
                return
                
            update_type = args[0]
            details = " ".join(args[1:])
            
            await self.update_task_thread(task_id, update_type, details)
            await ctx.send(f"Task {task_id} updated with {update_type}: {details}")
            
        elif action == "priority" and task_id:
            # Update task priority
            if not args:
                await ctx.send("Please specify a priority level (highest/expedited/normal).")
                return
                
            priority = args[0].lower()
            if priority not in self.task_priorities:
                await ctx.send(f"Invalid priority. Available: {', '.join(self.task_priorities)}")
                return
                
            task = self.bot.scanner.get_task_details(task_id)
            if not task:
                await ctx.send("Task not found.")
                return
                
            task['details']['priority'] = priority
            await self.update_all_task_boards()
            await ctx.send(f"Task {task_id} priority updated to {priority}.")

    @commands.command()
    async def dashboard(self, ctx, action: str, *args):
        """Dashboard management commands."""
        if action == "refresh":
            # Force refresh all dashboards
            await self.update_dashboards()
            await ctx.send("All dashboards refreshed.")
            
        elif action == "filter":
            # Filter dashboard view
            if not args:
                await ctx.send("Please specify a filter type and value.")
                return
                
            filter_type = args[0].lower()
            filter_value = " ".join(args[1:])
            
            if filter_type == "region":
                # Filter by region
                await self._filter_dashboard_by_region(ctx.channel, filter_value)
            elif filter_type == "priority":
                # Filter by priority
                await self._filter_dashboard_by_priority(ctx.channel, filter_value)
            elif filter_type == "type":
                # Filter by task type
                await self._filter_dashboard_by_type(ctx.channel, filter_value)
            else:
                await ctx.send(f"Invalid filter type. Available: region, priority, type")
                
        elif action == "clear":
            # Clear dashboard filters
            await self._clear_dashboard_filters(ctx.channel)
            await ctx.send("Dashboard filters cleared.")

    async def _filter_dashboard_by_region(self, channel: discord.TextChannel, region: str):
        """Filter dashboard to show only tasks in a specific region."""
        tasks = [t for t in self.bot.scanner.active_tasks.values() 
                if t['details'].get('region') == region]
        
        embed = discord.Embed(
            title=f"Tasks in {region}",
            description=f"Showing tasks for region: {region}",
            color=discord.Color.blue()
        )
        
        for task in tasks:
            value = f"**Type:** {task['type']}\n"
            value += f"**Status:** {task['status']}\n"
            value += f"**Priority:** {task['details'].get('priority', 'normal')}\n"
            
            embed.add_field(
                name=f"Task {task['id'][:8]}",
                value=value,
                inline=True
            )
            
        await self._update_channel_embed(channel, embed)

    async def _filter_dashboard_by_priority(self, channel: discord.TextChannel, priority: str):
        """Filter dashboard to show only tasks of a specific priority."""
        if priority not in self.task_priorities:
            return
            
        tasks = [t for t in self.bot.scanner.active_tasks.values() 
                if t['details'].get('priority') == priority]
        
        embed = discord.Embed(
            title=f"{priority.title()} Priority Tasks",
            description=f"Showing {priority} priority tasks",
            color=self._get_priority_color(priority)
        )
        
        for task in tasks:
            value = f"**Type:** {task['type']}\n"
            value += f"**Status:** {task['status']}\n"
            value += f"**Region:** {task['details'].get('region', 'Unknown')}\n"
            
            embed.add_field(
                name=f"Task {task['id'][:8]}",
                value=value,
                inline=True
            )
            
        await self._update_channel_embed(channel, embed)

    async def _filter_dashboard_by_type(self, channel: discord.TextChannel, task_type: str):
        """Filter dashboard to show only tasks of a specific type."""
        if task_type not in self.task_types:
            return
            
        tasks = [t for t in self.bot.scanner.active_tasks.values() if t['type'] == task_type]
        
        embed = discord.Embed(
            title=f"{task_type.title()} Tasks",
            description=f"Showing {task_type} tasks",
            color=discord.Color.blue()
        )
        
        for task in tasks:
            value = f"**Status:** {task['status']}\n"
            value += f"**Priority:** {task['details'].get('priority', 'normal')}\n"
            value += f"**Region:** {task['details'].get('region', 'Unknown')}\n"
            
            embed.add_field(
                name=f"Task {task['id'][:8]}",
                value=value,
                inline=True
            )
            
        await self._update_channel_embed(channel, embed)

    async def _clear_dashboard_filters(self, channel: discord.TextChannel):
        """Clear all dashboard filters and restore default view."""
        if channel.name == 'system-overview':
            embed = await self._create_system_overview_embed()
        elif channel.name == 'backline-dashboard':
            embed = await self._create_backline_dashboard_embed()
        elif channel.name == 'midline-dashboard':
            embed = await self._create_midline_dashboard_embed()
        elif channel.name == 'frontline-dashboard':
            embed = await self._create_frontline_dashboard_embed()
        elif channel.name == 'tech-dashboard':
            embed = await self._create_tech_dashboard_embed()
        else:
            return
            
        await self._update_channel_embed(channel, embed)

    @commands.command()
    async def task_limits(self, ctx, tasks_per_board: Optional[int] = None, 
                         embeds_per_thread: Optional[int] = None, 
                         max_total_tasks: Optional[int] = None):
        """Configure task board limits."""
        self.set_limits(tasks_per_board, embeds_per_thread, max_total_tasks)
        
        embed = discord.Embed(
            title="Task Board Limits",
            color=discord.Color.blue()
        )
        embed.add_field(name="Tasks per Board", value=str(self.max_tasks_per_board))
        embed.add_field(name="Embeds per Thread", value=str(self.max_embeds_per_thread))
        embed.add_field(name="Max Total Tasks", value=str(self.max_total_tasks))
        
        await ctx.send(embed=embed)

    @commands.command()
    async def task_org(self, ctx):
        """Create or recreate the task organization structure."""
        await self.create_task_organization(ctx.channel)
        await ctx.send("Task organization structure created!")

    @commands.command()
    async def task_move(self, ctx, task_id: str, new_status: str):
        """Move a task to a different status board."""
        if new_status not in self.task_statuses:
            await ctx.send(f"Invalid status. Available statuses: {', '.join(self.task_statuses)}")
            return
            
        task = self.bot.scanner.get_task_details(task_id)
        if not task:
            await ctx.send("Task not found.")
            return
            
        # Update task status
        if self.bot.scanner.update_task_status(task_id, new_status):
            await ctx.send(f"Task {task_id} moved to {new_status} status.")
            # Update all relevant task boards
            await self.update_all_task_boards()
        else:
            await ctx.send("Failed to update task status.")

    async def update_all_task_boards(self) -> None:
        """Update all task boards across all channels."""
        for guild in self.bot.guilds:
            for channel in guild.text_channels:
                # Check if this channel has any task boards
                async for message in channel.history(limit=100):
                    if message.id in self.task_boards:
                        # Determine task type from the first task
                        tasks = list(self.task_boards[message.id].keys())
                        if tasks:
                            task = self.bot.scanner.get_task_details(tasks[0])
                            if task:
                                await self.update_task_board(channel, task['type'])
                        break

    def _get_priority_color(self, priority: str) -> discord.Color:
        """Get the color for a priority level."""
        colors = {
            'highest': discord.Color.red(),
            'expedited': discord.Color.orange(),
            'normal': discord.Color.blue()
        }
        return colors.get(priority, discord.Color.blue())

    def _get_task_emoji(self, index: int) -> str:
        """Get an emoji for a task based on its index."""
        emojis = [
            '1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟',
            '🅰️', '🅱️', '🅲️', '🅳️', '🅴️', '🅵️', '🅶️', '🅷️', '🅸️', '🅹️'
        ]
        return emojis[index % len(emojis)]

    async def update_task_board(self, channel: discord.TextChannel, task_type: str) -> None:
        """Update the task board with current tasks."""
        # Find all task board messages in this channel
        messages_to_update = []
        async for message in channel.history(limit=100):
            if message.id in self.task_boards:
                messages_to_update.append(message)
                
        if not messages_to_update:
            return
            
        # Get new embeds
        new_embeds = await self._create_task_board_embed(task_type)
        
        # Update existing messages or create new ones as needed
        for i, embed in enumerate(new_embeds):
            if i < len(messages_to_update):
                # Update existing message
                message = messages_to_update[i]
                await message.edit(embed=embed)
                
                # Update reactions
                await message.clear_reactions()
                for task_id, emoji in self.task_boards[message.id].items():
                    await message.add_reaction(emoji)
            else:
                # Create new message
                message = await channel.send(embed=embed)
                self.task_boards[message.id] = {}
                
                # Add reactions
                for task_id, emoji in self.task_boards[message.id].items():
                    await message.add_reaction(emoji)
                    
        # Delete excess messages
        for message in messages_to_update[len(new_embeds):]:
            await message.delete()
            del self.task_boards[message.id]

def setup(bot):
    bot.add_cog(TaskManager(bot)) 