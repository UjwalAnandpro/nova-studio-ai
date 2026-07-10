import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable
from core.logger.custom_logger import log_action

class BaseAgent(ABC):
    """
    Abstract Base Class for all pipeline agents.
    Provides standard settings, execution wrappers, token counters and auto-retry frameworks.
    """
    def __init__(self, name: str):
        self._name = name
        self.enabled = True
        self.priority = 10
        self.provider = "Default"
        self.timeout = 30.0
        self.retries = 3
        self.concurrency = 1
        
        # Token and cost tracking metrics
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.estimated_cost = 0.0

    @property
    def name(self) -> str:
        return self._name

    @abstractmethod
    def run(self, project_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the agent's specific responsibility.
        Args:
            project_id: The target project workspace ID
            context: State context dictionary passed down from PipelineManager
        Returns:
            Updated context dictionary containing new generated metadata/assets
        """
        pass

    def log(self, action: str, status: str, duration: float = 0.0, message: str = ""):
        """Helper to log structured agent actions."""
        log_action(f"Agent:{self.name}", action, status, duration, message)

    def track_tokens(self, prompt: int, completion: int, cost_per_k_prompt: float = 0.0015, cost_per_k_completion: float = 0.002):
        """Accumulates prompt/completion tokens and estimates operation costs."""
        self.prompt_tokens += prompt
        self.completion_tokens += completion
        # Cost estimate
        self.estimated_cost += (prompt / 1000.0) * cost_per_k_prompt + (completion / 1000.0) * cost_per_k_completion

    def execute_with_retry(self, action_name: str, func: Callable, *args, **kwargs) -> Any:
        """
        Executes a block of code wrapped in an auto-retry engine.
        Handles rate limits, temporary timeouts and database lock failures.
        """
        last_error = None
        start_time = time.time()
        
        for attempt in range(1, self.retries + 1):
            try:
                self.log(action_name, "INFO", 0.0, f"Attempt {attempt}/{self.retries}...")
                res = func(*args, **kwargs)
                duration = time.time() - start_time
                self.log(action_name, "SUCCESS", duration, f"Execution completed successfully.")
                return res
            except Exception as e:
                last_error = e
                duration = time.time() - start_time
                self.log(action_name, "WARNING", duration, f"Attempt {attempt} failed: {str(e)}")
                if attempt < self.retries:
                    # Exponential backoff sleep: 1s, 2s, 4s...
                    time.sleep(2 ** (attempt - 1))
                    
        duration = time.time() - start_time
        self.log(action_name, "FAILED", duration, f"All retry attempts exhausted: {str(last_error)}")
        raise last_error
