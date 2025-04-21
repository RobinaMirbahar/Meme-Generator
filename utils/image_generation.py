from google.cloud import aiplatform
from google.cloud.aiplatform_v1 import PredictionServiceClient
from PIL import Image
from io import BytesIO
import base64
import time
import requests
from typing import Optional

STYLES = {
    "photo": {
        "prompt": "Professional photo of {prompt}, 8K UHD",
        "negative": "blurry, cartoon, drawing",
        "guidance": 12
    },
    "cartoon": {
        "prompt": "Pixar-style {prompt}, vibrant colors",
        "negative": "realistic, photo",
        "guidance": 10
    }
}

def initialize_vertex_ai(project: str, location: str, credentials=None):
    client_options = {"api_endpoint": f"{location}-aiplatform.googleapis.com"}
    return PredictionServiceClient(
        client_options=client_options,
        credentials=credentials
    )

def generate_image(
    prompt: str,
    style: str = "photo",
    client: Optional[PredictionServiceClient] = None,
    project_id: Optional[str] = None,
    location: Optional[str] = None,
    retries: int = 3
) -> Optional[Image.Image]:
    config = STYLES.get(style, STYLES["photo"])
    
    for attempt in range(retries):
        try:
            response = client.predict(
                endpoint=f"projects/{project_id}/locations/{location}/publishers/google/models/imagegeneration",
                instances=[{
                    "prompt": config["prompt"].format(prompt=prompt),
                    "negativePrompt": config["negative"]
                }],
                parameters={
                    "sampleCount": 1,
                    "style": style,
                    "guidanceScale": config["guidance"]
                }
            )
            
            img_data = base64.b64decode(response.predictions[0]["bytesBase64Encoded"])
            return Image.open(BytesIO(img_data)).convert("RGB")
            
        except Exception as e:
            time.sleep(2 ** attempt)
            continue
            
    return None

def get_fallback_image(style: str) -> Optional[Image.Image]:
    urls = {
        "photo": "https://placekitten.com/800/800",
        "cartoon": "https://placebear.com/800/800"
    }
    try:
        response = requests.get(urls.get(style, urls["photo"]), timeout=10)
        return Image.open(BytesIO(response.content)).convert("RGB")
    except:
        return None