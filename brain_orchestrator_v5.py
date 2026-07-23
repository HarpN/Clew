"""
brain_orchestrator_v5.py - Clew V5 Cognitive Brain Orchestrator
Extends CognitiveBrain to support process_thought_cycle_v5 yielding persona metadata and token streams.
"""

import logging
from typing import Tuple, Any, Optional
from brain_orchestrator import CognitiveBrain

logger = logging.getLogger("clew.brain_v5")

class CognitiveBrainV5(CognitiveBrain):
    """
    Clew V5 Orchestration Layer providing persona-aware streaming interface.
    """
    async def process_thought_cycle_v5(
        self,
        user_prompt: str,
        goal_tether_id: str = "mobile_default",
        manual_override_key: Optional[str] = None
    ) -> Tuple[bool, Any, str]:
        """
        Executes V5 thought cycle.
        Returns: (success: bool, result_stream: AsyncGenerator or str, persona_name: str)
        """
        success, result_stream, intent, coords = await self.process_thought_cycle(
            user_prompt=user_prompt,
            goal_tether_id=goal_tether_id,
            manual_override_key=manual_override_key
        )
        
        persona_name = "Clew Core"
        if hasattr(self, "active_personality_directives") and isinstance(self.active_personality_directives, dict):
            persona_name = self.active_personality_directives.get("name", "Clew Core")
        elif hasattr(self, "personality_quadrant") and hasattr(self.personality_quadrant, "current_profile"):
            profile = getattr(self.personality_quadrant, "current_profile", None)
            if profile and hasattr(profile, "name"):
                persona_name = profile.name

        return success, result_stream, persona_name
