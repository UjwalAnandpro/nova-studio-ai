# Release Notes - Nova Studio AI v1.0.0 (Production Release)

We are thrilled to present the initial production release of **Nova Studio AI (v1.0.0)**! 

Nova Studio AI is an offline-capable, local video creation workspace orchestrating modular pipelines of AI Agents to convert text ideas into complete editable video exports.

## Key Features

- **Decoupled API & Event Bus**: Central communication bus for thread-safe asynchronous operations.
- **Dynamic Plugin SDK**: Dynamic folder scanning for custom LLM, TTS, Image, Video, and Music providers.
- **Non-Linear Timeline Editor**: Cuts, clones, and ripple deletions.
- **Vocal Narration & Sidechain Ducking**: Integrated Kokoro-82M TTS and automatic soundtrack volume ducking.
- **Local Diagnostics & vacuum database**: Diagnostic health verification and automatic SQLite vacuums.

## Dependencies

- Python 3.10 / 3.11
- FFmpeg 5.0+
- SQLite 3
- Streamlit 1.30+

## Known Issues

- **ComfyUI Server Sync**: Ensure your local ComfyUI server is running on port 8188. If offline, the studio samplers run in mock simulation fallback.
