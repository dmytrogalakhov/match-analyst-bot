# scheduler.py
# Purpose: Find recent notable tennis matches worth analysing
#
# Three-source approach:
# 1. Web discovery — ask the web what tournaments are active
# 2. Config probing — search for results at tournaments from our own config
#    (catches smaller tournaments the web discovery misses)
# 3. General fallback — broad searches for any tennis results
#
# Only processes tournaments listed in config.py.
# Searches last 48 hours. Supports manual date override for testing.

import os
import json
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_community.tools.tavily_search import TavilySearchResults

from config import (
    TOURNAMENT_CATEGORIES,
    CATEGORY_PRIORITY,
    ROUND_PRIORITY,
    COVERAGE_RULES,
    MAX_MATCHES_PER_DAY,
)

load_dotenv()

llm = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    temperature=0,
)

search_tool = TavilySearchResults(max_results=5)

# Unique tournament names to probe from config (deduplicated, human-readable)
# These are the tournaments we'll actively check for results
CONFIG_TOURNAMENTS_TO_PROBE = [
    # Grand Slams
    "Australian Open",
    "Roland Garros",
    "Wimbledon",
    "US Open",
    # Masters 1000
    "Indian Wells",
    "Miami Open",
    "Monte Carlo Masters",
    "Madrid Open",
    "Italian Open Rome",
    "Canadian Open",
    "Cincinnati Masters",
    "Shanghai Masters",
    "Paris Masters",
    # ATP 500
    "Barcelona Open",
    "Dubai Tennis",
    "Acapulco Open",
    "Queen's Club",
    "Halle Open",
    "Hamburg Open",
    "Washington Citi Open",
    "Beijing China Open",
    "Tokyo Japan Open",
    "Vienna Open",
    "Basel Swiss Indoors",
    "Rotterdam Open",
    "Rio Open",
    # ATP 250 (selected major ones)
    "BMW Open Munich",
    "Lyon Open",
    "Geneva Open",
    "Stuttgart Open",
    "Eastbourne tennis",
    "Mallorca Open",
    "Atlanta Open",
    "Stockholm Open",
    "Antwerp European Open",
    "Marseille Open",
    "Adelaide tennis",
    "Brisbane tennis",
    # Finals
    "ATP Finals",
    "WTA Finals",
]


def categorize_tournament(tournament_name: str) -> dict:
    """Look up a tournament in our categories config."""
    name_lower = tournament_name.lower()
    for key, info in TOURNAMENT_CATEGORIES.items():
        if key in name_lower:
            return info
    return {"category": "Unknown", "surface": "Unknown"}


def probe_config_tournaments(search_date: str) -> tuple[list[str], str]:
    """
    Source 2: Search for results at tournaments from our own config.
    
    Instead of searching each tournament individually (too many API calls),
    we batch them into category-level searches.
    
    Returns (list of tournament names with results, combined search content)
    """
    print("  Source 2: Probing our configured tournaments...")

    # Search by category — one search per category level
    category_queries = [
        "Grand Slam tennis results this week",
        "ATP Masters 1000 results this week",
        "ATP 500 tennis results this week winner",
        "ATP 250 tennis results this week final winner",
    ]

    all_content = ""
    for query in category_queries:
        print(f"    Searching: '{query}'")
        try:
            results = search_tool.invoke(query)
            for r in results:
                content = r.get("content", "")
                url = r.get("url", "")
                if content:
                    all_content += f"\nSource: {url}\n{content}\n\n"
        except Exception as e:
            print(f"    ⚠ Failed: {e}")

    # Also search for any specific tournaments that are likely active
    # based on the current month (lightweight — just 2-3 extra searches)
    current_month = datetime.now().month
    month_specific = []
    
    # Pick a few tournaments likely active around this time
    # This is a rough heuristic, not a calendar
    month_tournaments = {
        1: ["Australian Open"],
        2: ["Rotterdam Open", "Dubai Tennis"],
        3: ["Indian Wells", "Miami Open"],
        4: ["Monte Carlo", "Barcelona Open", "BMW Open Munich", "Madrid Open"],
        5: ["Madrid Open", "Italian Open Rome", "Roland Garros", "Lyon Open", "Geneva Open"],
        6: ["Roland Garros", "Queen's Club", "Halle Open", "Wimbledon", "Eastbourne", "Mallorca"],
        7: ["Wimbledon", "Hamburg Open", "Atlanta Open"],
        8: ["Canadian Open", "Cincinnati Masters", "US Open", "Washington Citi Open"],
        9: ["US Open"],
        10: ["Beijing China Open", "Tokyo Japan Open", "Shanghai Masters"],
        11: ["Vienna Open", "Basel Swiss Indoors", "Paris Masters", "ATP Finals", "WTA Finals"],
        12: [],
    }
    
    for t_name in month_tournaments.get(current_month, []):
        query = f"{t_name} tennis results {search_date}"
        print(f"    Searching: '{query}'")
        try:
            results = search_tool.invoke(query)
            for r in results:
                content = r.get("content", "")
                url = r.get("url", "")
                if content:
                    all_content += f"\nSource: {url}\n{content}\n\n"
        except Exception as e:
            print(f"    ⚠ Failed: {e}")

    return all_content


