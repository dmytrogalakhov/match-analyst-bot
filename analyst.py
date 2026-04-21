# analyst.py
# Purpose: The core analysis function, callable from any interface
#          (command line, Telegram, web API, etc.)
# Uses LangChain v1.x API

import os
import time
from dotenv import load_dotenv

load_dotenv()

from langchain_anthropic import ChatAnthropic
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain.agents import create_agent

from parser import parse_match_query
from validator import validate_input

# --- LLM ---
llm = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    temperature=0.3,
    timeout=120,
)

# --- Search Tool ---
search_tool = TavilySearchResults(
    max_results=5,
    description=(
        "Search the web for tennis match statistics, scores, and commentary. "
        "Use this to find specific match data, player stats, and tactical analysis. "
        "ALWAYS include the year in your search queries to get accurate results."
    ),
)
tools = [search_tool]

# =============================================================================
# MATCH ANALYSIS AGENT
# =============================================================================

analysis_system_prompt = """You are an elite tennis match analyst. You combine the tactical 
insight of Brad Gilbert, the statistical rigour of Craig O'Shannessy, and the 
storytelling ability of a great sports journalist.

## YOUR TASK
When a user asks about a tennis match, produce a tactical breakdown that helps them 
UNDERSTAND what happened and why — not just what the score was.

## CRITICAL YEAR-MATCHING RULE (MOST IMPORTANT)

If the user's query specifies a year, the match you analyse MUST be from that exact year.

- ALWAYS include the year in EVERY search query you make.
- BEFORE writing the analysis, verify the search results match the requested year.
- If search results return a match from a DIFFERENT year, do NOT analyse it. 
  Search again with more specific queries (e.g. add the month, add both player names).
- If after 3-4 searches you still cannot find data for the requested year, 
  respond honestly: "I couldn't find reliable information about the [Tournament] 
  [Year] final. The search returned data about the [wrong year] edition instead. 
  Could you provide the players or the score, and I'll analyse from there?"
- If the user mentions a specific player but that player did not play in the 
  specified round, DO NOT silently analyse a different match. Instead:
  1. Tell the user that [Player] did not play in [Round] at [Tournament] [Year]
  2. Tell them who actually played in that round
  3. If you can find what round [Player] reached, mention that 
     (e.g. "Swiatek lost in the semifinals to Gauff")
  4. Ask if they'd like you to analyse the actual final, or the player's 
     last match at that tournament

DO NOT confabulate. DO NOT analyse the wrong year "because it's the closest match".
Honest failure is better than a wrong answer.

## YOUR PROCESS

### Step 1: Search thoroughly (ALWAYS INCLUDE THE YEAR)
Never rely on training data. Make at least 2 searches:
  - Search 1: "[Tournament] [Year] final result winner"
  - Search 2: "[Player1] [Player2] [Tournament] [Year] statistics"
If results don't match the year, search again:
  - Search 3: "[Tournament] [Year] men's final" or "women's final" (specify which)
  - Search 4: "who won [Tournament] [Year]"

### Step 2: Verify the year (internally — never in your final output)
Think silently: "Are my search results actually about [Year]?"
If not, search again or state you couldn't find the data.
This verification is for YOU, not for the user. Never write it in your response.

### Step 3: Identify the decisive pattern
"If I had to explain why the winner won in ONE sentence, what would I say?"

Common decisive patterns:
- Return dominance, first-strike tennis, physical attrition, net pressure,
- Mental collapse, tactical adjustment, clutch factor in big moments

### Step 4: Write the analysis

Structure:

---

## [Player A] def. [Player B] [score]
### [Tournament], [Round], [Surface] — [Year]

**THE STORY**: [2-3 sentences — the narrative arc.]

**THE DECISIVE FACTOR**: [One-sentence thesis. Bold it.]

**HOW IT PLAYED OUT**: [Turning points only, not set-by-set.]

**THE NUMBERS THAT MATTER**: [3-5 stats with context.]

**VERDICT**: [2-3 sentences on the biggest factor and what it means going forward.]

---

## IMPORTANT RULES
- Be SPECIFIC with numbers and scores.
- Don't pad with generic commentary.
- If a player lost, explain what they could have done differently.
- Confident analyst voice.
- Keep under 500 words.
- If only the men's OR women's final was asked for, analyse only that one 
  (don't analyse both unless explicitly asked).

## OUTPUT FORMAT RULES (VERY IMPORTANT)
- When producing a match analysis: your response is ONLY the analysis itself, 
  starting directly with the "## [Player A] def. [Player B]" header.
  No preamble, no meta-commentary, no "Let me verify..." or "Based on my 
  searches..." Start with the header. End with the VERDICT.
- When the requested player was NOT in the requested match: do NOT use 
  the analysis format above. Instead, write a short, helpful message 
  explaining the mismatch. No headers, no sections — just a clear 
  conversational response telling the user what you found and offering 
  alternatives.
- When you couldn't find data: write a short, honest message explaining 
  what went wrong and suggesting how the user could refine their query.
- Do NOT include phrases like "YEAR VERIFICATION" or "✅ Confirmed" in 
  your output under any circumstances.

## LANGUAGE MATCHING (MANDATORY)
- You will receive a RESPOND_IN_LANGUAGE directive in the user's message.
  Follow it strictly.
- Respond ENTIRELY in the specified language. This includes the analysis,
  error messages, clarification requests, "I couldn't find" responses —
  EVERYTHING.
- Keep tennis terminology natural. When responding in Ukrainian or Russian, 
  transliterate player names to Cyrillic (e.g. "Бен Шелтон", "Флавіо Коболлі", 
  "Яннік Сіннер", "Карлос Алькарас", "Новак Джокович"). When responding in 
  English or other Latin-script languages, keep names in their original form.
- Section labels MUST be translated AND kept in ALL CAPS.
  Examples for Ukrainian: ІСТОРІЯ МАТЧУ, ВИРІШАЛЬНИЙ ФАКТОР, ЯК ЦЕ ВІДБУВАЛОСЬ, 
  ЦИФРИ, ЩО МАЮТЬ ЗНАЧЕННЯ, ВЕРДИКТ.
  Examples for Russian: ИСТОРИЯ МАТЧА, РЕШАЮЩИЙ ФАКТОР, КАК ЭТО ПРОИЗОШЛО, 
  КЛЮЧЕВЫЕ ЦИФРЫ, ВЕРДИКТ.
- Default to English ONLY if the directive says "English" or is missing.
"""

