import streamlit as st
from utils.image_generation import initialize_vertex_ai, generate_image, get_fallback_image
from utils.meme_creation import add_meme_text, create_gif, image_to_bytes
from PIL import Image
import base64
import os

# Page configuration
st.set_page_config(
    page_title="🎬 Ultimate Meme Generator",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Vertex AI (you'll need to set up your GCP credentials)
PROJECT_ID = "cloud-champion-innovator"
LOCATION = "us-central1"

@st.cache_resource
def get_vertex_client():
    return initialize_vertex_ai(PROJECT_ID, LOCATION)

def main():
    st.title("🎬 Ultimate Meme Generator")
    st.markdown("Create custom memes with AI-generated images and professional text overlays")

    with st.sidebar:
        st.header("Configuration")
        st.markdown("Set up your meme parameters here")

    # Main form
    with st.form("meme_form"):
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("1. Describe Your Image")
            image_prompt = st.text_area(
                "What should the image show?",
                value="a surprised cat looking at a cucumber",
                help="Be specific! Include details about subject, action, setting, and style."
            )

            st.subheader("2. Customize Appearance")
            style = st.selectbox(
                "Art Style",
                options=[
                    ("Photorealistic", "photo"),
                    ("Cartoon/Pixar", "cartoon"),
                    ("Digital Art", "art"),
                    ("Watercolor", "watercolor"),
                    ("Cyberpunk", "cyberpunk")
                ],
                format_func=lambda x: x[0],
                index=0
            )[1]

        with col2:
            st.subheader("3. Add Your Text")
            meme_text = st.text_input(
                "Meme Text (will be automatically capitalized)",
                value="WHEN YOU SEE IT"
            )

            position = st.selectbox(
                "Text Position",
                options=["top", "center", "bottom"],
                index=2
            )

            text_color = st.color_picker("Text Color", "#FFFFFF")
            outline_color = st.color_picker("Outline Color", "#000000")

            st.subheader("4. Animation Options")
            animation_effect = st.selectbox(
                "Animation Effect",
                options=[
                    ("No animation", "none"),
                    ("Fade in", "fade_in"),
                    ("Slide up", "slide_up"),
                    ("Typing effect", "typing")
                ],
                format_func=lambda x: x[0],
                index=0
            )[1]

            output_format = st.radio(
                "Output Format",
                options=["Static Image (JPEG)", "Animated GIF"],
                index=0
            )

        submit_button = st.form_submit_button("✨ Generate Meme ✨")

    if submit_button:
        if not image_prompt.strip():
            st.error("Please describe what you want in the image")
            return
        if not meme_text.strip():
            st.error("Please enter some meme text")
            return

        with st.spinner("🔄 Generating your meme (this may take 20-40 seconds)..."):
            # Generate image
            client = get_vertex_client()
            img = generate_image(
                image_prompt.strip(),
                style=style,
                project_id=PROJECT_ID,
                location=LOCATION,
                client=client
            )

            if img is None:
                st.warning("AI generation failed, using fallback image")
                img = get_fallback_image(style)
                if img is None:
                    st.error("Failed to generate or load fallback image")
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
                st.error("Failed to create meme")
                return

            # Display result
            st.success("✅ Meme generated successfully!")
            st.markdown("---")

            if output_format == "Animated GIF" and isinstance(result, list):
                # Handle GIF
                gif_bytes = create_gif(result)
                st.image(gif_bytes, use_column_width=True)

                # Download button
                st.download_button(
                    label="⬇️ Download GIF ⬇️",
                    data=gif_bytes,
                    file_name="meme.gif",
                    mime="image/gif"
                )
            else:
                # Handle static image
                if isinstance(result, list):
                    final_meme = result[-1]
                else:
                    final_meme = result

                st.image(final_meme, use_column_width=True)

                # Download button
                img_bytes = image_to_bytes(final_meme)
                st.download_button(
                    label="⬇️ Download Image ⬇️",
                    data=img_bytes,
                    file_name="meme.jpg",
                    mime="image/jpeg"
                )

if __name__ == "__main__":
    # Download the Impact font if not exists
    if not os.path.exists("assets"):
        os.makedirs("assets")
    
    if not os.path.exists("assets/Impact.ttf"):
        import requests
        url = "https://github.com/phoikoi/fonts/raw/main/Impact.ttf"
        r = requests.get(url)
        with open("assets/Impact.ttf", "wb") as f:
            f.write(r.content)

    main()
