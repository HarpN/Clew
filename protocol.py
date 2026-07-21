"""
protocol.py - Clew LifeOS Domain Models & Intent Protocols
Defines strict Pydantic schemas for the Intent-Command-Response pattern.
Ensures model-agnostic, safe JSON parsing without direct code execution.
"""

import struct
import hashlib
from enum import Enum, IntEnum, IntFlag
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field

class HivemindMessageType(IntEnum):
    DELTA = 0x01
    HEARTBEAT = 0x02
    SYNC = 0x03

class HivemindFlags(IntFlag):
    NONE = 0x0000
    ENCRYPTED = 0x0001
    COMPRESSED = 0x0002

HIVEMIND_MAGIC = b"HIVE"  # 0x48 0x49 0x56 0x45
HIVEMIND_VERSION = 0x01
HIVEMIND_HEADER_SIZE = 128
MAX_PAYLOAD_CEILING = 16 * 1024 * 1024  # Strict 16MB ceiling (16,777,216 bytes)

def calculate_crc32c(data: bytes) -> int:
    """Calculates CRC32C (Castagnoli 0x82F63B78 polynomial)."""
    try:
        import crc32c
        return crc32c.crc32c(data)
    except ImportError:
        pass
    POLY = 0x82F63B78
    crc = 0xFFFFFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ (POLY if (crc & 1) else 0)
    return crc ^ 0xFFFFFFFF

def calculate_blake3_digest(payload: bytes) -> bytes:
    """Calculates 32-byte BLAKE3 payload hash with blake2b fallback."""
    try:
        import blake3
        return blake3.blake3(payload).digest()
    except ImportError:
        pass
    return hashlib.blake2b(payload, digest_size=32).digest()


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

class ComputeTier(str, Enum):
    TIER_1_LOCAL_BRAIN_STEM = "Tier 1: Local Brain Stem (Primary Orchestrator)"
    TIER_2_CLOUD_WARM = "Tier 2: Cloud Warm (Active Reasoning)"
    TIER_3A_CLOUD_COLD_BATCH = "Tier 3A: Cloud Cold (Async Batching)"
    TIER_3B_CLOUD_COLD_SANDBOX = "Tier 3B: Cloud Cold (Sandboxed Execution)"

class SyncCadenceState(str, Enum):
    ACTIVE_SESSION = "ACTIVE_SESSION"
    IDLE_BACKGROUND = "IDLE_BACKGROUND"
    PRE_SLEEP_FLUSH = "PRE_SLEEP_FLUSH"

class HeartbeatPayload(BaseModel):
    node_id: str = Field(default="clew-primary-node")
    sequence_nonce: int = Field(default=0)
    hlc_timestamp: float = Field(default=0.0, description="Hybrid Logical Clock timestamp")
    status_flags: Dict[str, bool] = Field(default_factory=lambda: {"ready": True, "idle": False, "cloud_promoted": False})

    def to_compact_bytes(self) -> bytes:
        import json
        data = self.model_dump()
        data["hlc_timestamp"] = round(data["hlc_timestamp"], 4)
        raw_bytes = json.dumps(data, separators=(',', ':')).encode('utf-8')
        if len(raw_bytes) > 128:
            compact_flags = {
                "r": data["status_flags"].get("ready", True),
                "i": data["status_flags"].get("idle", False),
                "p": data["status_flags"].get("cloud_promoted", False)
            }
            data["status_flags"] = compact_flags
            raw_bytes = json.dumps(data, separators=(',', ':')).encode('utf-8')
        if len(raw_bytes) < 64:
            raw_bytes = raw_bytes + b' ' * (64 - len(raw_bytes))
        return raw_bytes

    @classmethod
    def from_compact_bytes(cls, raw: bytes) -> "HeartbeatPayload":
        import json
        text = raw.decode('utf-8').strip()
        obj = json.loads(text)
        flags = obj.get("status_flags", {})
        if "r" in flags:
            obj["status_flags"] = {
                "ready": bool(flags.get("r", True)),
                "idle": bool(flags.get("i", False)),
                "cloud_promoted": bool(flags.get("p", False))
            }
        return cls(**obj)

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