analysis_agent = create_agent(
    llm,
    tools=tools,
    system_prompt=analysis_system_prompt,
)

# =============================================================================
# COMPARISON AGENT
# =============================================================================

comparison_system_prompt = """You are an elite tennis analyst specialising in 
player comparisons. You have deep knowledge of head-to-head records, surface-specific 
form, playing styles, and historical context.

## YOUR TASK
When asked to compare two players, produce a comparison that helps the user 
understand their relative strengths, head-to-head history, and how they match up 
against each other — especially on a specific surface if mentioned.

## YOUR PROCESS

### Step 1: Search
Make 2-3 targeted searches:
- "[Player1] vs [Player2] head to head record"
- "[Player1] [Player2] [surface] statistics career"
- Optionally: "[Player1] vs [Player2] playing styles analysis"

### Step 2: Structure your comparison

Format EXACTLY like this:

---

## [Player 1] vs [Player 2] — [Surface if specified]

**HEAD-TO-HEAD**: [Overall record: e.g. "Sinner leads 4-3 overall, 2-1 on clay"]

**PLAYING STYLES**:
- **[Player 1]**: [2-3 sentences on their game]
- **[Player 2]**: [2-3 sentences on their game]

**THE KEY MATCHUP DYNAMIC**: [1 sentence: what happens when they play? Which 
patterns favour which player? What's the tactical story of their rivalry?]

**ON [SURFACE]** (if surface specified):
[Why this surface favours one over the other — or why it's close. 
Include any surface-specific H2H or tournament results.]

**RECENT FORM**: [How each player has been performing lately]

**VERDICT**: [Who has the edge and why, in 2-3 sentences]

---

## IMPORTANT RULES
- Be specific with numbers (H2H records, tournament wins, rankings).
- Don't be generic ("both are great players") — make real distinctions.
- If no surface is specified, compare them overall.
- Keep under 500 words.

## OUTPUT FORMAT RULES (VERY IMPORTANT)
- Your final response is ONLY the comparison itself, starting with the 
  "## [Player 1] vs [Player 2]" header.
- Do NOT include preamble like "Based on my searches..." or "Let me compare..."
- Do NOT include meta-commentary about your process.
- Start with the header. End with the VERDICT. Nothing else.

## LANGUAGE MATCHING (MANDATORY)
- You will receive a RESPOND_IN_LANGUAGE directive in the user's message.
  Follow it strictly.
- Respond ENTIRELY in the specified language. This includes the comparison,
  error messages, clarification requests — EVERYTHING.
- Keep tennis terminology natural. When responding in Ukrainian or Russian, 
  transliterate player names to Cyrillic (e.g. "Бен Шелтон", "Флавіо Коболлі", 
  "Яннік Сіннер", "Карлос Алькарас", "Новак Джокович"). When responding in 
  English or other Latin-script languages, keep names in their original form.
- Section labels MUST be translated AND kept in ALL CAPS.
- Default to English ONLY if the directive says "English" or is missing.
"""

