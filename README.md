# Nova Studio AI - Professional Creative AI Workspace

Nova Studio AI is a production-grade, local, and offline non-linear video creation studio. It orchestrates a modular pipeline of AI Agents (Script, Voice, Storyboard, Timeline Compiler) to convert raw ideas into complete editable video exports.

## Core Features

- **Decoupled Event Bus Architecture**: Fully decoupled event-driven communication (modules publish and subscribe through a thread-safe broker).
- **Non-Linear Timeline Editor**: Supports splits, duplicate clones, ripple deletes, track lane visuals, and rollback history snapshots.
- **Vocal Narration & Sidechain Ducking**: Kokoro TTS integration with phoneme-level viseme lip sync and automatic soundtrack volume ducking.
- **Central Asset Search**: Fuzzy search indexing across characters metadata, clip scripts, and project structures.
- **REST API Gateway**: Spawns built-in daemon http server on port 9000 with outgoing webhook notifications.
- **Diagnostics & Auto-optimizer**: Health verification checks (GPU, ComfyUI, FFmpeg) and database auto-vacuum tools.

## Folder Directory Structure

```text
nova-studio/
├── core/
│   ├── api/            # EventBus, APIGateway, RESTServer, TaskQueue, Webhooks
│   ├── comfy/          # ComfyUI Connectors & Workflow Managers
│   ├── timeline/       # NLE Timeline cuts, snapshots versions
│   ├── generation/     # Structured prompts, characters consistency profile
│   ├── audio/          # Subtitle karaoke compilers, sidechain ducking, TTS
│   ├── database/       # SQLite storage indexing & tables
│   ├── logger/         # Rotating action logger
│   └── plugins/        # swappable provider script loaders
├── plugins/            # folder-based SDK plugins (e.g. sample_plugin)
├── tests/              # unit test suites
├── app.py              # Streamlit dashboard
├── requirements.txt    # dependencies list
└── README.md           # user guide
```

## Quick Start Guide

### 1. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 2. Launch Studio UI
```powershell
python -m streamlit run app.py
```

### 3. Query Local REST API
To verify the background REST Gateway is running:
```bash
curl http://127.0.0.1:9000/api/system
```

## Running Verification Tests
Execute the full test suite:
```powershell
python -m unittest discover tests
```
