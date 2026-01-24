"""
VoidCat RDC: Sovereign Spirit Core - Vector Client
==================================================
Wrapper for Weaviate vector database operations.
"""

import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import weaviate

logger = logging.getLogger("sovereign.vector")

# Configuration
WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://localhost:8090")

class VectorClient:
    """Async wrapper for Weaviate operations (v4)."""
    
    def __init__(self, url: str = WEAVIATE_URL):
        self._url = url
        self._client: Optional[weaviate.WeaviateClient] = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize connection to Weaviate and ensure schema exists."""
        try:
            if "localhost" in self._url:
                 # Host machine access (v4 pattern)
                self._client = weaviate.connect_to_local(port=8090, grpc_port=50051)
            elif "weaviate" in self._url:
                 # Docker internal access
                self._client = weaviate.connect_to_custom(
                    http_host="weaviate",
                    http_port=8080,
                    http_secure=False,
                    grpc_host="weaviate",
                    grpc_port=50051,
                    grpc_secure=False
                )
            else:
                 # Generic fallback
                host = self._url.split("://")[-1].split(":")[0]
                port = int(self._url.split(":")[-1]) if ":" in self._url.split("://")[-1] else 8080
                self._client = weaviate.connect_to_custom(
                    http_host=host,
                    http_port=port,
                    http_secure=self._url.startswith("https"),
                    grpc_host=host,
                    grpc_port=50051,
                    grpc_secure=False
                )

            # Test connection
            if self._client.is_live():
                logger.info(f"Connected to Weaviate at {self._url}")
                await self._ensure_schema()
                self._initialized = True
            else:
                logger.error("Weaviate client created but not live")
                
        except Exception as e:
            logger.error(f"Failed to initialize Weaviate: {e}")
            self._client = None

    async def _ensure_schema(self) -> None:
        """Ensure the EpisodicMemory collection exists with correct properties."""
        if not self._client:
            return

        from weaviate.classes.config import Property, DataType, Configure

        # Create collection if it doesn't exist
        if not self._client.collections.exists("EpisodicMemory"):
            logger.info("Creating EpisodicMemory collection...")
            self._client.collections.create(
                name="EpisodicMemory",
                description="Raw subjective and factual memories of agents.",
                properties=[
                    Property(name="author_id", data_type=DataType.TEXT),
                    Property(name="content", data_type=DataType.TEXT),
                    Property(name="subjective_voice", data_type=DataType.TEXT),
                    Property(name="emotional_valence", data_type=DataType.NUMBER),
                    Property(name="timestamp", data_type=DataType.DATE),
                    Property(name="tags", data_type=DataType.TEXT_ARRAY),
                ],
                vectorizer_config=Configure.Vectorizer.text2vec_transformers() # Uses the module in docker-compose
            )

    async def search(self, query: str, agent_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Perform semantic search for memories relevant to an agent."""
        if not self._client or not self._initialized:
            return []

        try:
            collection = self._client.collections.get("EpisodicMemory")
            response = collection.query.near_text(
                query=query,
                limit=limit
            )
            
            memories = []
            for obj in response.objects:
                props = obj.properties
                # Multi-field fallback for architectural transitions
                ts = props.get("timestamp") or props.get("created_at") or datetime.now().isoformat()
                
                memories.append({
                    "author_id": props.get("author_id"),
                    "content": props.get("content"),
                    "subjective_voice": props.get("subjective_voice"),
                    "emotional_valence": props.get("emotional_valence"),
                    "timestamp": ts,
                    "tags": props.get("tags", [])
                })
            return memories
        except Exception as e:
            logger.error(f"Weaviate search failed: {e}")
            return []

    async def insert_memory(self, memory: Dict[str, Any]) -> str:
        """Insert a new memory object into Weaviate."""
        if not self._client or not self._initialized:
            return ""

        try:
            collection = self._client.collections.get("EpisodicMemory")
            
            # Ensure timestamp exists before insertion
            if "timestamp" not in memory:
                memory["timestamp"] = datetime.now().isoformat()
            
            # Weaviate v4 accepts a dict directly
            uuid = collection.data.insert(properties=memory)
            return str(uuid)
        except Exception as e:
            logger.error(f"Weaviate insert failed: {e}")
            return ""

    async def close(self) -> None:
        if self._client:
            self._client.close()

    async def health_check(self) -> bool:
        if not self._client:
            return False
        try:
            return self._client.is_live()
        except Exception:
            return False



_vector_client: Optional[VectorClient] = None

def get_vector_client() -> VectorClient:
    global _vector_client
    if _vector_client is None:
        _vector_client = VectorClient()
    return _vector_client
