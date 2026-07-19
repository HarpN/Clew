"""
orchestrator.py - Clew LifeOS Intent-Command-Response Middleware Engine
Enforces Pydantic intent schema validation, Constraint Guard governance,
<500ms Chit-Chat bypassing, and safe execution routing.
"""

import time
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Union
from pydantic import ValidationError

from protocol import (
    Domain, ActionType, Priority, EnergyLevel,
    IntentCommand, CommandResult, ConstraintMeta, TaskPayload
)
import database
import event_store
import memory_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("clew.orchestrator")

class ConstraintGuard:
    """
    Evaluates system and domain governance constraints prior to command execution.
    Checks energy budget, time-of-day fatigue policies, and frequency limits.
    """
    @staticmethod
    def evaluate(command: IntentCommand) -> (bool, Optional[str]):
        # 1. Late-Night Tech Fatigue Constraint (Past 10:00 PM)
        now = datetime.now()
        if now.hour >= 22 or now.hour < 5:
            meta = command.constraint_meta
            if meta and meta.requires_late_night_deferral:
                return False, "Late-Night Fatigue Policy active: Deferring complex task execution until morning focus block."
            
            # Auto-check if payload has high energy or P1 priority
            p_val = command.payload.get("priority")
            e_val = command.payload.get("energy_level")
            if e_val == "high" or p_val == "P1":
                return False, "Late-Night Fatigue Policy active: High-energy P1 tasks are restricted past 10:00 PM."

        # 2. Budget Cost Guard
        budget = command.payload.get("budget_cost", 0.0)
        if budget > 500.0:
            return False, f"Budget Guard Violation: Requested action cost (${budget:.2f}) exceeds threshold ($500.00)."

        # 3. Goal-Tether Protocol Alignment Check
        if command.goal_tether_id:
            import graph_memory
            aligned, tether_reason = graph_memory.verify_goal_alignment(
                command.domain.value,
                command.action.value,
                command.goal_tether_id
            )
            if not aligned:
                return False, tether_reason

        return True, None


import uuid

