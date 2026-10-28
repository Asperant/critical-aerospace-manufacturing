"""Hypothesis profile for the dispatch suite.

Examples are bounded and derandomized so a CI run is reproducible: the same
examples run every time, and a failure prints its ``reproduce_failure`` blob.
No example database is written into the repository.
"""

from hypothesis import settings

settings.register_profile(
    "wp-sch-001",
    max_examples=100,
    deadline=None,
    derandomize=True,
    database=None,
    print_blob=True,
)
settings.load_profile("wp-sch-001")
