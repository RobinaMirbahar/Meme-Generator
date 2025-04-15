from google.cloud import aiplatform
from google.cloud.aiplatform_v1 import PredictionServiceClient
from PIL import Image
from io import BytesIO
import base64
import time
import requests

def initialize_vertex_ai(project_id, location):
    """Initialize Vertex AI client with retry logic"""
    client_options = {"api_endpoint": f"{location}-aiplatform.googleapis.com"}
    return PredictionServiceClient(client_options=client_options)

def generate_image(prompt, style="photo", project_id=None, location=None, client=None, retries=3):
    """Generate images with different styles and retry logic"""
    style_configs = {
        "photo": {
            "prompt_prefix": "Professional photograph of ",
            "prompt_suffix": ", 8K UHD, sharp focus, natural lighting",
            "negative_prompt": "blurry, cartoon, drawing, painting, text, watermark",
            "style": "photo",
            "guidance_scale": 12
        },
        "cartoon": {
            "prompt_prefix": "Pixar-style 3D animation of ",
            "prompt_suffix": ", vibrant colors, soft lighting, cartoon style",
            "negative_prompt": "realistic, photo, photograph, blurry, text",
            "style": "cartoon",
            "guidance_scale": 10
        },
        "art": {
            "prompt_prefix": "Concept art of ",
            "prompt_suffix": ", digital painting, artstation, trending, highly detailed",
            "negative_prompt": "photo, photograph, blurry, low quality, text",
            "style": "art",
            "guidance_scale": 11
        },
        "watercolor": {
            "prompt_prefix": "Beautiful watercolor painting of ",
            "prompt_suffix": ", soft edges, artistic, elegant composition",
            "negative_prompt": "photo, digital, sharp edges, text",
            "style": "watercolor",
            "guidance_scale": 9
        },
        "cyberpunk": {
            "prompt_prefix": "Cyberpunk neon-lit scene of ",
            "prompt_suffix": ", futuristic, rain, glowing lights, 4K detailed",
            "negative_prompt": "daylight, sunny, natural lighting, blurry",
            "style": "cyberpunk",
            "guidance_scale": 13
        }
    }

    config = style_configs.get(style, style_configs["photo"])

    for attempt in range(retries):
        try:
            endpoint = f"projects/{project_id}/locations/{location}/publishers/google/models/imagegeneration"

            response = client.predict(
                endpoint=endpoint,
                instances=[{
                    "prompt": f"{config['prompt_prefix']}{prompt}{config.get('prompt_suffix', '')}",
                    "negativePrompt": config["negative_prompt"]
                }],
                parameters={
                    "sampleCount": 1,
                    "aspectRatio": "1:1",
                    "style": config["style"],
                    "guidanceScale": config["guidance_scale"]
                }
            )

            if not response.predictions:
                raise ValueError("Empty response from API")

            img_data = response.predictions[0].get('bytesBase64Encoded')
            if not img_data:
                raise ValueError("No image data in response")

            img = Image.open(BytesIO(base64.b64decode(img_data)))

            if img.size[0] < 100 or img.size[1] < 100:
                raise ValueError("Generated image too small")

            return img

        except Exception as e:
            print(f"⚠️ Attempt {attempt + 1} failed: {str(e)}")
            if attempt < retries - 1:
                time.sleep(2)
                continue
            return None

def get_fallback_image(style):
    """Get a fallback image if generation fails"""
    fallback_urls = {
        "photo": "https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba",
        "cartoon": "https://images.unsplash.com/photo-1637858868799-7f26a0640eb6",
        "art": "https://images.unsplash.com/photo-1534447677768-be436bb09401",
        "watercolor": "https://images.unsplash.com/photo-1579783902614-a3fb3927b6a5",
        "cyberpunk": "https://images.unsplash.com/photo-1547036967-23d11aacaee0"
    }
    
    try:
        response = requests.get(
            fallback_urls.get(style, fallback_urls["photo"]),
            params={"ixlib": "rb-1.2.1", "auto": "format", "fit": "crop", "w": "800", "h": "800"},
            timeout=15
        )
        response.raise_for_status()
        return Image.open(BytesIO(response.content))
    except Exception as e:
        print(f"❌ Fallback failed: {str(e)}")
        return None
