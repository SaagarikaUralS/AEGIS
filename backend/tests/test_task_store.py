from app.orchestrator.task_store import task_store


task1 = task_store.create_task(
    case_id="CASE-001",
    agent_id="entity_extraction",
    description="Extract entities from RAW-001",
    evidence_ids=["RAW-001"],
)

task2 = task_store.create_task(
    case_id="CASE-001",
    agent_id="lead_intelligence",
    description="Generate leads from CASE-001 findings",
)

task_store.add_dependency(
    task2["task_id"],
    task1["task_id"],
)

print("TASK 1")
print(task1)

print("\nTASK 2")
print(task_store.get_task(task2["task_id"]))