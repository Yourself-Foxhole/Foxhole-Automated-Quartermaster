import discord
from discord.ext import commands, tasks
from typing import Dict, List, Optional, Tuple
import cv2
import numpy as np
from datetime import datetime, timedelta
import statistics
from dataclasses import dataclass
import re
import os

@dataclass
class TechProgress:
    item_name: str
    percentage: float
    timestamp: datetime
    tier: int
    wiki_url: str

class TechTracker(commands.Cog):
    def __init__(self, bot, start_tasks: bool = True):
        self.bot = bot
        self.tech_progress: Dict[str, List[TechProgress]] = {}  # item_name -> list of progress
        if start_tasks:
            self.update_tech_predictions.start()
        
    def _calculate_progress_percentage(self, image: np.ndarray, debug_name: str = "debug") -> float:
        """Robustly calculate the progress percentage from a progress bar image."""
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # Convert to reduced grayscale (10 shades)
        reduced_gray = np.floor_divide(blurred, 31) * 31  # This will give us different shades e.g. if 10 -- (0, 26, 52, ..., 234)

        # Create debug images
        debug_img = image.copy()
        debug_gray = cv2.cvtColor(reduced_gray, cv2.COLOR_GRAY2BGR)  # Convert back to BGR for visualization

        # Get image dimensions
        img_h, img_w = gray.shape

        # Focus on the first third of the image (first column)
        first_column = reduced_gray[:, :img_w//3]
        
        # Find horizontal lines (potential progress bars)
        # Use Sobel for horizontal edge detection
        sobely = cv2.Sobel(first_column, cv2.CV_64F, 0, 1, ksize=3)
        sobely = np.absolute(sobely)
        sobely = np.uint8(255 * sobely / np.max(sobely))
        
        # Threshold to find strong horizontal edges
        _, horizontal_edges = cv2.threshold(sobely, 127, 255, cv2.THRESH_BINARY)
        
        # Find contours of potential boxes
        contours, _ = cv2.findContours(horizontal_edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter and group contours into rows
        boxes = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            # Filter based on expected box dimensions - more lenient now
            if w > 5 and h > 5 and w < img_w//4 and h < img_h//8:
                boxes.append((y, y + h))  # Store top and bottom y-coordinates
        
        # Group boxes into rows based on vertical position
        rows = []
        if boxes:
            # Sort boxes by their top y-coordinate
            boxes.sort(key=lambda x: x[0])
            
            current_row = []
            for box in boxes:
                if not current_row or box[0] - current_row[-1][1] < 30:  # More lenient vertical grouping
                    current_row.append(box)
                else:
                    if current_row:
                        # Calculate row boundaries
                        row_top = min(box[0] for box in current_row)
                        row_bottom = max(box[1] for box in current_row)
                        rows.append((row_top, row_bottom))
                    current_row = [box]
            
            # Add the last row
            if current_row:
                row_top = min(box[0] for box in current_row)
                row_bottom = max(box[1] for box in current_row)
                rows.append((row_top, row_bottom))

        # For each row, look for a horizontal white line (progress bar)
        active_row = None
        active_row_region = None
        for row_top, row_bottom in rows:
            # Extract the row region
            row_region = reduced_gray[row_top:row_bottom, :]
            
            # Look for horizontal white lines in this row
            # A progress bar should be a continuous white line
            row_center = (row_top + row_bottom) // 2
            
            # Look at a wider region around the center line
            center_region = reduced_gray[row_center-4:row_center+4, :]
            
            # Calculate adaptive threshold based on the region's statistics
            mean_val = np.mean(center_region)
            std_val = np.std(center_region)
            threshold = mean_val + std_val  # Pixels brighter than mean + std are likely part of the progress bar
            
            # Check if there's a significant bright line
            bright_pixels = np.sum(center_region > threshold)
            if bright_pixels > center_region.size * 0.15:  # If more than 15% of the region is bright
                active_row = (row_top, row_bottom)
                active_row_region = row_region
                break

        # Draw detected rows and highlight the active row
        for row_top, row_bottom in rows:
            color = (0, 255, 0) if (row_top, row_bottom) == active_row else (0, 0, 255)
            # Draw row boundaries
            cv2.line(debug_img, (0, row_top), (img_w, row_top), color, 2)
            cv2.line(debug_img, (0, row_bottom), (img_w, row_bottom), color, 2)
            cv2.line(debug_gray, (0, row_top), (img_w, row_top), color, 2)
            cv2.line(debug_gray, (0, row_bottom), (img_w, row_bottom), color, 2)
            
            # Draw row center
            row_center = (row_top + row_bottom) // 2
            cv2.line(debug_img, (0, row_center), (img_w, row_center), (255, 0, 0), 1)
            cv2.line(debug_gray, (0, row_center), (img_w, row_center), (255, 0, 0), 1)

        # Calculate progress percentage if we found an active row
        percentage = 0.0
        if active_row_region is not None:
            # Get the center region of the active row
            row_center = (active_row[0] + active_row[1]) // 2
            center_region = reduced_gray[row_center-4:row_center+4, :]
            
            # Calculate adaptive threshold
            mean_val = np.mean(center_region)
            std_val = np.std(center_region)
            threshold = mean_val + std_val
            
            # Count bright pixels in the center region
            bright_pixels = np.sum(center_region > threshold)
            total_pixels = center_region.size
            
            # Calculate percentage
            percentage = (bright_pixels / total_pixels) * 100

        # Save both debug images
        output_dir = os.path.join(os.path.dirname(__file__), '../../tests/screenshot_parser/debug_outputs')
        output_dir = os.path.abspath(output_dir)
        os.makedirs(output_dir, exist_ok=True)
        cv2.imwrite(os.path.join(output_dir, f'debug_{debug_name}.png'), debug_img)
        cv2.imwrite(os.path.join(output_dir, f'debug_{debug_name}_gray.png'), debug_gray)

        return percentage

    def _create_progress_embed(self, progress: TechProgress) -> discord.Embed:
        """Create a Discord embed for tech progress."""
        embed = discord.Embed(
            title="Tech Progress Update",
            description=f"Progress: {progress.percentage:.1f}%",
            color=discord.Color.blue()
        )
        
        # Add item details
        embed.add_field(
            name="Item",
            value=progress.item_name,
            inline=True
        )
        
        # Add tier information
        embed.add_field(
            name="Tier",
            value=str(progress.tier),
            inline=True
        )
        
        # Add wiki link
        embed.add_field(
            name="Wiki",
            value=f"[View on Wiki]({progress.wiki_url})",
            inline=True
        )
        
        return embed

    def _predict_completion_time(self, item_name: str) -> Tuple[datetime, float]:
        """Predict when an item will be completed based on progress history."""
        if item_name not in self.tech_progress or len(self.tech_progress[item_name]) < 2:
            return None, 0.0
            
        progress_data = self.tech_progress[item_name]
        
        # Calculate progress rate
        time_diffs = []
        progress_diffs = []
        
        for i in range(1, len(progress_data)):
            time_diff = (progress_data[i].timestamp - progress_data[i-1].timestamp).total_seconds() / 3600  # hours
            progress_diff = progress_data[i].percentage - progress_data[i-1].percentage
            
            if time_diff > 0:  # Avoid division by zero
                time_diffs.append(time_diff)
                progress_diffs.append(progress_diff)
        
        if not time_diffs:
            return None, 0.0
            
        # Calculate average progress rate
        avg_progress_rate = statistics.mean(progress_diffs) / statistics.mean(time_diffs)  # % per hour
        
        if avg_progress_rate <= 0:
            return None, 0.0
            
        # Calculate time to completion
        current_progress = progress_data[-1].percentage
        remaining_progress = 100 - current_progress
        hours_to_completion = remaining_progress / avg_progress_rate
        
        # Calculate confidence based on data points and variance
        confidence = min(0.95, 0.5 + (len(progress_data) * 0.1))
        
        completion_time = datetime.now() + timedelta(hours=hours_to_completion)
        return completion_time, confidence

    def _format_time_prediction(self, completion_time: datetime, confidence: float) -> str:
        """Format the time prediction in a human-readable way."""
        if not completion_time:
            return "Unable to predict completion time"
            
        now = datetime.now()
        time_diff = completion_time - now
        
        # Format the prediction
        if time_diff.days > 0:
            prediction = f"in {time_diff.days} days"
        elif time_diff.seconds >= 3600:
            hours = time_diff.seconds // 3600
            prediction = f"in {hours} hours"
        else:
            minutes = time_diff.seconds // 60
            prediction = f"in {minutes} minutes"
            
        # Add confidence level
        confidence_text = "high" if confidence > 0.8 else "medium" if confidence > 0.5 else "low"
        prediction += f" (with {confidence_text} confidence)"
        
        return prediction

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handle tech progress screenshots."""
        if message.author.bot:
            return
            
        # Check for image attachments
        for attachment in message.attachments:
            if attachment.content_type and attachment.content_type.startswith('image/'):
                # Download and process the image
                image_data = await attachment.read()
                nparr = np.frombuffer(image_data, np.uint8)
                image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                # Calculate progress
                percentage = self._calculate_progress_percentage(image)
                
                # Create progress entry
                progress = TechProgress(
                    item_name="Current Tech",  # You'll need to implement item recognition
                    percentage=percentage,
                    timestamp=message.created_at,
                    tier=1,  # You'll need to implement tier detection
                    wiki_url="https://wiki.foxhole.gg"  # You'll need to implement wiki linking
                )
                
                # Store progress
                if progress.item_name not in self.tech_progress:
                    self.tech_progress[progress.item_name] = []
                self.tech_progress[progress.item_name].append(progress)
                
                # Create and send response embed
                embed = self._create_progress_embed(progress)
                await message.channel.send(embed=embed)

    @tasks.loop(minutes=5)
    async def update_tech_predictions(self):
        """Update tech predictions periodically."""
        for guild in self.bot.guilds:
            for channel in guild.text_channels:
                if channel.name == 'tech-dashboard':
                    # Create or update tech dashboard
                    embed = discord.Embed(
                        title="Tech Progress Dashboard",
                        description="Current tech progress and predictions",
                        color=discord.Color.blue()
                    )
                    
                    for item_name, progress_list in self.tech_progress.items():
                        if not progress_list:
                            continue
                            
                        current_progress = progress_list[-1]
                        completion_time, confidence = self._predict_completion_time(item_name)
                        
                        value = f"Progress: {current_progress.percentage:.1f}%\n"
                        if completion_time:
                            prediction = self._format_time_prediction(completion_time, confidence)
                            value += f"Predicted completion: {prediction}"
                            
                        embed.add_field(
                            name=item_name,
                            value=value,
                            inline=True
                        )
                    
                    # Update or create dashboard message
                    async for message in channel.history(limit=1):
                        if message.author == self.bot.user:
                            await message.edit(embed=embed)
                            break
                    else:
                        await channel.send(embed=embed)

    @commands.command()
    async def tech_status(self, ctx, item_name: Optional[str] = None):
        """Get the current status of tech progress."""
        if not item_name:
            # Show all tech progress
            embed = discord.Embed(
                title="Tech Progress Status",
                description="Current progress for all tracked items",
                color=discord.Color.blue()
            )
            
            for item_name, progress_list in self.tech_progress.items():
                if not progress_list:
                    continue
                    
                current_progress = progress_list[-1]
                completion_time, confidence = self._predict_completion_time(item_name)
                
                value = f"Progress: {current_progress.percentage:.1f}%\n"
                if completion_time:
                    prediction = self._format_time_prediction(completion_time, confidence)
                    value += f"Predicted completion: {prediction}"
                    
                embed.add_field(
                    name=item_name,
                    value=value,
                    inline=True
                )
        else:
            # Show specific item progress
            if item_name not in self.tech_progress or not self.tech_progress[item_name]:
                await ctx.send(f"No progress data found for {item_name}")
                return
                
            progress_list = self.tech_progress[item_name]
            current_progress = progress_list[-1]
            completion_time, confidence = self._predict_completion_time(item_name)
            
            embed = discord.Embed(
                title=f"Tech Progress: {item_name}",
                description=f"Current progress: {current_progress.percentage:.1f}%",
                color=discord.Color.blue()
            )
            
            if completion_time:
                prediction = self._format_time_prediction(completion_time, confidence)
                embed.add_field(
                    name="Predicted Completion",
                    value=prediction,
                    inline=False
                )
            
            # Add progress history
            if len(progress_list) > 1:
                history = "\n".join([
                    f"{p.timestamp.strftime('%H:%M')}: {p.percentage:.1f}%"
                    for p in progress_list[-5:]  # Show last 5 updates
                ])
                embed.add_field(
                    name="Recent Progress",
                    value=history,
                    inline=False
                )
        
        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(TechTracker(bot)) 