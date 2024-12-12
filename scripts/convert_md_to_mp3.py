import os
import sys
import re
from gtts import gTTS
from pathlib import Path

def convert_md_to_mp3(md_file_path):
    # Get the file name without the extension
    file_name = os.path.splitext(os.path.basename(md_file_path))[0]

    # Create the "sounds" directory in the parent folder of the input file
    parent_dir = Path(md_file_path).parent.parent
    sounds_dir = parent_dir / "sounds/en"
    sounds_dir.mkdir(exist_ok=True)

    # Read the Markdown content
    with open(md_file_path, "r") as file:
        lines = file.readlines()
        md_content = "".join(lines[3:])
        # md_content = file.read()

    # Remove Markdown syntax and HTML tags
    plain_text = re.sub(r'#+\s*|\*\*|\*|_|`|<[^>]+>', '', md_content)

    # Generate the MP3 file
    tts = gTTS(text=plain_text, lang="en")
    mp3_file_path = sounds_dir / f"{file_name}.mp3"
    tts.save(str(mp3_file_path))

    print(f"MP3 file generated: {mp3_file_path}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/convert_md_to_mp3.py <path_to_md_file>")
        sys.exit(1)

    md_file_path = sys.argv[1]
    if not os.path.isfile(md_file_path):
        print(f"Error: File {md_file_path} does not exist.")
        sys.exit(1)

    convert_md_to_mp3(md_file_path)