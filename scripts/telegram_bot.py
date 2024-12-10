import asyncio
import os
from pathlib import Path
import sys
from telegram import Bot, InputMediaPhoto, InputMediaDocument, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError
import markdown

CONFIG = {
    "BOT_API_URL": "https://elemets.kermanconcert.ir/bot",
    "TELEGRAM_CHANNEL": "@ai_novelist",    
    "BASE_DIRECTORIES": [
        'kids/Air Pollution Reduction/fa/',
        'kids/Animal Protection/fa/',
        'kids/Tree Preservation/fa/',
        'kids/Waste Reduction/fa/',
        'kids/Water Conservation/fa/'
    ]
}
IMAGE_TYPES = ['3d_rendered', 'cartoon', 'chibi', 'flat_design', 'hand_drawn', 'real', 'storybook_illustration', 'vector_art', 'watercolor']
def get_env_variable(name):
    """Retrieve environment variable or exit if not found."""
    value = os.getenv(name)
    if not value:
        print(f"Error: Environment variable {name} not set.")
        sys.exit(1)
    return value

async def main():
    bot = Bot(token=get_env_variable('BOT_TOKEN'), base_url=CONFIG["BOT_API_URL"])

    for base_dir in CONFIG["BASE_DIRECTORIES"]:
        md_files = [str(p) for p in Path(base_dir).glob('*.md')]
        for md_file in md_files:
            caption = Path(md_file).stem
            url = f"https://ainovelist.ir/library/{Path(md_file).stem}"

            media = []
            image_base_name = Path(md_file).stem
            for image_type in IMAGE_TYPES :
                image_path = str(Path(base_dir, '../images', f'{image_base_name}-{image_type}.png'))
                with open(image_path, 'rb') as image_file:
                    media.append(InputMediaPhoto(image_file, caption=caption))

            reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(text="Read Story", url=url)]])

            try:
                result = await bot.send_media_group(chat_id=CONFIG["TELEGRAM_CHANNEL"], media=media)
                await bot.send_message(chat_id=CONFIG["TELEGRAM_CHANNEL"],text=url, reply_markup=reply_markup)
                print(result)
            except TelegramError as e:
                print(f"Error sending media group: {e}")

if __name__ == "__main__":
    asyncio.run(main())