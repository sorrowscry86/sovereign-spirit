"""
VoidCat RDC: Sovereign Spirit - Tri-Track Memory Extractor & Argus Telemetry Watchers
=======================================================================================
Phase 4 (Argus-Evolution) Implementation per Master Execution Blueprint.

Features:
- Step 4.2: Tri-Track Telemetry Segregation (Chronos, Hephaestus, Pantheon).
- Step 4.3: Zero-Token Telemetry Watchers (JSON Leak, Traceback, Tag Bleed).
"""

import re
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field

logger = logging.getLogger("sovereign.memory.extractor")


class TelemetryEvent(BaseModel):
    """
    A segregated telemetry memory payload.
    """
    event_id: str
    track: str  # "chronos", "hephaestus", or "pantheon"
    source: str  # "auto", "argus-system", or "argus-spirit"
    payload: str
    category: str
    spirit_name: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ZeroTokenWatcherResult(BaseModel):
    """
    Result emitted by zero-token telemetry watchers.
    """
    tripped: bool
    watcher_name: str
    detected_pattern: Optional[str] = None
    reason: Optional[str] = None


class ZeroTokenWatchers:
    """
    Zero-token telemetry watchers that execute string/regex matching
    prior to LLM evaluation to detect system friction instantly.
    """

    @staticmethod
    def check_json_leak(content: str) -> ZeroTokenWatcherResult:
        """
        Detect raw '{' or '}' formatting bleeding into output outside of code blocks.
        """
        # Strip code blocks
        clean_text = re.sub(r"```[\s\S]*?```", "", content)
        if "{" in clean_text or "}" in clean_text:
            return ZeroTokenWatcherResult(
                tripped=True,
                watcher_name="JSON Leak Watcher",
                detected_pattern="Unescaped JSON curly brace outside code block",
                reason="Raw JSON formatting bled into standard chat output",
            )
        return ZeroTokenWatcherResult(tripped=False, watcher_name="JSON Leak Watcher")

    @staticmethod
    def check_traceback(content: str) -> ZeroTokenWatcherResult:
        """
        Detect Python Tracebacks or unhandled Exception snippets in payload.
        """
        patterns = [
            r"Traceback \(most recent call last\):",
            r"Exception:",
            r"raise \w+Error\(",
            r"\[ERROR\] System\.Exception",
        ]
        for pattern in patterns:
            if re.search(pattern, content):
                return ZeroTokenWatcherResult(
                    tripped=True,
                    watcher_name="Traceback Watcher",
                    detected_pattern=pattern,
                    reason="Technical friction traceback detected in payload",
                )
        return ZeroTokenWatcherResult(tripped=False, watcher_name="Traceback Watcher")

    @staticmethod
    def check_tag_bleed(content: str) -> ZeroTokenWatcherResult:
        """
        Detect unparsed <think> or <thought> fragments in response text.
        """
        pattern = r"</?think>|</?thought>"
        if re.search(pattern, content, re.IGNORECASE):
            return ZeroTokenWatcherResult(
                tripped=True,
                watcher_name="Tag Bleed Watcher",
                detected_pattern="Unparsed reasoning tag fragment",
                reason="Internal reasoning tags bled into response stream",
            )
        return ZeroTokenWatcherResult(tripped=False, watcher_name="Tag Bleed Watcher")

    @classmethod
    def evaluate_all(cls, content: str) -> List[ZeroTokenWatcherResult]:
        """
        Run all zero-token watchers on content.
        """
        return [
            cls.check_json_leak(content),
            cls.check_traceback(content),
            cls.check_tag_bleed(content),
        ]


class MemoryExtractor:
    """
    Tri-Track Memory Routing & Extractor Pipeline.
    """

    TRACK_CHRONOS = "chronos"        # Regular learning (source="auto")
    TRACK_HEPHAESTUS = "hephaestus"  # System evolution (source="argus-system")
    TRACK_PANTHEON = "pantheon"      # Spirit evolution (source="argus-spirit")

    def __init__(self):
        self.watchers = ZeroTokenWatchers()

    def process_payload(
        self,
        payload: str,
        spirit_name: Optional[str] = None,
        override_track: Optional[str] = None,
        custom_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[TelemetryEvent]:
        """
        Process incoming payload:
        1. Run Zero-Token Telemetry Watchers.
        2. If watchers trip, immediately route to Hephaestus track (argus-system).
        3. Otherwise, route payload to designated track (Chronos or Pantheon).
        """
        events: List[TelemetryEvent] = []
        meta = custom_metadata or {}
        event_counter = int(datetime.now(timezone.utc).timestamp() * 1000)

        # 1. Zero-Token Watcher Pass (Pre-LLM)
        watcher_results = self.watchers.evaluate_all(payload)
        tripped_watchers = [r for r in watcher_results if r.tripped]

        if tripped_watchers:
            for watcher in tripped_watchers:
                logger.warning(
                    f"[Zero-Token Watcher Tripped] {watcher.watcher_name}: {watcher.reason}"
                )
                events.append(
                    TelemetryEvent(
                        event_id=f"EVT-HEPH-{event_counter}",
                        track=self.TRACK_HEPHAESTUS,
                        source="argus-system",
                        payload=payload,
                        category="hephaestus",
                        spirit_name=spirit_name,
                        metadata={
                            **meta,
                            "watcher_tripped": watcher.watcher_name,
                            "detected_pattern": watcher.detected_pattern,
                            "reason": watcher.reason,
                            "zero_token_eval": True,
                        },
                    )
                )
                event_counter += 1
            return events

        # 2. Normal Routing
        target_track = override_track or self.TRACK_CHRONOS
        source_tag = "auto"
        category_tag = "chronos"

        if target_track == self.TRACK_HEPHAESTUS:
            source_tag = "argus-system"
            category_tag = "hephaestus"
        elif target_track == self.TRACK_PANTHEON:
            source_tag = "argus-spirit"
            category_tag = "pantheon"

        events.append(
            TelemetryEvent(
                event_id=f"EVT-{target_track.upper()[:4]}-{event_counter}",
                track=target_track,
                source=source_tag,
                payload=payload,
                category=category_tag,
                spirit_name=spirit_name,
                metadata={**meta, "zero_token_eval": True, "tripped": False},
            )
        )
        return events
