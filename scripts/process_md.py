import os
import sys
import base64
import requests
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
    """
    Optimizes an image using the TinyPNG API and returns the optimized image content.
    """
    try:
        # Set the TinyPNG API key
        tinify.key = get_env_variable('TINYPNG_API_KEY')

        # Read the image file
        with open(image_path, 'rb') as source:
            source_data = source.read()

        # Optimize the image and return the optimized data
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
    """
    Normalize string, remove non-alphanumeric characters, and replace spaces with underscores.
    Useful for handling non-English characters in file names.
    """
    text = unicodedata.normalize('NFKD', text)
    text = re.sub(r'[^\w\s-]', '', text).strip().lower()
    text = re.sub(r'[-\s]+', '_', text)
    return text

def extract_metadata(md_file_path):
    """
    Extract metadata from the file path and name.
    Returns a dictionary with keys: kid_name, age, location, random_id, topic.
    """
    path = Path(md_file_path)
    topic = path.parent.parent.name
    filename = path.stem  # e.g., 'nima-10-in-suburbs-2178184495'
    parts = filename.split('-')

    if re.fullmatch(r'[2-9]|1[0-1]', parts[0]):
        # No kid_name
        kid_name = "Unknown"
        age = parts[0]
        if len(parts) < 4:
            print(f"Error: Filename '{filename}' does not have enough parts.")
            return None
        location = parts[2]
        random_id = parts[3]
    else:
        # kid_name present
        if len(parts) < 5:
            print(f"Error: Filename '{filename}' does not have enough parts.")
            return None
        kid_name = parts[0]
        age = parts[1]
        location = parts[3]
        random_id = parts[4]

    # Clean kid_name
    kid_name_clean = slugify(kid_name)

    return {
        'kid_name': kid_name,
        'kid_name_clean': kid_name_clean,
        'age': age,
        'location': location,
        'random_id': random_id,
        'topic': topic
    }

def generate_custom_prompt(metadata, md_content, art_style):
    """
    Generates a custom prompt based on extracted metadata, Markdown content, and selected art style.
    """
    title = extract_title(md_content)
    sections = extract_sections(md_content)

    # Base prompt with aspect ratio instructions
    # prompt = f"Create a vibrant and engaging wide landscape-oriented {art_style} image for children based on the story titled '{title}':\n"
    prompt = f"kid in  {metadata['location'].replace('-', ' ').title()} , {art_style} image based on the story about {metadata['topic']}\n"

    # Include metadata
    # prompt += f"\n**Author:** {metadata['kid_name']} (Age: {metadata['age']})\n"
    # prompt += f"**Topic:** {metadata['topic']}\n"
    # prompt += f"**Location:** {metadata['location'].replace('-', ' ').title()}\n"
    # prompt += f"Emphasize the need for clear shapes and defined lines in your prompt. Specify that you want a polished, high-quality render\n"
    # Include sections with interactive prompts for the artist
    for heading, content in sections.items():
        prompt += f"\n**{heading}**: {content}\n"

    # Art Style Specific Instructions
    prompt += f"\n**Art Style:** {art_style}\n"
    
    if art_style == "Cartoon":
        prompt += "The characters should have exaggerated facial expressions and large, expressive eyes to appeal to children. Bright colors should dominate the scene.\n"
    elif art_style == "Watercolor":
        prompt += "Use soft brush strokes and a gentle color palette. The scenes should have a dreamy, serene feel.\n"
    elif art_style == "Flat Design":
        prompt += "The artwork should have simple shapes and minimal shading, with a modern, clean look.\n"
    elif art_style == "Vector Art":
        prompt += "Create smooth, clean lines and flat colors with a modern digital style.\n"
    elif art_style == "Hand-Drawn":
        prompt += "The illustration should have a hand-drawn, sketchy feel with detailed linework and textured coloring.\n"
    elif art_style == "3D Rendered":
        prompt += "The characters and environment should be realistically rendered in 3D, with a vibrant color palette.\n"
    elif art_style == "Storybook Illustration":
        prompt += "The style should be whimsical, with detailed backgrounds and expressive characters, as if from a classic children's book.\n"
    elif art_style == "Chibi":
        prompt += "The characters should have small bodies and large heads with cute, oversized eyes to give them a playful, adorable look.\n"

    # Additional instructions
    # prompt += (
        # "\nColor Scheme: Bright and lively colors.\n"
        # "**Orientation:** Landscape\n"
        # "**Aspect Ratio:** 16:9\n"
    # )

    return prompt[:2048]  # Ensure the prompt does not exceed 2048 characters


