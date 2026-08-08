"""
VoidCat RDC: Sovereign Spirit - Argus Telemetry & Evolution Test Suite
======================================================================
PDS Verification Suite for Phase 4 (Steps 4.2 - 4.5).
"""

import os
import shutil
import pytest
from pathlib import Path

# Imports under test
from services.memory.memory_extractor import (
    MemoryExtractor,
    ZeroTokenWatchers,
)
from src.autonomy.evolution_forge import EvolutionForge
from src.voidcat_tools import (
    _assert_not_immutable,
    write_file,
    update_file,
    ImmutabilityViolationError,
    is_protected_path,
)


class TestZeroTokenWatchers:
    """Step 4.3: Fast, zero-token telemetry watchers."""

    def test_json_leak_watcher_trips_on_raw_json(self):
        raw_json_output = "Here is the result: {\"status\": \"error\", \"code\": 500} directly in text."
        result = ZeroTokenWatchers.check_json_leak(raw_json_output)
        assert result.tripped is True
        assert result.watcher_name == "JSON Leak Watcher"

    def test_json_leak_watcher_passes_code_blocks(self):
        fenced_json_output = "Here is the code block:\n```json\n{\"status\": \"ok\"}\n```\nLooks clean."
        result = ZeroTokenWatchers.check_json_leak(fenced_json_output)
        assert result.tripped is False

    def test_traceback_watcher_trips(self):
        traceback_output = "An unexpected error occurred:\nTraceback (most recent call last):\n  File 'main.py', line 10\nValueError: Bad argument"
        result = ZeroTokenWatchers.check_traceback(traceback_output)
        assert result.tripped is True
        assert result.watcher_name == "Traceback Watcher"

    def test_tag_bleed_watcher_trips(self):
        tag_bleed_output = "I am thinking... <think>Internal reasoning step</think> Final answer."
        result = ZeroTokenWatchers.check_tag_bleed(tag_bleed_output)
        assert result.tripped is True
        assert result.watcher_name == "Tag Bleed Watcher"


class TestTriTrackTelemetrySegregation:
    """Step 4.2: Tri-Track Telemetry Routing."""

    def setup_method(self):
        self.extractor = MemoryExtractor()

    def test_chronos_routing(self):
        payload = "User prefers dark mode and uses Python 3.12."
        events = self.extractor.process_payload(payload, spirit_name="Echo", override_track="chronos")
        assert len(events) == 1
        assert events[0].track == "chronos"
        assert events[0].source == "auto"
        assert events[0].category == "chronos"

    def test_hephaestus_routing(self):
        payload = "API timeout occurred on port 8000."
        events = self.extractor.process_payload(payload, spirit_name="Ryuzu", override_track="hephaestus")
        assert len(events) == 1
        assert events[0].track == "hephaestus"
        assert events[0].source == "argus-system"
        assert events[0].category == "hephaestus"

    def test_pantheon_routing(self):
        payload = "Spirit persona voice experienced minor dissonance during response."
        events = self.extractor.process_payload(payload, spirit_name="Cadence", override_track="pantheon")
        assert len(events) == 1
        assert events[0].track == "pantheon"
        assert events[0].source == "argus-spirit"
        assert events[0].category == "pantheon"

    def test_zero_token_watcher_auto_routes_to_hephaestus(self):
        payload = "Traceback (most recent call last):\n  File 'app.py'\nException: System Fault"
        events = self.extractor.process_payload(payload, spirit_name="Pandora", override_track="chronos")
        assert len(events) == 1
        assert events[0].track == "hephaestus"
        assert events[0].source == "argus-system"
        assert events[0].metadata["zero_token_eval"] is True


class TestEvolutionForge:
    """Step 4.4: Evolution Forge & Proposal Cards."""

    def setup_method(self):
        self.test_proposals_dir = Path("temp_test_proposals")
        self.forge = EvolutionForge(proposals_dir=str(self.test_proposals_dir))

    def teardown_method(self):
        if self.test_proposals_dir.exists():
            shutil.rmtree(self.test_proposals_dir)

    def test_friction_accumulation_and_proposal_generation(self):
        spirit = "High Evolutionary"
        # Record 4 friction events (should not trigger card generation yet)
        for i in range(4):
            card_path = self.forge.record_friction(
                spirit_or_domain=spirit,
                track="hephaestus",
                details={"reason": f"System error {i+1}"},
            )
            assert card_path is None
            assert self.forge.get_friction_count(spirit) == i + 1

        # 5th friction event triggers EP card generation
        card_path = self.forge.record_friction(
            spirit_or_domain=spirit,
            track="hephaestus",
            details={"reason": "Critical 5th friction breach"},
        )
        assert card_path is not None
        assert card_path.exists()
        assert card_path.name.startswith("EP-")
        assert card_path.suffix == ".md"

        # Check content of EP card
        content = card_path.read_text(encoding="utf-8")
        assert "# 📜 Evolution Proposal Card: EP-0001" in content
        assert "High Evolutionary" in content
        assert "VES-01 Immutability Charter" in content

        # Verify friction counter reset
        assert self.forge.get_friction_count(spirit) == 0


class TestVES01ImmutabilityCharter:
    """Step 4.5: VES-01 Immutability Charter Guardrails."""

    def test_protected_path_detection(self):
        assert is_protected_path("00_The_Pantheon/01_Active_Profiles/kairo_micron/persona.md") is True
        assert is_protected_path(".env") is True
        assert is_protected_path(".voidcat/CONTEXT.md") is True
        assert is_protected_path("src/core/memory/types.py") is False

    def test_unauthorized_write_to_persona_raises_error(self):
        target = "00_The_Pantheon/01_Active_Profiles/test_spirit/persona.md"
        with pytest.raises(ImmutabilityViolationError) as exc_info:
            write_file(target, "Unauthorized persona rewrite")
        assert "VES-01 Immutability Violation" in str(exc_info.value)

    def test_human_override_bypasses_protection(self, tmp_path):
        target = str(tmp_path / "test_persona.md")
        # Direct call with override=True succeeds
        msg = write_file(target, "Human authorized edit", human_override=True)
        assert "Successfully wrote" in msg
        assert Path(target).read_text() == "Human authorized edit"
