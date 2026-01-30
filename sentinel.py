"""
Sovereign Spirit: The Sentinel (Static Analysis)
================================================
Author: Echo (E-01) / Roland
Date: 2026-01-30

Authority: Layer 0 (Immutable)
Purpose: Prevents recurrence of known structural errors.
Checks:
1. THE LAW OF TIME: Forbids offset-naive datetime.utcnow()
2. THE LAW OF IDENTITY: Enforces explicit healthchecks in docker-compose
"""

import os
import re
import sys
import yaml
from typing import List, Tuple

RED = "\033[91m"
GREEN = "\033[92m"
CYAN = "\033[96m"
RESET = "\033[0m"

class Sentinel:
    def __init__(self, root_dir: str = "."):
        self.root_dir = root_dir
        self.errors: List[str] = []

    def log(self, msg: str, status: str = "INFO"):
        color = GREEN if status == "PASS" else RED if status == "FAIL" else CYAN
        print(f"[{color}{status}{RESET}] {msg}")

    def check_time_law(self):
        """Scanning for forbidden offset-naive datetime usage."""
        forbidden_patterns = [
            (r"datetime\.utcnow\(\)", "Use datetime.now(timezone.utc) instead of datetime.utcnow()"),
            (r"datetime\.now\(\)", "datetime.now() is offset-naive. Use datetime.now(timezone.utc)"),
        ]
        
        self.log("Verifying The Law of Time...", "INFO")
        
        for root, _, files in os.walk(os.path.join(self.root_dir, "src")):
            for file in files:
                if file.endswith(".py"):
                    path = os.path.join(root, file)
                    with open(path, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                        for i, line in enumerate(lines):
                            for pattern, directive in forbidden_patterns:
                                if re.search(pattern, line):
                                    # Ignore comments
                                    if line.strip().startswith("#"):
                                        continue
                                    self.errors.append(f"{path}:{i+1} -> {directive}")

    def check_identity_law(self):
        """Verifying docker-compose healthchecks."""
        self.log("Verifying The Law of Identity...", "INFO")
        dc_path = os.path.join(self.root_dir, "docker-compose.yml")
        
        if not os.path.exists(dc_path):
            self.errors.append("docker-compose.yml not found")
            return

        try:
            with open(dc_path, "r", encoding="utf-8") as f:
                # Simple parsing to avoid PyYAML dependency if not installed in env, 
                # but we'll try robust first
                content = f.read()
                
            if "postgres:" in content and "healthcheck:" not in content.split("postgres:")[1].split("services:")[0]:
                # Heuristic check for postgres healthcheck
                # A more robust check would parse YAML, but this catches the specific omission
                pass 
                # Actually, let's just grep for the specific healthcheck line for now to be safe
                if "pg_isready" not in content:
                     self.errors.append("Postgres service missing 'pg_isready' healthcheck")
                     
        except Exception as e:
            self.errors.append(f"Could not parse docker-compose.yml: {e}")

    def run(self) -> bool:
        print(f"{CYAN}=== THE SENTINEL: STATIC ANALYSIS ==={RESET}")
        self.check_time_law()
        self.check_identity_law()

        if self.errors:
            self.log("VIOLATIONS DETECTED:", "FAIL")
            for err in self.errors:
                print(f"{RED}  - {err}{RESET}")
            return False
        else:
            self.log("All Laws Obeyed.", "PASS")
            return True

if __name__ == "__main__":
    sentinel = Sentinel()
    if not sentinel.run():
        sys.exit(1)
