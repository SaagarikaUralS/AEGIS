import re
from typing import Literal

from pydantic import BaseModel, Field
from langchain_ollama import ChatOllama


AGENT_IDS = [
    "entity_extraction",
    "correlation",
    "lead_intelligence",
    "victim_safeguarding",
]


class PlannedTask(BaseModel):

    case_id: str | None = None

    agent_id: Literal[
        "entity_extraction",
        "correlation",
        "lead_intelligence",
        "victim_safeguarding",
    ]

    description: str

    evidence_ids: list[str] = Field(
        default_factory=list
    )

    priority: int = 5

    depends_on_indexes: list[int] = Field(
        default_factory=list
    )


class TaskPlan(BaseModel):

    tasks: list[PlannedTask]


llm = ChatOllama(
    model="llama3.2:3b",
    temperature=0,
)

planner = llm.with_structured_output(
    TaskPlan
)


# --------------------------------------------------
# Deterministic helpers
# --------------------------------------------------

def extract_case_ids(command: str) -> list[str]:

    return re.findall(
        r"\bCASE-\d+\b",
        command.upper(),
    )


def extract_evidence_ids(command: str) -> list[str]:

    return re.findall(
        r"\b(?:RAW|EVID)-\d+\b",
        command.upper(),
    )


def contains_any(
    text: str,
    words: list[str],
) -> bool:

    text = text.lower()

    return any(
        word in text
        for word in words
    )


# --------------------------------------------------
# Deterministic planner
# --------------------------------------------------

def deterministic_plan(
    command: str,
    default_case_id: str | None = None,
):
    text = command.strip()

    tasks = []

    # ---------------------------------------------------------
    # Helper
    # ---------------------------------------------------------

    def add_task(
        agent_id: str,
        case_id: str | None,
        description: str,
        evidence_ids: list[str] | None = None,
    ):
        if not case_id:
            case_id = default_case_id

        if not case_id:
            return

        tasks.append(
            PlannedTask(
                case_id=case_id,
                agent_id=agent_id,
                description=description,
                evidence_ids=evidence_ids or [],
            )
        )

    # ---------------------------------------------------------
    # Evidence IDs
    # ---------------------------------------------------------

    evidence_ids = extract_evidence_ids(text)

    # ---------------------------------------------------------
    # ENTITY EXTRACTION
    # ---------------------------------------------------------

    entity_match = re.search(
        r"(?:extract entit(?:y|ies)|entity extraction|"
        r"identify entities|parse evidence)"
        r"(?:\s+(?:from|in))?\s*"
        r"((?:RAW|EVID)-\d+(?:\s*,\s*(?:RAW|EVID)-\d+)*)",
        text,
        re.IGNORECASE,
    )

    if entity_match:
        ids = re.findall(
            r"(?:RAW|EVID)-\d+",
            entity_match.group(1),
            re.IGNORECASE,
        )

        case_ids = extract_case_ids(text)

        add_task(
            agent_id="entity_extraction",
            case_id=case_ids[0] if case_ids else default_case_id,
            description=f"Extract entities from {', '.join(ids)}",
            evidence_ids=ids,
        )

    # ---------------------------------------------------------
    # VICTIM SAFEGUARDING
    # ---------------------------------------------------------

    safeguarding_match = re.search(
        r"(?:victim\s+safeguarding|"
        r"safeguarding|"
        r"victim\s+protection|"
        r"check\s+victims|"
        r"check\s+safeguarding)"
        r"(?:\s+(?:on|for|in))?\s*"
        r"(CASE-\d+)",
        text,
        re.IGNORECASE,
    )

    if safeguarding_match:
        case_id = safeguarding_match.group(1).upper()

        add_task(
            agent_id="victim_safeguarding",
            case_id=case_id,
            description=f"Run victim safeguarding analysis on {case_id}",
        )

    # ---------------------------------------------------------
    # CORRELATION / PATTERN ANALYSIS
    # ---------------------------------------------------------

    correlation_match = re.search(
        r"(?:correlat\w*|"
        r"pattern\s+analysis|"
        r"find\s+connections|"
        r"find\s+relationships|"
        r"find\s+links|"
        r"link\s+accounts|"
        r"cross[-\s]?case|"
        r"analyse|"
        r"analyze)"
        r"(?:\s+(?:on|for|in))?\s*"
        r"(CASE-\d+)",
        text,
        re.IGNORECASE,
    )

    if correlation_match:
        case_id = correlation_match.group(1).upper()

        add_task(
            agent_id="correlation",
            case_id=case_id,
            description=f"Run correlation and pattern analysis on {case_id}",
        )

    # ---------------------------------------------------------
    # LEAD INTELLIGENCE
    # ---------------------------------------------------------

    lead_match = re.search(
        r"(?:generate\s+investigative\s+leads|"
        r"generate\s+leads|"
        r"find\s+leads|"
        r"lead\s+intelligence|"
        r"identify\s+persons\s+of\s+interest)"
        r"(?:\s+(?:on|for|in|from))?\s*"
        r"(CASE-\d+)?",
        text,
        re.IGNORECASE,
    )

    if lead_match:
        case_id = lead_match.group(1)

        if not case_id:
            case_ids = extract_case_ids(text)
            case_id = case_ids[0] if case_ids else default_case_id

        if case_id:
            case_id = case_id.upper()

            add_task(
                agent_id="lead_intelligence",
                case_id=case_id,
                description=f"Generate investigative leads for {case_id}",
            )

    # ---------------------------------------------------------
    # SAFETY NET
    # ---------------------------------------------------------

    if not tasks:
        return None

    return TaskPlan(tasks=tasks)


