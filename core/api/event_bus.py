import time
import uuid
import threading
from typing import Dict, List, Any, Callable

class Event:
    """Represents a standard event published inside the application."""
    def __init__(self, event_type: str, module: str, action: str, 
                 project_id: Optional[str] = None, asset_id: Optional[str] = None, 
                 status: str = "SUCCESS", metadata: Optional[Dict[str, Any]] = None):
        self.id = f"evt_{str(uuid.uuid4())[:8]}"
        self.timestamp = round(time.time(), 2)
        self.type = event_type
        self.module = module
        self.action = action
        self.project_id = project_id
        self.asset_id = asset_id
        self.status = status
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "type": self.type,
            "module": self.module,
            "action": self.action,
            "project_id": self.project_id,
            "asset_id": self.asset_id,
            "status": self.status,
            "metadata": self.metadata
        }

def Optional(type_hint):
    return type_hint

class EventBus:
    """Central thread-safe Event Bus matching publish-subscribe architecture."""
    def __init__(self):
        self.lock = threading.Lock()
        self.subscribers: Dict[str, List[Callable[[Event], None]]] = {}
        self.event_history: List[Event] = []

    def subscribe(self, event_type: str, callback: Callable[[Event], None]):
        """Binds a callback listener to an event type."""
        with self.lock:
            if event_type not in self.subscribers:
                self.subscribers[event_type] = []
            self.subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Callable[[Event], None]):
        """Removes a listener callback."""
        with self.lock:
            if event_type in self.subscribers and callback in self.subscribers[event_type]:
                self.subscribers[event_type].remove(callback)

    def publish(self, event_type: str, module: str, action: str, 
                project_id: Optional[str] = None, asset_id: Optional[str] = None, 
                status: str = "SUCCESS", metadata: Optional[Dict[str, Any]] = None) -> Event:
        """Assembles and broadcasts an event to all active listeners."""
        evt = Event(event_type, module, action, project_id, asset_id, status, metadata)
        
        with self.lock:
            self.event_history.append(evt)
            # Cap history to last 100 events
            if len(self.event_history) > 100:
                self.event_history.pop(0)
                
            # Broadcast to specific listeners
            listeners = list(self.subscribers.get(event_type, []))
            # Broadcast to wildcard listeners
            wildcard_listeners = list(self.subscribers.get("*", []))
            
        # Trigger callbacks (outside lock to prevent deadlocks)
        for cb in listeners + wildcard_listeners:
            try:
                cb(evt)
            except Exception:
                pass
                
        return evt

    def get_history(self) -> List[Event]:
        with self.lock:
            return list(self.event_history)

# Singleton EventBus
event_bus = EventBus()
