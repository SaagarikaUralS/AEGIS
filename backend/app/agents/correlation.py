from typing import TypedDict, List, Dict, Any

from app.knowledge_graph.neo4j_client import neo4j_client


# ============================================================
# LANGGRAPH STATE
# ============================================================

class CorrelationState(TypedDict):
    case_id: str
    patterns: List[Dict[str, Any]]
    status: str


# ============================================================
# QUERY: SHARED ACCOUNTS
# ============================================================

SHARED_ACCOUNTS_QUERY = """
MATCH (a:Account)<-[:CONTAINS_ACCOUNT]-(c:Case)
WITH a, collect(DISTINCT c.case_id) AS cases
WHERE size(cases) > 1

RETURN
    a.username AS account,
    cases
ORDER BY size(cases) DESC
"""


# ============================================================
# QUERY: SHARED DEVICES
# ============================================================

SHARED_DEVICES_QUERY = """
MATCH (d:Device)<-[:CONTAINS_DEVICE]-(c:Case)
WITH d, collect(DISTINCT c.case_id) AS cases
WHERE size(cases) > 1

RETURN
    d.device_id AS device,
    cases
ORDER BY size(cases) DESC
"""


# ============================================================
# QUERY: PERSON → MULTIPLE ACCOUNTS
# ============================================================

MULTIPLE_ACCOUNTS_QUERY = """
MATCH (p:Person)-[:USES_ACCOUNT]->(a:Account)
WITH p, collect(DISTINCT a.username) AS accounts
WHERE size(accounts) > 1

RETURN
    p.person_id AS person,
    p.name AS person_name,
    accounts
ORDER BY size(accounts) DESC
"""


# ============================================================
# QUERY: PERSON → MULTIPLE DEVICES
# ============================================================

MULTIPLE_DEVICES_QUERY = """
MATCH (p:Person)-[:USES_DEVICE]->(d:Device)
WITH p, collect(DISTINCT d.device_id) AS devices
WHERE size(devices) > 1

RETURN
    p.person_id AS person,
    p.name AS person_name,
    devices
ORDER BY size(devices) DESC
"""


# ============================================================
# QUERY: SHARED LOCATIONS
# ============================================================

SHARED_LOCATIONS_QUERY = """
MATCH (l:Location)<-[:MENTIONS_LOCATION]-(c:Case)
WITH l, collect(DISTINCT c.case_id) AS cases
WHERE size(cases) > 1

RETURN
    l.location_id AS location,
    l.name AS location_name,
    cases
ORDER BY size(cases) DESC
"""


# ============================================================
# CROSS-CASE CORRELATION
# ============================================================

def detect_cross_case_patterns(state: CorrelationState):

    patterns = []

    # --------------------------------------------------------
    # SHARED ACCOUNTS
    # --------------------------------------------------------

    results = neo4j_client.run_query(
        SHARED_ACCOUNTS_QUERY
    )

    for result in results:

        patterns.append(
            {
                "pattern_type": "SHARED_ACCOUNT",
                "entity": result["account"],
                "cases": result["cases"],
                "description": (
                    f"Account {result['account']} "
                    f"appears in multiple cases: "
                    f"{', '.join(result['cases'])}"
                ),
            }
        )

    # --------------------------------------------------------
    # SHARED DEVICES
    # --------------------------------------------------------

    results = neo4j_client.run_query(
        SHARED_DEVICES_QUERY
    )

    for result in results:

        patterns.append(
            {
                "pattern_type": "SHARED_DEVICE",
                "entity": result["device"],
                "cases": result["cases"],
                "description": (
                    f"Device {result['device']} "
                    f"appears in multiple cases: "
                    f"{', '.join(result['cases'])}"
                ),
            }
        )

    # --------------------------------------------------------
    # PERSON → MULTIPLE ACCOUNTS
    # --------------------------------------------------------

    results = neo4j_client.run_query(
        MULTIPLE_ACCOUNTS_QUERY
    )

    for result in results:

        patterns.append(
            {
                "pattern_type": "MULTIPLE_ACCOUNTS",
                "entity": result["person"],
                "accounts": result["accounts"],
                "description": (
                    f"Person {result['person_name']} "
                    f"is associated with multiple accounts: "
                    f"{', '.join(result['accounts'])}"
                ),
            }
        )

    # --------------------------------------------------------
    # PERSON → MULTIPLE DEVICES
    # --------------------------------------------------------

    results = neo4j_client.run_query(
        MULTIPLE_DEVICES_QUERY
    )

    for result in results:

        patterns.append(
            {
                "pattern_type": "MULTIPLE_DEVICES",
                "entity": result["person"],
                "devices": result["devices"],
                "description": (
                    f"Person {result['person_name']} "
                    f"is associated with multiple devices: "
                    f"{', '.join(result['devices'])}"
                ),
            }
        )

    # --------------------------------------------------------
    # SHARED LOCATIONS
    # --------------------------------------------------------

    results = neo4j_client.run_query(
        SHARED_LOCATIONS_QUERY
    )

    for result in results:

        patterns.append(
            {
                "pattern_type": "SHARED_LOCATION",
                "entity": result["location"],
                "cases": result["cases"],
                "description": (
                    f"Location {result['location_name']} "
                    f"appears across multiple cases: "
                    f"{', '.join(result['cases'])}"
                ),
            }
        )

    # --------------------------------------------------------
    # RESULT
    # --------------------------------------------------------

    print("\nCORRELATION & PATTERN ANALYSIS")
    print("================================")

    if not patterns:

        print("No cross-entity patterns detected.")

    else:

        for pattern in patterns:

            print(
                f"[{pattern['pattern_type']}] "
                f"{pattern['description']}"
            )

    print("================================")

    return {
        **state,
        "patterns": patterns,
        "status": "COMPLETED",
    }


# ============================================================
# WRITE FINDINGS TO KNOWLEDGE GRAPH
# ============================================================

def write_patterns_to_graph(state: CorrelationState):

    for index, pattern in enumerate(
        state["patterns"],
        start=1
    ):

        finding_id = (
            f"{state['case_id']}-PATTERN-{index:03d}"
        )

        query = """
        MERGE (f:Finding {
            finding_id: $finding_id
        })

        SET
            f.type = $pattern_type,
            f.description = $description,
            f.status = 'NEW'

        WITH f

        MATCH (c:Case {
            case_id: $case_id
        })

        MERGE (c)-[:HAS_FINDING]->(f)
        """

        neo4j_client.run_query(
            query,
            {
                "finding_id": finding_id,
                "pattern_type": pattern["pattern_type"],
                "description": pattern["description"],
                "case_id": state["case_id"],
            },
        )

    print("\nCorrelation findings written to Neo4j.")

    return state


# ============================================================
# PUBLIC AGENT FUNCTION
# ============================================================

def run_correlation(case_id: str):

    initial_state: CorrelationState = {
        "case_id": case_id,
        "patterns": [],
        "status": "RUNNING",
    }

    state = detect_cross_case_patterns(
        initial_state
    )

    state = write_patterns_to_graph(
        state
    )

    return state