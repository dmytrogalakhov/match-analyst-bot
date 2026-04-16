# test_llm.py
# Purpose: confirm that our LLM connection works

import os
from dotenv import load_dotenv

# This reads your .env file and makes the keys available
load_dotenv()

# Verify the keys loaded correctly
anthropic_key = os.getenv("ANTHROPIC_API_KEY")
tavily_key = os.getenv("TAVILY_API_KEY")

if not anthropic_key:
    print("ERROR: ANTHROPIC_API_KEY not found. Check your .env file.")
    exit()
if not tavily_key:
    print("ERROR: TAVILY_API_KEY not found. Check your .env file.")
    exit()

print("API keys loaded successfully!")

# Now let's talk to Claude
from langchain_anthropic import ChatAnthropic

# Create an LLM instance
# - model: which Claude model to use (claude-sonnet-4-20250514 is fast and cheap, good for dev)
# - temperature: 0 = focused/deterministic, 1 = creative/random. 
#   For analysis we want 0.3 (mostly focused, slightly flexible)
llm = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    temperature=0.3,
)

# Send a simple message and print the response
response = llm.invoke("Who won the 2024 Australian Open men's singles final?")

print("\n--- LLM Response ---")
print(response.content)
print("--- End ---")