import datetime
import logging
from typing import Tuple, Dict, Any
from database import get_db_connection, dialect

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("clew.constraints")

class ConstraintGuard:
    """
    Sub-millisecond, deterministic Python constraint validation layer.
    Acts as the Left Hemisphere's 'Logical Guard' before starting any LLM generation.
    """
    def __init__(self):
        # High-energy task list triggers
        self.high_energy_keywords = ["refactor", "debug", "compile", "deploy", "migrate", "optimize", "pool"]

    def verify_pre_flight(self, intent_domain: str, action: str, params: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Runs comprehensive deterministic checks. Returns (is_valid, reason).
        """
        logger.info(f"Running pre-flight checks for domain: {intent_domain}, action: {action}")
        
        # Check 1: Late-Night Fatigue Standard (Temporal Check)
        is_valid, reason = self._check_late_night_fatigue(intent_domain, action, params)
        if not is_valid:
            return False, reason

        # Check 2: Financial/Budget Boundary Guard
        is_valid, reason = self._check_financial_bounds(intent_domain, action, params)
        if not is_valid:
            return False, reason

        # Check 3: Redundant Task Check (State Duplication Check)
        is_valid, reason = self._check_duplicate_tasks(intent_domain, action, params)
        if not is_valid:
            return False, reason

        return True, ""

    def _check_late_night_fatigue(self, domain: str, action: str, params: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Enforces late-night cognitive preservation rules (0ms overhead).
        Blocks complex deployments, migrations, or high-energy tasks past 10:00 PM.
        """
        current_time = datetime.datetime.now().time()
        cutoff_time = datetime.time(22, 0, 0) # 10:00 PM
        
        # Check current time against cutoff
        if current_time >= cutoff_time:
            # Check if task description or domain represents a high-energy technical workload
            task_title = params.get("title", "").lower()
            is_high_energy = (
                params.get("energy_level") == "high" or
                any(kw in task_title for kw in self.high_energy_keywords) or
                domain in ["CODER", "INFRASTRUCTURE", "CHORES"]
            )
            
            if is_high_energy:
                return False, "Late-Night Fatigue Policy active: High-energy tasks are restricted past 10:00 PM to prevent cognitive fatigue errors."
                
        return True, ""

    def _check_financial_bounds(self, domain: str, action: str, params: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Enforces deterministic financial safety rails directly from database values.
        """
        if domain == "FINANCE" and action == "ADD_TRANSACTION":
            amount = float(params.get("amount", 0.0))
            category = params.get("category", "general")
            max_limit = 500.00
            
            if amount > max_limit:
                return False, f"Financial Transaction Guard veto: Transaction amount ${amount:.2f} exceeds standard safety limit of ${max_limit:.2f} for '{category}'."
                
        return True, ""

    def _check_duplicate_tasks(self, domain: str, action: str, params: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Prevents adding task state duplicates, stopping the LLM from creating redundant work items.
        """
        if "ADD_TASK" in action or action == "ADD_TASK":
            title = params.get("title", "").strip()
            if not title:
                return True, ""
                
            sql = "SELECT COUNT(*) FROM tasks WHERE LOWER(title) = LOWER(?) AND status = 'pending';"
            
            try:
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(dialect.format_query(sql), (title,))
                    count = cursor.fetchone()[0]
                    
                    if count > 0:
                        return False, f"Task State Redundancy: Task '{title}' already exists in your active pending list."
            except Exception as e:
                logger.error(f"Error querying task duplication bounds: {e}")
                
        return True, ""


class Overseer:
    """
    Evaluates and approves the raw grounded data payload before it is routed to Broca's Area.
    """
    @staticmethod
    def approve_payload(payload: Any) -> Tuple[bool, str]:
        if not payload:
            return False, "Payload is empty or null."
        if isinstance(payload, dict):
            if payload.get("success") is False:
                return False, f"Factual execution failed: {payload.get('error', 'unknown error')}"
        return True, ""

