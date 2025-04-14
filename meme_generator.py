import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
import numpy as np
import textwrap
import time
import requests
from io import BytesIO
import base64
from google.cloud import aiplatform
from google.cloud.aiplatform_v1 import PredictionServiceClient

# Initialize session state
if 'img' not in st.session_state:
    st.session_state.img = None
if 'filtered_img' not in st.session_state:
    st.session_state.filtered_img = None
if 'final_meme' not in st.session_state:
    st.session_state.final_meme = None

# Configuration (replace with your actual values)
PROJECT_ID = "your-project-id"
LOCATION = "us-central1"
client_options = {"api_endpoint": f"{LOCATION}-aiplatform.googleapis.com"}
client = PredictionServiceClient(client_options=client_options)

# Page config
st.set_page_config(page_title="✨ Ultimate Meme Generator", layout="wide")

# Custom CSS
st.markdown("""
<style>
.stButton>button {
    background-color: #4CAF50;
    color: white;
    padding: 10px 24px;
    border: none;
    border-radius: 4px;
}
.stButton>button:hover {
    background-color: #45a049;
}
.stTextInput>div>div>input {
    border: 1px solid #4CAF50;
}
.stSelectbox>div>div>select {
    border: 1px solid #4CAF50;
}
</style>
""", unsafe_allow_html=True)

# Title
st.title("✨ Ultimate Meme Generator")
st.markdown("---")

# Sidebar for settings
with st.sidebar:
    st.header("Settings")
    image_source = st.radio("Image Source", ["Generate AI Image", "Upload Your Own"])
    
    if image_source == "Generate AI Image":
        prompt = st.text_input("Describe your image", "a shocked cat")
        style = st.selectbox("Style", ["Photorealistic", "Cartoon/Pixar", "Digital Art", "Watercolor", "Cyberpunk"])
    else:
        uploaded_file = st.file_uploader("Upload Image", type=["jpg", "jpeg", "png"])
    
    st.markdown("---")
    st.header("Text Options")
    num_texts = st.slider("Number of text elements", 1, 3, 1)
    
    texts = []
    positions = []
    colors = []
    outlines = []
    
    for i in range(num_texts):
        st.subheader(f"Text Element {i+1}")
        texts.append(st.text_input(f"Text {i+1}", key=f"text_{i}"))
        positions.append(st.selectbox(f"Position {i+1}", ["Top", "Center", "Bottom"], key=f"pos_{i}"))
        colors.append(st.color_picker(f"Text Color {i+1}", "#FFFFFF", key=f"color_{i}"))
        outlines.append(st.color_picker(f"Outline Color {i+1}", "#000000", key=f"outline_{i}"))
    
    st.markdown("---")
    st.header("Effects")
    filter_choice = st.selectbox("Image Filter", 
                               ["None", "Black & White", "Sepia", "Vintage", "Blur", "Sharpen", "Edge Detect"])
    
    st.markdown("---")
    st.header("Watermark")
    add_watermark = st.checkbox("Add Watermark")
    if add_watermark:
        watermark_text = st.text_input("Watermark Text", "@MemeGen")
        opacity = st.slider("Opacity", 0.1, 1.0, 0.5)

# Image processing functions
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
    sepia_filter = np.array([[0.393, 0.769, 0.189],
                            [0.349, 0.686, 0.168],
                            [0.272, 0.534, 0.131]])
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
        st.error(f"Watermark error: {str(e)}")
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
        st.error(f"Text overlay error: {str(e)}")
        return None

def generate_ai_image(prompt, style):
    style_configs = {
        "Photorealistic": {
            "prompt": f"Professional photograph of {prompt}, 8K UHD, sharp focus",
            "negative_prompt": "blurry, cartoon, drawing, painting, text"
        },
        "Cartoon/Pixar": {
            "prompt": f"Pixar-style 3D animation of {prompt}, vibrant colors",
            "negative_prompt": "realistic, photo, blurry"
        },
        "Digital Art": {
            "prompt": f"Digital painting of {prompt}, artstation style",
            "negative_prompt": "photo, blurry, low quality"
        },
        "Watercolor": {
            "prompt": f"Watercolor painting of {prompt}, soft edges",
            "negative_prompt": "digital, sharp edges"
        },
        "Cyberpunk": {
            "prompt": f"Cyberpunk style {prompt}, neon lights, futuristic",
            "negative_prompt": "daylight, natural lighting"
        }
    }
    
    config = style_configs.get(style, style_configs["Photorealistic"])
    
    try:
        endpoint = f"projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/imagegeneration"
        
        response = client.predict(
            endpoint=endpoint,
            instances=[{
                "prompt": config["prompt"],
                "negativePrompt": config["negative_prompt"]
            }],
            parameters={
                "sampleCount": 1,
                "aspectRatio": "1:1",
                "style": style.lower(),
                "guidanceScale": 12
            }
        )
        
        img_data = response.predictions[0].get('bytesBase64Encoded')
        return Image.open(BytesIO(base64.b64decode(img_data)))
    
    except Exception as e:
        st.error(f"AI generation failed: {str(e)}")
        # Fallback to placeholder
        prompt_encoded = requests.utils.quote(config["prompt"])
        response = requests.get(f"https://source.unsplash.com/800x800/?{prompt_encoded}")
        return Image.open(BytesIO(response.content))

# Generate or upload image
if st.button("Generate Meme"):
    with st.spinner("Creating your meme..."):
        try:
            if image_source == "Generate AI Image":
                st.session_state.img = generate_ai_image(prompt, style)
                st.success(f"Generated {style} image: {prompt}")
            else:
                if uploaded_file is not None:
                    st.session_state.img = Image.open(uploaded_file)
                    if max(st.session_state.img.size) > 2000:
                        st.session_state.img.thumbnail((2000, 2000))
                    st.success("Image uploaded successfully!")
                else:
                    st.warning("Please upload an image first")
                    st.stop()
            
            # Apply filter
            st.session_state.filtered_img = apply_filter(st.session_state.img, filter_choice)
            
            # Apply watermark if selected
            if add_watermark:
                st.session_state.filtered_img = add_watermark(
                    st.session_state.filtered_img, 
                    watermark_text, 
                    opacity
                )
            
            # Add meme text
            st.session_state.final_meme = add_meme_text(
                st.session_state.filtered_img,
                texts,
                positions,
                colors,
                outlines
            )
            
            if st.session_state.final_meme:
                st.success("Meme created successfully!")
            
        except Exception as e:
            st.error(f"Error creating meme: {str(e)}")

# Display results
if st.session_state.final_meme is not None:
    st.image(st.session_state.final_meme, use_container_width=True)
    
    # Download button
    buf = BytesIO()
    st.session_state.final_meme.save(buf, format="JPEG", quality=95)
    byte_im = buf.getvalue()
    
    st.download_button(
        label="Download Meme",
        data=byte_im,
        file_name=f"meme_{int(time.time())}.jpg",
        mime="image/jpeg"
    )
