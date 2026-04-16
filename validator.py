# validator.py
# Purpose: Check if the user's input is actually about a tennis match

import os
import json
from datetime import datetime
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic

load_dotenv()

llm = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    temperature=0,
)


def validate_input(user_input: str) -> dict:
    """
    Checks whether the user's message is a valid tennis match query.

    Returns:
    {
        "is_valid": True/False,
        "reason": "explanation if invalid",
        "suggestion": "helpful suggestion if invalid"
    }
    """

    now = datetime.now()
    current_year = now.year
    current_date_str = now.strftime("%B %d, %Y")

    validation_prompt = f"""Determine if this user message is asking about a tennis 
match, player performance, tennis statistics, or a player comparison that could 
be analysed.

TODAY'S DATE: {current_date_str}
CURRENT YEAR: {current_year}

User message: "{user_input}"

Return ONLY valid JSON with these fields:
- "is_valid": true if it's a tennis-related query that could be analysed, false otherwise
- "reason": if invalid, briefly explain why (e.g. "not about tennis", "too vague", "greeting")
- "suggestion": if invalid, suggest what they could ask instead

## IMPORTANT DATE RULES
- ANY year up to and including {current_year} is in the past or present — VALID.
- "This year", "last year", "recent", and tournament references without a year 
  are all VALID.
- Only flag as "future event" if the user explicitly asks about a year AFTER 
  {current_year}, OR a tournament that clearly hasn't happened yet 
  (e.g. "Wimbledon 2030").
- Do NOT reject queries just because they mention {current_year} — that's the 
  current year, not the future.

## EXAMPLES OF VALID QUERIES
- "Analyse the Sinner vs Djokovic AO 2025 final"
- "Why did Nadal lose at Roland Garros 2024?"
- "How did Swiatek play at the US Open?"
- "Djokovic Alcaraz Wimbledon 2024"
- "what happened with Novak at the AO this year"
- "Compare Sinner and Alcaraz on clay"
- "How do Swiatek and Sabalenka compare on hard courts?"
- "last roland garros final"

## EXAMPLES OF INVALID QUERIES
- "Hello" → reason: "greeting, not a tennis query"
- "Hi there" → reason: "greeting, not a tennis query"
- "Tell me about Djokovic" → reason: "too broad — need a specific match"
- "What's the weather?" → reason: "not about tennis"
- "Who is the best tennis player ever?" → reason: "opinion question, not match analysis"
- "How do I improve my backhand?" → reason: "coaching question, not match analysis"
- "thanks" → reason: "conversational reply, not a query"
- "Wimbledon 2030 final" → reason: "future event — hasn't happened yet"

Return ONLY the JSON. No markdown, no explanation, no code fences."""

    response = llm.invoke(validation_prompt)

    try:
        text = response.content.strip()
        # Strip code fences defensively
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        return json.loads(text)
    except (json.JSONDecodeError, IndexError):
        # Default to valid if we can't parse — better to try than to block
        return {"is_valid": True, "reason": None, "suggestion": None}