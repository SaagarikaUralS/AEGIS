import threading
import time
from concurrent.futures import ThreadPoolExecutor

from app.orchestrator.task_store import task_store
from app.orchestrator.task_graph import execute_task

from app.services.execution_service import (
    create_execution,
    start_agent_execution,
    complete_agent_execution,
    fail_agent_execution,
    complete_execution,
)

AGENT_CAPACITY = {
    "entity_extraction": 2,
    "correlation": 2,
    "lead_intelligence": 2,
    "victim_safeguarding": 1,
}


class TaskScheduler:

    def __init__(self):
        self.executor = ThreadPoolExecutor(
            max_workers=sum(AGENT_CAPACITY.values())
        )

        self.scheduler_thread = None
        self.lock = threading.Lock()

    def start(self):

        with self.lock:

            if (
                self.scheduler_thread
                and self.scheduler_thread.is_alive()
            ):
                return

            self.scheduler_thread = threading.Thread(
                target=self._run_loop,
                daemon=True,
            )

            self.scheduler_thread.start()

    def _run_loop(self):

        while True:

            task_store.refresh_waiting_tasks()

            ready_tasks = task_store.get_ready_tasks()

            scheduled_any = False

            for task in ready_tasks:

                agent_id = task["agent_id"]

                running = task_store.get_running_count(
                    agent_id
                )

                capacity = AGENT_CAPACITY.get(
                    agent_id,
                    1,
                )

                if running >= capacity:
                    continue

                task_store.mark_running(
                    task["task_id"]
                )

                self.executor.submit(
                    self._execute,
                    task["task_id"],
                )

            time.sleep(0.5)

    def _execute(self, task_id: str):

        task = task_store.get_task(task_id)

        if not task:
            return

        execution_id = None
        agent_execution_id = None

        try:

            print(
                f"[ORCHESTRATOR] Starting {task_id} "
                f"-> {task['agent_id']}"
            )

            # ----------------------------------------
            # Create execution record
            # ----------------------------------------

            execution_id = create_execution(
                case_id=task["case_id"],
                task_id=task_id,
            )

            agent_execution_id = start_agent_execution(
                execution_id=execution_id,
                agent_id=task["agent_id"],
                task_id=task_id,
            )

            # ----------------------------------------
            # Execute actual LangGraph task
            # ----------------------------------------

            result = execute_task(task)

            # ----------------------------------------
            # Mark agent execution complete
            # ----------------------------------------

            complete_agent_execution(
                agent_execution_id,
                result_summary=str(result)[:2000],
            )

            complete_execution(
                execution_id,
                status="COMPLETED",
            )

            # ----------------------------------------
            # Mark task complete
            # ----------------------------------------

            task_store.mark_completed(
                task_id
            )

            print(
                f"[ORCHESTRATOR] Completed {task_id}"
            )

        except Exception as exc:

            error = str(exc)

            print(
                f"[ORCHESTRATOR] Failed {task_id}: "
                f"{error}"
            )

            # ----------------------------------------
            # Record execution failure
            # ----------------------------------------

            if agent_execution_id:

                fail_agent_execution(
                    agent_execution_id,
                    error,
                )

            if execution_id:

                complete_execution(
                    execution_id,
                    status="PARTIAL_FAILURE",
                )

            # ----------------------------------------
            # Retry logic
            # ----------------------------------------

            updated_task = task_store.get_task(
                task_id
            )

            attempts = updated_task["attempts"]

            max_retries = updated_task["max_retries"]

            if attempts < max_retries:

                task_store.mark_ready_for_retry(
                    task_id,
                    error,
                )

                print(
                    f"[ORCHESTRATOR] Retrying {task_id}"
                )

            else:

                task_store.mark_human_review(
                    task_id,
                    error,
                )

                print(
                    f"[ORCHESTRATOR] "
                    f"{task_id} requires HUMAN REVIEW"
                )


scheduler = TaskScheduler()