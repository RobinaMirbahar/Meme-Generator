import streamlit as st
from utils.image_generation import initialize_vertex_ai, generate_image, get_fallback_image
from utils.meme_creation import add_meme_text, create_gif, image_to_bytes
from PIL import Image
import os
import json
import re
from google.oauth2 import service_account

# Page configuration
st.set_page_config(
    page_title="🎬 Ultimate Meme Generator",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

def clean_json(json_str):
    """Remove control characters from JSON"""
    return re.sub(r'[\x00-\x1f\x7f-\x9f]', '', json_str)
@st.cache_resource
def init_resources():
    """Initialize Vertex AI client with robust error handling"""
    try:
        if 'gcp' not in st.secrets:
            raise ValueError("Missing GCP configuration in secrets")
        
        # Load and validate credentials
        creds_json = st.secrets["gcp"]["credentials"]
        try:
            creds_dict = json.loads(creds_json)
        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON format in credentials: {e}")
            return None
            
        # Ensure private key has proper newlines
        if 'private_key' in creds_dict:
            creds_dict['private_key'] = creds_dict['private_key'].replace('\\n', '\n')
            
        # Validate required fields
        required_fields = ['project_id', 'private_key', 'client_email']
        if not all(field in creds_dict for field in required_fields):
            missing = [f for f in required_fields if f not in creds_dict]
            st.error(f"Missing required credential fields: {', '.join(missing)}")
            return None
            
        # Create credentials
        creds = service_account.Credentials.from_service_account_info(creds_dict)
        return initialize_vertex_ai(
            st.secrets["gcp"]["project_id"],
            "us-central1",
            credentials=creds
        )
        
    except Exception as e:
        st.error(f"Initialization failed: {str(e)}")
        return None
        
def safe_get_fallback_image(style):
    """Guaranteed fallback image with error handling"""
    try:
        img = get_fallback_image(style)
        if img is None:
            # Create a blank image as ultimate fallback
            img = Image.new('RGB', (800, 800), color='black')
            draw = ImageDraw.Draw(img)
            draw.text((100, 400), "Meme Generation Failed", fill="white")
        return img
    except Exception:
        return Image.new('RGB', (800, 800), color='black')

def main():
    st.title("🎬 Ultimate Meme Generator")
    
    with st.sidebar:
        st.header("Settings")
        if st.button("Check Configuration"):
            st.json({
                "font_available": os.path.exists("assets/Impact.ttf"),
                "gcp_configured": 'gcp' in st.secrets
            })
    
    with st.form("meme_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            prompt = st.text_area("Image Description", "a funny cat")
            style = st.selectbox("Style", ["photo", "cartoon"])
            
        with col2:
            text = st.text_input("Meme Text", "WHEN YOU SEE IT")
            output_format = st.radio("Format", ["Static Image", "Animated GIF"])
            
        if st.form_submit_button("Generate Meme"):
            with st.spinner("Creating your meme..."):
                try:
                    client = init_resources()
                    if client is None:
                        raise RuntimeError("Could not initialize Vertex AI client")
                    
                    img = generate_image(prompt, style, client=client) or safe_get_fallback_image(style)
                    
                    result = add_meme_text(
                        img, text,
                        animation_effect="fade_in" if output_format == "Animated GIF" else "none"
                    )
                    
                    if output_format == "Animated GIF" and isinstance(result, list):
                        st.image(create_gif(result), use_column_width=True)
                    else:
                        st.image(result, use_column_width=True)
                        
                except Exception as e:
                    st.error(f"Error generating meme: {str(e)}")
                    st.image(safe_get_fallback_image(style))

if __name__ == "__main__":
    from PIL import ImageDraw  # Import moved here to avoid circular imports
    main()