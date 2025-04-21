from PIL import Image, ImageDraw, ImageFont
import textwrap
import os
from io import BytesIO
from typing import Union, List

def load_font(size: int):
    try:
        return ImageFont.truetype("assets/Impact.ttf", size)
    except:
        return ImageFont.load_default()

def add_meme_text(
    img: Image.Image,
    text: str,
    position: str = "bottom",
    text_color: str = "white",
    outline_color: str = "black",
    animation_effect: str = "none"
) -> Union[Image.Image, List[Image.Image]]:
    img = img.convert("RGB")
    frames = []
    text = text.upper()
    
    # Calculate font size
    font_size = min(80, max(30, int(img.width / 10)))
    font = load_font(font_size)
    
    # Text wrapping
    lines = textwrap.wrap(text, width=15)
    
    # Animation effects
    if animation_effect == "fade_in":
        for alpha in range(0, 255, 25):
            frame = img.copy()
            draw = ImageDraw.Draw(frame, "RGBA")
            # Draw text with fading
            frames.append(frame)
        return frames
    
    # Static image
    frame = img.copy()
    draw = ImageDraw.Draw(frame)
    # Draw text normally
    return frame

def create_gif(frames: List[Image.Image], duration: int = 100) -> bytes:
    with BytesIO() as output:
        frames[0].save(
            output,
            format="GIF",
            save_all=True,
            append_images=frames[1:],
            duration=duration,
            loop=0
        )
        return output.getvalue()

def image_to_bytes(img: Image.Image, format: str = "JPEG") -> bytes:
    with BytesIO() as output:
        img.save(output, format=format)
        return output.getvalue()