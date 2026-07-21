"""
agent/agent.py - LiveKit WebRTC Real-Time Voice Agent Node

Handles sub-500ms voice interaction, intent processing, and asynchronous
non-blocking database operations on SQLite WAL database (assistant.db).
Supports both LiveKit Agents v0.x and v1.x pipeline models.
"""

import asyncio
import os
import sys
import math
from typing import Annotated, Optional, Dict, Any, List
from dotenv import load_dotenv

# Ensure parent directory is accessible for database imports
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import database

load_dotenv()

# Import LiveKit agents components with version fallback support
from livekit.agents import JobContext, WorkerOptions, JobProcess, llm, cli
try:
    from livekit.agents.voice_assistant import VoiceAssistant
except ImportError:
    try:
        from livekit.agents.voice import Agent as VoiceAssistant
    except ImportError:
        from livekit.agents import Agent as VoiceAssistant

from livekit.plugins import openai, silero

# Compatibility helpers for LiveKit Agents v0.x and v1.x
ai_callable = getattr(llm, "ai_callable", getattr(llm, "function_tool", None))

if hasattr(llm, "FunctionContext"):
    FunctionContextBase = llm.FunctionContext
else:
    class FunctionContextBase:
        def __init__(self, *args, **kwargs):
            pass


# Helper: Fetch active coordinates from the DB
def get_active_coordinates() -> dict:
    try:
        messages = database.get_chat_timeline(limit=10)
        for msg in reversed(messages):
            meta = msg.get("metadata")
            if isinstance(meta, dict) and "coordinates" in meta:
                return meta["coordinates"]
    except Exception as e:
        print(f"Error fetching active coordinates: {e}")
    return {"x": -0.5, "y": -0.5}


# Helper: Resolve voice synthesis options (speed, temperature)
def resolve_voice_synthesis_options(coords: dict) -> dict:
    x = coords.get("x", -0.5)
    y = coords.get("y", -0.5)
    
    # Calculate WPM: 165 - (y * 25)
    wpm = int(165 - (y * 25))
    
    # Calculate Pitch Shift (pitch_factor): 1.0 + (0.08 * x) + (0.04 * y)
    pitch_factor = round(1.0 + (0.08 * x) + (0.04 * y), 2)
    
    # speed ratio based on WPM
    pitch_speed_ratio = round(wpm / 165.0, 2)
    
    # Interpolate temperature based on coordinates
    from personality_quadrant import PERSONALITY_PROFILES
    
    distances = {}
    exact_match_temp = None
    for key, prof in PERSONALITY_PROFILES.items():
        cx = prof["coordinates"]["x"]
        cy = prof["coordinates"]["y"]
        dist = math.sqrt((x - cx)**2 + (y - cy)**2)
        if dist < 1e-5:
            exact_match_temp = prof["base_temperature"]
            break
        distances[key] = dist
        
    if exact_match_temp is not None:
        dynamic_temp = exact_match_temp
    else:
        weights = {k: 1.0 / v for k, v in distances.items()}
        sum_weights = sum(weights.values())
        dynamic_temp = sum(w * PERSONALITY_PROFILES[k]["base_temperature"] for k, w in weights.items()) / sum_weights
        
    dynamic_temp = round(dynamic_temp, 3)
    
    return {
        "speed": pitch_speed_ratio,
        "temperature": dynamic_temp
    }


# Helper: custom TTS wrapper for punctuation damping (stripping commas if y < -0.3)
def make_custom_tts(base_tts, y_val: float):
    original_synthesize = base_tts.synthesize
    original_stream = base_tts.stream
    
    def strip_commas_if_needed(text: str) -> str:
        if y_val < -0.3:
            return text.replace(",", "")
        return text

    def custom_synthesize(text: str, *args, **kwargs):
        modified_text = strip_commas_if_needed(text)
        return original_synthesize(modified_text, *args, **kwargs)
        
    def custom_stream(*args, **kwargs):
        stream_obj = original_stream(*args, **kwargs)
        original_push = stream_obj.push_text
        
        def custom_push(text: str, *args, **kwargs):
            modified_text = strip_commas_if_needed(text)
            return original_push(modified_text, *args, **kwargs)
            
        stream_obj.push_text = custom_push
        return stream_obj
        
    base_tts.synthesize = custom_synthesize
    base_tts.stream = custom_stream
    return base_tts


# Standalone function tools for LiveKit 1.x tools parameter
@ai_callable(description="Add a new task to the user's working state. Use when the user asks to remind them or create a task.")
async def add_fluid_task(
    content: Annotated[str, "The title or description of the task"],
    priority: Annotated[str, "Priority of the task: P1 (High), P2 (Medium), P3 (Low)"] = "P2",
    energy_level: Annotated[str, "Required energy level: low, medium, or high"] = "medium"
) -> str:
    p_map = {"P1": 1, "P2": 2, "P3": 3, "1": 1, "2": 2, "3": 3}
    p_val = p_map.get(priority.upper() if isinstance(priority, str) else "P2", 2)

    def _add_task_sync():
        task_id = database.add_task(
            title=content,
            priority=p_val,
            energy_level=energy_level,
            context_tags=["voice"]
        )
        database.log_telemetry(
            action="add_task_voice",
            task_id=task_id,
            energy_level=energy_level,
            metadata={"source": "livekit_webrtc"}
        )
        return task_id

    task_id = await asyncio.to_thread(_add_task_sync)
    return f"Task '{content}' (Priority {priority}) added successfully with ID #{task_id}."


