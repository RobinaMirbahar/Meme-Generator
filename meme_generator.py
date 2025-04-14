from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
import numpy as np
import textwrap
import time
import os
import requests
from io import BytesIO
import base64
import chainlit as cl

# Meme generation functions
def apply_filter(img, filter_name):
    filters = {
        'None': lambda x: x,
        'Black & White': lambda x: x.convert('L'),
        'Sepia': lambda x: sepia(x),
        'Vintage': lambda x: vintage(x),
        'Blur': lambda x: x.filter(ImageFilter.GaussianBlur(2)),
        'Sharpen': lambda x: x.filter(ImageFilter.SHARPEN),
        'Edge Detect': lambda x: x.filter(ImageFilter.FIND_EDGES)
    }
    return filters.get(filter_name, lambda x: x)(img)

def sepia(img):
    arr = np.array(img)
    sepia_filter = np.array([
        [0.393, 0.769, 0.189],
        [0.349, 0.686, 0.168],
        [0.272, 0.534, 0.131]
    ])
    sepia_img = arr.dot(sepia_filter.T)
    sepia_img[sepia_img > 255] = 255
    return Image.fromarray(sepia_img.astype('uint8'))

def vintage(img):
    arr = np.array(img)
    rows, cols = arr.shape[:2]
    x = np.linspace(-1, 1, cols)
    y = np.linspace(-1, 1, rows)
    X, Y = np.meshgrid(x, y)
    vignette = 1 - np.sqrt(X**2 + Y**2) / 1.4
    vignette = np.clip(vignette, 0, 1)
    for i in range(3):
        arr[:,:,i] = arr[:,:,i] * vignette
    noise = np.random.randint(-20, 20, arr.shape)
    arr = np.clip(arr + noise, 0, 255)
    return Image.fromarray(arr.astype('uint8'))

def add_watermark(img, watermark_text="@MemeGen", opacity=0.5):
    try:
        watermark = Image.new('RGBA', img.size, (0,0,0,0))
        draw = ImageDraw.Draw(watermark)
        
        try:
            font = ImageFont.truetype("arial.ttf", int(img.width/15))
        except:
            font = ImageFont.load_default()
        
        text_width = draw.textlength(watermark_text, font=font)
        text_height = font.size
        margin = img.width // 50
        x = img.width - text_width - margin
        y = img.height - text_height - margin
        
        draw.text((x, y), watermark_text, font=font, fill=(255,255,255,int(255*opacity)))
        
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        return Image.alpha_composite(img, watermark)
    except Exception as e:
        return img

def add_meme_text(img, texts, positions, colors, outline_colors):
    try:
        img = img.convert('RGB')
        draw = ImageDraw.Draw(img)
        
        for i, (text, position, color, outline) in enumerate(zip(texts, positions, colors, outline_colors)):
            base_size = min(80, max(30, int(img.width/12 - len(text)/3)))
            try:
                font = ImageFont.truetype("arial.ttf", base_size)
            except:
                font = ImageFont.load_default(size=base_size)
            
            text = text.upper()
            max_width = img.width * 0.9
            avg_char_width = base_size * 0.6
            wrap_width = min(20, int(max_width / avg_char_width))
            lines = textwrap.wrap(text, width=wrap_width)
            
            total_height = sum(font.getbbox(line)[3] - font.getbbox(line)[1] + 10 for line in lines)
            
            if position == 'Top':
                y = img.height * 0.05
            elif position == 'Bottom':
                y = img.height - total_height - int(img.height * 0.05)
            else:  # Center
                y = (img.height - total_height) // 2
            
            for line in lines:
                bbox = font.getbbox(line)
                text_width = bbox[2] - bbox[0]
                x = (img.width - text_width) // 2
                
                for dx in [-2, 0, 2]:
                    for dy in [-2, 0, 2]:
                        if dx != 0 or dy != 0:
                            draw.text((x+dx, y+dy), line, font=font, fill=outline)
                
                draw.text((x, y), line, font=font, fill=color)
                y += font.getbbox(line)[3] - font.getbbox(line)[1] + 10
                
        return img
    
    except Exception as e:
        return None

