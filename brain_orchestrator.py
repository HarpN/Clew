import asyncio
import logging
import re
from typing import Dict, Any, List, Tuple, Optional
from router import ModelRouter
from graph_memory import GraphMemory
from constraint_guard import ConstraintGuard
from neuromorphic_subsystems import Amygdala, Cerebellum
from personality_quadrant import PersonalityQuadrant


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("clew.brain")

# Ultra-fast path matching for immediate greetings (0ms LLM Latency)
GREETING_PATTERN = re.compile(
    r"^\s*(hello|hi|hey|greetings|clew|respond|wake up|yo|status)\b\s*$", 
    re.IGNORECASE
)

class CognitiveBrain:
    """
    The Orchestration Layer representing a biological multi-quadrant brain model.
    Enforces deterministic pre-flight vetos (Option A) to prevent streaming violations.
    """
    def __init__(self):
        self.router = ModelRouter()
        self.memory = GraphMemory()
        self.guard = ConstraintGuard()
        self.amygdala = Amygdala(stress_threshold=0.75)
        self.terse_mode_active = False
        self.cerebellum = Cerebellum()
        self.personality_quadrant = PersonalityQuadrant()

        
    def _check_fast_path(self, prompt: str) -> str:
        """
        Bypasses LLM generation entirely for common, high-frequency static greetings.
        """
        if GREETING_PATTERN.match(prompt):
            logger.info("Latency Optimization: Greeting fast-path triggered. Bypassing LLM pipeline.")
            return "Active. Ready to navigate the labyrinth. What are we building?"
        return None

    async def process_thought_cycle(
        self, 
        user_prompt: str, 
        goal_tether_id: str, 
        chat_history: Optional[List[Dict[str, Any]]] = None,
        keystroke_deltas: Optional[List[float]] = None,
        manual_override_key: Optional[str] = None
    ) -> Tuple[bool, Any, Any, Optional[Dict[str, float]]]:
        """
        Executes a synchronized, high-performance cognitive cycle.
        Returns: (is_success, friendly_response_or_generator, intent_or_reason, active_coordinates)
        """
        logger.info(f"Initiating cognitive thought cycle. Goal Tether: {goal_tether_id}")
        self.terse_mode_active = False
        
        # 1. 0ms Latency Fast-Path Check
        fast_response = self._check_fast_path(user_prompt)
        if fast_response:
            return True, fast_response, None, None

        # Intercept Hot-Paths
        matched = self.cerebellum.execute_hot_path(user_prompt)
        if matched:
            domain, action, params = matched
            logger.info("[CEREBELLUM] Hot-path muscle memory match. Bypassing Frontal Lobe.")
            
            from protocol import IntentCommand, Domain, ActionType
            import uuid
            
            # Instantiate a mock Intent object matching the returned domain and action payloads.
            intent = IntentCommand(
                command_id=str(uuid.uuid4()),
                goal_tether_id=goal_tether_id,
                domain=Domain(domain) if isinstance(domain, str) else domain,
                action=ActionType(action) if isinstance(action, str) else action,
                confidence=1.0,
                reasoning="Hot-path muscle memory match",
                payload=params
            )
            
            # Check deterministic constraints using self.guard.verify_pre_flight.
            is_valid, violation_reason = self.guard.verify_pre_flight(
                intent_domain=intent.domain.value if hasattr(intent.domain, "value") else str(intent.domain),
                action=intent.action.value if hasattr(intent.action, "value") else str(intent.action),
                params=params
            )
            
            if not is_valid:
                logger.warning(f"Pre-Flight Veto Triggered in Hot-Path: {violation_reason}")
                return False, f"⚠️ Constraint Guard Veto: {violation_reason}", "MANUAL_REVIEW_REQUIRED"
                
            # Run the database action directly using self._execute_command or your executor pipeline.
            from orchestrator import orchestrator
            try:
                db_result = orchestrator._execute_command(intent)
                logger.info(f"[CEREBELLUM] Database action executed successfully. Result: {db_result}")
                
                # Format a direct stream or message confirming the execution.
                confirm_msg = f"[CEREBELLUM] Hot-path execution successful. Action: {action} on Domain: {domain}. Task: '{params.get('title')}'."
                
                async def direct_stream():
                    yield confirm_msg
                    
                return True, direct_stream(), intent, None
            except Exception as e:
                logger.error(f"[CEREBELLUM] Database execution error in hot-path: {e}")
                return False, f"⚠️ Database execution error: {str(e)}", "HOT_PATH_EXECUTION_ERROR", None

        # 2. Context Pruning (Truncate to last 3 messages to prevent local CPU context bloat)
        pruned_history = []
        if chat_history:
            pruned_history = chat_history[-3:]
            logger.info(f"Context pruned to {len(pruned_history)} messages for performance.")

        # --- Friction Assessment Pass ---
        import database
        # 1. Get user messages to calculate delta_T fallback and extract last 3 user prompts
        history_timeline = chat_history if chat_history else database.get_chat_timeline(limit=10)
        user_msgs = [msg for msg in history_timeline if msg.get("speaker") == "user"]
        
        # Calculate message temporal delta if keystroke_deltas not sent
        resolved_deltas = keystroke_deltas
        if resolved_deltas is None:
            if len(user_msgs) >= 2:
                from datetime import datetime
                def parse_timestamp(ts):
                    if isinstance(ts, datetime):
                        return ts
                    if isinstance(ts, str):
                        ts_clean = ts.replace('T', ' ').split('.')[0].rstrip('Z')
                        for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S%z', '%Y-%m-%d'):
                            try:
                                return datetime.strptime(ts_clean, fmt)
                            except ValueError:
                                continue
                    return datetime.now()
                ts1 = parse_timestamp(user_msgs[-2].get("timestamp"))
                ts2 = parse_timestamp(user_msgs[-1].get("timestamp"))
                delta_t = abs((ts2 - ts1).total_seconds())
                resolved_deltas = [delta_t]
            else:
                resolved_deltas = []

        # Extract last 3 user prompts
        recent_prompts = [msg.get("content") or msg.get("message") or "" for msg in user_msgs[-3:]]
        # Guarantee the current prompt is included in recent_prompts if missing or new
        if not recent_prompts or (recent_prompts[-1] != user_prompt):
            recent_prompts.append(user_prompt)
            recent_prompts = recent_prompts[-3:]

        # Sentiment lexical analysis
        sentiment_score = self.amygdala.analyze_sentiment(user_prompt)

        # Compute friction F_user
        f_user = self.amygdala.calculate_friction(resolved_deltas, recent_prompts, sentiment_score)

        # Trigger shunting if friction score crosses stress threshold
        if self.amygdala.should_shunt_to_terse(f_user):
            self.terse_mode_active = True
            print("[AMYGDALA] Stress threshold crossed. Shunting to Terse Mode.", flush=True)
            logger.info("[AMYGDALA] Stress threshold crossed. Shunting to Terse Mode.")

        # Stage 2.5: Limbic Personality Quadrant Intercept
        self.active_personality_directives = self.personality_quadrant.resolve_limbic_tone(
            user_prompt=user_prompt,
            current_friction=f_user,
            manual_override_key=manual_override_key
        )

        # 3. Intent Classification (Fast single pass)
        intent = await self.router.classify_intent(user_prompt)
        
        # Extract metadata parameters from the prompt for the pre-flight verification
        # Extract potential dollar amount for financial bounds check
        amount_val = 0.0
        dollar_match = re.search(r'\$\s*(\d+(?:\.\d+)?)|(\d+(?:\.\d+)?)\s*dollars', user_prompt, re.IGNORECASE)
        if dollar_match:
            val_str = dollar_match.group(1) or dollar_match.group(2)
            try:
                amount_val = float(val_str)
            except ValueError:
                pass

        parsed_params = {
            "title": user_prompt,
            "energy_level": "high" if any(kw in user_prompt.lower() for kw in self.guard.high_energy_keywords) else "medium",
            "amount": amount_val
        }

        # 4. Deterministic Pre-Flight Veto (Option A - 0ms LLM Latency)
        # We validate system constraints *before* opening any streaming sockets
        is_valid, violation_reason = self.guard.verify_pre_flight(
            intent_domain=intent.domain.value if hasattr(intent.domain, "value") else str(intent.domain),
            action=intent.action.value if hasattr(intent.action, "value") else str(intent.action),
            params=parsed_params
        )
        
        if not is_valid:
            logger.warning(f"Pre-Flight Veto Triggered: {violation_reason}")
            # Immediately return a clean, static, human-friendly error warning.
            # No LLM tokens generated, no streaming, no "stutter" UX failures.
            return False, f"⚠️ Constraint Guard Veto: {violation_reason}", "MANUAL_REVIEW_REQUIRED", None

        # 5. Database Execution first
        from orchestrator import orchestrator
        from protocol import ActionType
        
        # Execute database command if not chitchat
        if intent.action not in (ActionType.CHITCHAT, "CHITCHAT"):
            try:
                db_result = orchestrator._execute_command(intent)
                grounded_payload = {
                    "success": True,
                    "action": intent.action.value if hasattr(intent.action, "value") else str(intent.action),
                    "domain": intent.domain.value if hasattr(intent.domain, "value") else str(intent.domain),
                    "result": db_result,
                    "intent_payload": intent.payload
                }
            except Exception as e:
                logger.error(f"Database execution error: {e}")
                grounded_payload = {
                    "success": False,
                    "error": str(e)
                }
        else:
            # For chitchat, the grounded payload is the raw user intent payload (which contains "message")
            grounded_payload = {
                "success": True,
                "action": "CHITCHAT",
                "domain": "CHITCHAT",
                "result": intent.payload
            }

        # Add dynamic terse_mode flag to grounded_payload
        if self.terse_mode_active:
            grounded_payload["terse_mode"] = True

        # 6. Overseer Approval
        from constraint_guard import Overseer
        is_approved, oversee_reason = Overseer.approve_payload(grounded_payload)
        if not is_approved:
            logger.warning(f"Overseer Veto Triggered: {oversee_reason}")
            return False, f"⚠️ Overseer Veto: {oversee_reason}", "OVERSEER_VETO", None

        # Register success in cerebellum
        from protocol import ActionType
        if intent.action not in (ActionType.CHITCHAT, "CHITCHAT"):
            domain_str = intent.domain.value if hasattr(intent.domain, "value") else str(intent.domain)
            action_str = intent.action.value if hasattr(intent.action, "value") else str(intent.action)
            self.cerebellum.register_success(user_prompt, domain_str, action_str, parsed_params)

        # 7. Route to Broca's Area (Semantic Translator)
        from broca_translator import BrocaArea
        broca = BrocaArea()
        stream_generator = broca.compile_response_stream(
            grounded_payload, 
            terse_mode=self.terse_mode_active,
            personality_directives=self.active_personality_directives
        )

        return True, stream_generator, intent, self.active_personality_directives.get("coordinates")

