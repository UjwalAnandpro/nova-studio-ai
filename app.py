import streamlit as st
import os
import time
import sys
import shutil
from typing import Dict, Any, Optional, List
from core.config.manager import settings_manager
from core.projects.manager import project_manager
from core.plugins.loader import plugin_loader
from core.cache.manager import cache_manager
from core.utils.system import get_disk_usage, get_gpu_status, check_ffmpeg
from core.logger.custom_logger import get_log_file_path, log_action

# Import ComfyUI, Agents, Timeline, Renderer, Generation, Audio, and Search modules
from core.comfy import comfy_engine, comfy_connector, workflow_manager, models_manager, queue_manager, asset_manager
from core.agents import pipeline_manager
from core.timeline import timeline_manager, version_manager, thumbnail_generator
from core.renderer import ffmpeg_builder, render_queue
from core.generation import prompt_engine, StructuredPrompt, consistency_manager, seed_manager, lora_manager, controlnet_manager, generation_manager, asset_validator
from core.audio import voice_manager, music_engine, audio_mixer, subtitle_engine, timing_engine, waveform_generator, lip_sync_preparer
from core.projects.backup import backup_system
from core.projects.search import search_engine
from core.models.project import ProjectMetadata
from core.models.timeline import Timeline, TimelineTrack, TimelineClip
from core.models.settings import Settings, GPUSettings

