from typing import Dict, Any

from langchain_ollama import ChatOllama

from app.knowledge_graph.neo4j_client import neo4j_client


# ============================================================
# LLM
# ============================================================

llm = ChatOllama(
    model="llama3.2:3b",
    temperature=0,
)


# ============================================================
# KNOWLEDGE GRAPH RETRIEVAL
# ============================================================

GET_CASE_CONTEXT = """
MATCH (c:Case {case_id: $case_id})

OPTIONAL MATCH (c)-[:INVOLVES]->(p:Person)
WITH c,
     collect(DISTINCT {
         type: 'PERSON',
         value: p.name,
         id: p.person_id
     }) AS people

OPTIONAL MATCH (c)-[:CONTAINS_ACCOUNT]->(a:Account)
WITH c, people,
     collect(DISTINCT {
         type: 'ACCOUNT',
         value: a.username
     }) AS accounts

OPTIONAL MATCH (c)-[:CONTAINS_DEVICE]->(d:Device)
WITH c, people, accounts,
     collect(DISTINCT {
         type: 'DEVICE',
         value: d.device_id,
         device_type: d.type
     }) AS devices

OPTIONAL MATCH (c)-[:MENTIONS_LOCATION]->(l:Location)
WITH c, people, accounts, devices,
     collect(DISTINCT {
         type: 'LOCATION',
         value: l.location_id
     }) AS locations

OPTIONAL MATCH (c)-[:HAS_FINDING]->(f:Finding)
WITH c, people, accounts, devices, locations,
     collect(DISTINCT {
         finding_id: f.finding_id,
         type: f.type,
         description: f.description
     }) AS findings

OPTIONAL MATCH (c)-[:HAS_LEAD]->(lead:Lead)
WITH c, people, accounts, devices, locations, findings,
     collect(DISTINCT {
         lead_id: lead.lead_id,
         subject: lead.subject,
         priority: lead.priority,
         confidence: lead.confidence,
         reason: lead.reason,
         recommended_direction: lead.recommended_direction
     }) AS leads

OPTIONAL MATCH (c)-[:HAS_SAFEGUARDING_FLAG]->(flag:SafeguardingFlag)
RETURN
    c.case_id AS case_id,
    c.title AS title,
    c.status AS status,
    people,
    accounts,
    devices,
    locations,
    findings,
    leads,
    collect(DISTINCT {
        flag_id: flag.flag_id,
        type: flag.type,
        severity: flag.severity,
        subject: flag.subject,
        description: flag.description,
        recommended_action: flag.recommended_action,
        status: flag.status
    }) AS safeguarding_flags
"""


def get_case_context(case_id: str) -> Dict[str, Any]:

    results = neo4j_client.run_query(
        GET_CASE_CONTEXT,
        {
            "case_id": case_id,
        },
    )

    if not results:
        return {
            "case_id": case_id,
            "error": "Case not found.",
        }

    return results[0]


# ============================================================
# COPILOT
# ============================================================

def ask_copilot(
    case_id: str,
    question: str,
) -> Dict[str, Any]:

    context = get_case_context(case_id)

    if "error" in context:
        return context

    prompt = f"""
You are AEGIS Case Intelligence Assistant.

You assist a human investigator by answering questions using
ONLY the investigative context retrieved from the AEGIS
Knowledge Graph below.

Do not invent facts.

If the available evidence does not support an answer, say so.

Be concise and investigative. Distinguish between:
- confirmed information
- detected patterns/findings
- generated leads
- safeguarding flags

Do not make accusations or definitive claims about a person.
Use terms such as "identified", "associated", "potential",
"flagged", or "requires investigation" where appropriate.

CASE:
{context}

INVESTIGATOR QUESTION:
{question}

Provide a concise answer suitable for an investigator dashboard.
"""

    response = llm.invoke(prompt)

    return {
        "case_id": case_id,
        "question": question,
        "answer": response.content.strip(),
        "context": context,
    }