def discover_via_web(search_date: str) -> str:
    """
    Source 1: Ask the web what tournaments are active and get results.
    Combined discovery + results in one step.
    """
    print("  Source 1: Web discovery...")

    queries = [
        f"tennis tournament results this week {search_date}",
        f"ATP WTA tennis results winners {search_date}",
    ]

    all_content = ""
    for query in queries:
        print(f"    Searching: '{query}'")
        try:
            results = search_tool.invoke(query)
            for r in results:
                content = r.get("content", "")
                url = r.get("url", "")
                if content:
                    all_content += f"\nSource: {url}\n{content}\n\n"
        except Exception as e:
            print(f"    ⚠ Failed: {e}")

    return all_content


def search_general_results(search_date: str, yesterday: str) -> str:
    """Source 3: Broad fallback searches."""
    print("  Source 3: General fallback searches...")

    queries = [
        f"tennis results {search_date} winner defeated",
        f"tennis results {yesterday} winner defeated",
        "tennis final winner this week ATP WTA",
    ]

    all_content = ""
    for query in queries:
        print(f"    Searching: '{query}'")
        try:
            results = search_tool.invoke(query)
            for r in results:
                content = r.get("content", "")
                url = r.get("url", "")
                if content:
                    all_content += f"\nSource: {url}\n{content}\n\n"
        except Exception as e:
            print(f"    ⚠ Failed: {e}")

    return all_content


def extract_matches(search_content: str, search_date: str, yesterday: str) -> list[dict]:
    """Use LLM to extract structured match data from all collected content."""
    if not search_content.strip():
        return []

    extraction_prompt = f"""Extract all completed professional tennis singles matches 
from the search results below. Look for matches completed on {search_date} 
or {yesterday} (last 48 hours).

Search results:
{search_content[:12000]}

Return ONLY a JSON array of match objects. Each match should have:
- "player1": winner's full name
- "player2": loser's full name
- "score": the match score (e.g. "6-3, 6-2"). Use "score not found" if unavailable.
- "tournament": tournament name
- "round": one of "F", "SF", "QF", "R16", "R32", "R64", "R128", "RR"
- "gender": "mens" or "womens"
- "is_upset": true if a lower-ranked/unseeded player beat a seeded or top-20 player
- "match_date": the date the match was played (e.g. "April 19, 2026")

Rules:
- Include matches completed on {search_date} OR {yesterday}
- Include matches from ANY professional tournament (ATP, WTA, any level)
- Do NOT include doubles — singles only
- Do NOT include matches that are scheduled but not yet played
- If the round isn't stated, infer from context
- Extract EVERY completed singles match you can find
- If no completed matches are found, return: []

Return ONLY the JSON array. No markdown, no explanation, no code fences."""

    response = llm.invoke(extraction_prompt)

    try:
        text = response.content.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        matches = json.loads(text)
        if not isinstance(matches, list):
            return []
        return matches
    except (json.JSONDecodeError, IndexError) as e:
        print(f"  ⚠ Could not parse matches: {e}")
        print(f"  Raw response preview: {response.content[:300]}")
        return []


def enrich_and_score(matches: list[dict]) -> list[dict]:
    """Add category, surface, and priority score to each match."""
    enriched = []
    for match in matches:
        tournament_name = match.get("tournament", "")
        cat_info = categorize_tournament(tournament_name)
        match["category"] = cat_info["category"]
        match["surface"] = cat_info["surface"]

        round_code = match.get("round", "R64")
        category = match["category"]
        round_score = ROUND_PRIORITY.get(round_code, 0)
        category_score = CATEGORY_PRIORITY.get(category, 1)
        match["priority_score"] = round_score + category_score

        if match.get("is_upset"):
            match["priority_score"] += 5

        enriched.append(match)
    return enriched


