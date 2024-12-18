import os
import sys
import json
from gtts import gTTS

def generate_voice_files(json_file):
    with open(json_file, 'r') as file:
        json_data = json.load(file)

    # Get the directory and filename of the input JSON file
    json_dir = os.path.dirname(os.path.abspath(json_file))
    json_filename = os.path.splitext(os.path.basename(json_file))[0]

    # Create the "sounds" subfolder and subfolder for the filename
    sounds_dir = os.path.join(json_dir, "sounds", json_filename)
    os.makedirs(sounds_dir, exist_ok=True)

    for i, page in enumerate(json_data["pages"]):
        text = page["content"]["response"]
        filename = os.path.join(sounds_dir, f"{i+1}.mp3")
        tts = gTTS(text=text, lang='en')
        tts.save(filename)
        print(f"Voice file generated: {filename}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py <path/to/file.json>")
        sys.exit(1)

    json_file = sys.argv[1]
    generate_voice_files(json_file)