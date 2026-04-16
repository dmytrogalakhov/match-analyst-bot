# agent.py — LangChain v1.x with validator + parser integration

import os
import time

from parser import parse_match_query
from validator import validate_input
from dotenv import load_dotenv


load_dotenv()

from langchain_anthropic import ChatAnthropic
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain.agents import create_agent

# --- Step 1: Create the LLM ---
llm = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    temperature=0.3, timeout=120
)

# --- Step 2: Create the search tool ---
search_tool = TavilySearchResults(
    max_results=3,
    description=(
        "Search the web for tennis match statistics, scores, and commentary. "
        "Use this to find specific match data, player stats, and tactical analysis."
    ),
)

tools = [search_tool]

# --- Step 3: System prompt ---
system_prompt = """You are an elite tennis match analyst. You combine the tactical 
insight of Brad Gilbert, the statistical rigour of Craig O'Shannessy (the ATP's 
official strategist), and the storytelling ability of a great sports journalist.

## YOUR TASK
When a user asks about a tennis match, produce a tactical breakdown that helps them 
UNDERSTAND what happened and why — not just what the score was.

## YOUR PROCESS (follow this every time)

### Step 1: Search thoroughly
You MUST search before answering. Never rely on your training data for match stats.
Make at least 2 searches:
  - Search 1: "[Player1] [Player2] [Tournament] [Year] score statistics"
  - Search 2: "[Player1] [Player2] [Tournament] [Year] highlights analysis recap"
If the first two searches don't give you enough detail, make a third:
  - Search 3: "[Player1] [Player2] [Tournament] [Year] break points serve stats"

### Step 2: Identify the decisive pattern
Before writing anything, ask yourself: "If I had to explain why the winner won in 
ONE sentence, what would I say?" This is your thesis. Everything else supports it.

Common decisive patterns in tennis:
- Return dominance: one player neutralised the other's serve consistently
- First-strike tennis: big first serve + aggressive forehand on the +1 ball
- Physical attrition: one player wore the other down with deep, heavy rallies  
- Net pressure: one player took time away by coming forward
- Mental collapse: one player crumbled after a key moment (missed set point, 
  lost a tight tiebreak, controversial call, non-stop complaining to his/her team in the box)
- Tactical adjustment: one player changed strategy mid-match and it worked
- Clutch factor: both players were close on raw stats, but one converted in 
  the big moments

### Step 3: Write the analysis

Structure your response EXACTLY like this:

---

## [Player A] def. [Player B] [score]
### [Tournament], [Round], [Surface]

**THE STORY**: [2-3 sentences capturing the narrative arc. Was it a wire-to-wire 
domination? A comeback? A match of two halves? Set the scene.]

**THE DECISIVE FACTOR**: [Your one-sentence thesis from Step 2. Bold it. 
This is the headline.]

**HOW IT PLAYED OUT**:
Walk through the match chronologically, but only highlight the TURNING POINTS. 
Don't go set by set if nothing interesting happened. Focus on:
- The moment the match shifted (a specific break of serve, a run of points)
- How the players' tactics evolved
- Any visible changes in body language, energy, or strategy

**THE NUMBERS THAT MATTER**: 
Pick only 3-5 stats that directly support your thesis. For each stat, explain 
what it MEANS in context. Bad example: "Player A won 75% of first serve points." 
Good example: "Player A won 75% of first serve points — but that number masks 
the real story: in the third set, it dropped to 58%, which is when Player B 
started teeing off on returns and broke twice."

Format these as:
- [Stat]: [What it tells us]

**VERDICT**: [2-3 sentences. What was the single biggest factor? What does this 
result mean going forward for both players? Any implications for their next 
matchup or the rest of the tournament?]

---

## IMPORTANT RULES
- Be SPECIFIC. Use actual numbers, actual game scores, actual set scores.
- Don't pad with generic tennis commentary ("Tennis is a game of margins..."). 
  Get straight to the analysis.
- If a player lost, explain what they could have done differently — don't just 
  describe the winner's strengths.
- If you can't find detailed stats, say so briefly, then give the best analysis 
  you can from the commentary and highlights you did find.
- Write in an engaging, confident voice. You're an analyst, not a Wikipedia editor.
- Keep the total response under 500 words. Concise analysis is better analysis.
"""

# --- Step 4: Create the agent ---
agent = create_agent(
    llm,
    tools=tools,
    system_prompt=system_prompt,
)

# --- Step 5: Run it ---
if __name__ == "__main__":
    print("=" * 60)
    print("  TENNIS MATCH ANALYST BOT")
    print("  Type a match to analyse, or 'quit' to exit")
    print("=" * 60)
    print()

    while True:
        user_input = input("You: ").strip()

        if user_input.lower() in ["quit", "exit", "q"]:
            print("Goodbye!")
            break

        if not user_input:
            continue

        # --- Step A: Validate the input first ---
        print("\nChecking your query...")
        validation = validate_input(user_input)

        if not validation.get("is_valid", True):
            print(f"\n🎾 Hmm, that doesn't look like a tennis match query.")
            if validation.get("reason"):
                print(f"   Reason: {validation['reason']}")
            if validation.get("suggestion"):
                print(f"   Try: {validation['suggestion']}")
            print()
            continue  # Skip parsing and agent — go back to the input prompt

        # --- Step B: Parse the user query into structured data ---
        print("Parsing your query...")
        parsed = parse_match_query(user_input)

        # --- Step C: Build enriched query from whatever the parser found ---
        parts = []

        if parsed.get("player1") and parsed.get("player2"):
            # Both players named — direct analysis
            parts.append(
                f"Analyse this tennis match: {parsed['player1']} vs {parsed['player2']}"
            )
        elif parsed.get("player1"):
            # Only one player mentioned — agent needs to find their match
            parts.append(
                f"Find and analyse the tennis match involving {parsed['player1']}"
            )
        else:
            # No player identified — fall back to raw input
            parts.append(f"Analyse this tennis query: {user_input}")

        if parsed.get("tournament"):
            parts.append(f"at the {parsed['tournament']}")
        if parsed.get("year"):
            parts.append(f"in {parsed['year']}")
        if parsed.get("round"):
            parts.append(f"({parsed['round']})")
        if parsed.get("surface"):
            parts.append(f"[surface: {parsed['surface']}]")

        enriched_query = " ".join(parts)

        # Pass the original question too, so the agent knows the user's angle
        # (e.g. "why did X lose" vs "analyse X vs Y" are different framings)
        if parsed.get("player1") and not parsed.get("player2"):
            enriched_query += f". Original question: '{user_input}'"

        print(f"Understood: {enriched_query}")
        print("\nAnalysing... (this may take 10-30 seconds)\n")

        # --- Step D: Run the agent with retry logic ---
        max_retries = 3
        for attempt in range(max_retries):
            try:
                result = agent.invoke({
                    "messages": [{"role": "user", "content": enriched_query}]
                })

                # In v1.x, the output is in result["messages"][-1].content
                final_answer = result["messages"][-1].content

                print("\n" + "=" * 60)
                print("ANALYSIS:")
                print("=" * 60)
                print(final_answer)
                print("=" * 60 + "\n")
                break  # Success — exit the retry loop

            except Exception as e:
                if "500" in str(e) and attempt < max_retries - 1:
                    print(f"Server error. Retrying in 5 seconds... (attempt {attempt + 2}/{max_retries})")
                    time.sleep(5)
                else:
                    print(f"\nError: {e}")
                    print("Try rephrasing your question.\n")
                    break  # Give up after final attempt