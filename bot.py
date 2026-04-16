# bot.py
# Purpose: Telegram interface for the Match Analyst agent
# Uses python-telegram-bot v21+ (async API)
# Uses HTML parse mode (more forgiving than Markdown for Telegram)

import os
import re
import html
import asyncio
import logging
from dotenv import load_dotenv

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from analyst import analyse_match

load_dotenv()

# --- Setup logging ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# --- Constants ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN not found in .env file")

TELEGRAM_MAX_LENGTH = 4000  # Telegram's cap is 4096; leave a buffer

# Known section labels — these are what Claude produces per our system prompt.
# We bold these explicitly so we don't depend on Claude's ** pairing being symmetric.
SECTION_LABELS = [
    "THE STORY",
    "THE DECISIVE FACTOR",
    "HOW IT PLAYED OUT",
    "THE NUMBERS THAT MATTER",
    "VERDICT",
    "HEAD-TO-HEAD",
    "PLAYING STYLES",
    "THE KEY MATCHUP DYNAMIC",
    "RECENT FORM",
]


def format_for_telegram(text: str) -> str:
    """
    Convert Claude's Markdown output to Telegram HTML.

    Strategy:
      1. Strip ALL asterisks (Claude's ** is unreliable — sometimes unpaired).
      2. Strip horizontal rule dividers (---).
      3. Escape HTML special chars.
      4. Bold the top header line (e.g. "Player A def. Player B 6-4 6-2").
      5. Bold known section labels like "THE STORY:" explicitly.
      6. Tidy up extra blank lines.
    """

    # Step 1: Remove all asterisks. We'll rebuild formatting from known patterns.
    text = text.replace("*", "")

    # Step 2: Remove horizontal rule lines
    text = re.sub(r"^\s*---+\s*$", "", text, flags=re.MULTILINE)

    # Step 3: Strip leading "## " / "### " / "# " markdown header syntax,
    # but remember which lines were headers so we can bold them.
    lines = text.split("\n")
    cleaned_lines = []
    header_line_indices = set()

    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith("### "):
            cleaned_lines.append(stripped[4:].rstrip())
            header_line_indices.add(len(cleaned_lines) - 1)
        elif stripped.startswith("## "):
            cleaned_lines.append(stripped[3:].rstrip())
            header_line_indices.add(len(cleaned_lines) - 1)
        elif stripped.startswith("# "):
            cleaned_lines.append(stripped[2:].rstrip())
            header_line_indices.add(len(cleaned_lines) - 1)
        else:
            cleaned_lines.append(line.rstrip())

    # Step 4: Escape HTML special chars line-by-line (so we can safely inject <b>)
    escaped_lines = [html.escape(line) for line in cleaned_lines]

    # Step 5: Wrap header lines in <b>...</b>
    formatted_lines = []
    for i, line in enumerate(escaped_lines):
        if i in header_line_indices and line.strip():
            formatted_lines.append(f"<b>{line}</b>")
        else:
            formatted_lines.append(line)

    text = "\n".join(formatted_lines)

    # Step 6: Bold section labels explicitly. These appear at the start of a line,
    # usually followed by a colon. Matching after HTML-escaping is fine because
    # the labels themselves have no special characters.
    for label in SECTION_LABELS:
        # Match: start of line, label, optional colon, rest of line
        # Replace with: <b>LABEL</b> + rest
        pattern = rf"^({re.escape(label)})(\s*:?)"
        text = re.sub(
            pattern,
            r"<b>\1</b>\2",
            text,
            flags=re.MULTILINE,
        )

    # Step 7: Collapse 3+ consecutive newlines into 2
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def split_message(text: str, max_length: int = TELEGRAM_MAX_LENGTH) -> list[str]:
    """Split messages over Telegram's limit at paragraph boundaries."""
    if len(text) <= max_length:
        return [text]

    chunks = []
    current_chunk = ""

    for paragraph in text.split("\n\n"):
        if len(current_chunk) + len(paragraph) + 2 > max_length:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = paragraph
        else:
            current_chunk += "\n\n" + paragraph if current_chunk else paragraph

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks


# --- Command handlers ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /start."""
    welcome = (
        "🎾 <b>Welcome to the Tennis Match Analyst!</b>\n\n"
        "I'm your personal tennis analyst. Send me a match and I'll break down "
        "what happened, who played well, and why.\n\n"
        "<b>Examples:</b>\n"
        "• Sinner vs Djokovic Australian Open 2025 final\n"
        "• Why did Alcaraz lose to Sinner at Wimbledon?\n"
        "• What happened in the last Roland Garros final?\n\n"
        "Type /help for more commands."
    )
    await update.message.reply_text(welcome, parse_mode=ParseMode.HTML)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /help."""
    help_text = (
        "<b>How to use me:</b>\n\n"
        "Just send me a tennis match you want analysed. I understand casual language.\n\n"
        "<b>What I can do:</b>\n"
        "• Analyse any ATP/WTA match — tell me the players, tournament, and year\n"
        "• Explain why someone won or lost\n"
        "• Break down stats, turning points, and tactics\n"
        "• Compare two players (e.g. 'Compare Sinner vs Alcaraz on clay')\n\n"
        "<b>Commands:</b>\n"
        "/start — welcome message\n"
        "/help — this message\n\n"
        "<b>Tip:</b> Include the year for best results. 'Sinner vs Djokovic AO 2025' "
        "works better than just 'Sinner vs Djokovic'."
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle any plain text message — runs the agent."""
    user_input = update.message.text
    user = update.effective_user
    logger.info(f"Message from {user.username or user.id}: {user_input}")

    thinking_msg = await update.message.reply_text(
        "🎾 Analysing the match... this usually takes 15–30 seconds."
    )

    try:
        response = await asyncio.to_thread(analyse_match, user_input, False)
        formatted = format_for_telegram(response)
        chunks = split_message(formatted)

        await thinking_msg.delete()

        for chunk in chunks:
            try:
                await update.message.reply_text(chunk, parse_mode=ParseMode.HTML)
            except Exception as e:
                logger.warning(f"HTML send failed: {e}. Falling back to plain text.")
                plain = re.sub(r"<[^>]+>", "", chunk)
                await update.message.reply_text(plain)

    except Exception as e:
        logger.error(f"Error handling message: {e}", exc_info=True)
        try:
            await thinking_msg.delete()
        except Exception:
            pass
        await update.message.reply_text(
            "⚠️ Sorry, something went wrong. Please try again in a moment."
        )


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Unknown command."""
    await update.message.reply_text(
        "I don't know that command. Try /help for what I can do."
    )


# --- Main ---
def main() -> None:
    """Start the bot."""
    logger.info("Starting Tennis Match Analyst Bot...")

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    logger.info("Bot is running. Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()