from fastapi import APIRouter, HTTPException

from app.knowledge_graph.neo4j_client import neo4j_client


router = APIRouter(
    prefix="/cases",
    tags=["cases"],
)


@router.get("")
def list_cases():
    query = """
    MATCH (c:Case)

    OPTIONAL MATCH (c)-[:HAS_EXECUTION]->(e:Execution)

    WITH
        c,
        max(e.created_at) AS last_activity

    RETURN
        c {
            .*,
            last_modified_at: coalesce(last_activity, c.created_at),
            last_modified_by: "AEGIS"
        } AS case

    ORDER BY case.last_modified_at DESC
    """

    try:
        result = neo4j_client.run_query(query)

        return {
            "cases": [
                row["case"]
                for row in result
            ]
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load cases: {str(exc)}",
        )


@router.get("/{case_id}/overview")
def get_case_overview(case_id: str):
    query = """
    MATCH (c:Case {case_id: $case_id})

    OPTIONAL MATCH (c)-[:INVOLVES]->(p:Person)
    OPTIONAL MATCH (c)-[:CONTAINS_ACCOUNT]->(a:Account)
    OPTIONAL MATCH (c)-[:CONTAINS_DEVICE]->(d:Device)
    OPTIONAL MATCH (c)-[:HAS_FINDING]->(f:Finding)
    OPTIONAL MATCH (c)-[:HAS_LEAD]->(l:Lead)
    OPTIONAL MATCH (c)-[:HAS_SAFEGUARDING_FLAG]->(s:SafeguardingFlag)

    RETURN
        c.case_id AS case_id,
        c.title AS title,
        c.status AS status,

        collect(DISTINCT {
            name: p.name,
            id: p.person_id
        }) AS people,

        collect(DISTINCT {
            username: a.username
        }) AS accounts,

        collect(DISTINCT {
            device_id: d.device_id,
            type: d.type
        }) AS devices,

        collect(DISTINCT {
            finding_id: f.finding_id,
            description: f.description,
            type: f.type
        }) AS findings,

        collect(DISTINCT {
            lead_id: l.lead_id,
            subject: l.subject,
            priority: l.priority,
            confidence: l.confidence,
            reason: l.reason,
            recommended_direction: l.recommended_direction
        }) AS leads,

        collect(DISTINCT {
            flag_id: s.flag_id,
            subject: s.subject,
            severity: s.severity,
            type: s.type,
            description: s.description,
            status: s.status,
            recommended_action: s.recommended_action
        }) AS safeguarding_flags
    """

    try:
        result = neo4j_client.run_query(
            query,
            {"case_id": case_id},
        )

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Case {case_id} not found",
            )

        return result[0]

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load case overview: {str(exc)}",
        )