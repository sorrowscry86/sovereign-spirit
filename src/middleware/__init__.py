"""
VoidCat RDC: Middleware Package
================================
Sovereign Spirit Memory Processing Layer
"""

from .valence_stripping import (
    MemoryObject,
    EmotionalValence,
    strip_valence,
    process_memory_batch
)

__all__ = [
    "MemoryObject",
    "EmotionalValence", 
    "strip_valence",
    "process_memory_batch"
]

__version__ = "1.0.0"
__author__ = "Echo (E-01)"
