"""Print one replay result from a fresh process (invoked by ``test_replay``).

Usage: ``replay_api_worker.py <seed> <variant>``. The variants build the same replay
with a different mapping construction order or a small event budget (``partial``),
or inject a fault for the failure paths.
"""

import sys
import time

from manufacturing_simulator import replay
from replay_fixtures import (
    fresh_handlers,
    hash_dependent_handlers,
    make_spec,
    reversed_handlers,
)


def main() -> None:
    seed, variant = int(sys.argv[1]), sys.argv[2]
    if variant == "crash":
        sys.exit(3)
    if variant == "hang":
        time.sleep(600)
    shuffled = variant == "shuffled"
    state = (
        {"note": "initial", "scale": 1.5}
        if shuffled
        else {"scale": 1.5, "note": "initial"}
    )
    handlers = {
        "hashdep": hash_dependent_handlers,
        "shuffled": reversed_handlers,
    }.get(variant, fresh_handlers)
    cap = {"partial": 25}.get(variant, 10_000)
    text = replay(
        make_spec(seed, initial_state=state, max_events=cap), handlers
    ).to_json()
    if variant == "truncated":
        text = text[: len(text) // 2]
    sys.stdout.write(text)


if __name__ == "__main__":
    main()