class HivemindFrame(BaseModel):
    magic: bytes = Field(default=HIVEMIND_MAGIC)
    version: int = Field(default=HIVEMIND_VERSION)
    msg_type: HivemindMessageType = Field(default=HivemindMessageType.DELTA)
    flags: int = Field(default=HivemindFlags.NONE)
    sequence_nonce: int = Field(default=0)
    hlc_timestamp: int = Field(default=0)
    payload_len: int = Field(default=0)
    header_crc32c: int = Field(default=0)
    signature: bytes = Field(default_factory=lambda: b'\x00' * 64)
    payload_digest: bytes = Field(default_factory=lambda: b'\x00' * 32)
    payload: bytes = Field(default_factory=bytes)

    def pack_header(self) -> bytes:
        """Packs the 128-byte Hivemind header with CRC32C computation."""
        if len(self.magic) != 4:
            raise ValueError("Magic must be exactly 4 bytes")
        if len(self.signature) != 64:
            raise ValueError("Signature must be exactly 64 bytes")
        if len(self.payload_digest) != 32:
            raise ValueError("Payload digest must be exactly 32 bytes")
        if self.payload_len > MAX_PAYLOAD_CEILING:
            raise ValueError(f"Payload length exceeds 16MB ceiling: {self.payload_len} > {MAX_PAYLOAD_CEILING}")

        header_pre_crc = struct.pack(
            "<4sBBHQQI",
            self.magic,
            self.version,
            int(self.msg_type),
            int(self.flags),
            self.sequence_nonce,
            self.hlc_timestamp,
            self.payload_len
        )
        self.header_crc32c = calculate_crc32c(header_pre_crc)

        header_bytes = struct.pack(
            "<4sBBHQQII64s32s",
            self.magic,
            self.version,
            int(self.msg_type),
            int(self.flags),
            self.sequence_nonce,
            self.hlc_timestamp,
            self.payload_len,
            self.header_crc32c,
            self.signature,
            self.payload_digest
        )
        assert len(header_bytes) == HIVEMIND_HEADER_SIZE
        return header_bytes

    def pack(self) -> bytes:
        """Packs full binary frame (128-byte header + variable payload)."""
        self.payload_len = len(self.payload)
        if self.payload_digest == b'\x00' * 32 and self.payload:
            self.payload_digest = calculate_blake3_digest(self.payload)
        header = self.pack_header()
        return header + self.payload

    @classmethod
    def unpack_header(cls, header_bytes: bytes) -> "HivemindFrame":
        """Unpacks and validates a 128-byte Hivemind header."""
        if len(header_bytes) < HIVEMIND_HEADER_SIZE:
            raise ValueError(f"Header size must be at least 128 bytes, got {len(header_bytes)}")

        magic, version, msg_type, flags, sequence_nonce, hlc_timestamp, payload_len, header_crc32c, signature, payload_digest = struct.unpack(
            "<4sBBHQQII64s32s",
            header_bytes[:128]
        )

        if magic != HIVEMIND_MAGIC:
            raise ValueError(f"Invalid magic bytes: {magic!r}, expected {HIVEMIND_MAGIC!r}")
        if version != HIVEMIND_VERSION:
            raise ValueError(f"Unsupported protocol version: {version:#x}, expected {HIVEMIND_VERSION:#x}")
        if payload_len > MAX_PAYLOAD_CEILING:
            raise ValueError(f"Payload length exceeds strict 16MB ceiling: {payload_len} > {MAX_PAYLOAD_CEILING}")

        header_pre_crc = header_bytes[:28]
        expected_crc = calculate_crc32c(header_pre_crc)
        if header_crc32c != expected_crc:
            raise ValueError(f"Header CRC32C mismatch: got {header_crc32c:#010x}, expected {expected_crc:#010x}")

        return cls(
            magic=magic,
            version=version,
            msg_type=HivemindMessageType(msg_type),
            flags=flags,
            sequence_nonce=sequence_nonce,
            hlc_timestamp=hlc_timestamp,
            payload_len=payload_len,
            header_crc32c=header_crc32c,
            signature=signature,
            payload_digest=payload_digest
        )

    @classmethod
    def unpack(cls, raw_frame: bytes) -> "HivemindFrame":
        """Unpacks full 128-byte header and payload, validating integrity."""
        frame = cls.unpack_header(raw_frame[:128])
        payload = raw_frame[128:128 + frame.payload_len]
        if len(payload) != frame.payload_len:
            raise ValueError(f"Truncated payload: expected {frame.payload_len} bytes, got {len(payload)}")

        if payload:
            actual_digest = calculate_blake3_digest(payload)
            if frame.payload_digest != b'\x00' * 32 and frame.payload_digest != actual_digest:
                raise ValueError("Payload digest mismatch (BLAKE3 validation failed)")

        frame.payload = payload
        return frame

