import chainlit as cl
from utils.image_generation import initialize_vertex_ai, generate_image, get_fallback_image
from utils.meme_creation import add_meme_text, create_gif, image_to_bytes
from PIL import Image
import base64
import os
import json
from google.oauth2 import service_account
from io import BytesIO

# Initialize Vertex AI client (cached)
@cl.cache
def get_vertex_client():
    try:
        # In Chainlit, you can use environment variables or a secrets.json file
        gcp_creds = json.loads(os.environ.get("GCP_CREDENTIALS"))
        credentials = service_account.Credentials.from_service_account_info(gcp_creds)
        
        client = initialize_vertex_ai(
            project_id=os.environ.get("GCP_PROJECT_ID"),
            location="us-central1",
            credentials=credentials
        )
        return client
    except Exception as e:
        print(f"Initialization failed: {str(e)}")
        return None

# Download Impact font if not exists
def download_font():
    if not os.path.exists("assets"):
        os.makedirs("assets")
    
    if not os.path.exists("assets/Impact.ttf"):
        try:
            import requests
            url = "https://github.com/phoikoi/fonts/raw/main/Impact.ttf"
            r = requests.get(url, timeout=10)
            with open("assets/Impact.ttf", "wb") as f:
                f.write(r.content)
        except Exception as e:
            print(f"Failed to download font: {str(e)}")

# Chainlit setup
@cl.on_chat_start
async def start():
    download_font()
    
    # Set up app UI
    await cl.Message(
        content="""# 🎬 Ultimate Meme Generator
Create custom memes with AI-generated images and professional text overlays"""
    ).send()
    
    # Initialize session variables
    cl.user_session.set("style", "photo")
    cl.user_session.set("position", "bottom")
    cl.user_session.set("text_color", "#FFFFFF")
    cl.user_session.set("outline_color", "#000000")
    cl.user_session.set("animation_effect", "none")
    cl.user_session.set("output_format", "Static Image (JPEG)")

@cl.action_callback("generate_meme")
async def on_action(action):
    # Get form values from session
    image_prompt = cl.user_session.get("image_prompt")
    meme_text = cl.user_session.get("meme_text")
    style = cl.user_session.get("style")
    position = cl.user_session.get("position")
    text_color = cl.user_session.get("text_color")
    outline_color = cl.user_session.get("outline_color")
    animation_effect = cl.user_session.get("animation_effect")
    output_format = cl.user_session.get("output_format")
    
    if not image_prompt.strip():
        await cl.Message(content="Please describe what you want in the image").send()
        return
    if not meme_text.strip():
        await cl.Message(content="Please enter some meme text").send()
        return

    msg = cl.Message(content="🔄 Generating your meme (this may take 20-40 seconds)...")
    await msg.send()
    
    try:
        # Generate image
        client = get_vertex_client()
        if client is None:
            await cl.Message(content="Vertex AI client not initialized. Check your GCP credentials.").send()
            return

        img = generate_image(
            image_prompt.strip(),
            style=style,
            client=client
        )

        if img is None:
            await msg.stream_token("AI generation failed, using fallback image...")
            img = get_fallback_image(style)
            if img is None:
                await cl.Message(content="Failed to generate or load fallback image").send()
                return

        # Add text overlay
        result = add_meme_text(
            img,
            meme_text.strip(),
            position=position,
            text_color=text_color,
            outline_color=outline_color,
            animation_effect=animation_effect if output_format == "Animated GIF" else "none"
        )

        if not result:
            await cl.Message(content="Failed to create meme").send()
            return

        # Display result
        await msg.stream_token("✅ Meme generated successfully!")
        
        if output_format == "Animated GIF" and isinstance(result, list):
            # Handle GIF
            gif_bytes = create_gif(result)
            
            # Create download button
            actions = [
                cl.Action(name="download", value=gif_bytes, label="⬇️ Download GIF", description="Download your meme as GIF")
            ]
            
            await cl.Message(
                content="Here's your animated meme!",
                elements=[cl.Image(name="meme", display="inline", content=gif_bytes)],
                actions=actions
            ).send()
        else:
            # Handle static image
            if isinstance(result, list):
                final_meme = result[-1]
            else:
                final_meme = result

            img_bytes = image_to_bytes(final_meme)
            
            # Create download button
            actions = [
                cl.Action(name="download", value=img_bytes, label="⬇️ Download Image", description="Download your meme as JPEG")
            ]
            
            await cl.Message(
                content="Here's your meme!",
                elements=[cl.Image(name="meme", display="inline", content=img_bytes)],
                actions=actions
            ).send()

    except Exception as e:
        await cl.Message(content=f"An error occurred: {str(e)}").send()

@cl.action_callback("download")
async def on_download(action):
    if action.value:
        # Determine file type
        file_ext = "gif" if action.name == "gif_download" else "jpg"
        file_name = f"meme.{file_ext}"
        
        # Send file to user
        await cl.Message(
            content=f"Downloading {file_name}...",
            elements=[cl.File(name=file_name, content=action.value, display="inline")]
        ).send()

@cl.on_message
async def main(message: cl.Message):
    # Show form elements
    elements = [
        cl.Text(name="image_prompt", display="sidebar", value="a surprised cat looking at a cucumber",
               label="What should the image show?", description="Be specific! Include details about subject, action, setting, and style."),
        
        cl.Text(name="meme_text", display="sidebar", value="WHEN YOU SEE IT",
               label="Meme Text (will be automatically capitalized)"),
        
        cl.Select(
            name="style",
            display="sidebar",
            value="photo",
            choices=[
                cl.Choice(label="Photorealistic", value="photo"),
                cl.Choice(label="Cartoon/Pixar", value="cartoon"),
                cl.Choice(label="Digital Art", value="art"),
                cl.Choice(label="Watercolor", value="watercolor"),
                cl.Choice(label="Cyberpunk", value="cyberpunk")
            ],
            label="Art Style"
        ),
        
        cl.Select(
            name="position",
            display="sidebar",
            value="bottom",
            choices=[
                cl.Choice(label="Top", value="top"),
                cl.Choice(label="Center", value="center"),
                cl.Choice(label="Bottom", value="bottom")
            ],
            label="Text Position"
        ),
        
        cl.ColorPicker(name="text_color", display="sidebar", value="#FFFFFF", label="Text Color"),
        cl.ColorPicker(name="outline_color", display="sidebar", value="#000000", label="Outline Color"),
        
        cl.Select(
            name="animation_effect",
            display="sidebar",
            value="none",
            choices=[
                cl.Choice(label="No animation", value="none"),
                cl.Choice(label="Fade in", value="fade_in"),
                cl.Choice(label="Slide up", value="slide_up"),
                cl.Choice(label="Typing effect", value="typing")
            ],
            label="Animation Effect"
        ),
        
        cl.RadioGroup(
            name="output_format",
            display="sidebar",
            value="Static Image (JPEG)",
            choices=[
                cl.Choice(label="Static Image (JPEG)", value="Static Image (JPEG)"),
                cl.Choice(label="Animated GIF", value="Animated GIF")
            ],
            label="Output Format"
        )
    ]
    
    # Store form values in session
    for element in elements:
        cl.user_session.set(element.name, element.value)
    
    # Add generate button
    actions = [
        cl.Action(name="generate_meme", value="generate", label="✨ Generate Meme ✨")
    ]
    
    await cl.Message(
        content="Configure your meme using the sidebar controls, then click Generate!",
        elements=elements,
        actions=actions
    ).send()
