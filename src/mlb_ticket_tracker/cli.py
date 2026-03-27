"""Command-line entry points."""

from __future__ import annotations

import sys


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "healthcheck":
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
