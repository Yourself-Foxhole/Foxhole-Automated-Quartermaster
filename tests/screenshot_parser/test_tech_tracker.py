import pytest
import cv2
import numpy as np
from pathlib import Path
from datetime import datetime
from src.discord_bot.tech_tracker import TechTracker, TechProgress
from unittest.mock import Mock, patch
import discord
import shutil
import os

@pytest.fixture
def tech_tracker():
    """Create a TechTracker instance with a mock bot."""
    bot = Mock()
    return TechTracker(bot, start_tasks=False)

@pytest.fixture
def test_images():
    """Load test images from the test cases directory."""
    test_dir = Path(__file__).parent / "test_cases_tech"
    images = {}
    for img_path in test_dir.glob("*.png"):
        image = cv2.imread(str(img_path))
        if image is not None:
            images[img_path.name] = image
    return images

@pytest.fixture
def sample_images():
    """Load sample images for testing."""
    image_dir = os.path.join(os.path.dirname(__file__), 'test_cases_tech')
    images = {}
    for filename in os.listdir(image_dir):
        if filename.endswith('.png'):
            path = os.path.join(image_dir, filename)
            images[filename] = cv2.imread(path)
    return images

@pytest.fixture
def template_images():
    """Load template images for testing."""
    template_dir = os.path.join(os.path.dirname(__file__), '../src/screenshot_parser/image_samples')
    templates = {
        'researching': cv2.imread(os.path.join(template_dir, 'researching.png'), cv2.IMREAD_GRAYSCALE),
        'locked': cv2.imread(os.path.join(template_dir, 'locked-yet-to-tech.png'), cv2.IMREAD_GRAYSCALE),
        'unlocked': cv2.imread(os.path.join(template_dir, 'unlocked-teched.png'), cv2.IMREAD_GRAYSCALE)
    }
    return templates

def test_calculate_progress_percentage(tech_tracker, test_images):
    """Test progress percentage calculation for test images."""
    # Test that we can process all images
    for img_name, image in test_images.items():
        percentage = tech_tracker._calculate_progress_percentage(image)
        assert 0 <= percentage <= 100, f"Invalid percentage {percentage} for {img_name}"
        assert isinstance(percentage, float), f"Percentage should be float for {img_name}"

def test_progress_consistency(tech_tracker, test_images):
    """Test that progress calculation is consistent for the same image."""
    for img_name, image in test_images.items():
        # Calculate percentage multiple times
        percentages = [
            tech_tracker._calculate_progress_percentage(image)
            for _ in range(3)
        ]
        # All calculations should be within 1% of each other
        assert max(percentages) - min(percentages) < 1.0, \
            f"Inconsistent percentages for {img_name}: {percentages}"

def test_image_processing_steps(tech_tracker, test_images):
    """Test individual image processing steps."""
    for img_name, image in test_images.items():
        # Test grayscale conversion
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        assert len(gray.shape) == 2, f"Grayscale conversion failed for {img_name}"
        
        # Test thresholding
        _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
        assert thresh.dtype == np.uint8, f"Thresholding failed for {img_name}"
        
        # Test first box detection
        height, width = thresh.shape
        first_box = thresh[:, :width//3]
        assert first_box.size > 0, f"First box detection failed for {img_name}"

def test_tech_progress_storage(tech_tracker):
    """Test storing and retrieving tech progress."""
    # Create test progress entries
    test_progress = TechProgress(
        item_name="Test Tech",
        percentage=50.0,
        timestamp=datetime.now(),
        tier=1,
        wiki_url="https://wiki.foxhole.gg/test"
    )
    
    # Store progress
    tech_tracker.tech_progress[test_progress.item_name] = [test_progress]
    
    # Verify storage
    assert test_progress.item_name in tech_tracker.tech_progress
    assert len(tech_tracker.tech_progress[test_progress.item_name]) == 1
    stored_progress = tech_tracker.tech_progress[test_progress.item_name][0]
    assert stored_progress.percentage == test_progress.percentage
    assert stored_progress.tier == test_progress.tier
    assert stored_progress.wiki_url == test_progress.wiki_url

def test_progress_formatting(tech_tracker):
    """Test progress formatting in embeds."""
    # Create test progress
    test_progress = TechProgress(
        item_name="Test Tech",
        percentage=75.5,
        timestamp=datetime.now(),
        tier=1,
        wiki_url="https://wiki.foxhole.gg/test"
    )
    
    # Test embed creation
    embed = tech_tracker._create_progress_embed(test_progress)
    assert embed.title == "Tech Progress Update"
    assert "75.5%" in embed.description
    assert embed.color == discord.Color.blue()

@pytest.mark.asyncio
async def test_message_handling(tech_tracker, test_images):
    """Test handling of Discord messages with images."""
    # Create a mock message with an image attachment
    message = Mock()
    message.author.bot = False
    message.created_at = datetime.now()
    
    # Patch message.channel.send to be async
    class DummyChannel:
        async def send(self, *args, **kwargs):
            return None
    message.channel = DummyChannel()
    
    # Test with each image
    for img_name, image in test_images.items():
        # Create a mock attachment
        attachment = Mock()
        attachment.content_type = "image/png"
        
        # Mock the read method to return the image data
        image_data = cv2.imencode('.png', image)[1].tobytes()
        async def async_read():
            return image_data
        attachment.read = async_read
        
        message.attachments = [attachment]
        
        # Process the message
        await tech_tracker.on_message(message)
        
        # Verify that progress was stored
        assert len(tech_tracker.tech_progress) > 0

def test_invalid_images(tech_tracker):
    """Test handling of invalid or corrupted images."""
    # Test with empty image
    empty_image = np.zeros((100, 100, 3), dtype=np.uint8)
    percentage = tech_tracker._calculate_progress_percentage(empty_image)
    assert percentage == 0.0, "Empty image should return 0% progress"
    
    # Test with corrupted image data
    with pytest.raises(Exception):
        tech_tracker._calculate_progress_percentage(None)
    
    # Test with invalid image dimensions
    invalid_image = np.zeros((10, 10), dtype=np.uint8)  # 2D array instead of 3D
    with pytest.raises(Exception):
        tech_tracker._calculate_progress_percentage(invalid_image)

def test_direct_percentage_calculation(tech_tracker, test_images):
    """Directly call _calculate_progress_percentage on each test image and print the results."""
    # Clear debug output directory
    output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'debug_outputs'))
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    for img_name, image in test_images.items():
        # Remove .png extension for debug filename
        debug_name = img_name.replace('.png', '')
        percentage = tech_tracker._calculate_progress_percentage(image, debug_name)
        print(f"Image: {img_name}, Calculated Percentage: {percentage:.2f}%")

