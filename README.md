# 🎾 Tennis Match Analyst Bot

An AI-powered Telegram bot that analyses professional tennis matches, explaining
not just what happened, but *why* — turning points, tactical patterns, and the
stats that actually mattered.

Built as a hands-on exploration of agentic AI: the bot autonomously decides when
to search the web, how to verify the data it finds, and how to structure its
analysis. Multiple specialised agents handle different query types (match analysis
vs player comparison).

## Features

- **Natural language queries**: "Why did Sinner beat Djokovic at the AO?" works 
  just as well as structured input
- **Tool-using agent**: Autonomously searches the web (Tavily) for match data
- **Year-aware parsing**: Understands "last Wimbledon" based on the current date
- **Input validation**: Rejects non-tennis queries with helpful suggestions
- **Comparison mode**: Compare two players, optionally filtered by surface
- **Telegram interface**: Chat with the bot from your phone
- **Honest failure**: If it can't find reliable data, it says so — rather than 
  confabulating

## Tech Stack

- **Python 3.11+**
- **LangChain v1.x** — agent orchestration
- **Anthropic Claude (Sonnet 4)** — the reasoning model
- **Tavily** — web search API
- **python-telegram-bot** — Telegram interface
- **[Hosting platform]** — always-on deployment

## Architecture

The system is intentionally modular:

- `validator.py` — fast LLM call that rejects non-tennis queries
- `parser.py` — extracts structured match info (players, year, tournament, surface) 
  from natural language, with date-aware inference
- `analyst.py` — the core agent. Two specialised agents (match analysis, 
  player comparison) share the same tools but have different system prompts
- `bot.py` — Telegram interface; formats output, handles message length limits, 
  runs the agent in a thread pool to stay responsive
- `agent.py` — original CLI-only version, kept for development

The agent uses the ReAct pattern via LangChain's `create_agent`: the LLM decides 
when to search, evaluates the results, and decides whether to search again before 
producing the final analysis.

## What I Learned

- **Prompt engineering matters more than model choice**: The difference between 
  a generic "player X served well" output and a specific "player X won 72% of 
  second-serve points in the third set" output is entirely in the system prompt.
- **Honest failure beats confabulation**: The agent initially returned 2024 match 
  data for 2025 queries because Tavily's coverage was weak. Adding a strict 
  year-verification rule taught it to say "I couldn't find that" instead.
- **Separation of concerns**: Splitting validation, parsing, and analysis into 
  separate components made each one easier to iterate on and debug.
- **Async matters for bots**: Running the synchronous agent in a thread pool 
  (`asyncio.to_thread`) keeps the bot responsive to other users during a slow 
  analysis.

## Running Locally


### Setup

```bash
git clone https://github.com/dmytrogalakhov/match-analyst-bot.git
cd match-analyst-bot
python3 -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### Run

```bash
# CLI mode for testing
python3 analyst.py

# Telegram bot
python3 bot.py
```

## Demo

Try the live bot: (https://t.me/tennis_analyst_rafik_bot)

## Example Output

**Query**: "Sinner vs Djokovic Australian Open 2025 final"

> ## Jannik Sinner def. Novak Djokovic 6-4, 7-6(4), 6-3
> ### Australian Open 2025, Final, Hard
> 
> **THE STORY**: Sinner's coronation was quieter than expected — no five-set 
> drama, no momentum shifts — just the 23-year-old Italian methodically 
> dismantling the greatest player of his generation...
> 
> [continues]

## Roadmap

- [ ] Drill recommender agent (analyse your own game, get training suggestions)
- [ ] Tournament scout mode (pre-tournament breakdowns)
- [ ] Multi-agent orchestration for weekly training plans
- [ ] Integration with live match data APIs

## License

MIT

---

Built with Claude, LangChain, and a lot of tennis.