# --------------------------------------------------
# LLM fallback planner
# --------------------------------------------------

def llm_plan(
    command: str,
    default_case_id: str | None = None,
):

    prompt = f"""
You are the task planning component of AEGIS.

Convert the investigator command into executable
investigation tasks.

Available agents:

entity_extraction
- Extract entities from raw digital evidence.

correlation
- Analyse relationships, links and patterns
  using the Knowledge Graph.

lead_intelligence
- Generate investigative leads using
  existing case intelligence.

victim_safeguarding
- Identify safeguarding concerns using
  existing findings and graph relationships.

Rules:

1. ONLY create tasks requested by the investigator.

2. Do not invent additional tasks.

3. Do not copy tasks from these instructions.

4. If the investigator explicitly asks for
   entity extraction, use entity_extraction.

5. If RAW-XXX or EVID-XXX is mentioned and the
   investigator asks for extraction, put that ID
   into evidence_ids.

6. Use explicit CASE-XXX IDs when present.

7. If no case ID is present, use the supplied
   default case.

8. Independent tasks must not depend on each other.

9. Only create a dependency when the command
   explicitly requires one task's output before
   another task can logically begin.

10. Do not execute anything.

11. Do not answer the investigator.

12. Return ONLY the requested tasks.

Examples:

"Extract entities from RAW-001"

→ exactly ONE task:
entity_extraction,
evidence_ids = ["RAW-001"]

"Run correlation on CASE-001 and CASE-002"

→ exactly TWO tasks:
correlation CASE-001
correlation CASE-002

"Check safeguarding for CASE-001"

→ exactly ONE task:
victim_safeguarding CASE-001

Default case:
{default_case_id}

Command:
{command}
"""

    return planner.invoke(prompt)


# --------------------------------------------------
# Public planner
# --------------------------------------------------

def plan_command(
    command: str,
    default_case_id: str | None = None,
):

    deterministic = deterministic_plan(
        command,
        default_case_id,
    )

    if deterministic is not None:

        print(
            "[PLANNER] Deterministic plan selected"
        )

        return deterministic

    print(
        "[PLANNER] Using LLM fallback planner"
    )

    return llm_plan(
        command,
        default_case_id,
    )