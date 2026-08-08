"""
VoidCat RDC: Sovereign Spirit Core - Memory Extractor Adapter
=============================================================
Re-exports services.memory.memory_extractor components into src.core.memory.
"""

from services.memory.memory_extractor import (
    MemoryExtractor,
    ZeroTokenWatchers,
    ZeroTokenWatcherResult,
    TelemetryEvent,
)

__all__ = [
    "MemoryExtractor",
    "ZeroTokenWatchers",
    "ZeroTokenWatcherResult",
    "TelemetryEvent",
]
