"""Run the toy scenario in a fresh process and print its canonical trace.

Invoked by ``test_determinism`` with different ``PYTHONHASHSEED`` values.
"""

import sys

from sim_fixtures import dumps, run_toy


def main() -> None:
    seed = int(sys.argv[1])
    sys.stdout.write(dumps(run_toy(seed)))


if __name__ == "__main__":
    main()