@ai_callable(description="Retrieve the current list of active or pending tasks from the user's working state.")
async def check_active_tasks() -> str:
    def _get_tasks_sync():
        pending = database.get_tasks(status="pending")
        in_progress = database.get_tasks(status="in_progress")
        return pending + in_progress

    tasks = await asyncio.to_thread(_get_tasks_sync)

    if not tasks:
        return "You currently have no active or pending tasks."

    summaries = []
    for t in tasks[:5]:
        p_label = f"P{t.get('priority', 2)}"
        summaries.append(f"- {t['title']} [{p_label}, {t.get('energy_level', 'medium')} energy]")

    total_count = len(tasks)
    summary_text = "\n".join(summaries)
    if total_count > 5:
        summary_text += f"\n...and {total_count - 5} more tasks."

    return f"Active tasks ({total_count}):\n{summary_text}"


class AssistantTools(FunctionContextBase):
    """
    Class-based tool context for LiveKit 0.x compatibility.
    """

    @ai_callable(description="Add a new task to the user's working state.")
    async def add_fluid_task(self, content: str, priority: str = "P2", energy_level: str = "medium") -> str:
        return await add_fluid_task(content=content, priority=priority, energy_level=energy_level)

    @ai_callable(description="Retrieve the current list of active or pending tasks.")
    async def check_active_tasks(self) -> str:
        return await check_active_tasks()


async def entrypoint(ctx: JobContext):
    await ctx.connect()

    fnc_ctx = AssistantTools()
    model = openai.LLM(model="gpt-4o-mini")

    kwargs = {
        "vad": silero.VAD.load(),
        "stt": openai.STT(),
        "llm": model,
        "tts": openai.TTS(),
    }
    if hasattr(llm, "FunctionContext"):
        kwargs["fnc_ctx"] = fnc_ctx
    else:
        kwargs["tools"] = [add_fluid_task, check_active_tasks]

    assistant = VoiceAssistant(**kwargs)

    @assistant.on("user_speech_committed")
    def on_user_speech(msg: llm.ChatMessage):
        content = msg.content if hasattr(msg, "content") else str(msg)

        # 1. Evaluate incoming prompt against Stage 2.5 Limbic Intercept before generating agent audio
        from personality_quadrant import PersonalityQuadrant
        quad = PersonalityQuadrant()
        
        # Load active coords from database to start transition from previous coordinates
        active_coords = get_active_coordinates()
        quad.current_coords = active_coords
        
        directives = quad.resolve_limbic_tone(user_prompt=content, current_friction=0.0)
        coords = directives.get("coordinates", {"x": -0.5, "y": -0.5})
        
        # 2. Resolve voice synthesis options (speed, temperature)
        voice_opts = resolve_voice_synthesis_options(coords)
        speed = voice_opts["speed"]
        dynamic_temp = voice_opts["temperature"]
        
        # 3. Log acoustic parameters
        pitch_factor = round(1.0 + (0.08 * coords["x"]) + (0.04 * coords["y"]), 2)
        logger.info(f"[VOICE_NODE] Modulating TTS: Speed={speed}x, Pitch={pitch_factor} for Mood Sector ({coords['x']}, {coords['y']})")
        print(f"[VOICE_NODE] Modulating TTS: Speed={speed}x, Pitch={pitch_factor} for Mood Sector ({coords['x']}, {coords['y']})", flush=True)
        
        # 4. Dynamically update voice assistant's TTS and LLM configs
        new_tts = openai.TTS(speed=speed)
        new_tts = make_custom_tts(new_tts, coords.get("y", -0.5))
        new_llm = openai.LLM(model="gpt-4o-mini", temperature=dynamic_temp)
        
        assistant.update_options(tts=new_tts, llm=new_llm)

        def save_user_speech():
            database.add_chat_message(
                content=content,
                source="mobile_voice",
                speaker="user",
                metadata={"icon": "🎙️", "node": "livekit_agent", "coordinates": coords}
            )

        asyncio.create_task(asyncio.to_thread(save_user_speech))

    @assistant.on("agent_speech_committed")
    def on_agent_speech(msg: llm.ChatMessage):
        content = msg.content if hasattr(msg, "content") else str(msg)

        def save_agent_speech():
            database.add_chat_message(
                content=content,
                source="mobile_voice",
                speaker="assistant",
                metadata={"icon": "🤖", "node": "livekit_agent"}
            )

        asyncio.create_task(asyncio.to_thread(save_agent_speech))

    if hasattr(assistant, "start"):
        assistant.start(ctx.room)
    await assistant.say("Voice node activated. How can I assist you today?", allow_interruptions=True)


if __name__ == "__main__":
    # Note: Requires LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET, and OPENAI_API_KEY in environment
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
