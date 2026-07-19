"""
router.py - Multi-Model Agentic Router for Clew LifeOS
Classifies requests into Tier 1 (Specialized Coder) or Tier 2 (Generalist LifeOS),
renders Jinja2 context-sensitive system prompts with auto-optimization hints,
and routes through orchestrator middleware with autonomous confidence fallback tuning.
"""

import os
import re
import json
import logging
from enum import Enum
from typing import Tuple, Dict, Any, Optional
import jinja2

from protocol import Domain, ActionType, Priority, EnergyLevel, IntentCommand, CommandResult
import orchestrator
import distillery
import graph_memory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("clew.router")

class ModelTier(str, Enum):
    TIER_1_CODER = "Tier 1 (Specialized Coder)"
    TIER_2_GENERALIST = "Tier 2 (Generalist LifeOS)"

CODER_MODEL = os.getenv("CODER_MODEL", "deepseek-coder")
GENERALIST_MODEL = os.getenv("GENERALIST_MODEL", "llama3")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_system_prompt(tier: ModelTier) -> str:
    """
    Renders context-sensitive Jinja2 system prompt corresponding to the target tier,
    injecting Living Agent.md standards and approved auto-optimization hints.
    """
    active_hints = distillery.load_active_hints()
    hints = active_hints.get(tier.value, [])
    standards = graph_memory.get_style_graph_standards()

    if tier == ModelTier.TIER_1_CODER:
        tmpl_path = os.path.join(BASE_DIR, "prompts", "coder_system_prompt.j2")
    else:
        tmpl_path = os.path.join(BASE_DIR, "prompts", "lifeos_system_prompt.j2")
        
    if os.path.exists(tmpl_path):
        with open(tmpl_path, "r", encoding="utf-8") as f:
            raw_tmpl = f.read()
        template = jinja2.Template(raw_tmpl)
        return template.render(
            optimization_hints=hints,
            living_agent_standards=standards
        )
        
    return f"Default system prompt for {tier.value}"

def classify_tier(query_text: str, domain_hint: Optional[Domain] = None) -> Tuple[ModelTier, str]:
    """
    Classifies query into Tier 1 Coder or Tier 2 Generalist.
    Enforces Autonomous Confidence Tuning: If domain confidence < 0.70, automatically
    fallback-routes to Tier 1 Specialized Coder for testing.
    """
    # Check domain confidence threshold
    domain_key = domain_hint.value if domain_hint else "GENERAL"
    confidence_score = orchestrator.orchestrator.get_domain_confidence(domain_key)
    
    if confidence_score < 0.70:
        logger.warning(f"Autonomous Confidence Tuning triggered: Domain '{domain_key}' confidence {confidence_score:.2f} < 0.70. Upgrading to Tier 1 Coder Specialist fallback.")
        return ModelTier.TIER_1_CODER, CODER_MODEL

    if domain_hint in (Domain.PROJECTS, Domain.CODE):
        return ModelTier.TIER_1_CODER, CODER_MODEL
        
    coder_keywords = r"\b(code|refactor|bug|python|function|git|docker|script|deploy|api|endpoint|query|database|sql)\b"
    if re.search(coder_keywords, query_text.lower()):
        return ModelTier.TIER_1_CODER, CODER_MODEL
        
    return ModelTier.TIER_2_GENERALIST, GENERALIST_MODEL

class AgenticRouter:
    """
    Multi-model router engine. Injects Jinja2 system prompts, handles protocol enforcement,
    and forwards Pydantic IntentCommand objects to orchestrator middleware.
    """
    def route(self, query_text: str, domain_hint: Optional[Domain] = None, override_dict: Optional[Dict[str, Any]] = None) -> CommandResult:
        tier, model_name = classify_tier(query_text, domain_hint)
        system_prompt = get_system_prompt(tier)
        
        logger.info(f"Routed query to [{tier.value}] using model '{model_name}'")
        
        if override_dict:
            intent_data = override_dict
        else:
            intent_data = self._simulate_llm_intent_classification(query_text, tier)
            
        res = orchestrator.orchestrator.process_intent(
            raw_input=intent_data,
            model_used=model_name,
            tier=tier.value
        )
        return res

    def _simulate_llm_intent_classification(self, query_text: str, tier: ModelTier) -> Dict[str, Any]:
        lower = query_text.lower()
        
        if tier == ModelTier.TIER_1_CODER:
            domain = "PROJECTS"
            action = "ADD_TASK"
            priority = "P1" if "urgent" in lower or "critical" in lower else "P2"
            energy = "high"
            title = query_text
        else:
            if "laundry" in lower or "wash" in lower or "clean" in lower:
                domain = "CHORES"
                action = "ADD_TASK"
                priority = "P2"
                energy = "low"
                title = query_text
            elif "buy" in lower or "purchase" in lower or "cost" in lower or "dollar" in lower:
                domain = "FINANCE"
                action = "ADD_TASK"
                priority = "P2"
                energy = "medium"
                title = query_text
            elif "hello" in lower or "hi" in lower or "how are you" in lower:
                domain = "CHITCHAT"
                action = "CHITCHAT"
                priority = "P3"
                energy = "low"
                title = query_text
            else:
                domain = "LOGISTICS"
                action = "ADD_TASK"
                priority = "P2"
                energy = "medium"
                title = query_text

        return {
            "domain": domain,
            "action": action,
            "reasoning": f"Routed via {tier.value}",
            "payload": {
                "title": title,
                "priority": priority,
                "energy_level": energy,
                "message": query_text if action == "CHITCHAT" else ""
            }
        }

# Module singleton instance
router = AgenticRouter()

class ModelRouter(AgenticRouter):
    """
    ModelRouter implementation for CognitiveBrain split-brain architecture.
    """
    async def classify_intent(self, user_prompt: str) -> IntentCommand:
        tier, model_name = classify_tier(user_prompt)
        intent_data = self._simulate_llm_intent_classification(user_prompt, tier)
        return IntentCommand(**intent_data)

    def select_tier(self, intent: Any) -> ModelTier:
        domain = getattr(intent, "domain", None)
        tier, _ = classify_tier("", domain_hint=domain)
        return tier

    def get_templated_prompt(self, model_tier: ModelTier, context_nodes: Optional[List[Dict[str, Any]]] = None) -> str:
        base_prompt = get_system_prompt(model_tier)
        if context_nodes:
            context_str = "\n=== Tether Context Nodes ===\n" + "\n".join([f"- {n.get('label', '')}" for n in context_nodes])
            return base_prompt + "\n" + context_str
        return base_prompt

    async def execute_completion(self, model_tier: ModelTier, system_prompt: str, user_prompt: str, goal_tether_id: Optional[str] = None) -> CommandResult:
        intent_dict = self._simulate_llm_intent_classification(user_prompt, model_tier)
        if goal_tether_id:
            intent_dict["goal_tether_id"] = goal_tether_id
            
        res = orchestrator.orchestrator.process_intent(
            raw_input=intent_dict,
            model_used=CODER_MODEL if model_tier == ModelTier.TIER_1_CODER else GENERALIST_MODEL,
            tier=model_tier.value
        )
        return res
