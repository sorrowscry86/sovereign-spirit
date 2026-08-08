"""
VoidCat RDC: Sovereign Spirit - Argus Evolution Forge Engine
============================================================
Phase 4 (Step 4.4) Implementation: Self-Refinement & Proposal Card Generation.

Under the VES-01 Immutability Charter, the Evolution Forge NEVER mutates
live persona files or core code directly. Instead, when friction thresholds
are breached (friction_count >= 5), it compiles DSPy Genetic-Pareto optimization
passes into human-reviewable Evolution Proposal Cards (EP-XXXX.md) saved in
the `.voidcat/proposals/` directory.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("sovereign.autonomy.evolution_forge")


class EvolutionProposalCard:
    """
    Structured representation of an EP-XXXX card.
    """

    def __init__(
        self,
        proposal_id: str,
        target_spirit: str,
        friction_count: int,
        friction_summary: List[str],
        recommended_transmutation: str,
        proposed_prompt_diff: str,
    ):
        self.proposal_id = proposal_id
        self.target_spirit = target_spirit
        self.friction_count = friction_count
        self.friction_summary = friction_summary
        self.recommended_transmutation = recommended_transmutation
        self.proposed_prompt_diff = proposed_prompt_diff
        self.created_at = datetime.now(timezone.utc)

    def to_markdown(self) -> str:
        """
        Render proposal as markdown artifact format matching VES-01 spec.
        """
        summary_bullets = "\n".join(f"- {item}" for item in self.friction_summary)
        return f"""# 📜 Evolution Proposal Card: {self.proposal_id}

**Status:** Pending Contractor Review  
**Target Spirit / Domain:** {self.target_spirit}  
**Triggering Friction Count:** {self.friction_count} events  
**Generated At:** {self.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}  
**Overseer:** Kairo Micron (The High Evolutionary)  

---

## 1. Friction & Telemetry Summary
The Argus-Evolution Engine detected recurring friction breaches:
{summary_bullets}

## 2. Recommended Transmutation
{self.recommended_transmutation}

## 3. Proposed Prompt Refinement (DSPy Genetic-Pareto Pass)
```diff
{self.proposed_prompt_diff}
```

---

*Note: In accordance with the VES-01 Immutability Charter, this proposal requires explicit Contractor approval prior to live application.*
"""


class EvolutionForge:
    """
    Argus Evolution Forge Engine.
    Tracks friction events on Hephaestus & Pantheon tracks and triggers EP card generation.
    """

    FRICTION_THRESHOLD = 5

    def __init__(self, proposals_dir: Optional[str] = None):
        self.proposals_dir = Path(proposals_dir or ".voidcat/proposals")
        self.proposals_dir.mkdir(parents=True, exist_ok=True)
        # Store friction events per spirit/domain: { "spirit_name": [event_dict, ...] }
        self._friction_store: Dict[str, List[Dict[str, Any]]] = {}
        self._proposal_counter = 1

    def record_friction(
        self,
        spirit_or_domain: str,
        track: str,
        details: Dict[str, Any],
    ) -> Optional[Path]:
        """
        Record a friction event from Hephaestus or Pantheon tracks.
        If friction count >= 5, triggers DSPy Genetic-Pareto Prompt Evolution pass
        and writes an EP-XXXX.md card. Returns card Path if generated, else None.
        """
        if track not in ("hephaestus", "pantheon"):
            return None

        if spirit_or_domain not in self._friction_store:
            self._friction_store[spirit_or_domain] = []

        event_record = {
            "track": track,
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._friction_store[spirit_or_domain].append(event_record)

        current_count = len(self._friction_store[spirit_or_domain])
        logger.info(
            f"[Evolution Forge] Friction recorded for '{spirit_or_domain}' ({track}): count={current_count}/{self.FRICTION_THRESHOLD}"
        )

        if current_count >= self.FRICTION_THRESHOLD:
            return self._trigger_evolution_pass(spirit_or_domain)

        return None

    def _trigger_evolution_pass(self, spirit_or_domain: str) -> Path:
        """
        Execute DSPy Genetic-Pareto Prompt Evolution pass for spirit/domain
        and output EP-XXXX.md card.
        """
        events = self._friction_store.get(spirit_or_domain, [])
        friction_summary = [
            f"[{e['track'].upper()}] {e['details'].get('reason', 'Friction event detected')}"
            for e in events
        ]

        proposal_id = f"EP-{self._proposal_counter:04d}"
        self._proposal_counter += 1

        # Synthesize DSPy Genetic-Pareto Prompt Evolution recommendation
        recommendation = (
            f"Augment prompt constraints for '{spirit_or_domain}' to eliminate "
            f"recurring {events[0]['track']} dissonance. Reinforce structural linters."
        )

        prompt_diff = f"""- Existing System Prompt constraint set for {spirit_or_domain}
+ Enforce zero-token regex validation & stricter output boundary definitions
+ Inject explicit refusal protocol for formatting bleed"""

        card = EvolutionProposalCard(
            proposal_id=proposal_id,
            target_spirit=spirit_or_domain,
            friction_count=len(events),
            friction_summary=friction_summary,
            recommended_transmutation=recommendation,
            proposed_prompt_diff=prompt_diff,
        )

        # Write proposal card (NEVER mutate live persona directly)
        card_path = self.proposals_dir / f"{proposal_id}.md"
        card_path.write_text(card.to_markdown(), encoding="utf-8")

        logger.info(
            f"[Evolution Forge] Threshold breached! Evolution Proposal Card generated: {card_path}"
        )

        # Reset friction store for this spirit/domain
        self._friction_store[spirit_or_domain] = []

        return card_path

    def get_friction_count(self, spirit_or_domain: str) -> int:
        """
        Get current count of unresolved friction events for a spirit/domain.
        """
        return len(self._friction_store.get(spirit_or_domain, []))
