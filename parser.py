# parser.py
# Purpose: Extract structured match info from natural language input

import os
import json
from datetime import datetime
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic

load_dotenv()

llm = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    temperature=0,  # deterministic parsing
)


def parse_match_query(user_input: str) -> dict:
    """
    Takes a natural language query about a tennis match and extracts
    structured information from it.
    """

    now = datetime.now()
    current_year = now.year
    current_date_str = now.strftime("%B %d, %Y")  # e.g. "April 16, 2026"

    parsing_prompt = f"""Extract tennis match information from this user query. 
Return ONLY valid JSON, no other text.

User query: "{user_input}"

TODAY'S DATE: {current_date_str}
CURRENT YEAR: {current_year}

Extract these fields (use null if not mentioned or not inferable):
- "player1": full name of the first player mentioned
- "player2": full name of the second player mentioned (null if not mentioned)
- "tournament": full tournament name (e.g. "Roland Garros" not "RG")
- "year": the year of the match. See inference rules below.
- "round": the round if mentioned (e.g. "Final", "Semifinal", "Quarterfinal")
- "surface": the surface if you can infer it from the tournament
- "query_type": one of "analysis", "comparison", "prediction", "stats"
- "gender": "mens" if the query implies the men's tour, "womens" if it implies 
  the women's tour, null if unclear. Use these signals:
  - "mens": mentions of male players (Sinner, Djokovic, Alcaraz, Nadal, Federer, 
    Zverev, Medvedev, etc.), or the words "ATP", "men", "men's"
  - "womens": mentions of female players (Swiatek, Sabalenka, Gauff, Rybakina, 
    Osaka, Serena, Venus, etc.), or the words "WTA", "women", "women's"
  - null: no player names and no gender keywords (e.g. just "Roland Garros 2025 final")

## YEAR INFERENCE RULES (very important)

Tournament timings in the calendar:
- Australian Open: January
- Indian Wells, Miami: March
- Monte Carlo, Madrid, Rome: April–May
- Roland Garros / French Open: late May–early June
- Wimbledon: late June–early July
- US Open: late August–early September
- ATP/WTA Finals: November

To infer the year from phrases like "last [tournament]" or "the last [tournament] final"
or just "[tournament] final" (with no year):
1. Check if the tournament has already been played in {current_year}, given today is {current_date_str}.
2. If YES → "last [tournament]" means {current_year}.
3. If NO → "last [tournament]" means {current_year - 1}.

Other phrases:
- "this year" → "{current_year}"
- "last year" → "{current_year - 1}"
- "recent" / "recently" → "{current_year}" if the tournament has happened this year, else "{current_year - 1}"

If the user gives an explicit year (e.g. "2024"), use that.

## EXPANSIONS

- Abbreviations: "AO" = "Australian Open", "RG" = "Roland Garros", 
  "USO" = "US Open", "Wimby" = "Wimbledon", "MC" = "Monte Carlo"
- Full player names: "Novak" = "Novak Djokovic", "Rafa" = "Rafael Nadal",
  "Sinner" = "Jannik Sinner", "Alcaraz" = "Carlos Alcaraz", 
  "Medvedev" = "Daniil Medvedev", "Zverev" = "Alexander Zverev",
  "Swiatek" = "Iga Swiatek", "Sabalenka" = "Aryna Sabalenka",
  "Gauff" = "Coco Gauff", "Rybakina" = "Elena Rybakina"

## OTHER RULES

- Surface from tournament: Australian Open = Hard, Roland Garros/French Open = Clay, 
  Wimbledon = Grass, US Open = Hard, Monte Carlo = Clay, Madrid = Clay, Rome = Clay, 
  Indian Wells = Hard, Miami = Hard
- If the user asks "why did X lose" → player1 = X (the person who lost), 
  player2 = null if the opponent is not named

Return ONLY the JSON object. No markdown, no explanation, no code fences."""

    response = llm.invoke(parsing_prompt)

    try:
        # Some models may still wrap JSON in code fences — strip them defensively
        text = response.content.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        parsed = json.loads(text)
        return parsed
    except (json.JSONDecodeError, IndexError):
        return {
            "player1": None,
            "player2": None,
            "tournament": None,
            "year": None,
            "round": None,
            "surface": None,
            "gender": None,
            "query_type": "analysis",
            "raw_query": user_input,
        }


def is_ambiguous(parsed: dict) -> tuple[bool, str | None]:
    """
    Checks if the parsed query is ambiguous and needs clarification.

    Returns a tuple:
        (False, None)      — the query is clear, proceed normally
        (True, "gender")   — we can't tell if it's men's or women's

    This is used by bot.py to decide whether to show clarification buttons
    before running the expensive agent.
    """
    # Gender ambiguity: tournament + final mentioned, but no gender signal
    # and no player names that would imply a gender
    if (
        parsed.get("tournament")
        and parsed.get("round") == "Final"
        and not parsed.get("gender")
        and not parsed.get("player1")
        and not parsed.get("player2")
    ):
        return (True, "gender")

    return (False, None)