def extract_title(md_content):
    """
    Extracts the title from the Markdown content.
    Assumes the title is the first line starting with '# '.
    """
    match = re.search(r'^#\s+(.*)', md_content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return "Untitled"

def extract_sections(md_content):
    """
    Extracts subheadings and their content.
    Returns a dictionary with subheading as key and content as value.
    """
    sections = {}
    matches = list(re.finditer(r'^##\s+(.*)', md_content, re.MULTILINE))
    last_index = 0
    last_heading = None
    for match in matches:
        if last_heading:
            sections[last_heading] = md_content[last_index:match.start()].strip()
        last_heading = match.group(1).strip()
        last_index = match.end()
    if last_heading:
        sections[last_heading] = md_content[last_index:].strip()
    return sections

def send_api_request(api_url, payload, headers, retries=3, backoff_factor=2):
    """Send POST request to the API with retry logic."""
    for attempt in range(1, retries + 1):
        try:
            print(f"Attempting request... (Attempt {attempt})")
            response = requests.post(api_url, json=payload, headers=headers)
            response.raise_for_status()

            print(f"Response Status: {response.status_code}")

            if response.status_code == 200:
                return response.content  # Return the binary content directly

        except requests.exceptions.RequestException as e:
            if attempt == retries:
                print(f"Failed after {retries} attempts: {e}")
                raise
            else:
                wait_time = backoff_factor ** attempt
                print(f"Attempt {attempt} failed: {e}. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)

    return None

def upload_file_to_github(owner, repo, path, content, commit_message, branch='main', github_token=None):
    """
    Uploads a file to GitHub using the Contents API.
    If the file exists, it updates it. Otherwise, it creates a new file.
    """
    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        file_info = response.json()
        sha = file_info['sha']
        payload = {
            "message": commit_message,
            "content": content,
            "sha": sha,
            "branch": branch
        }
    elif response.status_code == 404:
        payload = {
            "message": commit_message,
            "content": content,
            "branch": branch
        }
    else:
        print(f"Error accessing {api_url}: {response.status_code} {response.text}")
        return False

    put_response = requests.put(api_url, json=payload, headers=headers)
    if put_response.status_code in [200, 201]:
        print(f"Successfully {'updated' if response.status_code == 200 else 'created'} {path}")
        return True
    else:
        print(f"Error uploading file to GitHub: {put_response.status_code} {put_response.text}")
        return False

def process_markdown(md_file_path, account_id, api_token, github_owner, github_repo, github_branch='main', github_pat=None):
    """Process a single Markdown file to generate and upload images in different art styles."""
    metadata = extract_metadata(md_file_path)
    if not metadata:
        return None

    try:
        print(f"Reading Markdown file: {md_file_path}")
        with open(md_file_path, 'r', encoding='utf-8') as file:
            content = file.read()

        for art_style in AVAILABLE_ART_STYLES:
            print(f"Generating image with art style: {art_style}")

            prompt = generate_custom_prompt(metadata, content, art_style)
            print(f"Generated Prompt for {art_style}: {prompt}")

            # api_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/bytedance/stable-diffusion-xl-lightning"
            api_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/stabilityai/stable-diffusion-xl-base-1.0"
            # 
            payload = {
                "prompt": prompt,
                "height": 576,       # For 16:9 aspect ratio with width=1024
                "width": 1024,
                # "guidance": 1
            }
            headers = {
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json"
            }

            print(f"Sending request to Cloudflare AI API for art style: {art_style}")
            image_data = send_api_request(api_url, payload, headers)

            if image_data:
                image_filename = f"{Path(md_file_path).stem}-{slugify(art_style)}.png"
                image_path = Path(md_file_path).parent.parent / 'images' / image_filename

                image_path.parent.mkdir(parents=True, exist_ok=True)

                with open(image_path, 'wb') as image_file:
                    image_file.write(image_data)
                print(f"Image saved locally as {image_path}")


                try:
                    optimized_image_data = optimize_image(image_path)
                    with open(image_path, 'wb') as optimized_image_file:
                        optimized_image_file.write(optimized_image_data)
                    print(f"Optimized image saved locally as {image_path}")
                    encoded_image_data = base64.b64encode(optimized_image_data).decode('utf-8')
                except Exception as e:
                    print(f"Failed to optimize image {image_filename}: {e}")
                    encoded_image_data = base64.b64encode(image_data).decode('utf-8')

                commit_message = f"Add generated {art_style} image for {Path(md_file_path).name}"
                repo_path = str(image_path).replace("\\", "/")  # Ensure forward slashes

                success = upload_file_to_github(
                    owner=github_owner,
                    repo=github_repo,
                    path=repo_path,
                    content=encoded_image_data,
                    commit_message=commit_message,
                    branch=github_branch,
                    github_token=github_pat if github_pat else os.getenv('GHB_PAT')
                )

                if success:
                    print(f"Successfully uploaded {image_filename} to GitHub.")
                else:
                    print(f"Failed to upload {image_filename} to GitHub.")
            else:
                print(f"Failed to generate image for art style: {art_style}")

    except requests.exceptions.HTTPError as e:
        print(f"HTTP Request failed for {md_file_path}: {e}")
        print(f"Response Content: {e.response.text}")
    except requests.exceptions.RequestException as e:
        print(f"HTTP Request failed for {md_file_path}: {e}")
    except Exception as e:
        print(f"An error occurred while processing {md_file_path}: {e}")

    return None

def main():
    """Main function to process the provided Markdown file."""
    if len(sys.argv) != 2:
        print("Usage: python scripts/process_md.py <path_to_md_file>")
        sys.exit(1)
    md_file_path = sys.argv[1]
    if not os.path.isfile(md_file_path):
        print(f"Error: File {md_file_path} does not exist.")
        sys.exit(1)
    account_id = get_env_variable('CLOUDFLARE_ACCOUNT_ID')
    api_token = get_env_variable('CLOUDFLARE_API_TOKEN')
    github_owner = "AINovelist"
    github_repo = "stories"
    github_branch = "main"
    github_pat = os.getenv('GHB_PAT')
    image_path = process_markdown(
        md_file_path,
        account_id,
        api_token,
        github_owner,
        github_repo,
        github_branch,
        github_pat
    )

    if image_path:
        print("Image processing and upload completed successfully.")
    else:
        print("Image processing or upload failed.")

if __name__ == "__main__":
    main()