def filter_matches(matches: list[dict]) -> list[dict]:
    """
    Filter by coverage rules and config.
    - Must meet minimum round for its category
    - Must be in our tournament config (not Unknown), unless it's an upset
    - Upsets always pass
    """
    filtered = []
    for match in matches:
        category = match.get("category", "Unknown")
        round_code = match.get("round", "R64")
        min_round = COVERAGE_RULES.get(category, "SF")
        match_priority = ROUND_PRIORITY.get(round_code, 0)
        min_priority = ROUND_PRIORITY.get(min_round, 0)

        # Skip unknown tournaments (not in our config)
        if category == "Unknown" and not match.get("is_upset"):
            continue

        if match_priority >= min_priority:
            filtered.append(match)
        elif match.get("is_upset"):
            filtered.append(match)

    filtered.sort(key=lambda m: m["priority_score"], reverse=True)
    return filtered[:MAX_MATCHES_PER_DAY]


def get_matches_to_analyse(target_date: str = None) -> list[dict]:
    """
    Main entry point.

    Args:
        target_date: Optional date string (e.g. "April 19, 2026").
                     If not provided, uses today.
    """
    if target_date:
        search_date = target_date
        try:
            dt = datetime.strptime(target_date, "%B %d, %Y")
            yesterday = (dt - timedelta(days=1)).strftime("%B %d, %Y")
        except ValueError:
            yesterday = target_date
    else:
        search_date = datetime.now().strftime("%B %d, %Y")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%B %d, %Y")

    print("=" * 50)
    print(f"  SCHEDULER — searching: {search_date}")
    print(f"             also checking: {yesterday}")
    print("=" * 50)

    # Collect content from all three sources
    all_content = ""

    print("\nStep 1: Collecting data from multiple sources...")

    # Source 1: Web discovery
    web_content = discover_via_web(search_date)
    all_content += web_content

    # Source 2: Config-based probing
    config_content = probe_config_tournaments(search_date)
    all_content += config_content

    # Source 3: General fallback
    general_content = search_general_results(search_date, yesterday)
    all_content += general_content

    if not all_content.strip():
        print("\nNo search content found. Try again later.")
        return []

    # Extract matches from combined content
    print(f"\nStep 2: Extracting match data...")
    raw_matches = extract_matches(all_content, search_date, yesterday)
    print(f"  Found {len(raw_matches)} completed matches.")

    if not raw_matches:
        print("  No completed matches found.")
        return []

    # Deduplicate (same players + same tournament = same match)
    seen = set()
    unique_matches = []
    for m in raw_matches:
        key = (
            m.get("player1", "").lower(),
            m.get("player2", "").lower(),
            m.get("tournament", "").lower(),
        )
        if key not in seen:
            seen.add(key)
            unique_matches.append(m)
    
    if len(unique_matches) < len(raw_matches):
        print(f"  Deduplicated: {len(raw_matches)} → {len(unique_matches)} unique matches.")
    raw_matches = unique_matches

    # Categorize and score
    print("\nStep 3: Categorizing and scoring...")
    scored = enrich_and_score(raw_matches)

    print("\n  All matches found:")
    for m in scored:
        date_tag = f" ({m.get('match_date', '?')})" if m.get('match_date') else ""
        cat_tag = f"[{m['category']}]" if m['category'] != 'Unknown' else "[Unknown — will be filtered]"
        print(f"    • {m['player1']} def. {m['player2']} {m.get('score', '')}{date_tag}")
        print(f"      {m.get('tournament', '?')} {m.get('round', '?')} "
              f"{cat_tag} (priority: {m['priority_score']})")

    # Filter
    print("\nStep 4: Applying coverage rules...")
    selected = filter_matches(scored)

    print(f"\n  Selected {len(selected)} matches for analysis:")
    for m in selected:
        upset_tag = " ⚡UPSET" if m.get("is_upset") else ""
        print(f"    ✓ {m['player1']} def. {m['player2']} {m.get('score', '')}")
        print(f"      {m.get('tournament', '?')} {m.get('round', '?')} "
              f"[{m['category']}]{upset_tag}")

    return selected


# --- CLI ---
if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    if target:
        print(f"Manual date override: {target}")
    matches = get_matches_to_analyse(target)
    print(f"\n{'=' * 50}")
    print(f"{len(matches)} matches ready for analysis pipeline.")
    if matches:
        print("\nFull match data:")
        for m in matches:
            print(json.dumps(m, indent=2))