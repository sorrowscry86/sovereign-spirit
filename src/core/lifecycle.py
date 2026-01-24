"""
VoidCat RDC: Sovereign Spirit Core - Lifecycle Manager
======================================================
Coordinates the graceful initialization and shutdown of all persistent resources.
"""

import asyncio
import logging
from src.core.database import get_database
from src.core.cache import get_cache
from src.core.vector import get_vector_client
from src.core.graph import get_graph

logger = logging.getLogger("sovereign.lifecycle")

class LifecycleManager:
    """Manages the birth and death of Spirit connections."""
    
    @staticmethod
    async def initialize_all():
        """Boot up all cognitive spectra."""
        logger.info("Initializing Sovereign Spirit Infrastructure...")
        
        db = get_database()
        cache = get_cache()
        vector = get_vector_client()
        graph = get_graph()
        
        # Parallel init
        tasks = [
            db.initialize(),
            cache.initialize(),
            vector.initialize(),
            graph.initialize()
        ]
        await asyncio.gather(*tasks)
        
        # Start Heartbeat (Background Daemon)
        from src.core.heartbeat.service import get_heartbeat_service
        hb = get_heartbeat_service()
        await hb.start()
        
        logger.info("Lifecycle: Infrastructure Online.")

    @staticmethod
    async def shutdown():
        """Release all handles. No ghosts allowed."""
        logger.info("Directive: Executing Graceful Shutdown Sequence...")
        
        db = get_database()
        cache = get_cache()
        vector = get_vector_client()
        graph = get_graph()
        
        # Stop Heartbeat
        from src.core.heartbeat.service import get_heartbeat_service
        hb = get_heartbeat_service()
        await hb.stop()
        
        # Shutdown handles
        if db:
            logger.debug("Database handles released.")
            
        if cache:
            await cache.close()
            logger.info("Redis spectrum extinguished.")
            
        if vector:
            await vector.close()
            logger.info("Weaviate spectrum extinguished.")
            
        if graph:
            await graph.close()
            logger.info("Neo4j spectrum extinguished.")
            
        logger.info("Lifecycle: Shutdown Complete. All spirits laid to rest.")
