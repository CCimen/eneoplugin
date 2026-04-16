#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""Guard against clobbering an existing artifact.

Used by /eneo-milestone and /eneo-spec to ensure the new PRD/SPEC/plan does not
already exist before the slash command creates it (prevents silent overwrite
if the slug collides with an in-flight milestone).

Exit 2 if the path exists and --must-not-exist is set.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", required=True, type=Path, help="Target path")
    parser.add_argument(
        "--must-not-exist",
        action="store_true",
        help="Fail with exit 2 if the path exists",
    )
    parser.add_argument(
        "--must-be-empty",
        action="store_true",
        help="If path is a directory, fail if it is not empty",
    )
    args = parser.parse_args()

    path: Path = args.path
    if args.must_not_exist and path.exists():
        print(
            f"[validate_new_file] {path} already exists — choose a different slug or "
            f"remove the existing artifact first.",
            file=sys.stderr,
        )
        return 2

    if args.must_be_empty and path.is_dir() and any(path.iterdir()):
        print(
            f"[validate_new_file] directory {path} is not empty.",
            file=sys.stderr,
        )
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
