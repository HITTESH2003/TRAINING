"""Hand-curated query -> correct-chunk pairs, used to measure retrieval
accuracy at each embedding dimension.

Deliberately small (10 queries) and deliberately manual: every expected_chunk_id
below was picked by a human reading the actual chunk text in
../../3. CHUNKING/output/*/hierarchical.json, so anyone can verify by eye that
the "correct" answer really is correct -- no synthetic or LLM-generated ground
truth to second-guess. Each query targets a specific, unambiguous fact that
appears in exactly one chunk.
"""

from __future__ import annotations

QUERIES = [
    {
        "query": "What percentage did illegal border crossings drop by?",
        "expected_chunk_id": "federal_register_proclamation__hierarchical__0005",
    },
    {
        "query": "Which countries are NASA's international partners on the space station?",
        "expected_chunk_id": "nasa_iss_factsheet__hierarchical__0002",
    },
    {
        "query": "What was Region B's output in Q3?",
        "expected_chunk_id": "synthetic_sample__hierarchical__0001",
    },
    {
        "query": "How is efficiency calculated in the regional operations report?",
        "expected_chunk_id": "synthetic_sample__hierarchical__0002",
    },
    {
        "query": "What is the mailing address for NASA's Johnson Space Center?",
        "expected_chunk_id": "nasa_iss_factsheet__hierarchical__0000",
    },
    {
        "query": "How many scientific experiments have been conducted aboard the Space Station?",
        "expected_chunk_id": "nasa_iss_factsheet__hierarchical__0001",
    },
    {
        "query": "What tax changes were included in the One Big Beautiful Bill?",
        "expected_chunk_id": "federal_register_proclamation__hierarchical__0006",
    },
    {
        "query": "Who signed the regional operations report as Regional Director?",
        "expected_chunk_id": "synthetic_sample__hierarchical__0002",
    },
    {
        "query": "What date is being proclaimed as National Day of Patriotic Devotion?",
        "expected_chunk_id": "federal_register_proclamation__hierarchical__0010",
    },
    {
        "query": "Which region showed the largest quarter-over-quarter improvement?",
        "expected_chunk_id": "synthetic_sample__hierarchical__0000",
    },
]