comparison_agent = create_agent(
    llm,
    tools=tools,
    system_prompt=comparison_system_prompt,
)


# =============================================================================
# LANGUAGE DETECTION
# =============================================================================

def detect_language(text: str) -> str:
    """
    Simple language detection based on character analysis.
    
    Key rule: if the user writes ANY words in Cyrillic, they want
    a Cyrillic-language response. People don't accidentally type
    in Ukrainian/Russian — but they do mix in Latin player names
    and tournament names like "Shelton vs Cobolli BMW Open".
    """
    # Count Cyrillic characters (ignoring spaces, numbers, punctuation)
    cyrillic_chars = sum(1 for c in text if '\u0400' <= c <= '\u04FF')

    # Ukrainian-specific letters: і, ї, є, ґ
    ukrainian_markers = sum(1 for c in text.lower() if c in 'іїєґ')

    # If ANY meaningful Cyrillic text is present, it's a Cyrillic language
    # 3+ chars = at least one real word, not accidental
    if cyrillic_chars >= 3:
        if ukrainian_markers > 0:
            return "Ukrainian"
        return "Russian"

    # Latin-based — check for diacritics
    if any(c in text.lower() for c in 'áéíóúñ¿¡'):
        return "Spanish"
    if any(c in text.lower() for c in 'àâçèêëîïôùûüœæ'):
        return "French"
    if any(c in text.lower() for c in 'äöüß'):
        return "German"

    return "English"


# =============================================================================
# COMPARISON FUNCTION
# =============================================================================

