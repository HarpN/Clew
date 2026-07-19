"""
protocol.py - Clew LifeOS Domain Models & Intent Protocols
Defines strict Pydantic schemas for the Intent-Command-Response pattern.
Ensures model-agnostic, safe JSON parsing without direct code execution.
"""

from enum import Enum
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field

class Domain(str, Enum):
    FINANCE = "FINANCE"
    CHORES = "CHORES"
    LOGISTICS = "LOGISTICS"
    PROJECTS = "PROJECTS"
    WELLBEING = "WELLBEING"
    CODE = "CODE"
    CHITCHAT = "CHITCHAT"

class ActionType(str, Enum):
    ADD_TASK = "ADD_TASK"
    COMPLETE_TASK = "COMPLETE_TASK"
    DEFER_TASK = "DEFER_TASK"
    LOG_METRIC = "LOG_METRIC"
    SCHEDULE_EVENT = "SCHEDULE_EVENT"
    QUERY_STATE = "QUERY_STATE"
    CHITCHAT = "CHITCHAT"

class Priority(str, Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"

class EnergyLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class ConstraintMeta(BaseModel):
    energy_cost: EnergyLevel = EnergyLevel.MEDIUM
    budget_cost: float = Field(default=0.0, description="Financial cost associated with action")
    requires_late_night_deferral: bool = False
    frequency_key: Optional[str] = None

class TaskPayload(BaseModel):
    title: str
    description: Optional[str] = None
    priority: Priority = Priority.P2
    energy_level: EnergyLevel = EnergyLevel.MEDIUM
    context_tags: List[str] = Field(default_factory=list)
    due_date: Optional[str] = None
    budget_cost: float = 0.0

class MetricPayload(BaseModel):
    metric_name: str
    metric_value: float
    unit: Optional[str] = None
    notes: Optional[str] = None

class ChitChatPayload(BaseModel):
    message: str
    sentiment: Optional[str] = "neutral"

class IntentCommand(BaseModel):
    command_id: Optional[str] = Field(default=None, description="Unique command identifier UUID")
    goal_tether_id: Optional[str] = Field(default=None, description="Associated goal tether node ID")
    domain: Domain = Field(..., description="Target domain area")
    action: ActionType = Field(..., description="Action to perform")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    reasoning: str = Field(default="", description="LLM classification rationale")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Action-specific parameters")
    constraint_meta: Optional[ConstraintMeta] = Field(default_factory=ConstraintMeta)

class CommandResult(BaseModel):
    command_id: Optional[str] = None
    goal_tether_id: Optional[str] = None
    success: bool
    domain: Domain
    action: ActionType
    message: str
    data: Optional[Dict[str, Any]] = None
    latency_ms: float = 0.0
    blocked_by_constraint: bool = False
    constraint_reason: Optional[str] = None
    model_used: Optional[str] = None
    tier: Optional[str] = None
