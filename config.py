# config.py
# Purpose: Tournament categories, match priority rules, platform settings
#
# NOTE: This file does NOT try to track which tournaments are active.
# The scheduler searches the web for today's results and then uses
# this config to categorize and prioritize what it finds.

# --- Tournament Categories ---
# Used to assign priority to matches AFTER the scheduler finds them.
# The key is a lowercase substring that will be matched against
# tournament names found in search results.

TOURNAMENT_CATEGORIES = {
    # Grand Slams
    "australian open": {"category": "Grand Slam", "surface": "Hard"},
    "roland garros": {"category": "Grand Slam", "surface": "Clay"},
    "french open": {"category": "Grand Slam", "surface": "Clay"},
    "wimbledon": {"category": "Grand Slam", "surface": "Grass"},
    "us open": {"category": "Grand Slam", "surface": "Hard"},

    # Masters 1000
    "indian wells": {"category": "Masters 1000", "surface": "Hard"},
    "miami open": {"category": "Masters 1000", "surface": "Hard"},
    "monte carlo": {"category": "Masters 1000", "surface": "Clay"},
    "monte-carlo": {"category": "Masters 1000", "surface": "Clay"},
    "madrid open": {"category": "Masters 1000", "surface": "Clay"},
    "mutua madrid": {"category": "Masters 1000", "surface": "Clay"},
    "italian open": {"category": "Masters 1000", "surface": "Clay"},
    "rome masters": {"category": "Masters 1000", "surface": "Clay"},
    "internazionali": {"category": "Masters 1000", "surface": "Clay"},
    "canadian open": {"category": "Masters 1000", "surface": "Hard"},
    "rogers cup": {"category": "Masters 1000", "surface": "Hard"},
    "national bank open": {"category": "Masters 1000", "surface": "Hard"},
    "cincinnati": {"category": "Masters 1000", "surface": "Hard"},
    "western & southern": {"category": "Masters 1000", "surface": "Hard"},
    "shanghai masters": {"category": "Masters 1000", "surface": "Hard"},
    "rolex shanghai": {"category": "Masters 1000", "surface": "Hard"},
    "paris masters": {"category": "Masters 1000", "surface": "Hard (Indoor)"},
    "rolex paris": {"category": "Masters 1000", "surface": "Hard (Indoor)"},

    # ATP 500
    "bmw open": {"category": "ATP 500", "surface": "Clay"},
    "munich": {"category": "ATP 500", "surface": "Clay"},
    "barcelona open": {"category": "ATP 500", "surface": "Clay"},
    "barcelona": {"category": "ATP 500", "surface": "Clay"},
    "conde de godo": {"category": "ATP 500", "surface": "Clay"},
    "dubai": {"category": "ATP 500", "surface": "Hard"},
    "acapulco": {"category": "ATP 500", "surface": "Hard"},
    "mexican open": {"category": "ATP 500", "surface": "Hard"},
    "queen's": {"category": "ATP 500", "surface": "Grass"},
    "queen's club": {"category": "ATP 500", "surface": "Grass"},
    "halle open": {"category": "ATP 500", "surface": "Grass"},
    "terra wortmann": {"category": "ATP 500", "surface": "Grass"},
    "hamburg open": {"category": "ATP 500", "surface": "Clay"},
    "washington": {"category": "ATP 500", "surface": "Hard"},
    "citi open": {"category": "ATP 500", "surface": "Hard"},
    "beijing": {"category": "ATP 500", "surface": "Hard"},
    "china open": {"category": "ATP 500", "surface": "Hard"},
    "tokyo": {"category": "ATP 500", "surface": "Hard"},
    "japan open": {"category": "ATP 500", "surface": "Hard"},
    "vienna open": {"category": "ATP 500", "surface": "Hard (Indoor)"},
    "erste bank": {"category": "ATP 500", "surface": "Hard (Indoor)"},
    "basel": {"category": "ATP 500", "surface": "Hard (Indoor)"},
    "swiss indoors": {"category": "ATP 500", "surface": "Hard (Indoor)"},
    "rotterdam": {"category": "ATP 500", "surface": "Hard (Indoor)"},
    "abn amro": {"category": "ATP 500", "surface": "Hard (Indoor)"},
    "rio open": {"category": "ATP 500", "surface": "Clay"},

    # ATP 250 (selected — the ones most likely to appear in results)
    "lyon open": {"category": "ATP 250", "surface": "Clay"},
    "geneva open": {"category": "ATP 250", "surface": "Clay"},
    "stuttgart": {"category": "ATP 250", "surface": "Grass"},
    "boss open": {"category": "ATP 250", "surface": "Grass"},
    "eastbourne": {"category": "ATP 250", "surface": "Grass"},
    "mallorca": {"category": "ATP 250", "surface": "Grass"},
    "atlanta open": {"category": "ATP 250", "surface": "Hard"},
    "winston-salem": {"category": "ATP 250", "surface": "Hard"},
    "stockholm": {"category": "ATP 250", "surface": "Hard (Indoor)"},
    "antwerp": {"category": "ATP 250", "surface": "Hard (Indoor)"},
    "european open": {"category": "ATP 250", "surface": "Hard (Indoor)"},
    "marseille": {"category": "ATP 250", "surface": "Hard (Indoor)"},
    "montpellier": {"category": "ATP 250", "surface": "Hard (Indoor)"},
    "sofia open": {"category": "ATP 250", "surface": "Hard (Indoor)"},
    "adelaide": {"category": "ATP 250", "surface": "Hard"},
    "brisbane": {"category": "ATP 250", "surface": "Hard"},
    "auckland": {"category": "ATP 250", "surface": "Hard"},

    # ATP/WTA Finals
    "atp finals": {"category": "Finals", "surface": "Hard (Indoor)"},
    "wta finals": {"category": "Finals", "surface": "Hard (Indoor)"},
    "nitto atp finals": {"category": "Finals", "surface": "Hard (Indoor)"},
}


# --- Category Priority ---
# Higher number = more important tournament category
CATEGORY_PRIORITY = {
    "Grand Slam": 10,
    "Finals": 9,
    "Masters 1000": 7,
    "ATP 500": 4,
    "ATP 250": 2,
    "WTA 500": 4,
    "WTA 250": 2,
    "Unknown": 1,
}


# --- Round Priority ---
# Higher number = more important round
ROUND_PRIORITY = {
    "F": 10,
    "SF": 8,
    "QF": 6,
    "R16": 4,
    "R32": 2,
    "R64": 1,
    "R128": 0,
    "RR": 7,
}


# --- Coverage Rules ---
# Minimum round to cover per category
# Matches below this round are skipped (unless they're upsets)
COVERAGE_RULES = {
    "Grand Slam": "R16",
    "Finals": "RR",
    "Masters 1000": "R16",
    "ATP 500": "QF",
    "ATP 250": "F",
    "WTA 500": "QF",
    "WTA 250": "F",
    "Unknown": "SF",
}


# --- Platform Configuration ---
PLATFORMS = {
    "telegram": {
        "language": "Ukrainian",
        "max_length": 4000,
        "format": "html",
        "auto_publish": True,
    },
    "substack": {
        "language": "English",
        "max_length": None,
        "format": "markdown",
        "auto_publish": False,
    },
    "whatsapp": {
        "language": "English",
        "max_length": 3000,
        "format": "plain",
        "auto_publish": False,
    },
}


# --- Budget Limits ---
MAX_MATCHES_PER_DAY = 8
MAX_DAILY_BUDGET_USD = 3.00