"""
ui/app.py - Desktop Command Center Streamlit Interface
Renders the modern Clew Command Center desktop workspace, implementing split-screen
dashboard, real-time interactive tasks, and asynchronous token-by-token streaming.
"""

import os
import sys
import streamlit as st
import asyncio
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

# Ensure root repository directory is accessible for imports
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import database
import graph_memory
from router import router, ModelRouter, GENERALIST_MODEL, OLLAMA_OPTIONS, ModelTier
from brain_orchestrator import CognitiveBrain

# Initialize DB on load
database.init_db()

# Page configuration
st.set_page_config(
    page_title="Clew Command Center",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Dark theme & styling configuration
st.markdown("""
<style>
    /* Global Background and Colors */
    .stApp {
        background-color: #0F172A;
        color: #F8FAFC;
    }
    
    /* Neon gradients & header styling */
    h1, h2, h3 {
        color: #818CF8 !important;
        font-weight: 700 !important;
    }
    
    /* System Status Badges */
    .status-badge {
        display: inline-block;
        background: #1E293B;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 6px 12px;
        font-size: 0.85em;
        font-weight: 600;
        margin-right: 8px;
        color: #38BDF8;
    }
    
    /* Priority color tags */
    .priority-p1 {
        color: #EF4444;
        font-weight: bold;
    }
    .priority-p2 {
        color: #F59E0B;
        font-weight: bold;
    }
    .priority-p3 {
        color: #10B981;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

def make_sync_generator(async_gen):
    """
    Safely bridges an async generator into a synchronous python generator
    compatible with st.write_stream().
    """
    loop = asyncio.new_event_loop()
    try:
        while True:
            try:
                chunk = loop.run_until_complete(async_gen.__anext__())
                yield chunk
            except StopAsyncIteration:
                break
    finally:
        loop.close()

# Initialize cognitive components
brain = CognitiveBrain()

if "manual_limbic_override" not in st.session_state:
    st.session_state["manual_limbic_override"] = "AUTO (Dynamic)"

if "active_limbic_coordinates" not in st.session_state:
    st.session_state["active_limbic_coordinates"] = {"x": -0.5, "y": -0.5}

OVERRIDE_MAP = {
    "AUTO (Dynamic)": None,
    "Warm Companion": "WARM_PEER",
    "Dry System Analyst": "DRY_ANALYST",
    "Socratic Instructor": "SOCRATIC_TEACHER",
    "Blunt Code Critic": "BLUNT_CRITIC"
}

# Sidebar: System status, Goal Tether, and Strategy locks
with st.sidebar:
    st.image("https://raw.githubusercontent.com/google/material-design-icons/master/png/action/settings/db_light/2x/web_settings_db_light_48dp.png", width=48)
    st.title("Clew LifeOS")
    st.caption("Active Router: qwen2.5:3b-instruct (RTX GPU)")
    
    st.divider()
    
    # 1. Goal-Tether Selection
    st.subheader("🎯 Active Goal Tether")
    goals = graph_memory.get_nodes(entity_type="GOAL")
    if not goals:
        # Pre-seed default chores goal if none exists
        graph_memory.add_node("goal_tether_chores", "Manage daily chores", "GOAL")
        goals = graph_memory.get_nodes(entity_type="GOAL")
        
    goal_options = {g.get("node_id"): g.get("label", g.get("node_id")) for g in goals}
    selected_tether_id = st.selectbox(
        "Direct routing alignment target:",
        options=list(goal_options.keys()),
        format_func=lambda x: goal_options[x]
    )
    
    st.divider()
    
    # 2. System Status
    st.subheader("⚙️ System Status")
    wal_mode = database.check_wal_mode()
    st.markdown(f"<span class='status-badge'>DB Mode: {wal_mode.upper()}</span>", unsafe_allow_html=True)
    
    # Active strategy count
    adaptations = database.get_behavioral_adaptations(only_active=True)
    st.markdown(f"<span class='status-badge'>Rules Locked: {len(adaptations)}</span>", unsafe_allow_html=True)

# Main Workspace Layout: Columns [6, 6] split-screen
col_left, col_right = st.columns([1, 1])

# --- LEFT COLUMN: Active Working State ---
with col_left:
    st.header("⚡ Active Working State")
    
    # Create Task Expander
    with st.expander("➕ Create New Task", expanded=False):
        with st.form("new_task_form", clear_on_submit=True):
            title = st.text_input("Task Title*", placeholder="e.g. Review database indexing")
            description = st.text_area("Description")
            c_p, c_e = st.columns(2)
            with c_p:
                priority = st.selectbox("Priority", ["P1", "P2", "P3"], index=1)
            with c_e:
                energy = st.selectbox("Energy Level", ["low", "medium", "high"], index=1)
            due = st.text_input("Due Date (Optional)", placeholder="YYYY-MM-DD")
            
            submitted = st.form_submit_button("Add Task")
            if submitted and title:
                p_map = {"P1": 1, "P2": 2, "P3": 3}
                p_val = p_map.get(priority, 2)
                # Map domain from selected goal tether
                tag = selected_tether_id.lower().replace("goal_tether_", "")
                database.add_task(
                    title=title,
                    description=description,
                    priority=p_val,
                    energy_level=energy,
                    context_tags=[tag],
                    due_date=due if due else None
                )
                st.success(f"Added task: '{title}'")
                st.rerun()

    # Task Manager Filter & Listing
    st.subheader("📋 Task Manager")
    
    # Filter tools
    f_p, f_e, f_s = st.columns(3)
    with f_p:
        priority_filter = st.selectbox("Filter Priority", ["All", "P1", "P2", "P3"])
    with f_e:
        energy_filter = st.selectbox("Filter Energy", ["All", "low", "medium", "high"])
    with f_s:
        status_filter = st.selectbox("Filter Status", ["pending", "in_progress", "completed", "deferred"])
        
    tasks = database.get_tasks(status=status_filter)
    
    # Perform in-memory filter matching
    filtered_tasks = []
    for t in tasks:
        p_label = f"P{t.get('priority', 2)}"
        if priority_filter != "All" and p_label != priority_filter:
            continue
        if energy_filter != "All" and t.get("energy_level") != energy_filter:
            continue
        filtered_tasks.append(t)
        
    if filtered_tasks:
        for t in filtered_tasks:
            p_label = f"P{t.get('priority', 2)}"
            p_class = "priority-p1" if p_label == "P1" else ("priority-p2" if p_label == "P2" else "priority-p3")
            
            with st.container(border=True):
                st.markdown(f"**{t['title']}** (<span class='{p_class}'>{p_label}</span>)", unsafe_allow_html=True)
                if t.get("description"):
                    st.write(t["description"])
                st.caption(f"Energy: `{t.get('energy_level')}` | Target: `{t.get('due_date') or 'none'}`")
                
                # Mutation buttons
                b_c1, b_c2 = st.columns(2)
                with b_c1:
                    if st.button("✔️ Complete", key=f"comp_{t['id']}", use_container_width=True):
                        database.update_task_status(t['id'], 'completed')
                        st.rerun()
                with b_c2:
                    if st.button("⏳ Defer", key=f"defer_{t['id']}", use_container_width=True):
                        database.update_task_status(t['id'], 'deferred')
                        st.rerun()
    else:
        st.info("No matching tasks found.")

    # Focus Blocks
    st.divider()
    st.subheader("⏱️ Focus Blocks")
    blocks = database.get_focus_blocks()
    if blocks:
        for b in blocks:
            with st.container(border=True):
                st.markdown(f"**{b['title']}**")
                st.caption(f"Time: {b['start_time']} - {b['end_time']} | Status: `{b['status']}`")
    else:
        st.caption("No focus blocks scheduled.")

    # Proactive Logistics
    st.divider()
    st.subheader("📦 Proactive Logistics")
    logistics = database.get_pending_logistics()
    if logistics:
        for l in logistics:
            with st.container(border=True):
                st.markdown(f"**{l['title']}**")
                st.write(l.get("details", ""))
                st.caption(f"Target: {l.get('target_date')} | Rule: `{l.get('auto_trigger_rule')}`")
                if st.button("Resolve", key=f"resolve_log_{l['id']}", use_container_width=True):
                    database.update_logistic_status(l['id'], 'resolved')
                    st.rerun()
    else:
        st.caption("No pending proactive logistics.")

def execute_tool_call(prompt_to_run):
    """
    Executes a high-impact command that was intercepted and approved by the user.
    """
    deltas = st.session_state.get("typing_deltas", [])
    override_key = OVERRIDE_MAP.get(st.session_state.get("manual_limbic_override", "AUTO (Dynamic)"))
    is_success, friendly_res, intent_or_reason, coords = asyncio.run(
        brain.process_thought_cycle(
            prompt_to_run, 
            selected_tether_id, 
            keystroke_deltas=deltas,
            manual_override_key=override_key
        )
    )
    if coords:
        st.session_state["active_limbic_coordinates"] = coords
    st.session_state["terse_mode_active"] = getattr(brain, "terse_mode_active", False)
    return friendly_res

# --- RIGHT COLUMN: Unified Chat Timeline ---
with col_right:
    st.header("🎙️ Unified Chat Timeline")
    
    st.selectbox(
        "Limbic Mood Lock",
        options=["AUTO (Dynamic)", "Warm Companion", "Dry System Analyst", "Socratic Instructor", "Blunt Code Critic"],
        key="manual_limbic_override"
    )
    
    # Scrollable chat messages
    if st.session_state.get("terse_mode_active", False):
        st.markdown("""
            <div style="background-color: #3B0764; border: 1px solid #7C3AED; padding: 8px 12px; border-radius: 8px; margin-bottom: 12px; font-size: 0.9em; color: #F5F3FF;">
                🛡️ <b>Terse Mode active:</b> Silencing advice to minimize cognitive load.
            </div>
        """, unsafe_allow_html=True)

    # [SAFETY GUARD] Human-In-The-Loop (HITL) Interceptor
    # Protects against destructive mutations or permanent rule rewrites
    if "pending_mutation" in st.session_state and st.session_state.pending_mutation:
        st.warning("⚠️ High-Impact Operation Pending Approval")
        st.info(f"Command: {st.session_state.pending_mutation_text}")
        col_yes, col_no = st.columns(2)
        if col_yes.button("Confirm & Commit"):
            prompt_to_run = st.session_state.pending_mutation
            
            # Clear pending state and set bypass flag
            st.session_state.pending_mutation = None
            st.session_state.pending_mutation_text = ""
            st.session_state["bypass_hitl"] = True
            
            # Display and persist user message
            st.chat_message("user", avatar="👤").markdown(prompt_to_run)
            database.add_chat_message(content=prompt_to_run, source="desktop_text", speaker="user")
            
            friendly_res = execute_tool_call(prompt_to_run)
            
            # Handle response
            import types
            if isinstance(friendly_res, (types.AsyncGeneratorType, types.GeneratorType)) or hasattr(friendly_res, "__anext__"):
                with st.chat_message("assistant", avatar="🤖"):
                    try:
                        final_response = st.write_stream(make_sync_generator(friendly_res))
                        database.add_chat_message(content=final_response, source="agent", speaker="agent")
                    except Exception as stream_err:
                        st.error(f"⚠️ {str(stream_err)}")
            else:
                if isinstance(friendly_res, str):
                    reply_text = friendly_res
                elif hasattr(friendly_res, "message"):
                    reply_text = friendly_res.message
                else:
                    reply_text = str(friendly_res)
                with st.chat_message("assistant", avatar="🤖"):
                    st.markdown(reply_text)
                database.add_chat_message(content=reply_text, source="agent", speaker="agent")
            
            if "bypass_hitl" in st.session_state:
                del st.session_state["bypass_hitl"]
            st.success("Transaction committed safely.")
            st.rerun()
            
        if col_no.button("Abort"):
            st.session_state.pending_mutation = None
            st.session_state.pending_mutation_text = ""
            st.error("Operation cancelled by user.")
            st.rerun()

    messages = database.get_chat_timeline(limit=30)
    
    # Render historical messages
    for msg in messages:
        speaker = msg.get("speaker", "user")
        content = msg.get("content") or msg.get("message") or ""
        icon = msg.get("metadata", {}).get("icon", None)
        
        if speaker == "user":
            avatar = "👤" if not icon else icon
            st.chat_message("user", avatar=avatar).markdown(content)
        else:
            avatar = "🤖" if not icon else icon
            st.chat_message("assistant", avatar=avatar).markdown(content)
            
    # File uploader for visual attachments (Horizon 3)
    uploaded_file = st.file_uploader("Attach screenshot or diagram", type=["png", "jpg", "jpeg", "webp"], key="visual_attachment")
    
    # Chat Input processing
    if prompt := st.chat_input("Tell Clew to execute or add something..."):
        # Check if action is high impact (such as massive table updates or custom system modifications)
        # and hold for manual validation
        is_high_impact = any(kw in prompt.lower() for kw in ["delete all tasks", "drop table", "alter adaptation"])
        
        if is_high_impact and not st.session_state.get("bypass_hitl", False):
            st.session_state.pending_mutation = prompt
            st.session_state.pending_mutation_text = prompt
            st.rerun()
        else:
            # Calculate typing interval delta
            current_time = datetime.now()
            if "last_submission_time" in st.session_state:
                try:
                    last_time = datetime.fromisoformat(st.session_state["last_submission_time"])
                    interval = (current_time - last_time).total_seconds()
                    st.session_state["typing_deltas"] = [interval]
                except Exception:
                    st.session_state["typing_deltas"] = []
            else:
                st.session_state["typing_deltas"] = []
            st.session_state["last_submission_time"] = current_time.isoformat()

            # Process visual attachment if present
            image_summary = None
            if uploaded_file is not None:
                image_bytes = uploaded_file.read()
                with st.spinner("Processing visual attachment..."):
                    # Process image with router
                    image_summary = router.process_image_input(image_bytes, prompt="Analyze this image in detail and describe its contents.")
                    
                st.info(f"Visual Extraction Complete: {image_summary}")
                
                # Save visual memory to DB
                mock_emb = [0.1] * 1536
                database.store_visual_memory(
                    tether_id=selected_tether_id,
                    summary=image_summary,
                    ocr_data=image_summary,
                    image_path=uploaded_file.name,
                    embedding=mock_emb
                )
                
                # Prepend/inject image summary into prompt context for Stage 2
                prompt_original = prompt
                prompt = f"[Visual Input Summary: {image_summary}]\n{prompt_original}"
                
                # Display and persist user message with visual note
                st.chat_message("user", avatar="👤").markdown(f"🖼️ *Attached: {uploaded_file.name}*\n\n{prompt_original}")
                database.add_chat_message(content=f"🖼️ Attached: {uploaded_file.name}\n\n{prompt_original}", source="desktop_text", speaker="user")
            else:
                # Display and persist standard user message
                st.chat_message("user", avatar="👤").markdown(prompt)
                database.add_chat_message(content=prompt, source="desktop_text", speaker="user")
            
            # Process user prompt via cognitive cycle
            deltas = st.session_state.get("typing_deltas", [])
            override_key = OVERRIDE_MAP.get(st.session_state.get("manual_limbic_override", "AUTO (Dynamic)"))
            is_success, friendly_res, intent_or_reason, coords = asyncio.run(
                brain.process_thought_cycle(
                    prompt, 
                    selected_tether_id, 
                    keystroke_deltas=deltas,
                    manual_override_key=override_key
                )
            )
            if coords:
                st.session_state["active_limbic_coordinates"] = coords
            
            # Save shunting state in session state
            st.session_state["terse_mode_active"] = getattr(brain, "terse_mode_active", False)
            
            # Check if the result is an async generator for token streaming
            import types
            if isinstance(friendly_res, (types.AsyncGeneratorType, types.GeneratorType)) or hasattr(friendly_res, "__anext__"):
                with st.chat_message("assistant", avatar="🤖"):
                    try:
                        final_response = st.write_stream(make_sync_generator(friendly_res))
                        database.add_chat_message(content=final_response, source="agent", speaker="agent", metadata={"coordinates": coords})
                    except Exception as stream_err:
                        st.error(f"⚠️ {str(stream_err)}")
                st.rerun()
            else:
                if isinstance(friendly_res, str):
                    reply_text = friendly_res
                elif hasattr(friendly_res, "message"):
                    reply_text = friendly_res.message
                else:
                    reply_text = str(friendly_res)
                    
                with st.chat_message("assistant", avatar="🤖"):
                    st.markdown(reply_text)
                    
                database.add_chat_message(content=reply_text, source="agent", speaker="agent", metadata={"coordinates": coords})
                st.rerun()


# --- SYSTEM INSIGHTS PANELS (Bottom tabs) ---
st.divider()
st.subheader("📊 System Insights")

tab_cal, tab_locks, tab_telemetry, tab_gov, tab_compass = st.tabs([
    "📅 Calendar Events", 
    "🧠 Behavioral Memory Engine Strategy Locks", 
    "👁️ Audit Telemetry Logs",
    "⚙️ System Governance",
    "🧭 Limbic Compass"
])

with tab_cal:
    events = database.get_calendar_events()
    if events:
        st.dataframe(events, use_container_width=True)
    else:
        st.caption("No calendar events synced.")
        
with tab_locks:
    active_behavioral = database.get_behavioral_adaptations()
    if active_behavioral:
        st.dataframe(active_behavioral, use_container_width=True)
    else:
        st.caption("No behavioral memory strategies currently locked.")
        
with tab_telemetry:
    logs = database.get_telemetry_logs(limit=25)
    if logs:
        st.dataframe(logs, use_container_width=True)
    else:
        st.caption("No telemetry events logged.")

with tab_gov:
    st.write("### System Governance")
    audits = database.get_adaptation_audit_log(limit=50)
    if audits:
        for audit in audits:
            with st.container(border=True):
                # Distilled strategy adaptation
                new_strat = audit.get("new_strategy") or "None (Strategy Reverted)"
                old_strat = audit.get("old_strategy") or "None"
                st.markdown(f"**Distilled Strategy Adaptation:** `{new_strat}`")
                
                # Original user cluster telemetry
                st.markdown(f"**Original User Cluster Telemetry:** {audit.get('triggering_telemetry') or 'N/A'}")
                
                # Specific reasoning or timestamp details
                st.caption(f"Reasoning: {audit.get('llm_reasoning')} | Scenario: {audit.get('scenario_name') or 'N/A'} | Timestamp: {audit.get('timestamp')}")
                
                # Active Revert button
                if st.button("Revert", key=f"revert_{audit['audit_log_id']}"):
                    success = database.revert_adaptation(audit['audit_log_id'])
                    if success:
                        st.success(f"Successfully reverted adaptation {audit['audit_log_id']}!")
                        st.rerun()
                    else:
                        st.error("Failed to revert adaptation.")
    else:
        st.caption("No adaptation audits found.")

with tab_compass:
    st.write("### Limbic Compass")
    st.caption("Clew's real-time emotional-cognitive coordinates on the 2D Limbic plane.")
    
    # Calculate SVG position from coordinates
    coords = st.session_state.get("active_limbic_coordinates", {"x": -0.5, "y": -0.5})
    x = coords.get("x", -0.5)
    y = coords.get("y", -0.5)
    
    # Map coordinates [-1.0, 1.0] to SVG canvas [10, 310] with center at 160
    x_px = 160 + x * 130
    y_px = 160 - y * 130 # In SVG, y axis points down
    
    svg_html = f"""
    <div style="display: flex; justify-content: center; margin: 20px 0;">
        <svg width="340" height="340" viewBox="0 0 340 340" style="background-color: #0F172A; border-radius: 16px; border: 2px solid #1E293B; box-shadow: 0 4px 20px rgba(0,0,0,0.4);">
            <!-- Outer grid boundary -->
            <rect x="10" y="10" width="320" height="320" rx="12" fill="none" stroke="#1E293B" stroke-width="2" />
            
            <!-- Axis lines -->
            <line x1="170" y1="10" x2="170" y2="330" stroke="#334155" stroke-width="2" stroke-dasharray="4" />
            <line x1="10" y1="170" x2="330" y2="170" stroke="#334155" stroke-width="2" stroke-dasharray="4" />
            
            <!-- Axis labels -->
            <text x="170" y="25" fill="#818CF8" font-size="10" text-anchor="middle" font-weight="bold" letter-spacing="1">WARM (1.0)</text>
            <text x="170" y="325" fill="#818CF8" font-size="10" text-anchor="middle" font-weight="bold" letter-spacing="1">TERSE (-1.0)</text>
            <text x="15" y="174" fill="#818CF8" font-size="10" text-anchor="start" font-weight="bold" letter-spacing="1">LOGIC (-1.0)</text>
            <text x="325" y="174" fill="#818CF8" font-size="10" text-anchor="end" font-weight="bold" letter-spacing="1">EMOTIVE (1.0)</text>
            
            <!-- Quadrant Labels -->
            <!-- Top-Right: Warm Companion (0.5, 0.5) -->
            <text x="245" y="80" fill="#38BDF8" font-size="11" font-weight="bold" text-anchor="middle">Warm Companion</text>
            <text x="245" y="93" fill="#64748B" font-size="8" text-anchor="middle">(Emotive Synergy / Warm)</text>
            
            <!-- Top-Left: Socratic Instructor (-0.5, 0.5) -->
            <text x="95" y="80" fill="#38BDF8" font-size="11" font-weight="bold" text-anchor="middle">Socratic Instructor</text>
            <text x="95" y="93" fill="#64748B" font-size="8" text-anchor="middle">(Cold Logic / Warm)</text>
            
            <!-- Bottom-Left: Dry Analyst (-0.5, -0.5) -->
            <text x="95" y="250" fill="#38BDF8" font-size="11" font-weight="bold" text-anchor="middle">Dry Analyst</text>
            <text x="95" y="263" fill="#64748B" font-size="8" text-anchor="middle">(Cold Logic / Terse)</text>
            
            <!-- Bottom-Right: Blunt Critic (0.5, -0.5) -->
            <text x="245" y="250" fill="#38BDF8" font-size="11" font-weight="bold" text-anchor="middle">Blunt Critic</text>
            <text x="245" y="263" fill="#64748B" font-size="8" text-anchor="middle">(Emotive / Terse)</text>
            
            <!-- Glow definition -->
            <defs>
                <filter id="glow-point" x="-50%" y="-50%" width="200%" height="200%">
                    <feGaussianBlur stdDeviation="6" result="blur" />
                    <feComposite in="SourceGraphic" in2="blur" operator="over" />
                </filter>
            </defs>
            
            <!-- Glowing Marker for Active Coordinate -->
            <circle cx="{10 + x_px}" cy="{10 + y_px}" r="10" fill="#818CF8" filter="url(#glow-point)" opacity="0.8" />
            <circle cx="{10 + x_px}" cy="{10 + y_px}" r="5" fill="#FFFFFF" />
        </svg>
    </div>
    """
    st.markdown(svg_html, unsafe_allow_html=True)
    st.markdown(f"<div style='text-align: center; color: #94A3B8; font-family: monospace;'>Active State: X = {x:+.2f} | Y = {y:+.2f}</div>", unsafe_allow_html=True)
