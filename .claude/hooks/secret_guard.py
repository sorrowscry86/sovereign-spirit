"""
Secret Guard Hook — PreToolUse
===============================
Blocks Write/Edit operations that would embed literal secrets
into sensitive configuration files. Requires env var syntax instead.

Exit 2 = block the tool call and show the message.
Exit 0 = allow.
"""

import sys
import json
import re

SENSITIVE_PATHS = [
    ".env",
    "llm_providers",
    "_providers.yaml",
    "_providers.yml",
]

# Patterns that indicate a literal secret (not an env var reference)
SECRET_PATTERNS = [
    r'sk-[a-zA-Z0-9_\-]{20,}',           # OpenAI / Anthropic keys
    r'sk-ant-[a-zA-Z0-9_\-]{20,}',       # Anthropic keys
    r'(?i)api_key:\s*["\']?[a-zA-Z0-9_\-]{32,}["\']?',  # Generic long key (not ${...})
    r'(?i)api_key:\s*[a-zA-Z0-9_\-]{32,}',
    r'Bearer\s+[a-zA-Z0-9_\-\.]{32,}',   # Bearer tokens
    r'(?i)secret:\s*["\']?[a-zA-Z0-9_\-]{20,}["\']?',
]

# If it looks like an env var reference, it's fine
SAFE_PATTERNS = [
    r'\$\{[A-Z_]+\}',   # ${ENV_VAR}
    r'\$[A-Z_]+',       # $ENV_VAR
    r'^null$',
    r'^""$',
    r"^''$",
]

try:
    payload = json.load(sys.stdin)
except Exception:
    sys.exit(0)

tool_input = payload.get("tool_input", {})
file_path = tool_input.get("file_path", "") or tool_input.get("path", "")
content = tool_input.get("new_string", "") or tool_input.get("content", "")

# Only check sensitive files
if not any(s in file_path for s in SENSITIVE_PATHS):
    sys.exit(0)

# Skip if no content to check
if not content:
    sys.exit(0)

# Check each line for secret patterns
for line in content.splitlines():
    line_stripped = line.strip()

    # Skip comments
    if line_stripped.startswith("#"):
        continue

    # Skip lines that are clearly env var references
    if any(re.search(p, line_stripped) for p in SAFE_PATTERNS):
        continue

    # Flag literal secrets
    for pattern in SECRET_PATTERNS:
        if re.search(pattern, line_stripped):
            print(
                f"BLOCKED: Possible literal secret detected in {file_path}.\n"
                f"  Line: {line_stripped[:80]}...\n"
                f"  Use ${{ENV_VAR_NAME}} syntax instead of hardcoding secrets.\n"
                f"  Store the actual value in .env (never committed)."
            )
            sys.exit(2)

sys.exit(0)
