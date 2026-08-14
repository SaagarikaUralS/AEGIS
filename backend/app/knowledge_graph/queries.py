CREATE_CASE = """
MERGE (c:Case {case_id: $case_id})
SET c.title = $title,
    c.status = $status,
    c.created_at = $created_at
RETURN c
"""


CREATE_EVIDENCE = """
MATCH (c:Case {case_id: $case_id})
MERGE (e:Evidence {evidence_id: $evidence_id})
SET
    e.case_id = $case_id,
    e.type = $type,
    e.source = $source,
    e.description = $description
MERGE (c)-[:HAS_EVIDENCE]->(e)
RETURN e
"""


CREATE_PERSON = """
MATCH (c:Case {case_id: $case_id})
MERGE (p:Person {person_id: $person_id})
SET p.name = $name
MERGE (c)-[:INVOLVES]->(p)
RETURN p
"""


CREATE_ACCOUNT = """
MATCH (p:Person {person_id: $person_id})
MERGE (a:Account {username: $username})
MERGE (p)-[:USES_ACCOUNT]->(a)
RETURN a
"""


CREATE_DEVICE = """
MATCH (p:Person {person_id: $person_id})
MERGE (d:Device {device_id: $device_id})
SET d.type = $type
MERGE (p)-[:USES_DEVICE]->(d)
RETURN d
"""


GET_CASE = """
MATCH (c:Case {case_id: $case_id})
OPTIONAL MATCH (c)-[r]-(connected)
RETURN c, r, connected
"""


CREATE_RAW_EVIDENCE = """
MERGE (e:Evidence {evidence_id: $evidence_id})
SET
    e.case_id = $case_id,
    e.type = 'raw_text',
    e.source = 'synthetic',
    e.description = $description
WITH e
MATCH (c:Case {case_id: $case_id})
MERGE (c)-[:HAS_EVIDENCE]->(e)
RETURN e
"""