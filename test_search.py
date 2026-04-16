# test_search.py
# Purpose: confirm that Tavily web search works

import os
from dotenv import load_dotenv

load_dotenv()

from langchain_community.tools.tavily_search import TavilySearchResults

# Create the search tool
# - max_results: how many search results to return (5 is a good balance)
search_tool = TavilySearchResults(max_results=5)

# Test it with a tennis query
print("Searching for: Sinner vs Djokovic Australian Open 2025 stats\n")

results = search_tool.invoke("Sinner vs Djokovic Australian Open 2025 stats")

# Print each result
for i, result in enumerate(results):
    print(f"--- Result {i+1} ---")
    print(f"URL: {result['url']}")
    print(f"Content: {result['content'][:300]}...")  # First 300 characters
    print()