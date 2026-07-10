# Nova Studio AI - Developer & Plugin SDK Manual

This guide describes the internals of Nova Studio AI, how to extend providers, write automation rules, and customize plugins.

## 1. Event-Driven Architecture

All core systems broadcast their state changes to the `EventBus` singleton. To write custom listeners:

```python
from core.api.event_bus import event_bus, Event

def my_callback(evt: Event):
    print(f"Captured Event ID {evt.id} - Type: {evt.type}")

# Subscribe globally
event_bus.subscribe("*", my_callback)
```

## 2. Plugin SDK

Plugins reside under `plugins/<name>/` and must contain:
1. `plugin.json`: Metadata, categories, and declared system permissions.
2. `main.py`: A subclass of `SDKPlugin` (or specialized sub-classes like `VoiceProvider`, `ImageProvider`).

### Example plugin.json
```json
{
    "id": "my_tts_plugin",
    "name": "Local Custom TTS",
    "version": "1.0.0",
    "category": "tts",
    "permissions": {
        "filesystem": true,
        "network": false,
        "gpu": false,
        "external_processes": false
    }
}
```

### Example main.py
```python
from core.api.plugin_sdk import VoiceProvider

class CustomTTSPlugin(VoiceProvider):
    def __init__(self):
        super().__init__(
            name="Local Custom TTS",
            version="1.0.0",
            description="Example custom SDK speech synthesis provider plugin."
        )

    def generate_speech(self, text: str, output_path: str, voice: str = "Default", speed: float = 1.0):
        # Implementation details...
        pass
```

## 3. Future Roadmap Details

Nova Studio AI is architected to scale into:
- **AI Motion Capture & Lip Sync**: Automatically generating lip-sync tracks using audio waveforms matched to avatar head frames.
- **AI Translation & Multi-Language Dubbing**: Translating generated SRT files, re-narrating dialogue tracks, and matching pitch envelopes.
- **Distributed Rendering Nodes**: Dispatching FFmpeg build instructions to remote worker pools.
