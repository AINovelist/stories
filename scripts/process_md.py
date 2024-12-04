import os
import sys
import base64
import requests
from pathlib import Path
import subprocess
import time
import re
import unicodedata

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
    # Extract topic from the parent directory name (e.g., Air Pollution Reduction)
    topic = path.parent.name

    # Extract filename without extension
    filename = path.stem  # e.g., 'baran-6-in-city-8406805212'

    # Regex pattern to match the naming convention
    pattern = r'^(?P<kid_name>.+)-(?P<age>[2-9]|1[0-1])-in-(?P<location>[^-]+)-(?P<random_id>\d+)$'
    match = re.match(pattern, filename)

    if not match:
        print(f"Error: Filename '{filename}' does not match the expected pattern.")
        return None

    metadata = match.groupdict()

    # Handle non-English characters in kid_name
    metadata['kid_name_clean'] = slugify(metadata['kid_name'])

    return {
        'kid_name': metadata['kid_name'],
        'kid_name_clean': metadata['kid_name_clean'],
        'age': metadata['age'],
        'location': metadata['location'],
        'random_id': metadata['random_id'],
        'topic': topic
    }

def generate_custom_prompt(metadata, md_content):
    """
    Generates a custom prompt based on extracted metadata and Markdown content.
    """
    title = extract_title(md_content)
    sections = extract_sections(md_content)

    # Base prompt
    prompt = f"Create a vibrant and engaging illustration for children based on the story titled '{title}':\n"

    # Include metadata
    prompt += f"\n**Author:** {metadata['kid_name']} (Age: {metadata['age']})\n"
    prompt += f"**Topic:** {metadata['topic']}\n"
    prompt += f"**Location:** {metadata['location'].replace('-', ' ').title()}\n"

    # Include sections
    for heading, content in sections.items():
        prompt += f"\n**{heading}**: {content}\n"

    # Additional instructions
    prompt += "\nArt Style: Cartoon\nColor Scheme: Bright and lively colors.\nEnsure that the image captures the essence of water conservation and animal protection."

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
            return response.json()
        except requests.exceptions.RequestException as e:
            if attempt == retries:
                print(f"Failed after {retries} attempts: {e}")
                raise
            else:
                wait_time = backoff_factor ** attempt
                print(f"Attempt {attempt} failed: {e}. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)

def process_markdown(md_file_path, account_id, api_token):
    """Process a single Markdown file to generate and commit an image."""
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

        # Prepare API request
        api_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/black-forest-labs/flux-1-schnell"
        payload = {
            "prompt": prompt,
            "steps": 4  # Adjust as needed
        }
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }

        print(f"Sending request to Cloudflare AI API for file: {md_file_path}")
        # Send the request to the Cloudflare AI API with retry logic
        data = send_api_request(api_url, payload, headers)

        print(f"API Response: {data}")

        if 'image' not in data:
            print(f"Error: No 'image' field in API response for {md_file_path}")
            return None  # Indicate failure

        # Decode the Base64 image
        image_data = base64.b64decode(data['image'])

        # Determine image extension (assuming PNG; adjust if necessary)
        image_extension = 'png'
        image_filename = Path(md_file_path).stem + f".{image_extension}"
        image_path = Path(md_file_path).parent / image_filename

        # Save the image
        with open(image_path, 'wb') as img_file:
            img_file.write(image_data)
        print(f"Image saved to {image_path}")

        # Configure Git user
        subprocess.run(['git', 'config', 'user.name', 'github-actions[bot]'], check=True)
        subprocess.run(['git', 'config', 'user.email', 'github-actions[bot]@users.noreply.github.com'], check=True)

        # Add and commit the image
        subprocess.run(['git', 'add', str(image_path)], check=True)
        commit_message = f"Add generated image for {Path(md_file_path).name}"
        subprocess.run(['git', 'commit', '-m', commit_message], check=True)
        print(f"Committed {image_filename}")

        return image_path  # Return the path for potential further use

    except requests.exceptions.HTTPError as e:
        print(f"HTTP Request failed for {md_file_path}: {e}")
        print(f"Response Content: {e.response.text}")
    except requests.exceptions.RequestException as e:
        print(f"HTTP Request failed for {md_file_path}: {e}")
    except subprocess.CalledProcessError as e:
        print(f"Git command failed for {md_file_path}: {e}")
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

    image_path = process_markdown(md_file_path, account_id, api_token)

    if image_path:
        # Push the commit
        try:
            subprocess.run(['git', 'push'], check=True)
            print("Pushed changes to the repository.")
        except subprocess.CalledProcessError as e:
            print(f"Error pushing changes: {e}")

if __name__ == "__main__":
    main()