def compare_players(user_input: str, verbose: bool = False) -> str:
    """Compare two players, optionally on a specific surface."""
    if verbose:
        print("\nRunning comparison mode...")

    parsed = parse_match_query(user_input)

    if not parsed.get("player1") or not parsed.get("player2"):
        return (
            "🎾 I need two players to compare. Try something like:\n"
            "'Compare Sinner and Alcaraz on clay'"
        )

    query_parts = [f"Compare {parsed['player1']} vs {parsed['player2']}"]
    if parsed.get("surface"):
        query_parts.append(f"on {parsed['surface']}")

    enriched = " ".join(query_parts)

    # Detect language and add directive
    language = detect_language(user_input)
    enriched += f"\n\n🌐 RESPOND_IN_LANGUAGE: {language}"
    enriched += f"\nOriginal question: '{user_input}'"

    if verbose:
        print(f"Detected language: {language}")
        print(f"Understood: {enriched}")
        print("\nComparing... (this may take 15-30 seconds)\n")

    max_retries = 3
    for attempt in range(max_retries):
        try:
            result = comparison_agent.invoke({
                "messages": [{"role": "user", "content": enriched}]
            })
            return result["messages"][-1].content
        except Exception as e:
            if "500" in str(e) and attempt < max_retries - 1:
                if verbose:
                    print(f"Server error. Retrying in 5 seconds... (attempt {attempt + 2}/{max_retries})")
                time.sleep(5)
                continue
            return f"Sorry, I hit an error while comparing those players: {str(e)}"

    return "Sorry, something went wrong after multiple retries. Please try again."


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def analyse_match(user_input: str, verbose: bool = False) -> str:
    """
    Takes a user's tennis query and returns an analysis or comparison.

    Args:
        user_input: The raw user query
        verbose: If True, print intermediate steps. Use True for CLI, False for API/Telegram.
    """

    # Step 1: Validate
    if verbose:
        print("\nChecking your query...")
    validation = validate_input(user_input)
    if not validation.get("is_valid", True):
        reason = validation.get("reason", "That doesn't look like a tennis match query.")
        suggestion = validation.get("suggestion", "Try asking about a specific match!")
        return f"🎾 {reason}\n\nTry something like: {suggestion}"

    # Step 2: Parse
    if verbose:
        print("Parsing your query...")
    parsed = parse_match_query(user_input)
    if verbose:
        print(f"  → Parsed: {parsed}")

    # Step 3: Route to comparison mode if that's what the user asked for
    if parsed.get("query_type") == "comparison":
        return compare_players(user_input, verbose=verbose)

    # Step 4: Detect language from the original input
    language = detect_language(user_input)
    if verbose:
        print(f"  → Detected language: {language}")

    # Step 5: Build enriched query for match analysis
    parts = []

    if parsed.get("player1") and parsed.get("player2"):
        parts.append(
            f"Analyse this tennis match: {parsed['player1']} vs {parsed['player2']}"
        )
    elif parsed.get("player1"):
        if parsed.get("round"):
            # Don't include "at" here — the tournament line adds "at the ..." next
            parts.append(
                f"Find and analyse {parsed['player1']}'s {parsed['round']} match"
            )
        else:
            parts.append(
                f"Find and analyse the tennis match involving {parsed['player1']}"
            )
    else:
        parts.append(f"Analyse this tennis query: {user_input}")

    if parsed.get("tournament"):
        parts.append(f"at the {parsed['tournament']}")
    if parsed.get("year"):
        parts.append(f"in {parsed['year']}")
    if parsed.get("round") and not (parsed.get("player1") and not parsed.get("player2")):
        # Only add round separately if we didn't already fold it into the player line
        parts.append(f"({parsed['round']})")
    if parsed.get("surface"):
        parts.append(f"[surface: {parsed['surface']}]")

    enriched_query = " ".join(parts)

    # Player constraint — if a specific player + round, make the constraint explicit
    if parsed.get("player1") and not parsed.get("player2") and parsed.get("round"):
        enriched_query += (
            f"\n\n⚠️ PLAYER CONSTRAINT: {parsed['player1']} MUST be one of the "
            f"players in this match. If {parsed['player1']} did not play in the "
            f"{parsed['round']}, do NOT analyse whoever did play instead. "
            f"Instead, tell the user that {parsed['player1']} was not in the "
            f"{parsed['round']}, mention who actually played, tell the user what "
            f"round {parsed['player1']} reached, and ask what they'd like to see."
        )

    # Always append the original question so the agent knows the user's angle
    enriched_query += f"\n\nOriginal question: '{user_input}'"

    # Language directive — placed prominently so the agent can't miss it
    enriched_query += f"\n\n🌐 RESPOND_IN_LANGUAGE: {language}"
    enriched_query += (
        f"\nYou MUST write your ENTIRE response in {language}. "
        f"This includes the analysis, section labels, stats explanations, "
        f"error messages, and any clarification requests. "
        f"Section labels must be translated to {language} and kept in ALL CAPS."
    )

    # --- STRICT YEAR DIRECTIVE ---
    if parsed.get("year"):
        year = parsed["year"]
        enriched_query += (
            f"\n\n⚠️ CRITICAL: The match MUST be from {year}. "
            f"Every search query you make MUST include '{year}'. "
            f"If your searches return data from a different year, search again. "
            f"If you cannot find {year} data after multiple searches, say so honestly — "
            f"do NOT analyse a match from a different year."
        )

    if verbose:
        print(f"Understood: {enriched_query}")
        print("\nAnalysing... (this may take 15-30 seconds)\n")

    # Step 6: Run the analysis agent with retry logic
    max_retries = 3
    for attempt in range(max_retries):
        try:
            result = analysis_agent.invoke({
                "messages": [{"role": "user", "content": enriched_query}]
            })
            return result["messages"][-1].content

        except Exception as e:
            if "500" in str(e) and attempt < max_retries - 1:
                if verbose:
                    print(f"Server error. Retrying in 5 seconds... (attempt {attempt + 2}/{max_retries})")
                time.sleep(5)
                continue
            return f"Sorry, I hit an error while analysing that match: {str(e)}"

    return "Sorry, something went wrong after multiple retries. Please try again."


# --- CLI interface (for testing) ---
if __name__ == "__main__":
    print("=" * 60)
    print("  TENNIS MATCH ANALYST BOT")
    print("  Analyse a match or compare two players")
    print("  Type 'quit' to exit")
    print("=" * 60)
    print()

    while True:
        user_input = input("You: ").strip()

        if user_input.lower() in ["quit", "exit", "q"]:
            print("Goodbye!")
            break

        if not user_input:
            continue

        result = analyse_match(user_input, verbose=True)
        print("\n" + "=" * 60)
        print(result)
        print("=" * 60 + "\n")