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

## How to Set Up and Run the Application

Follow these step-by-step instructions to get Nova Studio AI running on your local machine:

### Prerequisites
Make sure you have **Python 3.10 or 3.11** installed on your system.

### 1. Clone the Repository
Clone this repository to your local workspace:
```bash
git clone https://github.com/<your-username>/nova-studio-ai.git
cd nova-studio-ai
```

### 2. Create a Virtual Environment (Recommended)
Set up a clean virtual environment to prevent dependency conflicts:
```bash
# On Windows
python -m venv venv
venv\Scripts\activate

# On Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
Install all required libraries specified in requirements list:
```bash
pip install -r requirements.txt
```

### 4. Configure settings (Optional)
On first run, the application will automatically initialize standard configuration folders and create an SQLite database. If you have custom executable paths (e.g., custom FFmpeg location or ComfyUI server port), you can edit the generated `core/config/settings.json` file or adjust them directly in the UI settings dashboard.

### 5. Launch the Streamlit Studio UI
Start the Streamlit application server using:
```bash
streamlit run app.py
```
After executing this command, Streamlit will compile the server and output local network pointers:
```text
  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.1.100:8501
```
Your default browser should open automatically to **`http://localhost:8501`**. If it does not, copy and paste that address into your browser manually.

### 6. Query Local REST API
To verify the background REST Gateway is running:
```bash
curl http://127.0.0.1:9000/api/system
```

## Running Verification Tests
To run the automated validation tests:
```bash
python -m unittest discover tests
```