@cl.on_chat_start
async def start():
    # Initialize session state
    cl.user_session.set("img", None)
    cl.user_session.set("filtered_img", None)
    cl.user_session.set("final_meme", None)
    
    # Welcome message
    await cl.Message(content="✨ Welcome to the Ultimate Meme Generator!").send()
    
    # Ask for image source
    actions = [
        cl.Action(name="generate_ai", value="generate_ai", label="Generate AI Image"),
        cl.Action(name="upload", value="upload", label="Upload Your Own")
    ]
    await cl.Message(content="How would you like to get your image?", actions=actions).send()

@cl.action_callback("generate_ai")
async def on_action_generate_ai(action):
    await cl.Message(content="You selected to generate an AI image").send()
    cl.user_session.set("image_source", "generate_ai")
    await get_ai_prompt()

async def get_ai_prompt():
    prompt = await cl.AskUserMessage(content="Describe your image (e.g., 'a shocked cat')", timeout=60).send()
    if prompt:
        cl.user_session.set("prompt", prompt['content'])
        await get_ai_style()

async def get_ai_style():
    style = await cl.AskUserMessage(
        content="Select a style:",
        actions=[
            cl.Action(name="photorealistic", value="Photorealistic", label="Photorealistic"),
            cl.Action(name="cartoon", value="Cartoon/Pixar", label="Cartoon/Pixar"),
            cl.Action(name="digital", value="Digital Art", label="Digital Art"),
            cl.Action(name="watercolor", value="Watercolor", label="Watercolor"),
            cl.Action(name="cyberpunk", value="Cyberpunk", label="Cyberpunk")
        ]
    ).send()
    if style:
        cl.user_session.set("style", style['content'])
        await get_text_options()

@cl.action_callback("upload")
async def on_action_upload(action):
    await cl.Message(content="Please upload your image file").send()
    cl.user_session.set("image_source", "upload")
    files = await cl.AskFileMessage(
        content="Upload an image file",
        accept=["image/jpeg", "image/png"],
        max_size_mb=10
    ).send()
    if files:
        file = files[0]
        img = Image.open(BytesIO(file.content))
        if max(img.size) > 2000:
            img.thumbnail((2000, 2000))
        cl.user_session.set("img", img)
        await cl.Message(content="Image uploaded successfully!").send()
        await get_text_options()

async def get_text_options():
    num_texts = await cl.AskUserMessage(
        content="How many text elements do you want? (1-3)",
        actions=[
            cl.Action(name="1", value="1", label="1"),
            cl.Action(name="2", value="2", label="2"),
            cl.Action(name="3", value="3", label="3")
        ]
    ).send()
    if num_texts:
        cl.user_session.set("num_texts", int(num_texts['content']))
        await get_text_details()

async def get_text_details():
    num_texts = cl.user_session.get("num_texts")
    texts = []
    positions = []
    colors = []
    outlines = []
    
    for i in range(num_texts):
        text = await cl.AskUserMessage(content=f"Enter text for element {i+1}").send()
        if text:
            texts.append(text['content'])
            
            position = await cl.AskUserMessage(
                content=f"Position for text {i+1}",
                actions=[
                    cl.Action(name="top", value="Top", label="Top"),
                    cl.Action(name="center", value="Center", label="Center"),
                    cl.Action(name="bottom", value="Bottom", label="Bottom")
                ]
            ).send()
            if position:
                positions.append(position['content'])
            
            color = await cl.AskUserMessage(content=f"Hex color for text {i+1} (e.g., #FFFFFF)").send()
            if color:
                colors.append(color['content'])
            
            outline = await cl.AskUserMessage(content=f"Hex outline color for text {i+1} (e.g., #000000)").send()
            if outline:
                outlines.append(outline['content'])
    
    cl.user_session.set("texts", texts)
    cl.user_session.set("positions", positions)
    cl.user_session.set("colors", colors)
    cl.user_session.set("outlines", outlines)
    
    await get_filter_options()

