import time
import uuid
import threading
from typing import Dict, List, Any, Callable, Optional

class QueueTask:
    def __init__(self, task_id: str, name: str, action: Callable[[], Any], priority: int = 1):
        self.id = task_id
        self.name = name
        self.action = action
        self.priority = priority # Higher runs first
        self.status = "queued" # queued, running, completed, failed, cancelled
        self.error: Optional[str] = None
        self.timestamp = time.time()

class TaskQueue:
    """Central Task Queue supporting priorities, pauses, resumes and background execution."""
    def __init__(self):
        self.lock = threading.Lock()
        self.tasks: Dict[str, QueueTask] = {}
        self.paused = False
        self.running = True
        
        # Spawn queue processing worker thread
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True, name="TaskQueueWorker")
        self.worker_thread.start()

    def add_task(self, name: str, action: Callable[[], Any], priority: int = 1) -> str:
        tid = f"task_{str(uuid.uuid4())[:8]}"
        task = QueueTask(tid, name, action, priority)
        with self.lock:
            self.tasks[tid] = task
        return tid

    def cancel_task(self, task_id: str):
        with self.lock:
            if task_id in self.tasks:
                self.tasks[task_id].status = "cancelled"

    def pause(self):
        with self.lock:
            self.paused = True

    def resume(self):
        with self.lock:
            self.paused = False

    def list_tasks(self) -> List[QueueTask]:
        with self.lock:
            return list(self.tasks.values())

    def _worker_loop(self):
        while self.running:
            time.sleep(0.1)
            
            with self.lock:
                if self.paused:
                    continue
                    
                # Find highest priority queued task
                queued_tasks = [t for t in self.tasks.values() if t.status == "queued"]
                if not queued_tasks:
                    continue
                    
                # Sort by priority desc, then timestamp asc
                queued_tasks.sort(key=lambda x: (-x.priority, x.timestamp))
                target_task = queued_tasks[0]
                target_task.status = "running"
                
            # Process action outside lock
            try:
                target_task.action()
                target_task.status = "completed"
            except Exception as e:
                target_task.status = "failed"
                target_task.error = str(e)

# Singleton TaskQueue
task_queue = TaskQueue()
