"""
VoidCat RDC: Sovereign Spirit Tools & VES-01 Immutability Charter Guardrails
=============================================================================
Phase 4 (Step 4.5) Implementation: Absolute application-layer immutability guards.

Protects core persona definitions, Layer 0 systemic laws, and environment configuration
from unauthorized mutation by autonomous optimization loops or unverified agents.
"""

import os
import re
import logging
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger("sovereign.tools.immutability")


class ImmutabilityViolationError(Exception):
    """
    Fatal exception raised when an unauthorized tool attempt is made
    to overwrite or mutate a protected immutable resource.
    """
    pass


# Protected target patterns per VES-01 Immutability Charter
PROTECTED_PATTERNS: List[str] = [
    r"persona\.md$",                    # All spirit persona files
    r"\.env$",                          # Main environment file
    r"\.env\..+$",                      # Environment variants (.env.example, .env.local)
    r"\.voidcat[/\\]CONTEXT\.md$",      # Workspace Layer 0 context
    r"Gemini\.md$",                     # Core Layer 0 System Doctrine
    r"VOIDCAT_CODEX\.md$",              # Master Codex
]


def is_protected_path(filepath: str) -> bool:
    """
    Check if a target filepath matches any VES-01 protected immutability pattern.
    """
    normalized_path = os.path.normpath(filepath)
    for pattern in PROTECTED_PATTERNS:
        if re.search(pattern, normalized_path, re.IGNORECASE):
            return True
    return False


def _assert_not_immutable(filepath: str, human_override: bool = False) -> None:
    """
    Validation check injected into tool write/update/patch operations.
    Throws ImmutabilityViolationError if target is protected and human_override is False.
    """
    if not human_override and is_protected_path(filepath):
        error_msg = (
            f"[FATAL: VES-01 Immutability Violation] Attempted unauthorized write "
            f"to protected resource: '{filepath}'. Automated mutations to core persona "
            f"and Layer 0 files are strictly forbidden without explicit human override."
        )
        logger.critical(error_msg)
        raise ImmutabilityViolationError(error_msg)


def write_file(filepath: str, content: str, human_override: bool = False) -> str:
    """
    Safely write content to a file, protected by the VES-01 Immutability Charter.
    """
    _assert_not_immutable(filepath, human_override=human_override)
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return f"Successfully wrote {len(content)} bytes to {filepath}"


def update_file(filepath: str, content: str, human_override: bool = False) -> str:
    """
    Safely update file content, protected by the VES-01 Immutability Charter.
    """
    _assert_not_immutable(filepath, human_override=human_override)
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    path.write_text(content, encoding="utf-8")
    return f"Successfully updated {filepath}"


def patch_file(filepath: str, target_content: str, replacement_content: str, human_override: bool = False) -> str:
    """
    Safely patch file content, protected by the VES-01 Immutability Charter.
    """
    _assert_not_immutable(filepath, human_override=human_override)
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    
    current_text = path.read_text(encoding="utf-8")
    if target_content not in current_text:
        raise ValueError(f"Target content not found in {filepath}")
    
    new_text = current_text.replace(target_content, replacement_content, 1)
    path.write_text(new_text, encoding="utf-8")
    return f"Successfully patched {filepath}"