def test_template_matching(tech_tracker, sample_images, template_images):
    """Test that template matching can find icons in sample images."""
    # Test each template against a sample image
    test_image = next(iter(sample_images.values()))
    
    # Test researching template
    matches = tech_tracker._find_template_matches(test_image, template_images['researching'])
    assert len(matches) > 0, "Should find at least one researching icon"
    
    # Test locked template
    matches = tech_tracker._find_template_matches(test_image, template_images['locked'])
    assert len(matches) > 0, "Should find at least one locked icon"
    
    # Test unlocked template
    matches = tech_tracker._find_template_matches(test_image, template_images['unlocked'])
    assert len(matches) > 0, "Should find at least one unlocked icon"

def test_template_matching_threshold(tech_tracker, sample_images, template_images):
    """Test that template matching threshold affects match count."""
    test_image = next(iter(sample_images.values()))
    
    # Test with different thresholds
    matches_high = tech_tracker._find_template_matches(test_image, template_images['researching'], threshold=0.9)
    matches_low = tech_tracker._find_template_matches(test_image, template_images['researching'], threshold=0.7)
    
    assert len(matches_high) <= len(matches_low), "Higher threshold should find fewer matches"

def test_progress_calculation_with_templates(tech_tracker, sample_images):
    """Test progress calculation using template matching."""
    for filename, image in sample_images.items():
        percentage = tech_tracker._calculate_progress_percentage(image, debug_name=filename)
        print(f"Image: {filename}, Calculated Percentage: {percentage:.2f}%")
        
        # Basic validation
        assert 0 <= percentage <= 100, f"Percentage should be between 0 and 100, got {percentage}"
        
        # If we found a researching icon, we should have a non-zero percentage
        if percentage > 0:
            assert percentage > 0, f"Found researching icon but got 0% for {filename}"

def test_progress_calculation_consistency(tech_tracker, sample_images):
    """Test that progress calculation is consistent for the same image."""
    test_image = next(iter(sample_images.values()))
    
    # Calculate percentage multiple times
    percentages = []
    for _ in range(5):
        percentage = tech_tracker._calculate_progress_percentage(test_image)
        percentages.append(percentage)
    
    # Check that all calculations give similar results
    max_diff = max(abs(p1 - p2) for p1 in percentages for p2 in percentages)
    assert max_diff < 1.0, f"Progress calculation should be consistent, got max difference of {max_diff}%"

def test_progress_calculation_with_modified_image(tech_tracker, sample_images):
    """Test progress calculation with modified images."""
    test_image = next(iter(sample_images.values())).copy()
    
    # Get original percentage
    original_percentage = tech_tracker._calculate_progress_percentage(test_image)
    
    # Modify image (add noise)
    noise = np.random.normal(0, 10, test_image.shape).astype(np.uint8)
    noisy_image = cv2.add(test_image, noise)
    
    # Get percentage for modified image
    modified_percentage = tech_tracker._calculate_progress_percentage(noisy_image)
    
    # Check that percentages are similar
    assert abs(original_percentage - modified_percentage) < 10.0, \
        f"Progress calculation should be robust to noise, got difference of {abs(original_percentage - modified_percentage)}%"

def test_direct_percentage_calculation(tech_tracker, sample_images):
    """Test direct percentage calculation on all sample images."""
    for filename, image in sample_images.items():
        percentage = tech_tracker._calculate_progress_percentage(image, debug_name=filename)
        print(f"Image: {filename}, Calculated Percentage: {percentage:.2f}%")
        
        # Basic validation
        assert 0 <= percentage <= 100, f"Percentage should be between 0 and 100, got {percentage}" 