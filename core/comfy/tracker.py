import asyncio
import json
import threading
import aiohttp
from typing import Optional
from core.logger.custom_logger import log_action
from core.config.manager import settings_manager
from core.comfy.queue_manager import queue_manager, Job

class ComfyWebSocketTracker:
    """
    Asynchronously listens to the ComfyUI WebSocket channel.
    Updates the QueueManager Job states in real-time as ComfyUI runs nodes.
    """
    def __init__(self):
        self.client_id = "nova_studio_client"
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
    def start(self):
        """Starts the background asyncio thread for WebSocket listening."""
        if self._thread and self._thread.is_alive():
            return
            
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_async_loop, daemon=True, name="ComfyWSListener")
        self._thread.start()

    def stop(self):
        """Stops the WebSocket listener thread."""
        self._stop_event.set()
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread:
            self._thread.join(timeout=1.0)

    def _run_async_loop(self):
        """Initializes and runs the asyncio event loop inside the background thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        
        try:
            self._loop.run_until_complete(self._websocket_listener())
        except Exception as e:
            log_action("WebSocketTracker", "AsyncLoop", "WARNING", 0.0, f"WebSocket listener thread exited: {str(e)}")
        finally:
            self._loop.close()

    async def _websocket_listener(self):
        """Main WebSocket loop utilizing aiohttp."""
        server_addr = settings_manager.settings.comfyui_address.replace("http://", "ws://").replace("https://", "wss://").rstrip('/')
        url = f"{server_addr}/ws?clientId={self.client_id}"
        
        log_action("WebSocketTracker", "Connect", "INFO", 0.0, f"WS Client connecting to {url}")
        
        while not self._stop_event.is_set():
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.ws_connect(url) as ws:
                        log_action("WebSocketTracker", "Connect", "SUCCESS", 0.0, "WebSocket link to ComfyUI activated.")
                        
                        async for msg in ws:
                            if self._stop_event.is_set():
                                break
                                
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                data = json.loads(msg.data)
                                await self._handle_ws_message(data)
                            elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                                break
                                
            except Exception as e:
                # Connection refused or closed - sleep and retry
                await asyncio.sleep(5.0)

    async def _handle_ws_message(self, message: dict):
        """Parses ComfyUI websocket packets and updates active job properties."""
        msg_type = message.get("type")
        data = message.get("data", {})
        
        prompt_id = data.get("prompt_id")
        if not prompt_id:
            return
            
        job = queue_manager.get_job(prompt_id)
        if not job:
            return
            
        if msg_type == "status":
            # queue state update
            pass
            
        elif msg_type == "execution_start":
            job.status = "Running"
            job.current_stage = "Executing Nodes"
            job.progress_pct = 5.0
            log_action("WebSocketTracker", "JobStart", "INFO", 0.0, f"ComfyUI started processing job {job.id}")
            
        elif msg_type == "executing":
            node_id = data.get("node")
            if node_id:
                job.current_node_id = str(node_id)
                job.current_stage = f"Running node {node_id}"
                log_action("WebSocketTracker", "NodeRun", "DEBUG", 0.0, f"Job {job.id} executing node {node_id}")
            else:
                # Completed execution on server
                job.status = "Completed"
                job.progress_pct = 100.0
                job.current_stage = "Finished"
                job.end_time = time.time()
                
        elif msg_type == "progress":
            current_step = data.get("value", 0)
            total_steps = data.get("max", 1)
            node_id = data.get("node")
            
            job.current_step = current_step
            job.total_steps = total_steps
            job.current_node_id = str(node_id)
            
            # Map progress to percentage (e.g. baseline 10% to 90%)
            step_ratio = current_step / total_steps if total_steps > 0 else 0
            job.progress_pct = round(10.0 + step_ratio * 80.0, 1)
            job.current_stage = f"Rendering (Step {current_step}/{total_steps})"
            
        elif msg_type == "executed":
            node_id = data.get("node")
            output = data.get("output", {})
            
            # Extract filenames generated by node
            images = output.get("images", [])
            for img in images:
                fn = img.get("filename")
                if fn:
                    job.output_files.append(fn)
                    
            log_action("WebSocketTracker", "NodeExecuted", "SUCCESS", 0.0, f"Node {node_id} generated output files: {job.output_files}")
            
        elif msg_type == "execution_error":
            job.status = "Failed"
            job.end_time = time.time()
            job.current_stage = "Execution Error"
            job.error_message = data.get("exception_message", "Node failed execution")
            log_action("WebSocketTracker", "JobError", "FAILED", 0.0, f"Job {job.id} execution error: {job.error_message}")

# Singleton tracker instance
websocket_tracker = ComfyWebSocketTracker()
# Auto start tracker thread on import
websocket_tracker.start()
