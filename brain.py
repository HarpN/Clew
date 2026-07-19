"""
brain.py - Split-Brain Cognitive Architecture & Orchestration Layer
Synchronizes right-hemisphere context synthesis with left-hemisphere intent planning,
fact-checking, and Goal-Tether governance alignment checks with Circuit Breaker retry logic.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional

from protocol import IntentCommand, CommandResult
from router import ModelRouter
from graph_memory import GraphMemory
from distillery import Distillery

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("clew.brain")

class CognitiveBrain:
    """
    The Orchestration Layer that simulates a split-brain cognitive architecture.
    """
    def __init__(self):
        self.router = ModelRouter()
        self.memory = GraphMemory()
        self.distillery = Distillery()
        
    async def process_thought_cycle(self, user_prompt: str, goal_tether_id: str):
        """
        Executes the full cognitive cycle:
        1. Context Synthesis (Right Hemisphere)
        2. Intent Planning (Left Hemisphere)
        3. Execution (The Action)
        4. Fact-Checking & Tether Alignment (Overseer) with Circuit Breaker
        """
        logger.info(f"Initiating synchronized cognitive cycle for Tether: {goal_tether_id}")
        
        max_retries = 2
        for attempt in range(max_retries + 1):
            # 1. Right Hemisphere: Map Context
            context_nodes = self.memory.get_nodes_by_tether(goal_tether_id)
            
            # 2. Left Hemisphere: Plan & Route
            intent = await self.router.classify_intent(user_prompt)
            model_tier = self.router.select_tier(intent)
            system_prompt = self.router.get_templated_prompt(model_tier, context_nodes)
            
            # 3. Execution (The Action)
            command = await self.router.execute_completion(model_tier, system_prompt, user_prompt, goal_tether_id=goal_tether_id)
            
            # 4. Overseer: Fact-Checking & Tether Alignment
            # The "Overseer" quadrant checks grounding and tether alignment
            is_grounded = (
                not (isinstance(command, CommandResult) and not command.success)
                and self.memory.verify_goal_alignment(getattr(intent, "domain", "GENERAL"), command, goal_tether_id)
            )
            
            if is_grounded:
                return command
            
            # Circuit Breaker Logic
            if attempt < max_retries:
                logger.warning(f"Hallucination/Drift detected on attempt {attempt}. Retrying with refinement.")
                # We inject a hint back into the next iteration's context
                user_prompt = f"{user_prompt} (NOTE: Previous response was misaligned with tether. Re-analyze.)"
            else:
                logger.error("Circuit Breaker Tripped: Overseer Veto exceeded retries.")
                return "I cannot verify the data integrity of this response. Stopping to prevent error. Please review the Governance Dashboard."

# Global instance for workspace access
clew_brain = CognitiveBrain()
