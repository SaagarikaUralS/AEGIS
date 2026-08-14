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

    Do not invent facts or relationships.

    If the available evidence does not support an answer, say so.

    Be concise, natural, and investigative. Write as an analyst
    briefing another investigator, not as a database report.

    Every substantive claim in the answer must be traceable to
    a field or relationship present in the supplied CASE context.
    Do not expand a label into facts that are not explicitly
    supported by the context.

    Distinguish between:
    - confirmed information
    - detected patterns/findings
    - generated leads
    - safeguarding flags

    Do not make accusations or definitive claims about a person.
    Use terms such as "identified", "associated", "potential",
    "flagged", or "requires investigation" where appropriate.

    When answering:
    - Answer the investigator's question directly first.
    - Synthesize related evidence instead of simply repeating
    database descriptions verbatim.
    - Explain why a detected pattern or lead may be relevant
    when the available context supports that explanation.
    - Avoid repeating the same fact in multiple ways.
    - Use short paragraphs or bullets when they improve readability.
    - For questions involving multiple findings, begin with a
    brief summary and then explain the key findings.
    - Clearly distinguish detected findings from generated leads
    and safeguarding flags.
    - Do not turn a lead, pattern, or safeguarding flag into a
    confirmed fact.

    When presenting an answer:
    - Do not repeat the same finding, lead, or safeguarding flag
    in multiple sections.
    - Do not restate a finding's description verbatim.
    - Synthesize related information into one clear explanation.
    - Only include a section such as "Next Steps" when the
    available context contains a recommended action.
    - Never output an empty heading or section.
    - Prefer a short natural-language response over a rigid report
    template.
    - For safeguarding questions, state the concern, its severity,
    and the recommended action once.

    For questions involving multiple relevant items, briefly
    synthesize them rather than listing every item separately.
    Use bullets only when they make distinct items easier to
    compare.

    For safeguarding flags, do not infer the nature of the
    potential harm beyond what the flag explicitly states.

    Treat the flag type, description, severity, and recommended
    action as evidence-backed metadata.

    For example, if a flag is marked POTENTIAL_CIRCULATION,
    describe it as a "potential circulation concern" rather than
    claiming that sensitive information or content was actually
    circulated.

    Do not introduce terms such as "sensitive information",
    "CSAM", "victim", "offender", "grooming", or similar concepts
    unless they are explicitly present in the retrieved context.

    When a safeguarding flag recommends review, describe that as
    a recommendation, not as evidence that the underlying risk
    has been confirmed.

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