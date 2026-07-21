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
import uuid
import requests
from enum import Enum
from typing import Tuple, Dict, Any, Optional, List
import jinja2

from protocol import Domain, ActionType, Priority, EnergyLevel, IntentCommand, CommandResult
import orchestrator
import distillery
import graph_memory
import database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("clew.router")

class ModelTier(str, Enum):
    TIER_1_LOCAL_BRAIN_STEM = "Tier 1: Local Brain Stem (Primary Orchestrator)"
    TIER_2_CLOUD_WARM = "Tier 2: Cloud Warm (Active Reasoning)"
    TIER_3A_CLOUD_COLD_BATCH = "Tier 3A: Cloud Cold (Async Batching)"
    TIER_3B_CLOUD_COLD_SANDBOX = "Tier 3B: Cloud Cold (Sandboxed Execution)"
    TIER_1_CODER = "Tier 1 (Specialized Coder)"
    TIER_2_GENERALIST = "Tier 2 (Generalist LifeOS)"
    VISION = "Vision Model"

CODER_MODEL = os.getenv("CODER_MODEL", "qwen2.5:3b-instruct")
GENERALIST_MODEL = os.getenv("GENERALIST_MODEL", "qwen2.5:3b-instruct")
VISION_MODEL = os.getenv("VISION_MODEL", "qwen2.5-vl")

# 3-Tier Compute Topology Model Defaults
LOCAL_BRAIN_STEM_MODEL = os.getenv("LOCAL_BRAIN_STEM_MODEL", "qwen2.5:7b-instruct")
CLOUD_WARM_MODEL = os.getenv("CLOUD_WARM_MODEL", "together:llama-3.3-70b-instruct")
CLOUD_COLD_BATCH_MODEL = os.getenv("CLOUD_COLD_BATCH_MODEL", "together-batch:deepseek-v3")
CLOUD_COLD_SANDBOX_MODEL = os.getenv("CLOUD_COLD_SANDBOX_MODEL", "modal:gvisor-sandbox")