async def get_filter_options():
    filter_choice = await cl.AskUserMessage(
        content="Select an image filter:",
        actions=[
            cl.Action(name="none", value="None", label="None"),
            cl.Action(name="bw", value="Black & White", label="Black & White"),
            cl.Action(name="sepia", value="Sepia", label="Sepia"),
            cl.Action(name="vintage", value="Vintage", label="Vintage"),
            cl.Action(name="blur", value="Blur", label="Blur"),
            cl.Action(name="sharpen", value="Sharpen", label="Sharpen"),
            cl.Action(name="edge", value="Edge Detect", label="Edge Detect")
        ]
    ).send()
    if filter_choice:
        cl.user_session.set("filter_choice", filter_choice['content'])
        await get_watermark_options()

async def get_watermark_options():
    add_watermark = await cl.AskUserMessage(
        content="Would you like to add a watermark?",
        actions=[
            cl.Action(name="yes", value="yes", label="Yes"),
            cl.Action(name="no", value="no", label="No")
        ]
    ).send()
    if add_watermark:
        if add_watermark['content'] == "yes":
            watermark_text = await cl.AskUserMessage(content="Enter watermark text").send()
            if watermark_text:
                cl.user_session.set("watermark_text", watermark_text['content'])
                
                opacity = await cl.AskUserMessage(
                    content="Select opacity (1-10 where 10 is fully visible)",
                    actions=[cl.Action(name=str(i), value=str(i/10), label=str(i)) for i in range(1, 11)]
                ).send()
                if opacity:
                    cl.user_session.set("opacity", float(opacity['content']))
        else:
            cl.user_session.set("watermark_text", None)
        
        await generate_meme()

async def generate_meme():
    with cl.Step(name="Generating Meme", type="run") as step:
        step.output = "Starting meme generation..."
        
        try:
            # Get or generate image
            if cl.user_session.get("image_source") == "generate_ai":
                step.output = "Generating AI image..."
                # Placeholder - replace with actual AI image generation
                response = requests.get("https://picsum.photos/800/800")
                img = Image.open(BytesIO(response.content))
                cl.user_session.set("img", img)
                step.output = "AI image generated!"
            else:
                img = cl.user_session.get("img")
            
            # Apply filter
            step.output = "Applying filters..."
            filtered_img = apply_filter(img, cl.user_session.get("filter_choice"))
            cl.user_session.set("filtered_img", filtered_img)
            
            # Apply watermark if selected
            if cl.user_session.get("watermark_text"):
                step.output = "Adding watermark..."
                filtered_img = add_watermark(
                    filtered_img, 
                    cl.user_session.get("watermark_text"), 
                    cl.user_session.get("opacity", 0.5)
                )
                cl.user_session.set("filtered_img", filtered_img)
            
            # Add meme text
            step.output = "Adding text..."
            final_meme = add_meme_text(
                filtered_img,
                cl.user_session.get("texts", []),
                cl.user_session.get("positions", []),
                cl.user_session.get("colors", []),
                cl.user_session.get("outlines", [])
            )
            
            if final_meme:
                cl.user_session.set("final_meme", final_meme)
                step.output = "Meme created successfully!"
                
                # Display the meme
                buf = BytesIO()
                final_meme.save(buf, format="JPEG", quality=95)
                buf.seek(0)
                
                # Create download button
                elements = [
                    cl.Image(name="meme", display="inline", content=buf.read()),
                    cl.DownloadButton(
                        name="download",
                        label="Download Meme",
                        path=buf,
                        file_name=f"meme_{int(time.time())}.jpg"
                    )
                ]
                
                await cl.Message(content="Here's your meme!", elements=elements).send()
            else:
                await cl.Message(content="Error creating meme").send()
            
        except Exception as e:
            await cl.Message(content=f"Error: {str(e)}").send()

@cl.on_chat_end
def end():
    # Clean up
    cl.user_session.delete("img")
    cl.user_session.delete("filtered_img")
    cl.user_session.delete("final_meme")