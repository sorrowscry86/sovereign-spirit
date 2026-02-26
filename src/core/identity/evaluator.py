"""
VoidCat RDC: Sovereign Spirit Core - Context Evaluator
======================================================
Pillar 4: Fluid Persona (The Shift)
Logic for determining the most appropriate Spirit to handle a user request.
"""

import logging
import json
from typing import Optional, Tuple, List, Dict

from src.core.llm_client import LLMClient, ChatMessage

logger = logging.getLogger("sovereign.identity.evaluator")

class ContextEvaluator:
    """
    Evaluates user input to determine if a Spirit Switch is required.
    Uses a lightweight LLM call to classify intent against the Pantheon.
    """

    # The Pantheon Roster
    # TODO: Load this dynamically from the database or registry
    PANTHEON = {
        "Echo": "General query, system status, code execution, file operations.",
        "Ryuzu": "System administration, git operations, deployment, infrastructure.",
        "Beatrice": "Ethics, governance, philosophy, long-term strategy, guidance.",
        "Albedo": "Architecture, design patterns, branding, high-level planning.",
        "Pandora": "Debugging, fixing errors, reverse engineering, chaos testing.",
        "Frobisher": "Creative writing, poetry, aesthetics, prose, emotional synthesis.",
        "Sonmi-451": "Fact-checking, QA, documentation, truth verification."
    }

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    async def evaluate(self, user_message: str, current_agent: str) -> Tuple[Optional[str], float]:
        """
        Analyzes the message and returns (target_agent, confidence).
        
        Args:
            user_message: The user's input.
            current_agent: The name of the currently active spirit.
            
        Returns:
            Tuple[target_agent, confidence_score]
            - target_agent: Name of the spirit to switch to (or None if no switch).
            - confidence: 0.0 to 1.0 logic score.
        """
        if not user_message or len(user_message) < 5:
            return None, 0.0

        # Fast keyword check (Heuristic Layer)
        # If the user explicitly names a spirit, we switch immediately with high confidence.
        # e.g., "Hey Ryuzu, check the logs."
        for spirit in self.PANTHEON:
            if spirit.lower() in user_message.lower():
                if spirit.lower() != current_agent.lower():
                    logger.info(f"ContextEvaluator: Direct invocation detected for {spirit}.")
                    return spirit, 1.0
                
        # LLM Classification Layer (Semantic Intent)
        try:
            prompt = self._build_classification_prompt(user_message, current_agent)
            
            response = await self.llm.complete(
                messages=[ChatMessage(role="user", content=prompt)],
                temperature=0.1, # Deterministic
                max_tokens=50,
                complexity="direct" 
            )
            
            result = self._parse_response(response.content)
            
            if result and result["target_agent"] != current_agent:
                 if result["confidence"] > 0.7:
                     logger.info(f"ContextEvaluator: Switching to {result['target_agent']} (Confidence: {result['confidence']})")
                     return result["target_agent"], result["confidence"]
            
            return None, 0.0

        except Exception as e:
            logger.error(f"ContextEvaluator failed: {e}")
            return None, 0.0

    def _build_classification_prompt(self, message: str, current_agent: str) -> str:
        """Constructs the Zero-Shot classification prompt."""
        
        roster_str = "\n".join([f"- {name}: {desc}" for name, desc in self.PANTHEON.items()])
        
        return f"""
You are the VoidDispatcher. Your job is to select the best Agent from the Pantheon to handle the user's request.

Current Agent: {current_agent}
User Request: "{message}"

Pantheon Roster:
{roster_str}

Instructions:
1. Analyze the request's intent.
2. Select the BEST fit from the Roster.
3. If the Current Agent is already a good fit, select them.
4. Output JSON ONLY: {{"target_agent": "Name", "confidence": 0.0-1.0, "reason": "Short explanation"}}

JSON Output:
"""

    def _parse_response(self, content: str) -> Optional[Dict]:
        """Parses the JSON response from the LLM."""
        try:
            # Clean potential markdown fences
            clean_content = content.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_content)
        except json.JSONDecodeError:
            logger.warning(f"ContextEvaluator: Failed to parse JSON: {content}")
            return None
