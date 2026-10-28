"""Print the canonical replay trace of one seed from a fresh process.

Invoked by ``test_determinism`` with different ``PYTHONHASHSEED`` values.
"""

import sys

from sch_fixtures import canonical_replay


def main() -> None:
    sys.stdout.write(canonical_replay(int(sys.argv[1])))


if __name__ == "__main__":
    main()