# [THREAT 3 PATCH] Limit GPU VRAM footprint to prevent CUDA memory starvation under multi-service contention
OLLAMA_OPTIONS = {
    "num_ctx": 2048,      # Constrains context token space to cap VRAM memory footprints
    "num_predict": 256,   # Caps generation token length to avoid KV cache expansion spikes
    "temperature": 0.2,
    "num_thread": 4       # Threads execution safely without starving system resources
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_system_prompt(tier: ModelTier, sql_results_json: Optional[str] = None) -> str:
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
            living_agent_standards=standards,
            sql_results_json=sql_results_json
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
    def route_compute_tier(self, tier: ModelTier, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Routes execution to the designated compute tier topology provider.
        - Tier 1: Local GPU + System RAM (Qwen 2.5 7B / Llama 3.2 3B) - sub-15ms.
        - Tier 2: Together AI Serverless API (Llama 3.3 70B, Qwen 2.5 Coder 32B, DeepSeek V3) - sub-second active reasoning.
        - Tier 3A: Together AI Batch API (Nightly re-indexing, prompt distillation) - 50% cost discount.
        - Tier 3B: Modal Serverless Containers (gVisor sandboxed environment).
        """
        if tier in (ModelTier.TIER_1_LOCAL_BRAIN_STEM, ModelTier.TIER_1_CODER):
            return {
                "tier": ModelTier.TIER_1_LOCAL_BRAIN_STEM.value,
                "hardware": "Local GPU + System RAM",
                "model": LOCAL_BRAIN_STEM_MODEL,
                "latency_target": "<15ms",
                "sandboxed": False
            }
        elif tier in (ModelTier.TIER_2_CLOUD_WARM, ModelTier.TIER_2_GENERALIST):
            return {
                "tier": ModelTier.TIER_2_CLOUD_WARM.value,
                "provider": "Together AI Serverless APIs",
                "model": CLOUD_WARM_MODEL,
                "latency_target": "<1s",
                "sandboxed": False
            }
        elif tier == ModelTier.TIER_3A_CLOUD_COLD_BATCH:
            return {
                "tier": ModelTier.TIER_3A_CLOUD_COLD_BATCH.value,
                "provider": "Together AI Batch API",
                "model": CLOUD_COLD_BATCH_MODEL,
                "discount": "50%",
                "async": True
            }
        elif tier == ModelTier.TIER_3B_CLOUD_COLD_SANDBOX:
            return {
                "tier": ModelTier.TIER_3B_CLOUD_COLD_SANDBOX.value,
                "provider": "Modal Serverless Containers",
                "model": CLOUD_COLD_SANDBOX_MODEL,
                "sandboxed": True,
                "environment": "gVisor"
            }
        return {
            "tier": ModelTier.TIER_1_LOCAL_BRAIN_STEM.value,
            "hardware": "Local GPU + System RAM",
            "model": LOCAL_BRAIN_STEM_MODEL,
            "latency_target": "<15ms"
        }

    def process_image_input(self, image_bytes_or_path, prompt: str = "Analyze this image and extract a summary and any OCR data.") -> str:
        import base64
        # 1. Read bytes
        if isinstance(image_bytes_or_path, str):
            with open(image_bytes_or_path, "rb") as f:
                img_bytes = f.read()
        else:
            img_bytes = image_bytes_or_path
            
        # 2. Encode to base64
        b64_str = base64.b64encode(img_bytes).decode("utf-8")
        
        # 3. Query Ollama
        ollama_host = os.getenv("OLLAMA_HOST", "http://ollama:11434/v1")
        native_host = ollama_host.replace("/v1", "").rstrip("/")
        url = f"{native_host}/api/chat"
        
        payload = {
            "model": VISION_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "images": [b64_str]
                }
            ],
            "stream": False
        }
        
        try:
            resp = requests.post(url, json=payload, timeout=90)
            resp.raise_for_status()
            # Try to get assistant message content
            return resp.json().get("message", {}).get("content", "")
        except Exception as e:
            logger.error(f"Error calling local vision model: {e}")
            return f"[VISION FALLBACK] Simulated extraction for image. Prompt: {prompt}"

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

def query_ollama_chat(messages: List[Dict[str, str]], model: Optional[str] = None, options: Optional[Dict[str, Any]] = None) -> str:
    if model is None:
        model = GENERALIST_MODEL
    ollama_host = os.getenv("OLLAMA_HOST", "http://ollama:11434/v1")
    native_host = ollama_host.replace("/v1", "").rstrip("/")
    url = f"{native_host}/api/chat"
    try:
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": options or OLLAMA_OPTIONS
        }

        logger.info(f"Querying Ollama chat model '{model}' at {url}...")
        resp = requests.post(url, json=payload, timeout=90)
        resp.raise_for_status()
        return resp.json().get("message", {}).get("content", "")
    except Exception as e:
        logger.error(f"Error querying Ollama chat model '{model}': {e}")
        if model != GENERALIST_MODEL:
            logger.info(f"Attempting fallback to '{GENERALIST_MODEL}' model...")
            try:
                payload["model"] = GENERALIST_MODEL
                resp = requests.post(url, json=payload, timeout=90)
                resp.raise_for_status()
                return resp.json().get("message", {}).get("content", "")
            except Exception as fe:
                logger.error(f"Fallback to '{GENERALIST_MODEL}' failed: {fe}")
        return ""

def get_chat_history_messages(system_prompt: str, user_prompt: str, limit: int = 3) -> List[Dict[str, str]]:
    messages = []
    
    # 1. System Prompt
    messages.append({"role": "system", "content": system_prompt})
    
    # 2. History
    try:
        db_messages = database.get_chat_timeline(limit=limit)
        for m in db_messages:
            role = "user" if m.get("speaker") == "user" else "assistant"
            content = m.get("content") or m.get("message") or ""
            
            # Avoid appending the current user message again if it's already in the database
            if role == "user" and content.strip() == user_prompt.strip():
                continue
                
            messages.append({"role": role, "content": content})
    except Exception as e:
        logger.error(f"Error building chat history: {e}")
        
    # 3. Current Prompt
    messages.append({"role": "user", "content": user_prompt})
    return messages

def extract_json(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    clean = text.strip()
    if clean.startswith("```"):
        lines = clean.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        clean = "\n".join(lines).strip()
        
    start_idx = clean.find("{")
    end_idx = clean.rfind("}")
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        json_str = clean[start_idx:end_idx+1]
        try:
            data = json.loads(json_str)
            if isinstance(data, dict) and "action" in data:
                act_upper = str(data["action"]).upper()
                if act_upper in ("SET_REMINDER", "CREATE_TASK", "SCHEDULE_EVENT"):
                    data["action"] = "ADD_TASK"
            return data
        except Exception:
            pass
    return None

class ModelRouter(AgenticRouter):
    """
    ModelRouter implementation for CognitiveBrain split-brain architecture.
    """
    async def classify_intent(self, user_prompt: str) -> IntentCommand:
        lower = user_prompt.strip().lower()
        
        # Static Chit-Chat Pre-Classifier (Instant 0ms Response for Greetings)
        greetings = {"hello", "hi", "hey", "greetings", "good morning", "good afternoon", "good evening", "clew respond"}
        if lower in greetings or re.match(r"^(hello|hi|hey|greetings|clear chat)\b", lower):
            logger.info("Static Chit-Chat Pre-Classifier matched. Bypassing LLM.")
            return IntentCommand(
                domain=Domain.CHITCHAT,
                action=ActionType.CHITCHAT,
                confidence=1.0,
                reasoning="Matched static greeting pattern.",
                payload={
                    "message": "Hello! I am ready to help. What would you like to do?"
                },
                command_id=str(uuid.uuid4())
            )
            
        tier, model_name = classify_tier(user_prompt)
        
        system = """You are the intent classification model for Clew LifeOS.
Analyze the user's prompt and respond ONLY with a JSON object matching this schema:
{
  "domain": "FINANCE" | "CHORES" | "LOGISTICS" | "PROJECTS" | "WELLBEING" | "CODE" | "CHITCHAT",
  "action": "ADD_TASK" | "COMPLETE_TASK" | "DEFER_TASK" | "LOG_METRIC" | "SCHEDULE_EVENT" | "QUERY_STATE" | "CHITCHAT",
  "confidence": float (0.0 to 1.0),
  "reasoning": "Brief explanation",
  "payload": {
     // For CHITCHAT: {"message": "A direct, helpful chat response answering the user."}
     // For ADD_TASK: {"title": "Task title", "description": "optional description", "priority": "P1"|"P2"|"P3", "energy_level": "low"|"medium"|"high"}
     // For COMPLETE_TASK: {"task_id": int}
     // For DEFER_TASK: {"task_id": int}
     // For LOG_METRIC: {"metric_name": "name", "metric_value": float}
  }
}

Guidelines:
- If the user is just saying hello, asking general questions, having a conversation, or asking a conversational question/command (e.g., "hello", "clew respond", "how are you", "can you help me"), you MUST classify it as domain=CHITCHAT and action=CHITCHAT. In the payload, write a friendly, conversational answer directly under the "message" key (e.g. {"message": "Hello! I am ready to help. What would you like to do?"}). Do NOT try to classify conversational phrases as task additions or metrics.
- If the user explicitly wants to add/create a task, classify as ADD_TASK. Extract details.
- Respond ONLY with valid raw JSON. Do NOT wrap it in markdown backticks or other text."""

        messages = get_chat_history_messages(system, user_prompt, limit=3)
        response_text = query_ollama_chat(messages, model=model_name)
        intent_data = extract_json(response_text)
        
        if intent_data and "domain" in intent_data and "action" in intent_data:
            logger.info(f"Successfully classified intent using LLM: {intent_data.get('domain')} - {intent_data.get('action')}")
            if "command_id" not in intent_data or not intent_data["command_id"]:
                intent_data["command_id"] = str(uuid.uuid4())
            return IntentCommand(**intent_data)

        logger.info("Falling back to simulated intent classification.")
        intent_data = self._simulate_llm_intent_classification(user_prompt, tier)
        return IntentCommand(**intent_data)

    def select_tier(self, intent: Any) -> ModelTier:
        domain = getattr(intent, "domain", None)
        tier, _ = classify_tier("", domain_hint=domain)
        return tier

    def get_templated_prompt(self, model_tier: ModelTier, context_nodes: Optional[List[Dict[str, Any]]] = None, sql_results_json: Optional[str] = None) -> str:
        base_prompt = get_system_prompt(model_tier, sql_results_json=sql_results_json)
        if context_nodes:
            context_str = "\n=== Tether Context Nodes ===\n" + "\n".join([f"- {n.get('label', '')}" for n in context_nodes])
            return base_prompt + "\n" + context_str
        return base_prompt

    async def execute_completion(
        self, 
        model_tier: Optional[ModelTier] = None, 
        system_prompt: str = "", 
        user_prompt: str = "", 
        goal_tether_id: Optional[str] = None, 
        planned_intent: Optional[IntentCommand] = None,
        tier: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Any:
        # Check if called from consolidation loop or requires raw text completion
        if tier is not None or options is not None:
            model_name = GENERALIST_MODEL
            if tier == "CODER" or (isinstance(model_tier, ModelTier) and model_tier == ModelTier.TIER_1_CODER):
                model_name = CODER_MODEL
            
            messages = get_chat_history_messages(system_prompt, user_prompt, limit=3)
            response_text = query_ollama_chat(messages, model=model_name, options=options)
            return response_text

        model_name = CODER_MODEL if model_tier == ModelTier.TIER_1_CODER else GENERALIST_MODEL
        
        if planned_intent:
            intent_dict = {
                "domain": planned_intent.domain.value if hasattr(planned_intent.domain, "value") else str(planned_intent.domain),
                "action": planned_intent.action.value if hasattr(planned_intent.action, "value") else str(planned_intent.action),
                "confidence": planned_intent.confidence,
                "reasoning": planned_intent.reasoning,
                "payload": planned_intent.payload,
                "command_id": planned_intent.command_id
            }
            logger.info("Bypassing second LLM call in execute_completion since planned_intent is provided.")
        else:
            messages = get_chat_history_messages(system_prompt, user_prompt, limit=3)
            response_text = query_ollama_chat(messages, model=model_name)
            intent_dict = extract_json(response_text)
        if not intent_dict:
            if response_text:
                clean_text = response_text.strip()
                if clean_text.startswith("```"):
                    lines = clean_text.splitlines()
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].startswith("```"):
                        lines = lines[:-1]
                    clean_text = "\n".join(lines).strip()
                logger.info("LLM returned plain text. Wrapping in CHITCHAT intent.")
                intent_dict = {
                    "domain": "CHITCHAT",
                    "action": "CHITCHAT",
                    "payload": {
                        "message": clean_text
                    }
                }

        if not intent_dict or not isinstance(intent_dict, dict) or "domain" not in intent_dict or "action" not in intent_dict:
            logger.info("Falling back to simulated intent classification for execution.")
            intent_dict = self._simulate_llm_intent_classification(user_prompt, model_tier)

        if goal_tether_id:
            intent_dict["goal_tether_id"] = goal_tether_id
            
        res = orchestrator.orchestrator.process_intent(
            raw_input=intent_dict,
            model_used=model_name,
            tier=model_tier.value
        )
        return res

    async def execute_streaming_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        history: Optional[List[Dict[str, str]]] = None,
        options: Optional[Dict[str, Any]] = None
    ):
        import httpx
        import json
        
        ollama_host = os.getenv("OLLAMA_HOST", "http://ollama:11434/v1")
        native_host = ollama_host.replace("/v1", "").rstrip("/")
        url = f"{native_host}/api/chat"
        
        # Build messages timeline
        if history:
            messages = [{"role": "system", "content": system_prompt}]
            for m in history:
                messages.append({"role": m.get("role", "user"), "content": m.get("content", "")})
            messages.append({"role": "user", "content": user_prompt})
        else:
            messages = get_chat_history_messages(system_prompt, user_prompt, limit=3)
            
        payload = {
            "model": GENERALIST_MODEL,
            "messages": messages,
            "stream": True,
            "options": options or OLLAMA_OPTIONS
        }
        
        logger.info(f"Initiating Ollama streaming completion on model '{GENERALIST_MODEL}'...")
        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                async with client.stream("POST", url, json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        try:
                            chunk_data = json.loads(line)
                            content = chunk_data.get("message", {}).get("content", "")
                            if content:
                                yield content
                        except Exception as parse_err:
                            logger.error(f"Error parsing Ollama stream chunk: {parse_err}")
        except Exception as e:
            logger.error(f"Ollama streaming completion failed: {e}")
            yield f"Error in streaming completion: {e}"
