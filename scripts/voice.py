import os
import markdown
from gtts import gTTS

def convert_md_to_mp3(input_file):
    # Read the Markdown file
    with open(input_file, 'r') as file:
        md_content = file.read()

    # Convert Markdown to HTML
    html_content = markdown.markdown(md_content)

    # Convert HTML to text
    text_content = html_to_text(html_content)

    # Generate MP3 file
    mp3_filename = os.path.splitext(os.path.basename(input_file))[0] + ".mp3"
    tts = gTTS(text=text_content, lang='en')
    tts.save(mp3_filename)

    print(f"MP3 file generated: {mp3_filename}")

def html_to_text(html):
    """
    Converts HTML content to plain text.
    """
    from html.parser import HTMLParser

    class HTMLToTextParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.text = ""

        def handle_data(self, data):
            self.text += data

    parser = HTMLToTextParser()
    parser.feed(html)
    return parser.text

if __name__ == "__main__":
    input_file = input("Enter the path to the Markdown file: ")
    convert_md_to_mp3(input_file)