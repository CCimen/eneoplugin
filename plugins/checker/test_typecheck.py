#!/usr/bin/env python3
"""
Test script for the typecheck MCP server.
Run this in the devcontainer to verify the typecheck function works.

Usage:
    cd /workspace  # or wherever eneo repo is
    uv run --with "fastmcp<3" python /path/to/test_typecheck.py
"""
import os
import sys
from pathlib import Path

# Add mcp directory to path
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir / "mcp"))

# Set project dir if not set
if "CLAUDE_PROJECT_DIR" not in os.environ:
    # Try to find workspace
    if Path("/workspace/backend/src/intric").exists():
        os.environ["CLAUDE_PROJECT_DIR"] = "/workspace"
    else:
        os.environ["CLAUDE_PROJECT_DIR"] = os.getcwd()

print("=" * 60)
print("TYPECHECK MCP SERVER TEST")
print("=" * 60)

# Import the server module
from typecheck_server import find_repo_root, is_new_file, typecheck

# Test 1: Find repo root
print("\n[TEST 1] find_repo_root()")
project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
repo_root = find_repo_root(project_dir)
print(f"  Project dir: {project_dir}")
print(f"  Repo root:   {repo_root}")
if repo_root and Path(repo_root, "backend/src/intric").exists():
    print("  ✅ PASS - Found valid repo root")
else:
    print("  ❌ FAIL - Could not find repo root with backend/src/intric")
    sys.exit(1)

# Test 2: Check all changed files (empty list)
print("\n[TEST 2] typecheck(files=[]) - Check all changed files")
result = typecheck.fn(files=[])
print(f"  Success: {result.success}")
print(f"  Files checked: {result.files_checked}")
print(f"  Summary: {result.summary}")
if result.error_count == 0:
    print("  ✅ PASS - No errors (or no files to check)")
else:
    print(f"  ⚠️  Found {result.error_count} error(s)")
    for err in result.errors[:5]:
        print(f"      {err.file}:{err.line} [{err.rule}] {err.message}")

# Test 3: Create a file with type error
print("\n[TEST 3] typecheck() with intentional type error")
test_file = Path(repo_root) / "backend/src/intric/_test_typecheck_temp.py"
test_content = '''# Temporary test file - DELETE ME
def get_name() -> str:
    return 42  # Type error: returning int instead of str

def main() -> None:
    name: str = get_name()
    print(name)
'''

try:
    test_file.write_text(test_content)
    print(f"  Created test file: {test_file}")

    # Run typecheck on the test file
    result = typecheck.fn(files=["src/intric/_test_typecheck_temp.py"])
    print(f"  Success: {result.success}")
    print(f"  Error count: {result.error_count}")
    print(f"  Summary: {result.summary}")

    if result.error_count > 0:
        print("  ✅ PASS - Type error detected!")
        for err in result.errors:
            print(f"      {err.file}:{err.line}:{err.column} [{err.rule}] {err.message}")
    else:
        print("  ⚠️  WARNING - No type error detected")
        print("      This might be expected if pyright isn't installed or can't run")

finally:
    # Clean up
    if test_file.exists():
        test_file.unlink()
        print(f"  Cleaned up test file")

# Test 4: Test is_new_file detection
print("\n[TEST 4] is_new_file() detection")
if repo_root:
    # Test with an existing file
    existing_file = "src/intric/__init__.py"
    is_new = is_new_file(existing_file, repo_root)
    print(f"  {existing_file}: is_new={is_new}")
    if not is_new:
        print("  ✅ PASS - Correctly detected existing file")
    else:
        print("  ❌ FAIL - Should not be detected as new")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
print("""
Next steps:
1. If all tests pass, the MCP server is working correctly
2. Push the plugin to GitHub
3. Install in your project: /plugin install checker@eneoplugin
4. Use the typecheck tool in Claude Code conversations
""")
