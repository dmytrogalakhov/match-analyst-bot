# publish_now.py
import os
import sys
import re
import asyncio
from dotenv import load_dotenv
from telegram import Bot
from telegram.constants import ParseMode
from analyst import analyse_match
from editor import format_for_telegram

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

if not TELEGRAM_BOT_TOKEN:
    print("ERROR: TELEGRAM_BOT_TOKEN not found in .env")
    sys.exit(1)
if not TELEGRAM_CHANNEL_ID:
    print("ERROR: TELEGRAM_CHANNEL_ID not found in .env")
    sys.exit(1)


def split_message(text, max_length=4000):
    if len(text) <= max_length:
        return [text]
    chunks = []
    current = ""
    for paragraph in text.split("\n\n"):
        if len(current) + len(paragraph) + 2 > max_length:
            if current:
                chunks.append(current.strip())
            current = paragraph
        else:
            current += "\n\n" + paragraph if current else paragraph
    if current:
        chunks.append(current.strip())
    return chunks


async def publish_to_channel(formatted_text):
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    chunks = split_message(formatted_text)
    for chunk in chunks:
        try:
            await bot.send_message(
                chat_id=TELEGRAM_CHANNEL_ID,
                text=chunk,
                parse_mode=ParseMode.HTML,
            )
        except Exception as e:
            print(f"HTML failed: {e}")
            plain = re.sub(r"<[^>]+>", "", chunk)
            await bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=plain)
    print(f"\n✅ Published to {TELEGRAM_CHANNEL_ID}!")


def main():
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = input("Match to analyse: ").strip()
        if not query:
            sys.exit(1)

    print(f"\n🎾 Generating analysis for: {query}")
    print("This may take 15-30 seconds...\n")

    raw_analysis = analyse_match(query, verbose=True)
    formatted = format_for_telegram(raw_analysis)

    print("\n" + "=" * 50)
    print("PREVIEW:")
    print("=" * 50)
    print(formatted)
    print("=" * 50)
    print(f"\nChannel: {TELEGRAM_CHANNEL_ID}")
    print(f"Length: {len(formatted)} characters")

    confirm = input("\nPublish to your channel? (yes/no): ").strip().lower()

    if confirm in ["yes", "y"]:
        asyncio.run(publish_to_channel(formatted))
    else:
        print("Cancelled.")


if __name__ == "__main__":
    main()