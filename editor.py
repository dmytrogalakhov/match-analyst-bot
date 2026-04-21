# editor.py
# Purpose: Format analysis content for each platform
# Takes the raw agent output and adapts it for Telegram, Substack, and WhatsApp

import re
import html
from datetime import datetime
from config import PLATFORMS

# Known section labels for bolding (same list as bot.py)
SECTION_LABELS = [
    "THE STORY", "THE DECISIVE FACTOR", "HOW IT PLAYED OUT",
    "THE NUMBERS THAT MATTER", "VERDICT", "HEAD-TO-HEAD",
    "PLAYING STYLES", "THE KEY MATCHUP DYNAMIC", "RECENT FORM",
]


def format_for_telegram(text: str, channel_name: str = "") -> str:
    """
    Format analysis for Telegram channel posting.
    Uses HTML parse mode. Very similar to bot.py's formatter,
    but adds channel branding and hashtags.
    """
    # Strip asterisks
    text = text.replace("*", "")

    # Remove horizontal rules
    text = re.sub(r"^\s*---+\s*$", "", text, flags=re.MULTILINE)

    # Convert markdown headers to bold
    lines = text.split("\n")
    cleaned_lines = []
    header_indices = set()

    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("### "):
            cleaned_lines.append(stripped[4:].rstrip())
            header_indices.add(len(cleaned_lines) - 1)
        elif stripped.startswith("## "):
            cleaned_lines.append(stripped[3:].rstrip())
            header_indices.add(len(cleaned_lines) - 1)
        elif stripped.startswith("# "):
            cleaned_lines.append(stripped[2:].rstrip())
            header_indices.add(len(cleaned_lines) - 1)
        else:
            cleaned_lines.append(line.rstrip())

    # Escape HTML
    escaped = [html.escape(line) for line in cleaned_lines]

    # Bold headers
    formatted = []
    for i, line in enumerate(escaped):
        if i in header_indices and line.strip():
            formatted.append(f"<b>{line}</b>")
        else:
            formatted.append(line)

    text = "\n".join(formatted)

    # Bold English section labels
    for label in SECTION_LABELS:
        pattern = rf"^({re.escape(label)})(\s*:?)"
        text = re.sub(pattern, r"<b>\1</b>\2", text, flags=re.MULTILINE)

    # Bold translated section labels (ALL-CAPS Cyrillic/Latin with commas)
    text = re.sub(
        r"^([А-ЯЄІЇҐA-Z][А-ЯЄІЇҐA-Z\s,]{2,50})(:)",
        r"<b>\1</b>\2",
        text,
        flags=re.MULTILINE,
    )

    # Clean up blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Add channel branding footer
    text = text.strip()
    text += "\n\n🎾 #Tennis #TacticalAnalysis"

    return text


def format_for_substack(text: str, match_info: dict = None) -> str:
    """
    Format analysis for Substack newsletter.
    Substack uses standard Markdown. We enhance with:
    - SEO-friendly title
    - Editorial intro
    - Subscribe CTA at the end
    """
    # The agent output is already in Markdown — mostly leave it as-is
    # but clean up any formatting issues

    # Remove horizontal rules at the very start/end (they look odd in newsletters)
    text = re.sub(r"^\s*---+\s*\n", "", text)
    text = re.sub(r"\n\s*---+\s*$", "", text)

    # Build SEO title from match info if available
    title = ""
    if match_info:
        p1 = match_info.get("player1", "")
        p2 = match_info.get("player2", "")
        tournament = match_info.get("tournament", "")
        year = datetime.now().year
        if p1 and p2 and tournament:
            title = f"# {p1} vs {p2} at {tournament} {year}: A Tactical Breakdown\n\n"

    # Add subscribe CTA
    cta = (
        "\n\n---\n\n"
        "*Enjoyed this analysis? Subscribe to get tactical breakdowns of every "
        "major tennis match delivered to your inbox.*"
    )

    return title + text.strip() + cta


def format_for_whatsapp(text: str) -> str:
    """
    Format analysis for WhatsApp Channel.
    WhatsApp has very limited formatting:
    - *bold* (single asterisks)
    - _italic_ (underscores)
    - No headers, no HTML, no markdown links
    
    We need to make this scannable on a phone screen.
    """
    # Strip markdown headers — replace with emoji section markers
    text = re.sub(r"^##\s+(.+)$", r"🎾 \1", text, flags=re.MULTILINE)
    text = re.sub(r"^###\s+(.+)$", r"📊 \1", text, flags=re.MULTILINE)
    text = re.sub(r"^#\s+(.+)$", r"🏆 \1", text, flags=re.MULTILINE)

    # Remove horizontal rules
    text = re.sub(r"^\s*---+\s*$", "", text, flags=re.MULTILINE)

    # Convert **bold** to *bold* (WhatsApp uses single asterisk)
    text = re.sub(r"\*\*(.+?)\*\*", r"*\1*", text, flags=re.DOTALL)

    # Convert known section labels to WhatsApp bold
    for label in SECTION_LABELS:
        pattern = rf"^({re.escape(label)})(\s*:?)"
        text = re.sub(pattern, r"*\1*\2", text, flags=re.MULTILINE)

    # Bold translated section labels
    text = re.sub(
        r"^([А-ЯЄІЇҐA-Z][А-ЯЄІЇҐA-Z\s,]{2,50})(:)",
        r"*\1*\2",
        text,
        flags=re.MULTILINE,
    )

    # Clean up blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Trim for mobile reading — WhatsApp posts should be concise
    text = text.strip()

    # Add footer
    text += "\n\n🎾 Tennis Tactical Analysis"

    return text


def format_content(raw_analysis: str, platform: str, match_info: dict = None) -> str:
    """
    Main entry point. Routes to the right formatter.
    
    Args:
        raw_analysis: The agent's raw output (Markdown)
        platform: "telegram", "substack", or "whatsapp"
        match_info: Optional dict with player1, player2, tournament, etc.
    """
    if platform == "telegram":
        return format_for_telegram(raw_analysis)
    elif platform == "substack":
        return format_for_substack(raw_analysis, match_info)
    elif platform == "whatsapp":
        return format_for_whatsapp(raw_analysis)
    else:
        raise ValueError(f"Unknown platform: {platform}")


# --- CLI for testing ---
if __name__ == "__main__":
    sample = """## Carlos Alcaraz def. Jannik Sinner 4-6, 6-7(4), 6-4, 7-6(3), 7-6(10-2)
### Roland Garros, Final, Clay — 2025

**THE STORY**: In 5 hours and 29 minutes of pure tennis theater, Alcaraz pulled 
off one of the greatest comebacks in Grand Slam history.

**THE DECISIVE FACTOR**: Alcaraz's supernatural ability to elevate his level when 
facing elimination.

**THE NUMBERS THAT MATTER**: 
- Break points: Alcaraz converted 5/14
- Unforced errors sets 4-5: Just 12 vs 23 in sets 2-3

**VERDICT**: Championship DNA defined this match.
"""

    print("=" * 50)
    print("TELEGRAM VERSION:")
    print("=" * 50)
    print(format_content(sample, "telegram"))

    print("\n" + "=" * 50)
    print("SUBSTACK VERSION:")
    print("=" * 50)
    print(format_content(sample, "substack", {
        "player1": "Carlos Alcaraz",
        "player2": "Jannik Sinner",
        "tournament": "Roland Garros",
    }))

    print("\n" + "=" * 50)
    print("WHATSAPP VERSION:")
    print("=" * 50)
    print(format_content(sample, "whatsapp"))