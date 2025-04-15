from PIL import Image, ImageDraw, ImageFont
import textwrap
import os
import imageio
from io import BytesIO
import base64

def load_font(font_size):
    """Load the Impact font with fallback"""
    try:
        font_path = os.path.join("assets", "Impact.ttf")
        return ImageFont.truetype(font_path, font_size)
    except:
        print("⚠️ Using fallback font")
        return ImageFont.load_default(size=font_size)

def add_text_to_frame(draw, lines, font, img_width, img_height, total_height, position, text_color, outline_color, y_offset=0):
    """Helper function to add text to a frame with proper positioning"""
    if position == "top":
        y = int(img_height * 0.1) + y_offset
    elif position == "center":
        y = (img_height - total_height) // 2 + y_offset
    else:  # bottom (default)
        y = img_height - total_height - int(img_height * 0.1) + y_offset

    for line in lines:
        bbox = font.getbbox(line)
        text_width = bbox[2] - bbox[0]
        x = (img_width - text_width) // 2

        for dx in [-3, 0, 3]:
            for dy in [-3, 0, 3]:
                if dx != 0 or dy != 0:
                    draw.text((x+dx, y+dy), line, font=font, fill=outline_color)

        for dx, dy in [(-1,-1), (1,-1), (-1,1), (1,1)]:
            draw.text((x+dx, y+dy), line, font=font, fill="#aaaaaa")
        draw.text((x, y), line, font=font, fill=text_color)

        y += (bbox[3] - bbox[1]) + 10

def add_meme_text(img, text, position="bottom", text_color="#FFFFFF", outline_color="#000000", animation_effect="none"):
    """Add professional meme text with animation effects"""
    try:
        img = img.convert('RGB')
        frames = []

        base_size = min(80, max(40, int(img.width/12)))
        font_size = max(base_size - (len(text)//3), 30)
        font = load_font(font_size)

        text = text.upper()
        max_width = img.width * 0.9
        avg_char_width = font_size * 0.6
        wrap_width = min(20, int(max_width / avg_char_width))
        lines = textwrap.wrap(text, width=wrap_width)

        line_heights = [font.getbbox(line)[3] - font.getbbox(line)[1] for line in lines]
        total_height = sum(line_heights) + 10 * (len(lines) - 1)

        if animation_effect == "none":
            frame = img.copy()
            draw = ImageDraw.Draw(frame)
            add_text_to_frame(draw, lines, font, img.width, img.height, total_height, position, text_color, outline_color)
            return frame
        elif animation_effect == "fade_in":
            for i in range(10):
                alpha = int(255 * (i+1)/10)
                frame = img.copy()
                overlay = Image.new('RGBA', frame.size, (0,0,0,0))
                draw = ImageDraw.Draw(overlay)
                add_text_to_frame(draw, lines, font, img.width, img.height, total_height, position,
                                 f"{text_color}{alpha:02x}", f"{outline_color}{alpha:02x}")
                frame.paste(overlay, (0,0), overlay)
                frames.append(frame)
            return frames
        elif animation_effect == "slide_up":
            for i in range(10):
                frame = img.copy()
                draw = ImageDraw.Draw(frame)
                offset = int((img.height * 0.2) * (10-i)/10)
                add_text_to_frame(draw, lines, font, img.width, img.height, total_height, position,
                                text_color, outline_color, y_offset=offset)
                frames.append(frame)
            return frames
        elif animation_effect == "typing":
            frame = img.copy()
            draw = ImageDraw.Draw(frame)
            for i in range(1, len(text)+1):
                partial_text = text[:i]
                partial_lines = textwrap.wrap(partial_text, width=wrap_width)
                temp_frame = img.copy()
                temp_draw = ImageDraw.Draw(temp_frame)
                add_text_to_frame(temp_draw, partial_lines, font, img.width, img.height, total_height,
                                position, text_color, outline_color)
                frames.append(temp_frame)
            for _ in range(5):
                frames.append(frames[-1])
            return frames
        else:
            frame = img.copy()
            draw = ImageDraw.Draw(frame)
            add_text_to_frame(draw, lines, font, img.width, img.height, total_height, position, text_color, outline_color)
            return frame

    except Exception as e:
        print(f"⚠️ Text overlay error: {str(e)}")
        return None

def create_gif(frames, duration=100, loop=0):
    """Create a GIF from frames"""
    with BytesIO() as output:
        frames[0].save(
            output,
            format='GIF',
            save_all=True,
            append_images=frames[1:],
            duration=duration,
            loop=loop,
            optimize=True
        )
        return output.getvalue()

def image_to_bytes(img, format='JPEG'):
    """Convert PIL image to bytes"""
    with BytesIO() as output:
        img.save(output, format=format, quality=95)
        return output.getvalue()
