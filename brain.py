"""
brain.py - Split-Brain Cognitive Architecture & Orchestration Layer
Synchronizes right-hemisphere context synthesis with left-hemisphere intent planning,
fact-checking, and Goal-Tether governance alignment checks with Circuit Breaker retry logic.
"""

import asyncio
import logging
import json
from typing import Dict, Any, List, Optional

from protocol import IntentCommand, CommandResult, ActionType
from router import ModelRouter, GENERALIST_MODEL, OLLAMA_OPTIONS
from graph_memory import GraphMemory
from distillery import Distillery
from orchestrator import ConstraintGuard

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
        
    async def process_thought_cycle(self, user_prompt: str, goal_tether_id: str, chat_history: Optional[List[Dict[str, str]]] = None):
        """
        Executes the full cognitive cycle using pre-flight constraint checks:
        1. Context Synthesis (Right Hemisphere)
        2. Intent Planning (Left Hemisphere)
        3. Deterministic Pre-Flight Veto (DSV)
        4. Context Pinning & Enrichment
        5. Execution / Completion
        """
        logger.info(f"Initiating synchronized cognitive cycle for Tether: {goal_tether_id}")
        
        # 1. Right Hemisphere: Map Context
        context_nodes = self.memory.get_nodes_by_tether(goal_tether_id)
        
        # 2. Left Hemisphere: Plan & Route
        intent = await self.router.classify_intent(user_prompt)
        
        # 3. Deterministic Pre-Flight Veto (DSV)
        is_valid, violation_reason = ConstraintGuard.verify_pre_flight(intent, goal_tether_id)
        
        if not is_valid:
            logger.warning(f"Pre-Flight Veto Triggered: {violation_reason}")
            # Log constraint violation in Event Store
            import event_store
            event_store.record_event(
                event_type="CONSTRAINT_BLOCKED",
                domain=intent.domain.value if hasattr(intent.domain, "value") else str(intent.domain),
                title=f"Blocked {intent.action.value if hasattr(intent.action, 'value') else str(intent.action)}",
                description=violation_reason,
                tradeoff_context="Constraint Guard enforced safety rules in pre-flight veto.",
                metadata={"command_id": intent.command_id, "goal_tether_id": goal_tether_id}
            )
            return f"⚠️ Constraint Guard Veto: {violation_reason}"
            
        # 4. Context Enrichment (Strict Context Pinning)
        sql_results_json = None
        if intent.action == ActionType.QUERY_STATE:
            # Pre-Flight Query execution
            from orchestrator import orchestrator
            try:
                db_results = orchestrator._execute_command(intent)
                sql_results_json = json.dumps(db_results)
            except Exception as e:
                logger.error(f"Pre-flight query execution failed: {e}")
                sql_results_json = "{}"
                
        model_tier = self.router.select_tier(intent)
        system_prompt = self.router.get_templated_prompt(model_tier, context_nodes, sql_results_json=sql_results_json)
        
        # 5. Dispatch completion / execution (Static response for brain.py)
        if intent.domain == "CHITCHAT" or intent.action == ActionType.CHITCHAT or intent.action == ActionType.QUERY_STATE:
            # For queries and chitchat, execute normal completion to get text response
            # Pass planned_intent=None for QUERY_STATE so that it executes the LLM completion with the grounded context.
            res = await self.router.execute_completion(
                model_tier,
                system_prompt,
                user_prompt,
                goal_tether_id=goal_tether_id,
                planned_intent=None if intent.action == ActionType.QUERY_STATE else intent
            )
            return res
        else:
            # For database mutations, execute the command and return the result
            return await self.router.execute_completion(
                model_tier,
                system_prompt,
                user_prompt,
                goal_tether_id=goal_tether_id,
                planned_intent=intent
            )

# Global instance for workspace access
clew_brain = CognitiveBrain()
