"""
distillery.py - Self-Optimization Distillery Service
Analyzes user feedback, flags decisions needing review in event_store,
proposes Jinja2 system prompt optimization hints in proposed_optimizations.json,
and provides Human-in-the-Loop Accept/Reject approval controls.
"""

import os
import json
import uuid
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

import database
import event_store

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("clew.distillery")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROPOSALS_FILE = os.path.join(BASE_DIR, "proposed_optimizations.json")
ACTIVE_HINTS_FILE = os.path.join(BASE_DIR, "active_optimizations.json")

def load_proposals() -> List[Dict[str, Any]]:
    if os.path.exists(PROPOSALS_FILE):
        try:
            with open(PROPOSALS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading proposals: {e}")
    return []

def save_proposals(proposals: List[Dict[str, Any]]) -> None:
    with open(PROPOSALS_FILE, "w", encoding="utf-8") as f:
        json.dump(proposals, f, indent=2)

def load_active_hints() -> Dict[str, List[str]]:
    """
    Returns active approved hints grouped by tier.
    Structure: {"Tier 1 (Specialized Coder)": [...], "Tier 2 (Generalist LifeOS)": [...]}
    """
    if os.path.exists(ACTIVE_HINTS_FILE):
        try:
            with open(ACTIVE_HINTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading active hints: {e}")
    return {"Tier 1 (Specialized Coder)": [], "Tier 2 (Generalist LifeOS)": []}

def save_active_hints(hints_dict: Dict[str, List[str]]) -> None:
    with open(ACTIVE_HINTS_FILE, "w", encoding="utf-8") as f:
        json.dump(hints_dict, f, indent=2)

class DistilleryService:
    """
    Analyzes negative feedback and manages prompt optimization proposals.
    """
    def run_daily_distillation(self) -> Dict[str, Any]:
        logger.info("Running daily feedback distillation job...")
        feedback_items = database.get_intent_feedback(limit=100)
        
        proposals = load_proposals()
        existing_ids = {p.get("id") for p in proposals}
        
        negative_count = 0
        new_proposals_count = 0
        
        for item in feedback_items:
            rating = item.get("user_rating", 5)
            correction = item.get("correction_text") or ""
            cmd_id = item.get("command_id", "")
            
            # Identify negative feedback (rating <= 2 or correction present)
            if rating <= 2 or correction.strip():
                negative_count += 1
                
                # 1. Constraint Pruning: Flag related decision in Event Store
                event_store.record_event(
                    event_type="NEEDS_REVIEW",
                    domain="GOVERNANCE",
                    title=f"Decision Needs Review for Command '{cmd_id}'",
                    description=f"User feedback rating {rating}/5 with correction: '{correction}'",
                    tradeoff_context="Distillery flagged command decision for review based on negative feedback."
                )
                
                # 2. Continuous Standard-Extraction: Log RULE node in Style_Graph
                if correction.strip():
                    import graph_memory
                    std_node_id = f"rule_std_{cmd_id[:8]}" if cmd_id else f"rule_{uuid.uuid4().hex[:8]}"
                    std_label = f"Standard Rule: {correction.strip()}"
                    graph_memory.add_node(
                        node_id=std_node_id,
                        label=std_label,
                        entity_type="RULE",
                        properties={"source_command": cmd_id, "extracted_at": datetime.now().isoformat()}
                    )

                # 3. Format Proposed Optimization Hint
                today_str = datetime.now().strftime("%Y-%m-%d")
                hint_text = f"[AUTO-OPTIMIZATION: Learned from feedback {today_str}] Avoid misclassification: {correction if correction else 'User rated performance poorly.'}"
                
                # Check for existing duplicate proposal for this command
                proposal_id = f"prop_{cmd_id[:8]}" if cmd_id else str(uuid.uuid4())
                if proposal_id not in existing_ids:
                    tier = "Tier 1 (Specialized Coder)" if "code" in correction.lower() or "bug" in correction.lower() else "Tier 2 (Generalist LifeOS)"
                    new_prop = {
                        "id": proposal_id,
                        "command_id": cmd_id,
                        "target_tier": tier,
                        "hint_text": hint_text,
                        "reasoning": f"Negative rating ({rating}/5): {correction}",
                        "status": "pending",
                        "created_at": datetime.now().isoformat()
                    }
                    proposals.append(new_prop)
                    existing_ids.add(proposal_id)
                    new_proposals_count += 1

        save_proposals(proposals)
        logger.info(f"Distillation complete. Evaluated {len(feedback_items)} feedback items, {negative_count} negative, {new_proposals_count} new proposals created.")
        
        return {
            "evaluated_feedback": len(feedback_items),
            "negative_feedback_count": negative_count,
            "new_proposals_created": new_proposals_count,
            "total_pending_proposals": len([p for p in proposals if p.get("status") == "pending"])
        }

    def get_pending_proposals(self) -> List[Dict[str, Any]]:
        proposals = load_proposals()
        return [p for p in proposals if p.get("status") == "pending"]

    def accept_optimization(self, proposal_id: str) -> bool:
        proposals = load_proposals()
        target = None
        for p in proposals:
            if p.get("id") == proposal_id:
                p["status"] = "accepted"
                p["accepted_at"] = datetime.now().isoformat()
                target = p
                break
                
        if not target:
            logger.warning(f"Proposal '{proposal_id}' not found.")
            return False
            
        save_proposals(proposals)
        
        # Append approved hint to active optimizations
        active = load_active_hints()
        tier = target.get("target_tier", "Tier 2 (Generalist LifeOS)")
        if tier not in active:
            active[tier] = []
        if target["hint_text"] not in active[tier]:
            active[tier].append(target["hint_text"])
            
        save_active_hints(active)
        logger.info(f"Accepted optimization proposal '{proposal_id}' for {tier}.")
        return True

    def reject_optimization(self, proposal_id: str) -> bool:
        proposals = load_proposals()
        target = None
        for p in proposals:
            if p.get("id") == proposal_id:
                p["status"] = "rejected"
                p["rejected_at"] = datetime.now().isoformat()
                target = p
                break
                
        if not target:
            logger.warning(f"Proposal '{proposal_id}' not found.")
            return False
            
        save_proposals(proposals)
        logger.info(f"Rejected optimization proposal '{proposal_id}'.")
        return True

# Module singleton instance
distillery = DistilleryService()
Distillery = DistilleryService
