"""
VoidCat RDC: The Cloaking Maneuver
==================================
Migrates sensitive keys from .env to VoidKey and purges the plain-text file.
"""

import os
import sys
from pathlib import Path

# Add VoidKey src to path
VOIDKEY_SRC = r"C:\Users\Wykeve\Projects\The Great Library\40_Systems\Ongoing\VoidKey\src"
sys.path.append(VOIDKEY_SRC)

from voidkey import VoidKey

def cloak():
    env_path = Path("c:/Users/Wykeve/Projects/The Great Library/20_Projects/01_Active/Sovereign Spirit/.env")
    if not env_path.exists():
        print("[ERROR] .env file not found.")
        return

    vk = VoidKey()
    sensitive_keys = [
        "OPENROUTER_API_KEY", 
        "OPENAI_API_KEY", 
        "POSTGRES_PASSWORD", 
        "NEO4J_PASSWORD"
    ]
    
    new_lines = []
    migrated_count = 0

    print(f"--- [START] Cloaking Maneuver ---")
    
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                new_lines.append(line)
                continue
            
            if "=" in stripped:
                key, val = stripped.split("=", 1)
                if key in sensitive_keys and val and "your_" not in val and "sk-your" not in val:
                    print(f"Migrating {key} to encrypted vault...")
                    if vk.set_key(key, val):
                        print(f"✅ {key} encrypted.")
                        new_lines.append(f"{key}=${{{key}}}\n") # Use placeholder syntax
                        migrated_count += 1
                    else:
                        print(f"❌ Failed to encrypt {key}.")
                        new_lines.append(line)
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)

    # Ensure Handshake Token is present
    handshake_token = "BIFROST_HANDSHAKE_TOKEN=VOIDC@T_BIFROST_2026\n"
    if not any("BIFROST_HANDSHAKE_TOKEN" in l for l in new_lines):
        new_lines.append("\n# 5. BIFROST RELAY HANDSHAKE\n")
        new_lines.append(handshake_token)

    # Write the cloaked file
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    print(f"--- [FINISH] Cloaking Complete ---")
    print(f"Migrated {migrated_count} keys to VoidKey.")
    print(f"Purged plain-text secrets from .env.")

if __name__ == "__main__":
    cloak()
