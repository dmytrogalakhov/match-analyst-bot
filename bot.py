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

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from analyst import analyse_match
from parser import parse_match_query, is_ambiguous

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
      6. Bold any ALL-CAPS label ending in colon (catches translated labels).
      7. Tidy up extra blank lines.
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

    # Step 6: Bold known English section labels explicitly.
    for label in SECTION_LABELS:
        pattern = rf"^({re.escape(label)})(\s*:?)"
        text = re.sub(
            pattern,
            r"<b>\1</b>\2",
            text,
            flags=re.MULTILINE,
        )

    # Step 7: Fallback — bold any ALL-CAPS line-start label ending in a colon.
    # Catches translated section labels like "ІСТОРІЯ МАТЧУ:" in Ukrainian,
    # "ИСТОРИЯ МАТЧА:" in Russian, "ЦИФРИ, ЩО МАЮТЬ ЗНАЧЕННЯ:" etc.
    # Allows Latin, Cyrillic (including Ukrainian letters), spaces, and commas.
    text = re.sub(
        r"^([А-ЯЄІЇҐA-Z][А-ЯЄІЇҐA-Z\s,]{2,50})(:)",
        r"<b>\1</b>\2",
        text,
        flags=re.MULTILINE,
    )

    # Step 8: Collapse 3+ consecutive newlines into 2
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


# =============================================================================
# COMMAND HANDLERS
# =============================================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /start."""
    welcome = (
        "🎾 <b>Welcome to TennisMind!</b>\n\n"
        "I'm your personal tennis analyst. Send me a match and I'll break down "
        "what happened, who played well, and why.\n\n"
        "<b>Examples:</b>\n"
        "• Sinner vs Alcaraz Roland Garros 2025 final\n"
        "• Compare Sinner to Alcaraz\n"
        "• What happened in the last Australian Open final?\n\n"
        "<b>Commands:</b>\n"
        "/help — what I can do\n"
        "/racket — get a racket recommendation 🆕\n\n"
        "Type /help for more details."
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
        "• Compare two players (e.g. 'Compare Sinner vs Alcaraz on clay')\n"
        "• 🆕 Get a personalised racket recommendation (/racket)\n\n"
        "<b>Commands:</b>\n"
        "/start — welcome message\n"
        "/help — this message\n"
        "/racket — racket recommendation wizard\n\n"
        "<b>Tip:</b> Include the year for best results. 'Sinner vs Djokovic AO 2025' "
        "works better than just 'Sinner vs Djokovic'."
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)


# =============================================================================
# CORE: RUN AGENT AND REPLY
# =============================================================================

async def run_agent_and_reply(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_input: str,
) -> None:
    """
    Run the agent and send the result to the user.
    
    This is the shared function called by both:
    - handle_message (when query is unambiguous → run immediately)
    - handle_callback (after user taps a clarification button)
    """
    chat_id = update.effective_chat.id

    thinking_msg = await context.bot.send_message(
        chat_id=chat_id,
        text="🎾 Analysing the match... this usually takes 15–30 seconds.",
    )

    try:
        # Run the sync agent in a thread pool so the bot stays responsive
        response = await asyncio.to_thread(analyse_match, user_input, False)

        # Format for Telegram HTML
        formatted = format_for_telegram(response)

        # Split if too long
        chunks = split_message(formatted)

        # Delete the "thinking..." message and send the real response
        await thinking_msg.delete()

        for chunk in chunks:
            try:
                await context.bot.send_message(
                    chat_id=chat_id, text=chunk, parse_mode=ParseMode.HTML
                )
            except Exception as e:
                logger.warning(f"HTML send failed: {e}. Falling back to plain text.")
                plain = re.sub(r"<[^>]+>", "", chunk)
                await context.bot.send_message(chat_id=chat_id, text=plain)

    except Exception as e:
        logger.error(f"Error handling message: {e}", exc_info=True)
        try:
            await thinking_msg.delete()
        except Exception:
            pass
        await context.bot.send_message(
            chat_id=chat_id,
            text="⚠️ Sorry, something went wrong. Please try again in a moment.",
        )


# =============================================================================
# MESSAGE HANDLER (with clarification logic)
# =============================================================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle any plain text message.
    
    Flow:
    1. Quick-parse the query (one fast LLM call)
    2. Check if ambiguous (e.g. "Roland Garros 2025 final" — men's or women's?)
    3. If ambiguous → show buttons and wait for user to pick
    4. If clear → run the agent directly
    """
    user_input = update.message.text
    user = update.effective_user
    logger.info(f"Message from {user.username or user.id}: {user_input}")

    # Quick parse to check for ambiguity BEFORE the heavy agent call
    parsed = parse_match_query(user_input)
    ambiguous, ambiguity_type = is_ambiguous(parsed)

    if ambiguous and ambiguity_type == "gender":
        # Stash the original query so we can resume after the user picks
        context.user_data["pending_query"] = user_input

        keyboard = [
            [
                InlineKeyboardButton("🎾 Men's", callback_data="gender:mens"),
                InlineKeyboardButton("🎾 Women's", callback_data="gender:womens"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "Quick question — men's or women's final?",
            reply_markup=reply_markup,
        )
        return  # Wait for button tap before running the agent

    # No ambiguity — run the agent directly
    await run_agent_and_reply(update, context, user_input)


# =============================================================================
# CALLBACK HANDLER (button taps)
# =============================================================================

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle inline keyboard button taps (e.g. Men's / Women's clarification).
    
    Flow:
    1. User tapped a button → we get the callback_data (e.g. "gender:mens")
    2. Retrieve the original query from context.user_data
    3. Enrich the query with the user's choice
    4. Run the agent with the enriched query
    """
    query = update.callback_query
    await query.answer()  # Acknowledge the tap so Telegram stops showing a spinner

    data = query.data  # e.g. "gender:mens"

    if data.startswith("gender:"):
        gender_choice = data.split(":")[1]  # "mens" or "womens"
        pending = context.user_data.get("pending_query")

        if not pending:
            await query.edit_message_text(
                "Sorry, I lost track of your original question. Please send it again."
            )
            return

        # Enrich the query with the gender and clear pending state
        gender_word = "men's" if gender_choice == "mens" else "women's"
        enriched_input = f"{pending} ({gender_word} final)"
        context.user_data.pop("pending_query", None)

        # Edit the button message to show what they picked (nicer UX)
        await query.edit_message_text(f"Got it — analysing the {gender_word} final...")

        # Now run the full agent pipeline with the enriched query
        await run_agent_and_reply(update, context, enriched_input)


# =============================================================================
# UNKNOWN COMMAND HANDLER
# =============================================================================

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Unknown command."""
    await update.message.reply_text(
        "I don't know that command. Try /help for what I can do."
    )
# =============================================================================
#  PLACEHOLDER/RACKET COMMAND 
# =============================================================================

async def racket_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /racket — placeholder until the full feature is built."""
    await update.message.reply_text(
        "🎾 <b>Racket Recommendation Wizard</b>\n\n"
        "This feature is coming soon! I'll ask you about your playing level, "
        "style, and preferences, then recommend the perfect racket for your game.\n\n"
        "Stay tuned — it's being built right now. 🚀",
        parse_mode=ParseMode.HTML,
    )

# =============================================================================
# MAIN
# =============================================================================

def main() -> None:
    """Start the bot."""
    logger.info("Starting Tennis Match Analyst Bot...")

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("racket", racket_command))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    logger.info("Bot is running. Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()