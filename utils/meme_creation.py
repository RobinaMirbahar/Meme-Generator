from PIL import Image, ImageDraw, ImageFont, ImageSequence
import textwrap
import os
from io import BytesIO
from typing import Union, List, Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_font(font_size: int) -> ImageFont.FreeTypeFont:
    """Load Impact font with multiple fallback options"""
    font_paths = [
        "assets/Impact.ttf",  # Local project font
        "/usr/share/fonts/truetype/msttcorefonts/Impact.ttf",  # Linux
        "/Library/Fonts/Impact.ttf",  # macOS
        "C:/Windows/Fonts/impact.ttf"  # Windows
    ]
    
    for path in font_paths:
        try:
            if os.path.exists(path):
                return ImageFont.truetype(path, font_size)
        except Exception as e:
            logger.warning(f"Failed to load font from {path}: {str(e)}")
            continue
    
    logger.warning("Impact font not found, using default font")
    try:
        return ImageFont.truetype("arial.ttf", font_size)
    except:
        return ImageFont.load_default()

def calculate_text_dimensions(font: ImageFont.FreeTypeFont, text: str, wrap_width: int) -> tuple:
    """Calculate text dimensions after wrapping"""
    lines = textwrap.wrap(text, width=wrap_width)
    max_width = 0
    total_height = 0
    
    for line in lines:
        bbox = font.getbbox(line)
        line_width = bbox[2] - bbox[0]
        line_height = bbox[3] - bbox[1]
        max_width = max(max_width, line_width)
        total_height += line_height + 10  # 10px line spacing
    
    return lines, max_width, total_height

def add_text_to_frame(
    draw: ImageDraw.Draw,
    lines: List[str],
    font: ImageFont.FreeTypeFont,
    img_width: int,
    img_height: int,
    position: str,
    text_color: str,
    outline_color: str,
    y_offset: int = 0
) -> None:
    """Add text with outline to an image frame"""
    _, _, total_height = calculate_text_dimensions(font, " ".join(lines), 15)
    
    # Calculate Y position
    if position == "top":
        y = int(img_height * 0.1) + y_offset
    elif position == "center":
        y = (img_height - total_height) // 2 + y_offset
    else:  # bottom
        y = img_height - total_height - int(img_height * 0.1) + y_offset

    # Draw each line
    for line in lines:
        bbox = font.getbbox(line)
        text_width = bbox[2] - bbox[0]
        x = (img_width - text_width) // 2

        # Draw outline (8 directions for smoothness)
        for dx, dy in [(-2,-2), (0,-2), (2,-2),
                       (-2,0),          (2,0),
                       (-2,2),  (0,2),  (2,2)]:
            draw.text((x+dx, y+dy), line, font=font, fill=outline_color)

        # Draw main text
        draw.text((x, y), line, font=font, fill=text_color)
        y += (bbox[3] - bbox[1]) + 10  # Move to next line

def add_meme_text(
    img: Image.Image,
    text: str,
    position: str = "bottom",
    text_color: str = "#FFFFFF",
    outline_color: str = "#000000",
    animation_effect: str = "none"
) -> Union[Image.Image, List[Image.Image]]:
    """Add meme text to image with optional animations"""
    try:
        if not isinstance(img, Image.Image):
            raise ValueError("Invalid image provided")
        
        img = img.convert("RGB")
        text = str(text).upper()
        frames = []
        
        # Calculate dynamic font size
        base_size = min(80, max(30, int(img.width / 12)))
        font = load_font(base_size)
        
        # Text wrapping
        avg_char_width = base_size * 0.6
        wrap_width = max(5, min(20, int(img.width * 0.9 / avg_char_width)))
        lines, _, total_height = calculate_text_dimensions(font, text, wrap_width)
        
        # Handle animation effects
        if animation_effect == "fade_in":
            for alpha in range(0, 255, 25):
                frame = img.copy()
                overlay = Image.new("RGBA", frame.size, (0,0,0,0))
                draw = ImageDraw.Draw(overlay)
                rgba_text = text_color + f"{alpha:02x}"
                rgba_outline = outline_color + f"{alpha:02x}"
                add_text_to_frame(draw, lines, font, img.width, img.height, 
                                position, rgba_text, rgba_outline)
                frame.paste(overlay, (0,0), overlay)
                frames.append(frame)
            return frames
        
        elif animation_effect == "slide_up":
            for i in range(10):
                frame = img.copy()
                draw = ImageDraw.Draw(frame)
                offset = int((img.height * 0.2) * (10-i)/10)
                add_text_to_frame(draw, lines, font, img.width, img.height,
                                position, text_color, outline_color, offset)
                frames.append(frame)
            return frames
        
        elif animation_effect == "typing":
            current_text = ""
            for char in text:
                current_text += char
                temp_lines, _, _ = calculate_text_dimensions(font, current_text, wrap_width)
                frame = img.copy()
                draw = ImageDraw.Draw(frame)
                add_text_to_frame(draw, temp_lines, font, img.width, img.height,
                                position, text_color, outline_color)
                frames.append(frame)
            # Add 5 frames of the final result
            frames.extend([frames[-1]] * 5)
            return frames
        
        # Default case (no animation)
        frame = img.copy()
        draw = ImageDraw.Draw(frame)
        add_text_to_frame(draw, lines, font, img.width, img.height,
                         position, text_color, outline_color)
        return frame

    except Exception as e:
        logger.error(f"Error in add_meme_text: {str(e)}")
        raise

def create_gif(frames: List[Image.Image], duration: int = 100) -> bytes:
    """Create GIF from frames with error handling"""
    try:
        if not frames:
            raise ValueError("No frames provided for GIF creation")
            
        if len(frames) < 2:
            raise ValueError("Need at least 2 frames for GIF")
            
        with BytesIO() as output:
            frames[0].save(
                output,
                format="GIF",
                save_all=True,
                append_images=frames[1:],
                duration=duration,
                loop=0,
                optimize=True,
                disposal=2  # Clear background between frames
            )
            return output.getvalue()
    except Exception as e:
        logger.error(f"GIF creation failed: {str(e)}")
        raise

def image_to_bytes(img: Image.Image, format: str = "JPEG", quality: int = 90) -> bytes:
    """Convert PIL Image to bytes with error handling"""
    try:
        if format.upper() == "JPEG":
            img = img.convert("RGB")
            
        with BytesIO() as output:
            img.save(output, format=format, quality=quality)
            return output.getvalue()
    except Exception as e:
        logger.error(f"Image to bytes conversion failed: {str(e)}")
        raise