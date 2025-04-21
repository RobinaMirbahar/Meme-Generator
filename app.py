import streamlit as st
from utils.image_generation import initialize_vertex_ai, generate_image, get_fallback_image
from utils.meme_creation import add_meme_text, create_gif, image_to_bytes
from PIL import Image
import os
import json
from google.oauth2 import service_account

# Page config
st.set_page_config(
    page_title="🎬 Ultimate Meme Generator",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_resource
def init_resources():
    """Initialize fonts and Vertex AI client"""
    # Download font if missing
    if not os.path.exists("assets/Impact.ttf"):
        from urllib.request import urlretrieve
        os.makedirs("assets", exist_ok=True)
        urlretrieve(
            "https://github.com/phoikoi/fonts/raw/main/Impact.ttf",
            "assets/Impact.ttf"
        )
    
    # Initialize Vertex AI
    try:
        creds = service_account.Credentials.from_service_account_info(
            json.loads(st.secrets["gcp"]["credentials"])
        return initialize_vertex_ai(
            st.secrets["gcp"]["project_id"],
            "us-central1",
            credentials=creds
        )
    except Exception as e:
        st.error(f"Initialization error: {e}")
        return None

def main():
    st.title("🎬 Ultimate Meme Generator")
    st.markdown("Create custom memes with AI-generated images")
    
    with st.sidebar:
        st.header("Settings")
        with st.expander("Credits"):
            st.markdown("""
            - Vertex AI for image generation
            - Streamlit for UI
            - PIL/Pillow for image processing
            """)
    
    with st.form("meme_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            prompt = st.text_area(
                "Image Description",
                "a surprised cat looking at a cucumber",
                help="Describe the image you want to generate"
            )
            style = st.selectbox(
                "Style",
                ["photo", "cartoon", "art", "watercolor", "cyberpunk"]
            )
            
        with col2:
            text = st.text_input("Meme Text", "WHEN YOU SEE IT")
            position = st.selectbox("Text Position", ["top", "center", "bottom"])
            output_format = st.radio("Format", ["Static Image", "Animated GIF"])
            
        if st.form_submit_button("Generate Meme"):
            with st.spinner("Creating your meme..."):
                client = init_resources()
                img = generate_image(prompt, style, client=client) or get_fallback_image(style)
                
                if img:
                    result = add_meme_text(
                        img, text, 
                        position=position,
                        animation_effect="fade_in" if output_format == "Animated GIF" else "none"
                    )
                    
                    if output_format == "Animated GIF