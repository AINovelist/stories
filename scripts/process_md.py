import os
import sys
import base64
import requests
from pathlib import Path
import subprocess

def get_env_variable(name):
    value = os.getenv(name)
    if not value:
        print(f"Error: Environment variable {name} not set.")
        sys.exit(1)
    return value

def process_markdown(md_file_path, account_id, api_token):
    try:
        print(f"Reading Markdown file: {md_file_path}")
        # Read the .md file content
        with open(md_file_path, 'r', encoding='utf-8') as file:
            content = file.read()

        # Create the prompt (customize as needed)
        prompt = content.replace('\n', ' ').strip()
        if len(prompt) > 2048:
            prompt = prompt[:2048]

        # Prepare API request
        api_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/black-forest-labs/flux-1-schnell"
        payload = {
            "prompt": prompt,
            "steps": 4  # You can adjust the number of steps as needed
        }
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }

        print(f"Sending request to Cloudflare AI API for file: {md_file_path}")
        # Send the request to the Cloudflare AI API
        response = requests.post(api_url, json=payload, headers=headers)
        print(f"API Response Status: {response.status_code}")
        print(f"API Response Body: {response.text}")
        response.raise_for_status()  # Raise an error for bad status codes

        data = response.json()
        if 'image' not in data:
            print(f"Error: No 'image' field in API response for {md_file_path}")
            return

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

    except requests.exceptions.HTTPError as e:
        print(f"HTTP Request failed for {md_file_path}: {e}")
        print(f"Response Content: {e.response.text}")
    except requests.exceptions.RequestException as e:
        print(f"HTTP Request failed for {md_file_path}: {e}")
    except subprocess.CalledProcessError as e:
        print(f"Git command failed for {md_file_path}: {e}")
    except Exception as e:
        print(f"An error occurred while processing {md_file_path}: {e}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/process_md.py <path_to_md_file>")
        sys.exit(1)

    md_file_path = sys.argv[1]
    if not os.path.isfile(md_file_path):
        print(f"Error: File {md_file_path} does not exist.")
        sys.exit(1)

    account_id = get_env_variable('CLOUDFLARE_ACCOUNT_ID')
    api_token = get_env_variable('CLOUDFLARE_API_TOKEN')

    process_markdown(md_file_path, account_id, api_token)

    # Push the commit
    try:
        subprocess.run(['git', 'push'], check=True)
        print("Pushed changes to the repository.")
    except subprocess.CalledProcessError as e:
        print(f"Error pushing changes: {e}")

if __name__ == "__main__":
    main()
