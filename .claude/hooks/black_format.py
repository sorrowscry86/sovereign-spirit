"""
Black Auto-Format Hook — PostToolUse
======================================
Runs Black formatter silently after any Python file is written or edited.
Never blocks — formatting failures are logged but don't interrupt workflow.
"""

import sys
import json
import subprocess

try:
    payload = json.load(sys.stdin)
except Exception:
    sys.exit(0)

tool_input = payload.get("tool_input", {})
file_path = tool_input.get("file_path", "") or tool_input.get("path", "")

if not file_path.endswith(".py"):
    sys.exit(0)

try:
    result = subprocess.run(
        ["python", "-m", "black", "--quiet", file_path],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        # Log but don't block — Black may fail on syntax errors we're mid-fixing
        print(f"Black: could not format {file_path} ({result.stderr.strip()})")
except Exception as e:
    print(f"Black hook error: {e}")

sys.exit(0)
