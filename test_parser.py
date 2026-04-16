# test_parser.py
from parser import parse_match_query

test_queries = [
    "Analyse the Sinner vs Djokovic Australian Open 2025 final",
    "Why did Novak lose at the AO this year?",
    "Swiatek Sabalenka French Open 2024",
    "What happened in the Alcaraz Sinner semifinal at Roland Garros last year?",
    "How did Medvedev do at the US Open 2024?",
]

for query in test_queries:
    print(f"Input:  {query}")
    result = parse_match_query(query)
    print(f"Parsed: {result}")
    print()