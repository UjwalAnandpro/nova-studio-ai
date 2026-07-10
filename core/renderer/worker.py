import os
import subprocess
import threading
import time
import re
import uuid
from typing import Dict, List, Any, Optional
from core.config.manager import settings_manager
from core.projects.manager import project_manager
from core.logger.custom_logger import log_action

class RenderJob:
    """Represents a video rendering job in the queue."""
    def __init__(self, project_id: str, output_path: str, command: List[str], total_duration: float):
        self.id = f"render_{str(uuid.uuid4())[:8]}"
        self.project_id = project_id
        self.output_path = output_path
        self.command = command
        self.total_duration = total_duration
        
        # Queued, Running, Completed, Cancelled, Failed
        self.status = "Queued"
        self.progress_pct = 0.0
        self.start_time = 0.0
        self.end_time = 0.0
        self.fps = 0.0
        self.speed = "0.0x"
        self.logs: List[str] = []
        self.error_message = ""

    def to_dict(self) -> Dict[str, Any]:
        elapsed = 0.0
        if self.start_time > 0.0:
            elapsed = time.time() - self.start_time if self.end_time == 0.0 else self.end_time - self.start_time
            
        return {
            "id": self.id,
            "project_id": self.project_id,
            "output_path": self.output_path,
            "status": self.status,
            "progress_pct": round(self.progress_pct, 1),
            "elapsed_time": round(elapsed, 1),
            "fps": self.fps,
            "speed": self.speed,
            "error_message": self.error_message,
            "log_lines_count": len(self.logs)
        }

class RenderQueue:
    """
    Manages background execution of FFmpeg render jobs.
    Runs a worker thread that processes queued rendering tasks.
    """
    def __init__(self):
        self.lock = threading.Lock()
        self.jobs: Dict[str, RenderJob] = {}
        self.queue: List[str] = []
        self.current_job_id: Optional[str] = None
        self._process: Optional[subprocess.Popen] = None
        
        # Start worker daemon thread
        self._worker_thread = threading.Thread(target=self._process_queue_loop, daemon=True, name="RenderQueueWorker")
        self._worker_thread.start()

    def add_job(self, project_id: str, output_path: str, command: List[str], total_duration: float) -> str:
        """Adds a rendering job to the queue."""
        job = RenderJob(project_id, output_path, command, total_duration)
        with self.lock:
            self.jobs[job.id] = job
            self.queue.append(job.id)
        log_action("RenderQueue", "AddJob", "SUCCESS", 0.0, f"Added render job {job.id} for project {project_id}")
        return job.id

    def cancel_job(self, job_id: str) -> bool:
        """Cancels a queued or currently running render job."""
        with self.lock:
            if job_id not in self.jobs:
                return False
                
            job = self.jobs[job_id]
            if job.status == "Queued":
                job.status = "Cancelled"
                if job_id in self.queue:
                    self.queue.remove(job_id)
                return True
                
            if job.status == "Running" and self.current_job_id == job_id:
                job.status = "Cancelled"
                job.end_time = time.time()
                # Terminate subprocess
                if self._process:
                    try:
                        self._process.kill()
                    except Exception:
                        pass
                return True
                
        return False

    def get_job(self, job_id: str) -> Optional[RenderJob]:
        with self.lock:
            return self.jobs.get(job_id)

    def list_jobs(self) -> List[RenderJob]:
        with self.lock:
            return list(self.jobs.values())

    def _process_queue_loop(self):
        """Infinite loop polling for queued rendering jobs."""
        while True:
            job_id = None
            with self.lock:
                if self.queue:
                    job_id = self.queue.pop(0)
                    self.current_job_id = job_id
                    
            if job_id:
                self._run_render_job(job_id)
                with self.lock:
                    self.current_job_id = None
            else:
                time.sleep(1.0)

    def _run_render_job(self, job_id: str):
        job = self.get_job(job_id)
        if not job or job.status == "Cancelled":
            return
            
        job.status = "Running"
        job.start_time = time.time()
        
        ffmpeg_bin = settings_manager.settings.ffmpeg_path
        cmd = [ffmpeg_bin] + job.command
        
        log_action("RenderWorker", "StartRender", "INFO", 0.0, f"Running: {' '.join(cmd[:10])}...")
        
        try:
            # Popen reads progress pipes
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                encoding="utf-8",
                errors="replace"
            )
            
            # Pattern to parse time progress e.g., time=00:00:05.12
            time_pattern = re.compile(r"time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})")
            fps_pattern = re.compile(r"fps=\s*([\d\.]+)")
            speed_pattern = re.compile(r"speed=\s*([\d\.]+)x")
            
            while True:
                line = self._process.stdout.readline()
                if not line:
                    break
                    
                # Store log line
                job.logs.append(line.strip())
                
                # Parse progress
                time_match = time_pattern.search(line)
                if time_match:
                    hours, mins, secs, centis = map(int, time_match.groups())
                    curr_seconds = hours * 3600 + mins * 60 + secs + centis / 100.0
                    
                    # Update percentage
                    if job.total_duration > 0:
                        pct = (curr_seconds / job.total_duration) * 100.0
                        job.progress_pct = min(99.0, pct)
                        
                # Parse FPS
                fps_match = fps_pattern.search(line)
                if fps_match:
                    job.fps = float(fps_match.group(1))
                    
                # Parse Speed
                speed_match = speed_pattern.search(line)
                if speed_match:
                    job.speed = f"{speed_match.group(1)}x"
                    
            self._process.wait()
            return_code = self._process.returncode
            
            if job.status == "Cancelled":
                log_action("RenderWorker", "Render", "WARNING", 0.0, f"Job {job.id} cancelled by user.")
                return
                
            if return_code == 0:
                job.status = "Completed"
                job.progress_pct = 100.0
                log_action("RenderWorker", "Render", "SUCCESS", time.time() - job.start_time, f"Render finished successfully: {job.output_path}")
            else:
                job.status = "Failed"
                # Get last few lines of logs to formulate error message
                err_logs = [line for line in job.logs if "Error" in line or "failed" in line.lower()]
                job.error_message = err_logs[-1] if err_logs else f"FFmpeg failed with exit code {return_code}"
                log_action("RenderWorker", "Render", "FAILED", 0.0, f"Render failed: {job.error_message}")
                
        except Exception as e:
            if job.status != "Cancelled":
                job.status = "Failed"
                job.error_message = str(e)
                log_action("RenderWorker", "Render", "FAILED", 0.0, f"Render exception: {str(e)}")
        finally:
            job.end_time = time.time()
            self._process = None

# Singleton RenderQueue
render_queue = RenderQueue()