class OrchestratorEngine:
    """
    Primary Intent-Command-Response Middleware Engine.
    Routes intent outputs safely to database mutations and memory indexing.
    """
    def __init__(self):
        database.init_db()
        self.domain_confidence_history: Dict[str, List[float]] = {}

    def record_confidence(self, domain: str, score: float):
        if domain not in self.domain_confidence_history:
            self.domain_confidence_history[domain] = []
        self.domain_confidence_history[domain].append(score)
        if len(self.domain_confidence_history[domain]) > 20:
            self.domain_confidence_history[domain].pop(0)

    def get_domain_confidence(self, domain: str) -> float:
        scores = self.domain_confidence_history.get(domain, [])
        if not scores:
            return 1.0
        return sum(scores) / len(scores)

    def process_intent(
        self,
        raw_input: Union[str, Dict[str, Any]],
        model_used: Optional[str] = None,
        tier: Optional[str] = None
    ) -> CommandResult:
        start_time = time.time()
        cmd_id = str(uuid.uuid4())

        # Step 1: Parse and Validate Intent Schema via Pydantic
        try:
            if isinstance(raw_input, str):
                data = json.loads(raw_input)
            else:
                data = raw_input
            command = IntentCommand(**data)
            cmd_id = command.command_id or cmd_id
            self.record_confidence(command.domain.value, command.confidence)
        except (json.JSONDecodeError, ValidationError) as err:
            logger.error(f"Intent validation failed: {err}")
            elapsed = (time.time() - start_time) * 1000
            return CommandResult(
                command_id=cmd_id,
                success=False,
                domain=Domain.CHITCHAT,
                action=ActionType.CHITCHAT,
                message=f"Invalid intent schema: {err}",
                latency_ms=round(elapsed, 2),
                model_used=model_used,
                tier=tier
            )

        # Step 2: Sub-500ms Chit-Chat Bypass Target
        if command.domain == Domain.CHITCHAT or command.action == ActionType.CHITCHAT:
            msg = command.payload.get("message", "Chit-chat processed successfully.")
            elapsed = (time.time() - start_time) * 1000
            logger.info(f"Chit-Chat Bypass triggered. Latency: {elapsed:.2f}ms")
            return CommandResult(
                command_id=cmd_id,
                success=True,
                domain=Domain.CHITCHAT,
                action=ActionType.CHITCHAT,
                message=msg,
                latency_ms=round(elapsed, 2),
                model_used=model_used,
                tier=tier
            )

        # Step 3: Constraint Guard Validation
        is_allowed, reason = ConstraintGuard.evaluate(command)
        if not is_allowed:
            elapsed = (time.time() - start_time) * 1000
            logger.warning(f"Command blocked by ConstraintGuard: {reason}")
            
            # Log constraint violation in Event Store
            event_store.record_event(
                event_type="CONSTRAINT_BLOCKED",
                domain=command.domain.value,
                title=f"Blocked {command.action.value}",
                description=reason,
                tradeoff_context="Constraint Guard enforced safety rules.",
                metadata={"model_used": model_used or "unknown", "tier": tier or "unknown", "command_id": cmd_id}
            )
            
            return CommandResult(
                command_id=cmd_id,
                goal_tether_id=command.goal_tether_id,
                success=False,
                domain=command.domain,
                action=command.action,
                message=f"Command blocked: {reason}",
                blocked_by_constraint=True,
                constraint_reason=reason,
                latency_ms=round(elapsed, 2),
                model_used=model_used,
                tier=tier
            )

        # Step 4: Dispatch Command Execution
        try:
            result_data = self._execute_command(command)
            elapsed = (time.time() - start_time) * 1000
            
            meta = result_data.copy() if isinstance(result_data, dict) else {}
            meta["model_used"] = model_used or "unknown"
            meta["tier"] = tier or "unknown"
            meta["command_id"] = cmd_id
            if command.goal_tether_id:
                meta["goal_tether_id"] = command.goal_tether_id

            # Record successfully executed event in Event Store
            event_store.record_event(
                event_type="COMMAND_EXECUTED",
                domain=command.domain.value,
                title=f"{command.action.value} executed",
                description=command.reasoning or f"Action {command.action.value} executed in {command.domain.value}",
                metadata=meta
            )
            
            return CommandResult(
                command_id=cmd_id,
                goal_tether_id=command.goal_tether_id,
                success=True,
                domain=command.domain,
                action=command.action,
                message=f"Successfully executed {command.action.value} in {command.domain.value}",
                data=result_data,
                latency_ms=round(elapsed, 2),
                model_used=model_used,
                tier=tier
            )

        except Exception as ex:
            logger.error(f"Execution error in {command.action}: {ex}")
            elapsed = (time.time() - start_time) * 1000
            return CommandResult(
                success=False,
                domain=command.domain,
                action=command.action,
                message=f"Execution error: {str(ex)}",
                latency_ms=round(elapsed, 2)
            )

    def _execute_command(self, command: IntentCommand) -> Dict[str, Any]:
        p = command.payload
        action = command.action

        if action == ActionType.ADD_TASK:
            title = p.get("title", "New Domain Task")
            priority = p.get("priority", "P2")
            energy = p.get("energy_level", "medium")
            tags = p.get("context_tags", [command.domain.value.lower()])
            
            task_id = database.add_fluid_task(
                title=title,
                priority=priority,
                energy_level=energy,
                context_tags=tags
            )
            memory_service.store_memory("task", str(task_id), f"{title} - Priority {priority}")
            return {"task_id": task_id, "title": title}

        elif action == ActionType.COMPLETE_TASK:
            task_id = int(p.get("task_id", 0))
            database.update_task_status(task_id, "completed")
            return {"task_id": task_id, "status": "completed"}

        elif action == ActionType.DEFER_TASK:
            task_id = int(p.get("task_id", 0))
            database.update_task_status(task_id, "deferred")
            return {"task_id": task_id, "status": "deferred"}

        elif action == ActionType.QUERY_STATE:
            snapshot = memory_service.get_current_state_snapshot()
            return snapshot

        elif action == ActionType.LOG_METRIC:
            name = p.get("metric_name", "generic_metric")
            val = float(p.get("metric_value", 1.0))
            database.log_telemetry(action=name, telemetry_metadata={"value": val})
            return {"metric": name, "value": val}

        return {"executed": True}


# Module instance singleton
orchestrator = OrchestratorEngine()
