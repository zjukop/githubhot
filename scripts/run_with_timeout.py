#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: run_with_timeout.py SECONDS COMMAND [ARG ...]", file=sys.stderr)
        return 2
    timeout = float(argv[0])
    if timeout <= 0:
        print("timeout must be positive", file=sys.stderr)
        return 2
    try:
        return subprocess.run(argv[1:], check=False, timeout=timeout).returncode
    except subprocess.TimeoutExpired:
        print(f"command timed out after {timeout:g}s: {argv[1]}", file=sys.stderr)
        return 124


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
