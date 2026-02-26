"""
VoidCat RDC: Sovereign Spirit - VoidKey Client
==============================================
Client for interacting with the VoidKey Bifrost Relay.
Allows Dockerized containers to fetch host-encrypted secrets.
"""

import os
import logging
import requests
from typing import Optional

logger = logging.getLogger("sovereign.core.voidkey")

class VoidKeyClient:
    """Client to fetch keys from the host-side VoidKey Relay."""
    
    def __init__(self, host: str = "host.docker.internal", port: int = 8080):
        # host.docker.internal is the standard DNS for host access on Desktop
        # For non-docker environments, we use 127.0.0.1
        self.host = os.getenv("VOIDKEY_RELAY_HOST", host)
        self.port = os.getenv("VOIDKEY_RELAY_PORT", port)
        self.base_url = f"http://{self.host}:{self.port}"
        self.token = os.getenv("BIFROST_HANDSHAKE_TOKEN", "VOIDC@T_BIFROST_2026")

    def get_key(self, name: str) -> Optional[str]:
        """Fetch a key from the relay."""
        url = f"{self.base_url}/vk/{name}"
        headers = {"X-Bifrost-Token": self.token}
        
        try:
            logger.debug(f"Requesting key '{name}' from VoidKey Relay...")
            response = requests.get(url, headers=headers, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                return data.get("value")
            elif response.status_code == 404:
                logger.warning(f"Key '{name}' not found in VoidKey vault.")
            else:
                logger.error(f"VoidKey Relay error ({response.status_code}): {response.text}")
                
        except Exception as e:
            logger.error(f"Failed to connect to VoidKey Relay: {e}")
            
        return None

# Singleton
_client = VoidKeyClient()

def get_vk_key(name: str) -> Optional[str]:
    """Helper to fetch a key from the global VoidKey client."""
    return _client.get_key(name)
