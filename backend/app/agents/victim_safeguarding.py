from typing import TypedDict, List, Dict, Any

from app.knowledge_graph.neo4j_client import neo4j_client


# ============================================================
# LANGGRAPH STATE
# ============================================================

class VictimSafeguardingState(TypedDict):
    case_id: str
    flags: List[Dict[str, Any]]
    status: str


# ============================================================
# QUERY: CROSS-CASE ENTITIES
# ============================================================

CROSS_CASE_ACCOUNTS = """
MATCH (a:Account)<-[:CONTAINS_ACCOUNT]-(c:Case)
WITH a, collect(DISTINCT c.case_id) AS cases
WHERE size(cases) > 1

RETURN
    a.username AS account,
    cases
ORDER BY size(cases) DESC
"""


CROSS_CASE_DEVICES = """
MATCH (d:Device)<-[:CONTAINS_DEVICE]-(c:Case)
WITH d, collect(DISTINCT c.case_id) AS cases
WHERE size(cases) > 1

RETURN
    d.device_id AS device,
    cases
ORDER BY size(cases) DESC
"""


# ============================================================
# EXISTING FINDINGS
# ============================================================

CASE_FINDINGS = """
MATCH (c:Case {case_id: $case_id})-[:HAS_FINDING]->(f:Finding)

RETURN
    f.finding_id AS finding_id,
    f.type AS type,
    f.description AS description
"""


# ============================================================
# DETECT SAFEGUARDING FLAGS
# ============================================================

def detect_safeguarding_flags(
    state: VictimSafeguardingState
):

    flags = []

    # --------------------------------------------------------
    # CROSS-CASE ACCOUNT REUSE
    # --------------------------------------------------------

    account_results = neo4j_client.run_query(
        CROSS_CASE_ACCOUNTS
    )

    for result in account_results:

        flags.append(
            {
                "flag_type": "POTENTIAL_CIRCULATION",
                "severity": "HIGH",
                "subject": result["account"],
                "description": (
                    f"Account {result['account']} "
                    f"appears across multiple investigative "
                    f"cases: {', '.join(result['cases'])}."
                ),
                "recommended_action": (
                    "Review linked evidence across cases "
                    "and assess whether safeguarding "
                    "measures are required."
                ),
            }
        )

    # --------------------------------------------------------
    # CROSS-CASE DEVICE REUSE
    # --------------------------------------------------------

    device_results = neo4j_client.run_query(
        CROSS_CASE_DEVICES
    )

    for result in device_results:

        flags.append(
            {
                "flag_type": "REPEATED_DEVICE",
                "severity": "MEDIUM",
                "subject": result["device"],
                "description": (
                    f"Device {result['device']} "
                    f"appears across multiple investigative "
                    f"cases: {', '.join(result['cases'])}."
                ),
                "recommended_action": (
                    "Review associated evidence and "
                    "determine whether the repeated "
                    "device relationship requires "
                    "safeguarding review."
                ),
            }
        )

    # --------------------------------------------------------
    # EXISTING FINDINGS
    # --------------------------------------------------------

    findings = neo4j_client.run_query(
        CASE_FINDINGS,
        {
            "case_id": state["case_id"]
        }
    )

    for finding in findings:

        if finding["type"] == "SHARED_ACCOUNT":

            flags.append(
                {
                    "flag_type": "REVIEW_SHARED_ACCOUNT",
                    "severity": "HIGH",
                    "subject": "Cross-case account",
                    "description": (
                        "A correlation finding indicates "
                        "that an account is associated with "
                        "multiple investigative cases."
                    ),
                    "recommended_action": (
                        "Review the linked evidence for "
                        "potential repeat victim exposure "
                        "or content circulation."
                    ),
                }
            )

    # --------------------------------------------------------
    # OUTPUT
    # --------------------------------------------------------

    print("\nVICTIM SAFEGUARDING")
    print("==============================")

    if not flags:

        print("No safeguarding flags detected.")

    else:

        for flag in flags:

            print(
                f"[{flag['severity']}] "
                f"{flag['flag_type']}"
            )

            print(
                f"Subject: {flag['subject']}"
            )

            print(
                f"Reason: {flag['description']}"
            )

            print(
                f"Action: "
                f"{flag['recommended_action']}"
            )

            print("------------------------------")

    return {
        **state,
        "flags": flags,
        "status": "COMPLETED",
    }


# ============================================================
# WRITE FLAGS TO KNOWLEDGE GRAPH
# ============================================================

def write_flags_to_graph(
    state: VictimSafeguardingState
):

    for index, flag in enumerate(
        state["flags"],
        start=1
    ):

        flag_id = (
            f"{state['case_id']}-SAFEGUARD-{index:03d}"
        )

        query = """
        MERGE (s:SafeguardingFlag {
            flag_id: $flag_id
        })

        SET
            s.type = $flag_type,
            s.severity = $severity,
            s.subject = $subject,
            s.description = $description,
            s.recommended_action = $recommended_action,
            s.status = 'OPEN'

        WITH s

        MATCH (c:Case {
            case_id: $case_id
        })

        MERGE (c)-[:HAS_SAFEGUARDING_FLAG]->(s)
        """

        neo4j_client.run_query(
            query,
            {
                "flag_id": flag_id,
                "flag_type": flag["flag_type"],
                "severity": flag["severity"],
                "subject": flag["subject"],
                "description": flag["description"],
                "recommended_action": flag[
                    "recommended_action"
                ],
                "case_id": state["case_id"],
            },
        )

    print(
        "\nSafeguarding flags written to Neo4j."
    )

    return state


# ============================================================
# PUBLIC AGENT FUNCTION
# ============================================================

def run_victim_safeguarding(case_id: str):

    initial_state: VictimSafeguardingState = {
        "case_id": case_id,
        "flags": [],
        "status": "RUNNING",
    }

    state = detect_safeguarding_flags(
        initial_state
    )

    state = write_flags_to_graph(
        state
    )

    return state