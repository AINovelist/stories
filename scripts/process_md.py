import os
import sys
import base64
import requests
from pathlib import Path
import re
import unicodedata
import time

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
    # Extract topic from the parent directory name (e.g., Tree Preservation)
    # Assuming structure: /kids/<Topic>/en/<filename>.md
    topic = path.parent.parent.name

    # Extract filename without extension
    filename = path.stem  # e.g., 'nima-10-in-suburbs-2178184495'

    # Split the filename by hyphens
    parts = filename.split('-')

    # Determine if the first part is age (2-11)
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

def generate_custom_prompt(metadata, md_content):
    """
    Generates a custom prompt based on extracted metadata and Markdown content.
    """
    title = extract_title(md_content)
    sections = extract_sections(md_content)

    # Base prompt with aspect ratio instructions
    prompt = f"Create a vibrant and engaging **wide**, **landscape-oriented** illustration for children based on the story titled '{title}':\n"

    # Include metadata
    prompt += f"\n**Author:** {metadata['kid_name']} (Age: {metadata['age']})\n"
    prompt += f"**Topic:** {metadata['topic']}\n"
    prompt += f"**Location:** {metadata['location'].replace('-', ' ').title()}\n"

    # Include sections
    for heading, content in sections.items():
        prompt += f"\n**{heading}**: {content}\n"

    # Additional instructions
    prompt += (
        "\nArt Style: Cartoon\n"
        "Color Scheme: Bright and lively colors.\n"
        "**Orientation:** Landscape\n"
        "**Aspect Ratio:** 16:9"
    )

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
            response = requests.post(api_url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()  # Assuming the response is JSON
        except requests.exceptions.RequestException as e:
            if attempt == retries:
                print(f"Failed after {retries} attempts: {e}")
                raise
            else:
                wait_time = backoff_factor ** attempt
                print(f"Attempt {attempt} failed: {e}. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)

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

    # Check if the file already exists to get its SHA
    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        # File exists, prepare to update
        file_info = response.json()
        sha = file_info['sha']
        payload = {
            "message": commit_message,
            "content": content,
            "sha": sha,
            "branch": branch
        }
    elif response.status_code == 404:
        # File does not exist, prepare to create
        payload = {
            "message": commit_message,
            "content": content,
            "branch": branch
        }
    else:
        print(f"Error accessing {api_url}: {response.status_code} {response.text}")
        return False

    # Create or update the file
    put_response = requests.put(api_url, json=payload, headers=headers)
    if put_response.status_code in [200, 201]:
        print(f"Successfully {'updated' if response.status_code == 200 else 'created'} {path}")
        return True
    else:
        print(f"Error uploading file to GitHub: {put_response.status_code} {put_response.text}")
        return False

def process_markdown(md_file_path, account_id, api_token, github_owner, github_repo, github_branch='main', github_pat=None):
    """Process a single Markdown file to generate and upload an image."""
    metadata = extract_metadata(md_file_path)
    if not metadata:
        return None

    try:
        print(f"Reading Markdown file: {md_file_path}")
        # Read the .md file content
        with open(md_file_path, 'r', encoding='utf-8') as file:
            content = file.read()

        # Generate custom prompt
        prompt = generate_custom_prompt(metadata, content)
        print(f"Generated Prompt: {prompt}")

        # Prepare API request with aspect_ratio
        api_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/bytedance/stable-diffusion-xl-lightning"
        payload = {
            "prompt": prompt,
            "height": 576,       # For 16:9 aspect ratio with width=1024
            "width": 1024,
            # "guidance": 7.5,     # Adjust as needed
            # "num_steps": 20      # Maximum allowed
            # Add other parameters if needed
        }
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }

        print(f"Sending request to Cloudflare AI API for file: {md_file_path}")
        # Send the request to the Cloudflare AI API with retry logic
        data = send_api_request(api_url, payload, headers)

        print(f"API Response: {data}")

        # Assuming the response contains the image data as a base64-encoded string
        # If the API returns the image directly as binary, adjust accordingly

        if isinstance(data, dict):
            # Check if 'result' contains 'image' key
            if 'result' in data and 'image' in data['result']:
                image_base64 = data['result']['image']
            else:
                print(f"Error: No 'image' field in API response for {md_file_path}")
                return None
        elif isinstance(data, str):
            # If the response is directly the base64 string
            image_base64 = data
        else:
            print(f"Unexpected API response format for {md_file_path}: {data}")
            return None

        # Decode the Base64 image
        image_data = base64.b64decode(image_base64)

        # Encode the image data in Base64 for GitHub API
        image_base64_github = base64.b64encode(image_data).decode('utf-8')

        # Determine image extension (assuming PNG; adjust if necessary)
        image_extension = 'png'
        image_filename = Path(md_file_path).stem + f".{image_extension}"

        # Define the images directory path
        images_dir = Path(md_file_path).parent.parent / 'images'  # Moves up from /en/ to the topic directory and then into /images/

        # Ensure the images directory exists locally (optional)
        # Not necessary for GitHub API uploads, but useful if you want to keep a local copy
        # images_dir.mkdir(parents=True, exist_ok=True)

        # Set the full image path
        image_path = images_dir / image_filename

        # Generate commit message
        commit_message = f"Add generated image for {Path(md_file_path).name}"

        # Define the path in the repository (use forward slashes)
        repo_path = str(image_path).replace("\\", "/")

        # Upload the image to GitHub using the Contents API
        success = upload_file_to_github(
            owner=github_owner,
            repo=github_repo,
            path=repo_path,
            content=image_base64_github,
            commit_message=commit_message,
            branch=github_branch,
            github_token=github_pat if github_pat else os.getenv('GHB_PAT')
        )

        if success:
            print(f"Successfully uploaded {image_filename} to GitHub.")
            return image_path
        else:
            print(f"Failed to upload {image_filename} to GitHub.")
            return None

    except requests.exceptions.HTTPError as e:
        print(f"HTTP Request failed for {md_file_path}: {e}")
        print(f"Response Content: {e.response.text}")
    except requests.exceptions.RequestException as e:
        print(f"HTTP Request failed for {md_file_path}: {e}")
    except Exception as e:
        print(f"An error occurred while processing {md_file_path}: {e}")

    return None  # Indicate failure

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

    # GitHub Repository Details
    github_owner = "AINovelist"  # Replace with your GitHub username or organization
    github_repo = "stories"       # Replace with your repository name
    github_branch = "main"        # Replace with your default branch name if different

    # Optional: Use a GitHub PAT if needed
    github_pat = os.getenv('GHB_PAT')  # Ensure you set this in your GitHub Secrets

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
