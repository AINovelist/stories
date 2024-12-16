import os
import sys
import base64
import requests
import json
from pathlib import Path
import re
import unicodedata
import time
import tinify

AVAILABLE_ART_STYLES = [
    "Cartoon",
    "Watercolor",
    "Flat Design",
    "Vector Art",
    "Hand-Drawn",
    "3D Rendered",
    "Storybook Illustration",
    "Chibi",
    "Real"
]

def optimize_image(image_path):
    """Optimize image using TinyPNG."""
    try:
        tinify.key = get_env_variable('TINYPNG_API_KEY')
        tinify.proxy = "http://127.0.0.1:12334"
        with open(image_path, 'rb') as source:
            source_data = source.read()
        result_data = tinify.from_buffer(source_data).to_buffer()
        return result_data
    except tinify.errors.AccountError as e:
        print(f"TinyPNG API account error: {e}")
        return None
    except tinify.errors.ClientError as e:
        print(f"TinyPNG API client error: {e}")
        return None
    except Exception as e:
        print(f"Error optimizing image {image_path}: {e}")
        return None

def get_env_variable(name):
    """Retrieve environment variable or exit if not found."""
    value = os.getenv(name)
    if not value:
        print(f"Error: Environment variable {name} not set.")
        sys.exit(1)
    return value

def slugify(text):
    """Normalize string for file names."""
    text = unicodedata.normalize('NFKD', text)
    text = re.sub(r'[^\w\s-]', '', text).strip().lower()
    text = re.sub(r'[-\s]+', '_', text)
    return text

def generate_custom_prompt(page_data, art_style):
    """Generate image prompt based on page content and selected art style."""
    title = page_data['title']
    content = page_data['content']['response']
    prompt = f"Art style: {art_style}\n{page_data['image_prompt']}\n"
    
    if art_style == "Cartoon":
        prompt += "Exaggerate facial expressions, bright colors, and a whimsical feel."
    elif art_style == "Watercolor":
        prompt += "Use soft brush strokes and dreamy tones."
    elif art_style == "Flat Design":
        prompt += "Use simple shapes with minimal shading and modern aesthetics."
    elif art_style == "Vector Art":
        prompt += "Flat colors, clean lines, and digital style."
    elif art_style == "Hand-Drawn":
        prompt += "Detailed sketches with textured colors."
    elif art_style == "3D Rendered":
        prompt += "Realistic 3D models with vibrant colors."
    elif art_style == "Storybook Illustration":
        prompt += "Whimsical, expressive characters and detailed backgrounds."
    elif art_style == "Chibi":
        prompt += "Cute characters with oversized heads and large eyes."

    return prompt[:2048]

def send_api_request(api_url, payload, headers, retries=3, backoff_factor=2):
    """Send POST request to the API with retry logic."""
    for attempt in range(1, retries + 1):
        try:
            response = requests.post(api_url, json=payload, headers=headers)
            response.raise_for_status()

            if response.status_code == 200:
                return response.content  # Return the binary content directly
        except requests.exceptions.RequestException as e:
            if attempt == retries:
                print(f"Failed after {retries} attempts: {e}")
                raise
            else:
                wait_time = backoff_factor ** attempt
                print(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)

    return None

def process_json(json_file_path, account_id, api_token):
    """Process JSON file and generate and save images."""
    try:
        # Read JSON data
        with open(json_file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)

        # Extract story name and parent directory from the input JSON file path
        json_parent_dir = Path(json_file_path).parent
        story_name = Path(json_file_path).stem  # Get the name of the JSON file (e.g., 'story1')

        # Construct the path for saving the images
        pagedstory_dir = json_parent_dir.parent / "pagedstory" / story_name
        pagedstory_dir.mkdir(parents=True, exist_ok=True)  # Create the pagedstory folder if it doesn't exist

        pages = data.get('pages', [])

        for page_index, page in enumerate(pages, 1):  # Page index starts from 1
            for art_style in AVAILABLE_ART_STYLES:
                print(f"Generating image with art style: {art_style}")
                prompt = generate_custom_prompt(page, art_style)

                # Send request to Cloudflare or AI service
                api_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/stabilityai/stable-diffusion-xl-base-1.0"
                payload = {
                    "prompt": prompt,
                    "height": 576,  # For 16:9 aspect ratio with width=1024
                    "width": 1024,
                }
                headers = {
                    "Authorization": f"Bearer {api_token}",
                    "Content-Type": "application/json"
                }

                print(f"Sending request for art style: {art_style}")
                image_data = send_api_request(api_url, payload, headers)

                if image_data:
                    # Construct the image filename with page number and art style
                    image_filename = f"{page_index}-{slugify(art_style)}.png"
                    image_path = pagedstory_dir / image_filename

                    # Save the image locally
                    with open(image_path, 'wb') as image_file:
                        image_file.write(image_data)
                    print(f"Image saved locally as {image_path}")

                    try:
                        # Optimize image
                        optimized_image_data = optimize_image(image_path)
                        if optimized_image_data:
                            with open(image_path, 'wb') as optimized_image_file:
                                optimized_image_file.write(optimized_image_data)
                            print(f"Optimized image saved locally as {image_path}")
                    except Exception as e:
                        print(f"Failed to optimize image {image_filename}: {e}")

    except Exception as e:
        print(f"An error occurred while processing {json_file_path}: {e}")

def main():
    """Main function to process the provided JSON file."""
    if len(sys.argv) != 2:
        print("Usage: python scripts/process_json.py <path_to_json_file>")
        sys.exit(1)

    json_file_path = sys.argv[1]
    if not os.path.isfile(json_file_path):
        print(f"Error: File {json_file_path} does not exist.")
        sys.exit(1)

    account_id = get_env_variable('CLOUDFLARE_ACCOUNT_ID')
    api_token = get_env_variable('CLOUDFLARE_API_TOKEN')

    process_json(json_file_path, account_id, api_token)

if __name__ == "__main__":
    main()
