import uuid
import time
import threading
from typing import Dict, Any, List, Optional
from core.logger.custom_logger import log_action
from core.comfy.connector import comfy_connector

class Job:
    """Represents an execution job within the ComfyUI pipeline."""
    def __init__(self, workflow_name: str, project_id: str, prompt_id: Optional[str] = None):
        self.id = prompt_id or f"job_{str(uuid.uuid4())[:8]}"
        self.workflow_name = workflow_name
        self.project_id = project_id
        
        # waiting, running, completed, failed, cancelled
        self.status = "Waiting"
        self.progress_pct = 0.0
        self.current_stage = "Preparing"
        self.current_node_id = ""
        self.current_node_type = ""
        self.current_step = 0
        self.total_steps = 0
        
        self.start_time = time.time()
        self.end_time = 0.0
        self.error_message = ""
        self.output_files: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "workflow_name": self.workflow_name,
            "project_id": self.project_id,
            "status": self.status,
            "progress_pct": self.progress_pct,
            "current_stage": self.current_stage,
            "current_node_id": self.current_node_id,
            "current_node_type": self.current_node_type,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "elapsed_time": round(time.time() - self.start_time, 1) if self.end_time == 0.0 else round(self.end_time - self.start_time, 1),
            "error_message": self.error_message,
            "output_files": self.output_files
        }

class QueueManager:
    """
    Manages job states, schedules execution threads, and triggers cancellations.
    """
    def __init__(self):
        self.lock = threading.Lock()
        self.jobs: Dict[str, Job] = {}
        self.active_jobs_queue: List[str] = []

    def get_job(self, job_id: str) -> Optional[Job]:
        with self.lock:
            return self.jobs.get(job_id)

    def list_jobs(self) -> List[Job]:
        with self.lock:
            return list(self.jobs.values())

    def add_job(self, job: Job):
        with self.lock:
            self.jobs[job.id] = job
            self.active_jobs_queue.append(job.id)

    def cancel_job(self, job_id: str) -> bool:
        """Interrupts and stops a job execution."""
        job = self.get_job(job_id)
        if not job:
            return False
            
        with self.lock:
            job.status = "Cancelled"
            job.current_stage = "Aborted"
            job.end_time = time.time()
            if job_id in self.active_jobs_queue:
                self.active_jobs_queue.remove(job_id)
                
        # Send cancel request to ComfyUI if online
        if comfy_connector.is_connected:
            success, _, err = comfy_connector.post("/interrupt")
            if success:
                log_action("QueueManager", "CancelJob", "SUCCESS", 0.0, f"Interrupted ComfyUI server for job {job_id}")
                return True
            else:
                log_action("QueueManager", "CancelJob", "FAILED", 0.0, f"Failed to interrupt ComfyUI: {err}")
        
        log_action("QueueManager", "CancelJob", "SUCCESS", 0.0, f"Cancelled job locally: {job_id}")
        return True

    def simulate_offline_job(self, job_id: str, execute_callback: Any):
        """Simulates running a job offline for demonstration and fallback workflows."""
        job = self.get_job(job_id)
        if not job:
            return
            
        def run_simulation():
            try:
                # Stages: Preparing, Uploading Assets, Running Nodes, Completed
                stages = [
                    ("Preparing", 0.0, 10),
                    ("Uploading Assets", 0.1, 20),
                    ("Running Node: Load Checkpoint [Node 4]", 0.3, 30),
                    ("Running Node: CLIP Text Encode [Node 6]", 0.5, 45),
                    ("Running Node: KSampler [Node 3]", 0.7, 75),
                    ("Running Node: VAE Decode [Node 8]", 0.9, 90),
                    ("Downloading Results", 0.95, 95)
                ]
                
                for stage_name, progress_ratio, pct in stages:
                    time.sleep(0.5)
                    with self.lock:
                        if job.status == "Cancelled":
                            return
                        job.status = "Running"
                        job.current_stage = stage_name
                        job.progress_pct = float(pct)
                        
                        if "KSampler" in stage_name:
                            job.total_steps = 20
                            # simulate step counting
                            for step in range(1, 21):
                                if job.status == "Cancelled":
                                    return
                                job.current_step = step
                                # increment progress slightly
                                job.progress_pct = 45.0 + (step / 20.0) * 30.0
                                time.sleep(0.08)
                                
                # Run actual generator code (mock outputs saving)
                outputs = execute_callback()
                
                with self.lock:
                    if job.status == "Cancelled":
                        return
                    job.status = "Completed"
                    job.progress_pct = 100.0
                    job.current_stage = "Completed"
                    job.output_files = outputs
                    job.end_time = time.time()
                    
                log_action("QueueManager", "SimulateJob", "SUCCESS", time.time() - job.start_time, f"Simulated job {job_id} finished.")
            except Exception as e:
                with self.lock:
                    job.status = "Failed"
                    job.error_message = str(e)
                    job.end_time = time.time()
                log_action("QueueManager", "SimulateJob", "FAILED", 0.0, f"Simulated job failed: {str(e)}")

        t = threading.Thread(target=run_simulation, daemon=True, name=f"Simulate_{job_id}")
        t.start()

# Singleton QueueManager
queue_manager = QueueManager()