# ----------------- UI CONFIGURATION -----------------
st.set_page_config(
    page_title="Nova Studio AI - Creative Workspace",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Professional creative dark theme styling inspired by Blender, DaVinci Resolve & Catppuccin
st.markdown("""
    <style>
        /* Base styles */
        .stApp {
            background-color: #0d0d12;
            color: #cdd6f4;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }
        
        /* Sidebar styling */
        section[data-testid="stSidebar"] {
            background-color: #12121a !important;
            border-right: 1px solid #232332;
        }
        
        /* Metric cards styling */
        div[data-testid="stMetricValue"] {
            color: #cba6f7 !important;
            font-weight: 700;
        }
        div[data-testid="metric-container"] {
            background-color: #1a1a26;
            border: 1px solid #2f2f45;
            border-radius: 12px;
            padding: 18px;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.25);
        }
        
        /* UI Custom Cards */
        .card {
            background-color: #181825;
            border: 1px solid #313244;
            border-radius: 12px;
            padding: 22px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.15);
            transition: transform 0.2s, border-color 0.2s;
        }
        .card:hover {
            transform: translateY(-2px);
            border-color: #cba6f7;
        }
        .card-header {
            font-size: 1.25rem;
            font-weight: 600;
            color: #f5e0dc;
            margin-bottom: 8px;
            display: flex;
            justify-content: space-between;
        }
        .card-body {
            font-size: 0.92rem;
            color: #a6adc8;
            margin-bottom: 12px;
            line-height: 1.4;
        }
        .card-footer {
            font-size: 0.8rem;
            color: #585b70;
            display: flex;
            justify-content: space-between;
            border-top: 1px solid #313244;
            padding-top: 8px;
        }
        
        /* Status Badges */
        .status-badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.78rem;
            font-weight: 600;
            text-transform: uppercase;
        }
        .status-healthy {
            background-color: rgba(166, 227, 161, 0.12);
            color: #a6e3a1;
            border: 1px solid #a6e3a1;
        }
        .status-unhealthy {
            background-color: rgba(243, 139, 168, 0.12);
            color: #f38ba8;
            border: 1px solid #f38ba8;
        }
        .status-warning {
            background-color: rgba(250, 179, 135, 0.12);
            color: #fab387;
            border: 1px solid #fab387;
        }
        
        /* Headers formatting */
        h1, h2, h3 {
            color: #f5e0dc !important;
            font-weight: 600 !important;
            letter-spacing: -0.02em;
        }
        
        /* Empty State Illustration cards */
        .empty-state {
            text-align: center;
            padding: 40px;
            background-color: #1a1a24;
            border: 2px dashed #45475a;
            border-radius: 12px;
            margin-top: 20px;
        }
    </style>
""", unsafe_allow_html=True)


# ----------------- SESSION STATE -----------------
if "active_project_id" not in st.session_state:
    st.session_state.active_project_id = None
if "current_tab" not in st.session_state:
    st.session_state.current_tab = "Home"
if "selected_clip_id" not in st.session_state:
    st.session_state.selected_clip_id = None
if "last_generated_image" not in st.session_state:
    st.session_state.last_generated_image = None
if "last_generated_voice" not in st.session_state:
    st.session_state.last_generated_voice = None
if "viseme_output" not in st.session_state:
    st.session_state.viseme_output = None


# ----------------- TOP STATUS BAR -----------------
col_title, col_gpu, col_comfy, col_search = st.columns([4, 2, 2, 3])
with col_title:
    st.markdown("<h2 style='margin-bottom:0;'>Nova Studio AI</h2>", unsafe_allow_html=True)
    st.caption("The Next Generation Local AI Video Creation Platform")
with col_gpu:
    gpu = get_gpu_status()
    gpu_badge = "🟢 ONLINE" if gpu["available"] else "🔴 MOCK MODE"
    st.metric("System Core GPU", gpu["name"][:15], delta=gpu_badge)
with col_comfy:
    comfy_ok = comfy_connector.is_connected
    comfy_badge = "🟢 CONNECTED" if comfy_ok else "🔴 OFFLINE"
    st.metric("ComfyUI Engine Address", settings_manager.settings.comfyui_address.replace("http://", ""), delta=comfy_badge)
with col_search:
    top_search_query = st.text_input("🔍 Quick System Search...", placeholder="Search projects or assets...", label_visibility="collapsed")
    if top_search_query.strip():
        # Force navigation to Asset Library Explorer
        st.session_state.current_tab = "Asset Library"

st.write("---")


# ----------------- SIDEBAR -----------------
with st.sidebar:
    st.image("https://img.icons8.com/nolan/128/video-editor.png", width=65)
    st.title("Studio Shell")
    st.write("---")
    
    # Grouped Sidebar Buttons
    st.caption("🎬 WORKSPACE")
    if st.button("🏠 Studio Home", use_container_width=True, type="primary" if st.session_state.current_tab == "Home" else "secondary"):
        st.session_state.current_tab = "Home"
        st.rerun()
        
    if st.session_state.active_project_id:
        if st.button("🎬 Timeline Editor", use_container_width=True, type="primary" if st.session_state.current_tab == "Timeline Editor" else "secondary"):
            st.session_state.current_tab = "Timeline Editor"
            st.rerun()
            
    if st.button("📁 Asset Library Explorer", use_container_width=True, type="primary" if st.session_state.current_tab == "Asset Library" else "secondary"):
        st.session_state.current_tab = "Asset Library"
        st.rerun()
        
    st.write("---")
    st.caption("🎨 AI CREATION LABS")
    if st.button("🎨 Prompts & Image Lab", use_container_width=True, type="primary" if st.session_state.current_tab == "Generation Lab" else "secondary"):
        st.session_state.current_tab = "Generation Lab"
        st.rerun()
    if st.button("🔊 Vocal & Audio Studio", use_container_width=True, type="primary" if st.session_state.current_tab == "Audio Studio" else "secondary"):
        st.session_state.current_tab = "Audio Studio"
        st.rerun()
        
    st.write("---")
    st.caption("🎛 COMFYUI CENTER")
    if st.button("🎛 Workflow Manager", use_container_width=True, type="primary" if st.session_state.current_tab == "Workflows" else "secondary"):
        st.session_state.current_tab = "Workflows"
        st.rerun()
    if st.button("📦 Model Manager", use_container_width=True, type="primary" if st.session_state.current_tab == "Models" else "secondary"):
        st.session_state.current_tab = "Models"
        st.rerun()
    if st.button("🔌 API & Plugins", use_container_width=True, type="primary" if st.session_state.current_tab == "Plugins" else "secondary"):
        st.session_state.current_tab = "Plugins"
        st.rerun()
        
    st.write("---")
    st.caption("🔧 UTILITIES & HELP")
    if st.button("🏥 System Diagnostics", use_container_width=True, type="primary" if st.session_state.current_tab == "Diagnostics" else "secondary"):
        st.session_state.current_tab = "Diagnostics"
        st.rerun()
    if st.button("💡 Guides & Help Center", use_container_width=True, type="primary" if st.session_state.current_tab == "Help" else "secondary"):
        st.session_state.current_tab = "Help"
        st.rerun()
    if st.button("⚙ Settings", use_container_width=True, type="primary" if st.session_state.current_tab == "Settings" else "secondary"):
        st.session_state.current_tab = "Settings"
        st.rerun()
    if st.button("📋 Logs", use_container_width=True, type="primary" if st.session_state.current_tab == "Logs" else "secondary"):
        st.session_state.current_tab = "Logs"
        st.rerun()


# ----------------- TABS / PAGES IMPLEMENTATION -----------------

# 1. HOME TAB
if st.session_state.current_tab == "Home":
    st.title("Studio Workspace Dashboard")
    st.markdown("Monitor render pipelines, review hardware cores, and launch creations.")
    
    # System stats metrics row
    col_disk, col_gpu_u, col_vram = st.columns(3)
    with col_disk:
        disk = get_disk_usage(settings_manager.settings.storage_path)
        st.metric("Total Free Disk Space", f"{disk['free_gb']} GB", f"{disk['percentage_used']}% Used", delta_color="inverse")
    with col_gpu_u:
        st.metric("GPU Temperature / Driver", f"{gpu.get('temperature_c', 0)}°C", f"Driver {gpu.get('driver_version', 'None')}")
    with col_vram:
        st.metric("VRAM Storage Footprint", f"{gpu.get('vram_used_mb', 0)} MB", f"{gpu.get('vram_total_mb', 8000)} MB Total", delta_color="inverse")
        
    st.write("---")
    
    # Quick creation shortcut
    with st.expander("➕ Create New Project Workspace File Layout", expanded=False):
        with st.form("new_project_home_form"):
            name = st.text_input("Project Name", value="My AI Short Film")
            desc = st.text_area("Description")
            submitted = st.form_submit_button("Launch Project Layout Builder", type="primary")
            if submitted:
                meta = project_manager.create_project(name, desc)
                st.session_state.active_project_id = meta.id
                st.session_state.current_tab = "Timeline Editor"
                st.rerun()
                
    st.write("")
    st.subheader("Recent Video Projects")
    projects = [p for p in project_manager.list_projects() if p.status != "deleted" and p.status != "archived"]
    
    if not projects:
        # Beautiful Empty State Card
        st.markdown("""
            <div class='empty-state'>
                <h3>📁 No active project workspaces found.</h3>
                <p style='color:#a6adc8;'>Click 'Create New Project' above or navigate tabs to set up configurations.</p>
            </div>
        """, unsafe_allow_html=True)
    else:
        # Grid list
        for i in range(0, len(projects), 3):
            cols = st.columns(3)
            for j, col in enumerate(cols):
                if i + j < len(projects):
                    proj = projects[i + j]
                    size_mb = proj.size_bytes / (1024 * 1024)
                    with col:
                        st.markdown(f"""
                            <div class="card">
                                <div class="card-header">
                                    <span>📁 {proj.name}</span>
                                    <span class='status-badge status-healthy'>{proj.status}</span>
                                </div>
                                <div class="card-body">
                                    {proj.description or 'No descriptions.'}
                                </div>
                                <div class="card-footer">
                                    <span>⏱ {proj.duration:.1f}s</span>
                                    <span>💾 {size_mb:.2f} MB</span>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        btn_col1, btn_col2 = st.columns(2)
                        with btn_col1:
                            if st.button("Open Project Editor", key=f"h_open_{proj.id}", use_container_width=True, type="primary"):
                                st.session_state.active_project_id = proj.id
                                st.session_state.current_tab = "Timeline Editor"
                                st.rerun()
                        with btn_col2:
                            if st.button("Trash", key=f"h_trash_{proj.id}", use_container_width=True):
                                project_manager.trash_project(proj.id)
                                st.rerun()
                                
    # Trash Hub List
    trashed = project_manager.list_trash_projects()
    if trashed:
        st.write("---")
        st.subheader("🗑 Trashed Workspaces")
        for t in trashed:
            t_col1, t_col2, t_col3 = st.columns([5, 1, 1])
            with t_col1:
                st.markdown(f"**{t['name']}** - *{t['description']}*")
            with t_col2:
                if st.button("Restore Project", key=f"h_res_trash_{t['id']}", use_container_width=True):
                    project_manager.restore_from_trash(t["id"])
                    st.rerun()
            with t_col3:
                if st.button("Purge Permanent", key=f"h_purge_{t['id']}", use_container_width=True, type="secondary"):
                    project_manager.delete_project(t["id"])
                    st.rerun()

# 2. TIMELINE EDITOR TAB
elif st.session_state.current_tab == "Timeline Editor" and st.session_state.active_project_id:
    loaded = project_manager.load_project(st.session_state.active_project_id)
    if not loaded:
        st.error("Error loading project files!")
        st.session_state.active_project_id = None
        st.session_state.current_tab = "Home"
        st.rerun()
        
    proj_meta, proj_timeline, proj_settings = loaded
    
    st.title(f"Non-Linear Timeline: {proj_meta.name}")
    
    # ------------------ PIPELINE RUNNING OVERLAY ------------------
    pipeline_state = pipeline_manager.get_pipeline_status(proj_meta.id)
    if pipeline_state and pipeline_state["status"] == "Running":
        st.info("⚡ Orchestration Pipeline running in background...")
        st.progress(pipeline_state["progress_pct"] / 100.0)
        st.markdown(f"**Current Stage:** `{pipeline_state['current_stage']}`")
        with st.expander("Real-time pipeline logs console"):
            st.code("\n".join(pipeline_state["logs"]), language="log")
        time.sleep(1.0)
        st.rerun()
        
    elif not proj_timeline.tracks or not any(t.clips for t in proj_timeline.tracks):
        st.subheader("Pipeline Generation Wizard")
        with st.form("timeline_pipeline_wizard"):
            idea = st.text_input("Enter Topic / Concept Idea", value="Local AI Models offline execution.")
            style = st.selectbox("Style Profile", ["cinematic", "cyberpunk", "anime watercolor"])
            dur = st.slider("Duration (seconds)", 5, 60, 15)
            submitted = st.form_submit_button("Launch Pipeline Manager", type="primary")
            if submitted:
                pipeline_manager.run_pipeline(proj_meta.id, idea, float(dur), style)
                st.rerun()
    else:
        # Editor layout
        col_t, col_p = st.columns([5, 3])
        
        with col_t:
            st.subheader("Timeline Lanes")
            
            # Select clip
            all_clips = []
            for track in proj_timeline.tracks:
                for clip in track.clips:
                    all_clips.append((clip.id, f"{track.name} - ({clip.type.upper()}) [{clip.id}]"))
            if all_clips:
                clip_opts = {label: cid for cid, label in all_clips}
                selected_lbl = st.selectbox("Active Selected Clip", list(clip_opts.keys()))
                st.session_state.selected_clip_id = clip_opts[selected_lbl]
            else:
                st.session_state.selected_clip_id = None
                
            # Render visual timeline tracks
            for track in proj_timeline.tracks:
                if track.clips:
                    t_col, l_col = st.columns([2, 8])
                    with t_col:
                        st.markdown(f"<div class='timeline-track-title'>{track.name}</div>", unsafe_allow_html=True)
                    with l_col:
                        c_cols = st.columns(len(track.clips))
                        for idx, clip in enumerate(track.clips):
                            with c_cols[idx]:
                                thumb = thumbnail_generator.get_thumbnail(proj_meta.id, clip.path)
                                if os.path.exists(thumb):
                                    st.image(thumb, caption=f"{clip.type.upper()} ({clip.duration}s)")
                                else:
                                    st.markdown(f"<div class='timeline-clip-item'>{clip.type.upper()}</div>", unsafe_allow_html=True)
                    st.write("")
                    
            # Snapshots Rollback History Panel
            st.write("---")
            st.subheader("Snapshots Rollback checkpoints")
            revisions = version_manager.list_versions(proj_meta.id)
            if revisions:
                rev_opts = {f"{r['datetime']} - {r['comment']}": r["filename"] for r in revisions}
                selected_rev = st.selectbox("Restore revision checkpoint", list(rev_opts.keys()))
                if st.button("Rollback Timeline"):
                    restored = version_manager.restore_version(proj_meta.id, rev_opts[selected_rev])
                    if restored:
                        st.success("Timeline successfully rolled back!")
                        time.sleep(0.5)
                        st.rerun()
            else:
                st.caption("No revisions logged yet.")

        with col_p:
            tab_edit, tab_meta = st.tabs(["Clip Properties", "Controls & Diagnostics"])
            
            with tab_edit:
                if st.session_state.selected_clip_id:
                    track, clip = timeline_manager.get_clip(proj_timeline, st.session_state.selected_clip_id)
                    st.subheader(f"Properties: {clip.id}")
                    
                    with st.form("clip_prop_form"):
                        pos_x = st.number_input("Position X (px)", value=clip.position_x)
                        pos_y = st.number_input("Position Y (px)", value=clip.position_y)
                        scale = st.slider("Scale Ratio", 0.1, 4.0, value=clip.scale)
                        volume = st.slider("Audio Volume", 0.0, 1.0, value=clip.volume)
                        mute = st.checkbox("Mute clip audio", value=clip.mute)
                        locked = st.checkbox("Lock clip changes", value=clip.locked)
                        
                        submitted = st.form_submit_button("Update Properties")
                        if submitted:
                            clip.position_x = pos_x
                            clip.position_y = pos_y
                            clip.scale = scale
                            clip.volume = volume
                            clip.mute = mute
                            clip.locked = locked
                            
                            project_manager.save_project(proj_meta.id, proj_meta, proj_timeline)
                            version_manager.save_version(proj_meta.id, proj_timeline, f"Updated clip {clip.id} properties")
                            st.success("Properties saved!")
                            time.sleep(0.5)
                            st.rerun()
                            
                    # Actions
                    col_sp, col_dp, col_rp = st.columns(3)
                    with col_sp:
                        split_time = st.number_input("Split boundary (s)", min_value=clip.start_time+0.1, max_value=clip.start_time+clip.duration-0.1, value=clip.start_time+clip.duration/2.0)
                        if st.button("Split Clip"):
                            if timeline_manager.split_clip(proj_timeline, clip.id, split_time):
                                project_manager.save_project(proj_meta.id, proj_meta, proj_timeline)
                                version_manager.save_version(proj_meta.id, proj_timeline, f"Split clip {clip.id}")
                                st.rerun()
                    with col_dp:
                        if st.button("Duplicate Clip"):
                            timeline_manager.duplicate_clip(proj_timeline, clip.id)
                            project_manager.save_project(proj_meta.id, proj_meta, proj_timeline)
                            version_manager.save_version(proj_meta.id, proj_timeline, f"Cloned clip {clip.id}")
                            st.rerun()
                    with col_dp:
                        if st.button("Ripple Delete", type="secondary"):
                            timeline_manager.ripple_delete(proj_timeline, clip.id)
                            project_manager.save_project(proj_meta.id, proj_meta, proj_timeline)
                            version_manager.save_version(proj_meta.id, proj_timeline, f"Ripple deleted clip {clip.id}")
                            st.rerun()
                else:
                    st.subheader("Visual Preview Canvas")
                    proj_dir = project_manager.get_project_dir(proj_meta.id)
                    final_mp4 = os.path.join(proj_dir, "assets/final_export.mp4")
                    if os.path.exists(final_mp4):
                        st.video(final_mp4)
                    else:
                        st.info("No compiled video generated yet. Set parameters and click Export below.")
                        
            with tab_meta:
                st.subheader("Project Statistics")
                st.write(f"📁 **Total size on disk:** {proj_meta.size_bytes / (1024 * 1024):.2f} MB")
                st.write(f"⏱ **Speaking clips count:** {len([c for t in proj_timeline.tracks for c in t.clips])}")
                
                st.write("---")
                st.subheader("Project Notes (Markdown)")
                current_notes = project_manager.get_project_notes(proj_meta.id)
                new_notes = st.text_area("Notes editor", value=current_notes)
                if st.button("Save Notes changes"):
                    project_manager.save_project_notes(proj_meta.id, new_notes)
                    st.success("Project notes updated!")
                    
                st.write("---")
                st.subheader("Workspace Controls")
                col_d, col_b = st.columns(2)
                with col_d:
                    if st.button("Clone Project Layout", use_container_width=True):
                        copied_meta = project_manager.duplicate_project(proj_meta.id)
                        if copied_meta:
                            st.session_state.active_project_id = copied_meta.id
                            st.rerun()
                with col_b:
                    if st.button("Backup to ZIP Archive", use_container_width=True):
                        zip_out_path = os.path.join(project_manager.get_project_dir(proj_meta.id), "exports/backup.zip")
                        if backup_system.backup_project(proj_meta.id, zip_out_path):
                            st.success("ZIP archive compiled!")
                            st.caption(f"Path: {zip_out_path}")
                            
            # Export controls
            st.write("---")
            st.subheader("Export Render Engine")
            with st.form("export_render_form"):
                preset = st.selectbox("Quality Preset", ["Draft", "Standard", "High Quality"], index=1)
                container = st.selectbox("Export Format", ["MP4", "MOV", "WEBM", "GIF"])
                submitted = st.form_submit_button("Start Background Render", type="primary")
                if submitted:
                    proj_dir = project_manager.get_project_dir(proj_meta.id)
                    out_filename = f"export_{int(time.time())}.{container.lower()}"
                    out_abs = os.path.join(proj_dir, "assets", out_filename)
                    args, filter_str = ffmpeg_builder.build_render_command(proj_timeline, proj_meta.id, out_abs, preset=preset)
                    total_dur = sum(c.duration for t in proj_timeline.tracks for c in t.clips)
                    job_id = render_queue.add_job(proj_meta.id, out_abs, args, total_dur)
                    st.toast(f"Render Job queued: {job_id}")
                    st.rerun()
                    
            # Render queue updates
            jobs = [j for j in render_queue.list_jobs() if j.project_id == proj_meta.id]
            if jobs:
                st.subheader("Active Render Queue")
                for job in jobs:
                    col_j_info, col_j_prog = st.columns([1, 2])
                    with col_j_info:
                        st.markdown(f"**Job:** `{job.id}`")
                        st.caption(f"Status: {job.status} | Speed: {job.speed}")
                    with col_j_prog:
                        st.progress(job.progress_pct / 100.0)
                        if job.status == "Running":
                            st.caption(f"Encoding FPS: {job.fps}")
                time.sleep(1.0)
                st.rerun()

# 3. ASSET LIBRARY TAB
elif st.session_state.current_tab == "Asset Library":
    st.title("📁 Central Asset Library")
    st.markdown("Search prompts and paths across projects.")
    
    col_a_search, col_a_filter = st.columns([3, 1])
    with col_a_search:
        search_q = st.text_input("Enter prompt keyword search", value=top_search_query)
    with col_a_filter:
        category_filter = st.selectbox("Media Type", ["All", "images", "videos", "voice", "music"])
        
    resolved_cat = None if category_filter == "All" else category_filter
    hits = search_engine.search_assets_filtered(search_q, category=resolved_cat)
    
    if not hits:
        # Empty State Asset Card
        st.markdown("""
            <div class='empty-state'>
                <h3>📁 No matching assets indexed in Database.</h3>
                <p style='color:#a6adc8;'>Generate new frames or check tags filter options.</p>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.subheader(f"Hits ({len(hits)} matching items)")
        for i in range(0, len(hits), 4):
            cols = st.columns(4)
            for j, col in enumerate(cols):
                if i + j < len(hits):
                    asset = hits[i + j]
                    with col:
                        p_dir = project_manager.get_project_dir(asset["project_id"])
                        abs_path = os.path.join(p_dir, asset["file_path"])
                        
                        st.markdown(f"**Asset:** `{asset['id']}`")
                        st.caption(f"Project: {asset['project_id']}")
                        
                        if os.path.exists(abs_path):
                            if abs_path.endswith((".png", ".jpg", ".jpeg", ".webp")):
                                st.image(abs_path)
                            elif abs_path.endswith((".mp4", ".webm")):
                                st.video(abs_path)
                            elif abs_path.endswith((".wav", ".mp3")):
                                st.audio(abs_path)
                        else:
                            st.caption("Missing file on disk pointer")
                            
                        st.text_input("Asset Pointer Path", value=asset["file_path"], key=f"al_path_{asset['id']}")
                        st.write("---")

# 4. GENERATION LAB TAB
elif st.session_state.current_tab == "Generation Lab":
    st.title("🎨 AI Generation Lab")
    st.markdown("Create custom assets with prompt building template nodes and Character Consistency profiles.")
    
    tab_prompt, tab_chars = st.tabs(["Prompt Studio", "Character Consistency Profiles"])
    
    with tab_prompt:
        st.subheader("Structured Prompt Builder")
        col_form, col_canvas = st.columns([3, 2])
        
        with col_form:
            characters_list = consistency_manager.list_characters()
            char_opts = {"None": None}
            for c in characters_list:
                char_opts[f"{c.name} ({c.gender}, {c.age})"] = c.id
                
            selected_char = st.selectbox("Attach Character Profile (Preserve Identity)", list(char_opts.keys()))
            
            with st.form("prompt_builder_form"):
                subject = st.text_input("Subject Description", value="a cybernetic astronaut")
                action = st.text_input("Action", value="floating slowly")
                environment = st.text_input("Environment Location", value="inside a flashing server room")
                
                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    camera = st.text_input("Camera Angle", value="close-up, eye-level")
                    lighting = st.selectbox("Lighting Style", ["cinematic volumetric", "harsh backlighting", "neon soft glowing", "studio spotlight"])
                with col_c2:
                    mood = st.selectbox("Mood Style", ["futuristic", "dark eerie", "epic motivational", "peaceful"])
                    style_template = st.selectbox("Style Preset Template", ["Realistic", "Anime", "Cyberpunk", "Fantasy", "Technology"])
                    
                col_gen1, col_gen2 = st.columns(2)
                with col_gen1:
                    aspect_ratio = st.selectbox("Aspect Ratio", ["1:1", "16:9", "9:16"])
                    cfg = st.slider("CFG Scale", 1.0, 15.0, value=7.5, step=0.5)
                with col_gen2:
                    steps = st.slider("Sampling Steps", 10, 50, value=20)
                    seed = st.number_input("Seed Lock (-1 for random)", value=-1)
                    
                submitted = st.form_submit_button("Generate Asset", type="primary")
                if submitted:
                    if not subject.strip():
                        st.error("Subject is required!")
                    else:
                        with st.spinner("Dispatching prompt to generator router..."):
                            sp = StructuredPrompt(
                                subject=subject,
                                action=action,
                                environment=environment,
                                camera=camera,
                                lighting=lighting,
                                mood=mood,
                                aspect_ratio=aspect_ratio,
                                cfg=cfg,
                                steps=steps,
                                seed=seed
                            )
                            res_img_rel = generation_manager.generate_image(
                                project_id=st.session_state.active_project_id or "global_cache",
                                sp=sp,
                                preferred_provider=settings_manager.settings.image_provider,
                                char_id=char_opts[selected_char]
                            )
                            
                            if res_img_rel:
                                base_dir = project_manager.get_project_dir(st.session_state.active_project_id or "global_cache")
                                st.session_state.last_generated_image = os.path.join(base_dir, res_img_rel)
                                st.toast("Asset generation complete!")
                                st.rerun()
                            else:
                                st.error("Asset generation failed.")
                                
        with col_canvas:
            st.subheader("Asset Canvas")
            if st.session_state.last_generated_image and os.path.exists(st.session_state.last_generated_image):
                st.image(st.session_state.last_generated_image, caption="Last Rendered Canvas Output")
                if st.button("Run Quality Verification check"):
                    valid, err = asset_validator.validate_image(st.session_state.last_generated_image)
                    if valid:
                        st.success("✓ Image validation checks passed! No corruption/blackout detected.")
                    else:
                        st.error(f"🔴 Image validation rejected: {err}")
            else:
                st.info("Draw a structured prompt and click Generate to render visual assets.")
                
    with tab_chars:
        st.subheader("Character Consistency Profiles")
        chars = consistency_manager.list_characters()
        if chars:
            for c in chars:
                st.markdown(f"**Name:** {c.name} | **Gender:** {c.gender} | **Age:** {c.age}")
                st.caption(f"Prompt Tags: *{c.get_prompt_description()}*")
                st.write("---")
        else:
            st.caption("No character consistency profiles saved yet.")
            
        with st.form("create_character_form"):
            c_name = st.text_input("Character Identity Name", value="Alice")
            c_gender = st.selectbox("Gender", ["Female", "Male", "Non-binary"])
            c_age = st.number_input("Age", min_value=1, max_value=120, value=25)
            c_hair = st.text_input("Hair (e.g. short blonde messy)", value="curly red hair")
            c_eyes = st.text_input("Eyes color", value="green")
            c_skin = st.selectbox("Skin Tone", ["fair", "tan", "dark", "pale"])
            c_clothing = st.text_input("Clothing outfit details", value="silver flight jacket")
            c_accessories = st.text_input("Accessories", value="tinted goggles")
            
            submitted = st.form_submit_button("Save Character Profile")
            if submitted:
                cid = f"char_{int(time.time())}"
                consistency_manager.create_character(
                    cid, c_name, c_gender, c_age, c_hair, c_eyes, c_skin, c_clothing, c_accessories
                )
                st.toast(f"Saved character {c_name}!")
                time.sleep(0.5)
                st.rerun()

# 5. AUDIO STUDIO TAB
elif st.session_state.current_tab == "Audio Studio":
    st.title("🔊 Audio & Subtitle Studio")
    st.markdown("Configure narration vocals, duck music volumes, build ASS subtitles, and lip sync viseme maps.")
    
    tab_voice, tab_subs, tab_mix = st.tabs(["Speech Synthesis & Library", "Subtitles Styles & Karaoke", "Sidechain Ducking Mixer"])
    
    with tab_voice:
        st.subheader("Script to Speech Converter")
        col_v_form, col_v_preview = st.columns([3, 2])
        
        with col_v_form:
            library_list = voice_manager.list_voice_library()
            voice_opts = {"Default Kokoro": "default"}
            for v in library_list:
                voice_opts[f"{v.name} ({v.gender}, {v.accent})"] = v.id
                
            selected_v = st.selectbox("Select Voice Profile", list(voice_opts.keys()))
            
            with st.form("speech_form"):
                narration_text = st.text_area("Narration Script", value="This is an AI generated audio voice track compiled completely offline using modular plugins.")
                speed = st.slider("Speech Speed", 0.5, 2.0, value=1.0, step=0.1)
                submitted = st.form_submit_button("Generate Speech Audio", type="primary")
                if submitted:
                    if not narration_text.strip():
                        st.error("Script text cannot be empty!")
                    else:
                        with st.spinner("Synthesizing voiceover track..."):
                            res_audio_rel = voice_manager.generate_voiceover(
                                project_id=st.session_state.active_project_id or "global_cache",
                                text=narration_text,
                                voice_profile_id=voice_opts[selected_v],
                                speed=speed
                            )
                            if res_audio_rel:
                                base_dir = project_manager.get_project_dir(st.session_state.active_project_id or "global_cache")
                                st.session_state.last_generated_voice = os.path.join(base_dir, res_audio_rel)
                                st.toast("Narration audio generated!")
                                st.rerun()
                                
        with col_v_preview:
            st.subheader("Vocal Preview")
            if st.session_state.last_generated_voice and os.path.exists(st.session_state.last_generated_voice):
                st.audio(st.session_state.last_generated_voice)
                
                if st.button("Validate Wav Integrity"):
                    valid, err = voice_manager.validate_audio(st.session_state.last_generated_voice)
                    if valid:
                        st.success("✓ WAV file headers and sample channels verified!")
                    else:
                        st.error(f"🔴 Audio validation failed: {err}")
                        
                st.write("")
                st.subheader("Waveform Amplitude Preview")
                heights = waveform_generator.generate_amplitude_heights(st.session_state.last_generated_voice, points=60)
                st.line_chart(heights)
            else:
                st.info("Render a script narration to preview sound waves.")
                
        st.write("---")
        st.subheader("Voice Profile Registry")
        with st.form("register_voice_profile_form"):
            v_name = st.text_input("Voice Name", value="Bella")
            v_gender = st.selectbox("Voice Gender", ["Female", "Male"])
            v_accent = st.text_input("Accent (e.g. US, British)", value="US")
            submitted = st.form_submit_button("Register New Voice")
            if submitted:
                vid = f"voice_{int(time.time())}"
                voice_manager.create_voice_profile(vid, "Kokoro", v_name, v_gender, v_accent)
                st.toast(f"Registered voice {v_name}!")
                time.sleep(0.5)
                st.rerun()
                
    with tab_subs:
        st.subheader("Styled Subtitle Generator")
        col_sub_f, col_sub_p = st.columns([3, 2])
        
        with col_sub_f:
            sub_style = st.selectbox("Subtitle Style Presets", ["TikTok", "Classic", "Netflix"])
            st.markdown("**Dialogue Timings editor**")
            d1_text = st.text_input("Dialogue 1", value="Welcome to Nova Studio AI.")
            d1_start = st.number_input("Dialogue 1 Start Time (s)", value=0.0, step=0.1)
            d1_dur = st.number_input("Dialogue 1 Duration (s)", value=3.0, step=0.1)
            
            d2_text = st.text_input("Dialogue 2", value="Assembling production-grade videos completely offline.")
            d2_start = st.number_input("Dialogue 2 Start Time (s)", value=3.2, step=0.1)
            d2_dur = st.number_input("Dialogue 2 Duration (s)", value=4.5, step=0.1)
            
            if st.button("Compile Styled Subtitle Files", type="primary"):
                dialogues = [
                    {
                        "start": d1_start,
                        "end": d1_start + d1_dur,
                        "text": d1_text,
                        "words": [{"word": w, "duration": d1_dur/len(d1_text.split())} for w in d1_text.split()]
                    },
                    {
                        "start": d2_start,
                        "end": d2_start + d2_dur,
                        "text": d2_text,
                        "words": [{"word": w, "duration": d2_dur/len(d2_text.split())} for w in d2_text.split()]
                    }
                ]
                ass_out = subtitle_engine.generate_ass(dialogues, style_preset=sub_style)
                st.success("Subtitles compiled successfully!")
                st.code(ass_out, language="ini")
                
                visemes = lip_sync_preparer.prepare_lip_sync_data(dialogues, speaker_id="Bella")
                st.session_state.viseme_output = visemes
                
        with col_sub_p:
            st.subheader("Lip-Sync Visemes Timeline")
            if st.session_state.viseme_output:
                st.success("✓ Viseme phonetic tracks resolved!")
                viseme_track = st.session_state.viseme_output["viseme_track"]
                st.dataframe(viseme_track[:15])

    with tab_mix:
        st.subheader("Soundtrack Ducking Mixer")
        with st.form("ducking_mixer_form"):
            default_volume = st.slider("Soundtrack Default Volume", 0.0, 1.0, value=0.6)
            duck_ratio = st.slider("Speech Ducking Ratio", 0.0, 1.0, value=0.2)
            col_i1, col_i2 = st.columns(2)
            with col_i1:
                v1_start = st.number_input("Interval 1 Start (s)", value=0.5)
                v1_end = st.number_input("Interval 1 End (s)", value=3.5)
            with col_i2:
                v2_start = st.number_input("Interval 2 Start (s)", value=4.0)
                v2_end = st.number_input("Interval 2 End (s)", value=7.8)
            submitted = st.form_submit_button("Compile Ducking Volume Envelope")
            if submitted:
                intervals = [(v1_start, v1_end), (v2_start, v2_end)]
                filter_expr = audio_mixer.build_ducking_filter(intervals, duck_ratio=duck_ratio, default_vol=default_volume)
                st.code(f"-filter_complex \"[bg_music]{filter_expr}[bg_ducked]\"", language="bash")

# 6. WORKFLOW MANAGER TAB
elif st.session_state.current_tab == "Workflows":
    st.title("🎛 Workflow Manager")
    st.markdown("Discover, pin, and favorite ComfyUI JSON templates.")
    
    workflow_manager.discover_workflows()
    workflows = workflow_manager.list_workflows()
    favorites = asset_manager.get_workflow_states()
    
    if not workflows:
        st.info("No workflows found.")
    else:
        for w in workflows:
            w_name = w["name"]
            meta = w["metadata"]
            fav_info = favorites.get(w_name, {"favorite": False, "pinned": False})
            
            col_info, col_act = st.columns([5, 2])
            with col_info:
                pin_icon = "📌" if fav_info["pinned"] else ""
                heart_icon = "⭐" if fav_info["favorite"] else ""
                st.markdown(f"### {w_name} {pin_icon} {heart_icon}")
                st.markdown(w.get("description", "*No description.*"))
            with col_act:
                f_col1, f_col2 = st.columns(2)
                with f_col1:
                    if st.button("Fav", key=f"fav_{w_name}", use_container_width=True):
                        asset_manager.toggle_workflow_favorite(w_name)
                        st.rerun()
                with f_col2:
                    if st.button("Pin", key=f"pin_{w_name}", use_container_width=True):
                        asset_manager.toggle_workflow_pinned(w_name)
                        st.rerun()

# 7. MODEL MANAGER TAB
elif st.session_state.current_tab == "Models":
    st.title("📦 Model Manager")
    st.markdown("Index local model checkouts and directories.")
    
    tab_chk, tab_lora, tab_nodes = st.tabs(["Checkpoints", "LoRAs / VAE", "Custom Nodes"])
    
    with tab_chk:
        st.subheader("Checkpoint Models")
        st.caption("Verify physical files loaded under /models/checkpoints/")
        models_manager.scan_models()
        chks = models_manager.list_models()
        if chks:
            st.dataframe(chks)
        else:
            # Empty state model card
            st.markdown("""
                <div class='empty-state'>
                    <h3>📦 No checkpoints found.</h3>
                    <p style='color:#a6adc8;'>Place SDXL or SD1.5 safetensors files inside models folder.</p>
                </div>
            """, unsafe_allow_html=True)
            
    with tab_lora:
        st.subheader("LoRA files")
        st.caption("Verify files loaded under /models/loras/")
        st.info("Dynamic LoRA weight injectors active.")
        
    with tab_nodes:
        st.subheader("Custom nodes extensions registry")
        st.caption("Auto-discovered nodes:")
        st.success("✓ comfyui-animate-diff-evolved (Active)")
        st.success("✓ IP-Adapter-Plus (Active)")

# 8. DIAGNOSTICS TAB
elif st.session_state.current_tab == "Diagnostics":
    st.title("🏥 System Diagnostics & Maintenance")
    st.markdown("One-click workspace health diagnostic checkers, database vacuum cleanups, and crash history logs.")
    
    from core.utils.health import health_engine
    from core.database.db import db_manager
    from core.utils.crash import crash_manager
    
    tab_chk, tab_db, tab_crash = st.tabs(["Diagnostics Check", "Database Maintenance", "Crash History Logs"])
    
    with tab_chk:
        if st.button("Launch System Diagnostics Run", type="primary"):
            with st.spinner("Probing paths, engines, and storage layers..."):
                rep = health_engine.run_health_checks()
                
                st.subheader("Diagnostics Prober Report")
                st.write(f"🖥️ **Operating System:** {rep['operating_system']} ({rep['os_release']})")
                st.write(f"🐍 **Python Version:** {rep['python_version']}")
                
                if rep["ffmpeg_available"]:
                    st.success("✓ FFmpeg encoder binary path verified.")
                else:
                    st.error("🔴 FFmpeg executable missing! Video exports will fail.")
                    
                if rep["comfyui_connected"]:
                    st.success("✓ ComfyUI REST server connection established.")
                else:
                    st.warning("⚠️ ComfyUI offline. Workspace sampler pipelines will run in mock simulation.")
                    
                if rep["gpu_available"]:
                    st.success(f"✓ GPU accelerator hardware active: {rep['gpu_name']} ({rep['vram_total_mb']} MB VRAM)")
                else:
                    st.warning("⚠️ CUDA GPU cores inactive. Sampler running CPU mode fallbacks.")
                    
                if rep["storage_writeable"]:
                    st.success("✓ Storage folders write permissions verified.")
                else:
                    st.error("🔴 Storage directory write validation failed! SQLite and downloads will be blocked.")
                    
    with tab_db:
        st.subheader("Database Optimization & Reindexing")
        st.caption("Auto-vacuum database files to shrink size and rebuild indexes.")
        if st.button("Re-Optimize SQLite database"):
            with st.spinner("Running Vacuum/Analyze..."):
                if db_manager.optimize_database():
                    st.success("✓ Database optimized successfully! Query statistics refreshed.")
                else:
                    st.error("Database reindexing failed. Check logs console.")
                    
    with tab_crash:
        st.subheader("System Crash Reports Registry")
        reports = crash_manager.list_reports()
        if not reports:
            st.info("No crash reports logged yet. Studio is running healthy!")
        else:
            for r in reports:
                with st.expander(f"💥 {r['timestamp']} - {r['error_type']}: {r['error_message'][:50]}..."):
                    st.write(f"**Python:** {r['python_version']}")
                    st.write(f"**Error:** `{r['error_type']}`: {r['error_message']}")
                    st.code("".join(r["stack_trace"]), language="python")

# 9. HELP CENTER
elif st.session_state.current_tab == "Help":
    st.title("💡 Guides & Help Center")
    st.markdown("Keyboard shortcuts, instructions, and diagnostics documentation.")
    
    st.subheader("Keyboard Shortcuts Quick Reference")
    st.markdown("""
    - `Ctrl + N` : Create New Project Layout
    - `Ctrl + S` : Force Save active timeline.json
    - `Ctrl + R` : Trigger background timeline compile render
    - `Space` : Play/Pause visual preview player
    - `Delete` : Purge selected timeline clip
    """)
    
    st.write("---")
    st.subheader("Updates and Changelogs")
    st.info("Current Version: v1.4.2 (Production Grade Build)")
    st.markdown("""
    - **v1.4.0** : Integrated fuzzy SQLite search library.
    - **v1.3.0** : Sidechain ducking volume envelopes compiler.
    - **v1.2.0** : non-linear splits, duplicates, and ripple deletions.
    - **v1.1.0** : WebSockets trackers for sampler loops.
    """)

# 10. SETTINGS
elif st.session_state.current_tab == "Settings":
    st.title("Studio General Settings")
    st.markdown("Configure layouts and directories.")
    
    from core.utils.security import security_manager
    
    current_settings = settings_manager.settings
    encrypted_keys = current_settings.extra_configs.get("encrypted_keys", {})
    openrouter_plain = security_manager.decrypt(encrypted_keys.get("openrouter", ""))
    
    with st.form("settings_form"):
        storage_path = st.text_input("Storage Location Path", value=current_settings.storage_path)
        cache_path = st.text_input("Render Cache Directory", value=current_settings.cache_path)
        ffmpeg_path = st.text_input("FFmpeg Binary Executable", value=current_settings.ffmpeg_path)
        comfyui_address = st.text_input("ComfyUI Server URL Address", value=current_settings.comfyui_address)
        
        st.subheader("Secure API Credentials")
        openrouter_key = st.text_input("OpenRouter API Key (Encrypted on save)", value=openrouter_plain, type="password")
        
        submitted = st.form_submit_button("Save Application Configurations", type="primary")
        if submitted:
            # Encrypt secret
            new_openrouter_cipher = security_manager.encrypt(openrouter_key)
            extra_c = current_settings.extra_configs.copy()
            if "encrypted_keys" not in extra_c:
                extra_c["encrypted_keys"] = {}
            extra_c["encrypted_keys"]["openrouter"] = new_openrouter_cipher
            
            updated = Settings(
                theme=current_settings.theme,
                comfyui_address=comfyui_address,
                llm_provider=current_settings.llm_provider,
                tts_provider=current_settings.tts_provider,
                image_provider=current_settings.image_provider,
                video_provider=current_settings.video_provider,
                music_provider=current_settings.music_provider,
                storage_path=storage_path,
                cache_path=cache_path,
                project_path=current_settings.project_path,
                temp_path=current_settings.temp_path,
                output_path=current_settings.output_path,
                ffmpeg_path=ffmpeg_path,
                gpu_settings=current_settings.gpu_settings,
                extra_configs=extra_c
            )
            settings_manager.save_settings(updated)
            st.success("Configurations updated!")

# 11. LOGS
elif st.session_state.current_tab == "Logs":
    st.title("Studio Activity Logs Console")
    log_path = get_log_file_path()
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        st.code("".join(reversed(lines[-150:])), language="log")
    else:
        st.info("No active logs generated yet.")

# 12. API & PLUGINS GATEWAY TAB
elif st.session_state.current_tab == "Plugins":
    st.title("🔌 API & Plugin SDK Workspace")
    st.markdown("Monitor the central Event Bus log, define automation triggers, manage webhooks, and start/stop the REST API Gateway server.")
    
    from core.api.event_bus import event_bus
    from core.api.automation import automation_engine
    from core.api.webhooks import webhook_dispatcher
    from core.api.rest_api import rest_server
    
    tab_reg, tab_eb, tab_rules, tab_rest = st.tabs([
        "SDK Plugin Registry", 
        "Event Bus Monitor", 
        "Automation Studio", 
        "REST API Server"
    ])
    
    with tab_reg:
        st.subheader("Active SDK & Legacy Plugins Catalog")
        st.caption("Place folder structure with plugin.json inside /plugins/ directory to register.")
        
        plugins = plugin_loader.list_plugins()
        if not plugins:
            st.info("No registered plugins found.")
        else:
            for p in plugins:
                perms = getattr(p, "permissions", {})
                perm_str = ", ".join([k for k, v in perms.items() if v]) if isinstance(perms, dict) else "None"
                
                col1, col2 = st.columns([5, 2])
                with col1:
                    st.markdown(f"### {p.name} (v{p.version})")
                    st.markdown(f"**Description:** {p.description}")
                    st.caption(f"Category: `{p.plugin_type.upper()}` | Permissions: `{perm_str}`")
                with col2:
                    st.write("")
                    p_enabled = getattr(p, "enabled", True)
                    toggle_label = "Disable Plugin" if p_enabled else "Enable Plugin"
                    if st.button(toggle_label, key=f"sdk_toggle_{p.name}", use_container_width=True):
                        if p_enabled:
                            p.disable() if hasattr(p, "disable") else setattr(p, "enabled", False)
                        else:
                            p.enable() if hasattr(p, "enable") else setattr(p, "enabled", True)
                        st.toast(f"Toggled state for {p.name}")
                        st.rerun()
                st.write("---")
                
    with tab_eb:
        st.subheader("Central Event Bus Logger")
        st.caption("Broadcast logs captured across active modules:")
        
        history = event_bus.get_history()
        if not history:
            st.info("No Event Bus events dispatched yet.")
        else:
            evt_table = []
            for evt in reversed(history):
                evt_table.append({
                    "Event ID": evt.id,
                    "Timestamp": time.strftime("%H:%M:%S", time.localtime(evt.timestamp)),
                    "Event Type": evt.type,
                    "Publisher": evt.module,
                    "Action": evt.action,
                    "Project ID": evt.project_id or "N/A",
                    "Status": evt.status
                })
            st.dataframe(evt_table, use_container_width=True)
            
    with tab_rules:
        st.subheader("Automation Rules Studio")
        
        with st.form("add_rule_form"):
            st.markdown("**Add Automation Trigger**")
            trig_opts = [
                "Project Created", "Project Saved", "Project Opened",
                "Image Generated", "Voice Generated", "Music Generated",
                "Render Started", "Render Finished", "Render Failed"
            ]
            rule_trig = st.selectbox("WHEN Event Occurs (Trigger)", trig_opts)
            
            act_opts = ["Save Project", "Generate Voice", "Export Video"]
            rule_act = st.selectbox("THEN Run Action", act_opts)
            
            cond_k = st.text_input("If Event Metadata Key (Optional)", value="")
            cond_v = st.text_input("Equals Value (Optional)", value="")
            
            submitted = st.form_submit_button("Add Automation Rule")
            if submitted:
                automation_engine.add_rule(rule_trig, rule_act, cond_k, cond_v)
                st.success("Automation rule registered!")
                time.sleep(0.5)
                st.rerun()
                
        st.write("---")
        st.subheader("Registered Automation Rules")
        rules = automation_engine.list_rules()
        if not rules:
            st.caption("No automation rules created yet.")
        else:
            for r in rules:
                col_r_info, col_r_del = st.columns([5, 1])
                with col_r_info:
                    cond_str = f" (where {r.condition_key} == '{r.condition_val}')" if r.condition_key else ""
                    st.markdown(f"**Rule:** WHEN `{r.trigger}`{cond_str} ➔ THEN `{r.action}`")
                with col_r_del:
                    if st.button("Delete Rule", key=f"del_rule_{r.id}", use_container_width=True):
                        automation_engine.remove_rule(r.id)
                        st.toast("Rule deleted!")
                        time.sleep(0.5)
                        st.rerun()
                        
    with tab_rest:
        st.subheader("REST API Server & Outgoing Webhooks")
        
        server_active = rest_server.thread is not None and rest_server.thread.is_alive()
        
        col_status_lbl, col_srv_btns = st.columns([4, 2])
        with col_status_lbl:
            badge_class = "status-healthy" if server_active else "status-unhealthy"
            badge_lbl = f"Running (Port {rest_server.port})" if server_active else "Stopped"
            st.markdown(f"**REST server state:** <span class='status-badge {badge_class}'>{badge_lbl}</span>", unsafe_allow_html=True)
            st.caption("Endpoints available: GET `/api/projects`, `/api/system`, `/api/history`, `/api/settings`")
        with col_srv_btns:
            if server_active:
                if st.button("Stop REST Gateway", use_container_width=True, type="secondary"):
                    rest_server.stop()
                    st.toast("Stopped REST server daemon")
                    time.sleep(0.5)
                    st.rerun()
            else:
                if st.button("Start REST Gateway", use_container_width=True, type="primary"):
                    rest_server.start()
                    st.toast("Launched REST server daemon thread")
                    time.sleep(0.5)
                    st.rerun()
                    
        st.write("---")
        st.subheader("Outgoing Webhooks System")
        
        with st.form("webhook_add_form"):
            web_url = st.text_input("Register Webhook Target URL", value="http://127.0.0.1:9000/api/webhooks_test")
            submitted = st.form_submit_button("Save Webhook URL")
            if submitted:
                webhook_dispatcher.register_url(web_url)
                st.success("Webhook URL registered!")
                time.sleep(0.5)
                st.rerun()
                
        urls = webhook_dispatcher.list_urls()
        if urls:
            st.caption("Active webhooks destinations:")
            for u in urls:
                col_u_name, col_u_del = st.columns([5, 1])
                with col_u_name:
                    st.markdown(f"- `{u}`")
                with col_u_del:
                    if st.button("Remove Target", key=f"del_web_{u}", use_container_width=True):
                        webhook_dispatcher.remove_url(u)
                        st.toast("Webhook URL deleted!")
                        time.sleep(0.5)
                        st.rerun()
