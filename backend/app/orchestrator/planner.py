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
                case_id=case_id.upper(),
                agent_id=agent_id,
                description=description,
                evidence_ids=evidence_ids or [],
            )
        )

    # ---------------------------------------------------------
    # Split command into operation clauses
    #
    # Examples:
    #
    # "correlation on CASE-001 and CASE-002"
    #   -> one clause, two cases
    #
    # "entity extraction on CASE-001 and correlation
    #  for CASE-002"
    #   -> two clauses
    # ---------------------------------------------------------

    clauses = re.split(
        r"\s+\band\b\s+(?="
        r"(?:run|perform|execute|do|"
        r"extract|entity|correlat|analyse|analyze|"
        r"generate|find|check|identify|"
        r"victim|safeguard|lead)"
        r")",
        text,
        flags=re.IGNORECASE,
    )

    # ---------------------------------------------------------
    # If "and" is only connecting multiple CASE IDs,
    # don't split it.
    #
    # Example:
    # "correlation on CASE-001 and CASE-002"
    #
    # remains one clause.
    # ---------------------------------------------------------

    # ---------------------------------------------------------
    # Process each operation independently
    # ---------------------------------------------------------

    for clause in clauses:

        clause = clause.strip()

        if not clause:
            continue

        case_ids = extract_case_ids(clause)
        evidence_ids = extract_evidence_ids(clause)

        # =====================================================
        # ENTITY EXTRACTION
        # =====================================================

        entity_requested = bool(
            re.search(
                r"\b(?:extract\s+entit(?:y|ies)|"
                r"entity\s+extraction|"
                r"entity\s+extractor|"
                r"extractor\s+agent|"
                r"identify\s+entities|"
                r"parse\s+evidence)\b",
                clause,
                re.IGNORECASE,
            )
        )

        if entity_requested:

            # -------------------------------------------------
            # Multiple CASE IDs
            #
            # "entity extraction on CASE-001 and CASE-002"
            # -------------------------------------------------

            if case_ids:

                for case_id in case_ids:

                    add_task(
                        agent_id="entity_extraction",
                        case_id=case_id,
                        description=(
                            f"Extract entities from "
                            f"available evidence in {case_id}"
                        ),
                        evidence_ids=evidence_ids,
                    )

            # -------------------------------------------------
            # Evidence IDs without explicit CASE
            # -------------------------------------------------

            elif evidence_ids:

                add_task(
                    agent_id="entity_extraction",
                    case_id=default_case_id,
                    description=(
                        f"Extract entities from "
                        f"{', '.join(evidence_ids)}"
                    ),
                    evidence_ids=evidence_ids,
                )

            # -------------------------------------------------
            # No case/evidence → default case
            # -------------------------------------------------

            else:

                add_task(
                    agent_id="entity_extraction",
                    case_id=default_case_id,
                    description=(
                        f"Extract entities from "
                        f"available evidence in "
                        f"{default_case_id}"
                    ),
                )

        # =====================================================
        # CORRELATION
        # =====================================================

        correlation_requested = bool(
            re.search(
                r"\b(?:"
                r"correlat\w*|"
                r"correlati+on|"
                r"pattern\s+analysis|"
                r"find\s+connections|"
                r"find\s+relationships|"
                r"find\s+links|"
                r"link\s+accounts|"
                r"cross[-\s]?case|"
                r"analyse|"
                r"analyze"
                r")\b",
                clause,
                re.IGNORECASE,
            )
        )

        if correlation_requested:

            if case_ids:

                for case_id in case_ids:

                    add_task(
                        agent_id="correlation",
                        case_id=case_id,
                        description=(
                            f"Run correlation and pattern "
                            f"analysis on {case_id}"
                        ),
                    )

            else:

                add_task(
                    agent_id="correlation",
                    case_id=default_case_id,
                    description=(
                        f"Run correlation and pattern "
                        f"analysis on {default_case_id}"
                    ),
                )

        # =====================================================
        # LEAD INTELLIGENCE
        # =====================================================

        lead_requested = bool(
            re.search(
                r"\b(?:"
                r"generate\s+investigative\s+leads|"
                r"generate\s+leads|"
                r"lead\s+generation|"
                r"find\s+leads|"
                r"lead\s+intelligence|"
                r"identify\s+persons\s+of\s+interest"
                r")\b",
                clause,
                re.IGNORECASE,
            )
        )

        if lead_requested:

            if case_ids:

                for case_id in case_ids:

                    add_task(
                        agent_id="lead_intelligence",
                        case_id=case_id,
                        description=(
                            f"Generate investigative leads "
                            f"for {case_id}"
                        ),
                    )

            else:

                add_task(
                    agent_id="lead_intelligence",
                    case_id=default_case_id,
                    description=(
                        f"Generate investigative leads "
                        f"for {default_case_id}"
                    ),
                )

        # =====================================================
        # VICTIM SAFEGUARDING
        # =====================================================

        safeguarding_requested = bool(
            re.search(
                r"\b(?:victim\s+safeguarding|"
                r"victim\s+safeguard|"
                r"safeguarding|"
                r"safeguard|"
                r"victim\s+protection|"
                r"check\s+victims|"
                r"check\s+safeguarding)\b",
                clause,
                re.IGNORECASE,
            )
        )

        if safeguarding_requested:

            if case_ids:

                for case_id in case_ids:

                    add_task(
                        agent_id="victim_safeguarding",
                        case_id=case_id,
                        description=(
                            f"Run victim safeguarding "
                            f"analysis on {case_id}"
                        ),
                    )

            else:

                add_task(
                    agent_id="victim_safeguarding",
                    case_id=default_case_id,
                    description=(
                        f"Run victim safeguarding "
                        f"analysis on {default_case_id}"
                    ),
                )

    # ---------------------------------------------------------
    # Safety net
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