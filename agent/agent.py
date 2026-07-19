"""
agent/agent.py - LiveKit WebRTC Real-Time Voice Agent Node

Handles sub-500ms voice interaction, intent processing, and asynchronous
non-blocking database operations on SQLite WAL database (assistant.db).
Supports both LiveKit Agents v0.x and v1.x pipeline models.
"""

import asyncio
import os
import sys
from typing import Annotated, Optional
from dotenv import load_dotenv

# Ensure parent directory is accessible for database imports
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import database

load_dotenv()

# Import LiveKit agents components with version fallback support
from livekit.agents import JobContext, WorkerOptions, JobProcess, llm
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


# Standalone function tools for LiveKit 1.x tools parameter
@ai_callable(description="Add a new task to the user's working state. Use when the user asks to remind them or create a task.")
async def add_fluid_task(
    content: Annotated[str, llm.TypeInfo(description="The title or description of the task")],
    priority: Annotated[str, llm.TypeInfo(description="Priority of the task: P1 (High), P2 (Medium), P3 (Low)")] = "P2",
    energy_level: Annotated[str, llm.TypeInfo(description="Required energy level: low, medium, or high")] = "medium"
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

        def save_user_speech():
            database.add_chat_message(
                content=content,
                source="mobile_voice",
                speaker="user",
                metadata={"icon": "🎙️", "node": "livekit_agent"}
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
    JobProcess.run(WorkerOptions(entrypoint_fnc=entrypoint))
