from core.api.plugin_sdk import SDKPlugin
from core.api.event_bus import event_bus, Event
from core.logger.custom_logger import log_action

class SampleTransitionsPlugin(SDKPlugin):
    """A sample transitions SDK plugin listening to EventBus actions."""
    def __init__(self):
        super().__init__(
            name="Sample Transitions Plugin",
            version="1.0.0",
            plugin_type="exporter",
            description="A sample transitions plugin demonstrating events subscriptions."
        )

    def initialize(self) -> bool:
        # Subscribe to EventBus notifications
        event_bus.subscribe("Project Created", self.on_project_created)
        log_action("SamplePlugin", "Initialize", "SUCCESS", 0.0, "Sample transitions plugin initialized.")
        return True

    def on_project_created(self, evt: Event):
        # Callback custom handler
        log_action("SamplePlugin", "OnProjectCreated", "INFO", 0.0, f"Sample plugin caught event: Project {evt.project_id} created.")

    def unload(self):
        # Unsubscribe to clean up
        event_bus.unsubscribe("Project Created", self.on_project_created)
        log_action("SamplePlugin", "Unload", "SUCCESS", 0.0, "Sample transitions plugin unloaded.")
