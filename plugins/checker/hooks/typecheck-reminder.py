#!/usr/bin/env python3
"""
PostToolUse hook: Remind Claude to run typecheck after editing Python files.

This creates the "edit → check → fix → continue" workflow that catches
type errors early instead of waiting for the Stop hook.
"""
import json
import sys


def main():
    input_data = json.load(sys.stdin)

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    # Only trigger on Edit or Write tools
    if tool_name not in ("Edit", "Write"):
        sys.exit(0)

    # Get the file path
    file_path = tool_input.get("file_path", "")

    # Only trigger for Python files in the intric scope
    if not file_path.endswith(".py"):
        sys.exit(0)

    if "src/intric" not in file_path and "backend/src/intric" not in file_path:
        sys.exit(0)

    # Extract just the filename for the message
    filename = file_path.split("/")[-1]

    # Return additional context to remind Claude to typecheck
    result = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": (
                f"[Type Check Reminder] You edited {filename}. "
                f"Run typecheck(files=[\"{file_path.split('backend/')[-1] if 'backend/' in file_path else file_path}\"]) "
                "to verify no type errors before continuing. Fix any errors found."
            ),
        }
    }
    print(json.dumps(result))
    sys.exit(0)


if __name__ == "__main__":
    main()
