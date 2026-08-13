from typing import TypedDict, List, Dict, Any

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.knowledge_graph.neo4j_client import neo4j_client


# ============================================================
# STRUCTURED OUTPUT MODELS
# ============================================================

class Entity(BaseModel):
    entity_type: str = Field(
        description="Entity type: Person, Account, Device, or Location"
    )
    entity_id: str = Field(
        description="Stable identifier for the entity"
    )
    name: str = Field(
        description="Human-readable name or value"
    )


class EntityExtractionResult(BaseModel):
    entities: List[Entity]


# ============================================================
# LANGGRAPH STATE
# ============================================================

class EntityExtractionState(TypedDict):
    case_id: str
    evidence_id: str
    evidence_text: str
    entities: List[Dict[str, Any]]
    status: str


# ============================================================
# LOCAL LLM
# ============================================================

llm = ChatOllama(
    model="llama3.2:3b",
    temperature=0,
)

structured_llm = llm.with_structured_output(
    EntityExtractionResult
)


# ============================================================
# PROMPT
# ============================================================

prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You are the Entity Extraction Agent in AEGIS,
an AI-assisted child protection investigation platform.

Your ONLY responsibility is to extract structured
investigative entities from the supplied evidence.

Do NOT:
- investigate
- infer guilt
- make investigative decisions
- invent entities
- infer relationships that are not explicitly present

Extract ONLY entities explicitly present in the evidence.

Possible entity types:

- Person
- Account
- Device
- Location

For each entity provide:

1. entity_type
2. entity_id
3. name

Use identifiers directly provided by the evidence whenever
possible.

Example:

Evidence:
"Account alpha_synthetic was associated with Device-001.
The record references Subject Alpha and Location-X."

Expected entities:

Account:
alpha_synthetic

Device:
Device-001

Person:
Subject Alpha

Location:
Location-X
""",
        ),
        (
            "human",
            """
Case ID:
{case_id}

Evidence ID:
{evidence_id}

Evidence:
{evidence_text}
""",
        ),
    ]
)


# ============================================================
# ENTITY EXTRACTION
# ============================================================

def extract_entities(state: EntityExtractionState):

    chain = prompt | structured_llm

    result = chain.invoke(
        {
            "case_id": state["case_id"],
            "evidence_id": state["evidence_id"],
            "evidence_text": state["evidence_text"],
        }
    )

    entities = [
        entity.model_dump()
        for entity in result.entities
    ]

    print("\nENTITY EXTRACTION RESULT")
    print("--------------------------------")

    for entity in entities:
        print(
            f"{entity['entity_type']}: "
            f"{entity['name']} "
            f"({entity['entity_id']})"
        )

    print("--------------------------------")

    return {
        **state,
        "entities": entities,
        "status": "COMPLETED",
    }


# ============================================================
# WRITE ENTITIES TO NEO4J
# ============================================================

def write_entities_to_graph(state: EntityExtractionState):

    for entity in state["entities"]:

        entity_type = entity["entity_type"]
        entity_id = entity["entity_id"]
        name = entity["name"]

        if entity_type == "Person":

            query = """
            MERGE (p:Person {person_id: $entity_id})
            SET p.name = $name

            WITH p

            MATCH (c:Case {case_id: $case_id})
            MATCH (e:Evidence {evidence_id: $evidence_id})

            MERGE (c)-[:INVOLVES]->(p)
            MERGE (e)-[:MENTIONS]->(p)
            """

        elif entity_type == "Account":

            query = """
            MERGE (a:Account {username: $entity_id})
            SET a.name = $name

            WITH a

            MATCH (c:Case {case_id: $case_id})
            MATCH (e:Evidence {evidence_id: $evidence_id})

            MERGE (c)-[:CONTAINS_ACCOUNT]->(a)
            MERGE (e)-[:MENTIONS]->(a)
            """

        elif entity_type == "Device":

            query = """
            MERGE (d:Device {device_id: $entity_id})
            SET d.name = $name

            WITH d

            MATCH (c:Case {case_id: $case_id})
            MATCH (e:Evidence {evidence_id: $evidence_id})

            MERGE (c)-[:CONTAINS_DEVICE]->(d)
            MERGE (e)-[:MENTIONS]->(d)
            """

        elif entity_type == "Location":

            query = """
            MERGE (l:Location {location_id: $entity_id})
            SET l.name = $name

            WITH l

            MATCH (c:Case {case_id: $case_id})
            MATCH (e:Evidence {evidence_id: $evidence_id})

            MERGE (c)-[:MENTIONS_LOCATION]->(l)
            MERGE (e)-[:MENTIONS]->(l)
            """

        else:
            print(f"Skipping unknown entity type: {entity_type}")
            continue

        neo4j_client.run_query(
            query,
            {
                "case_id": state["case_id"],
                "evidence_id": state["evidence_id"],
                "entity_id": entity_id,
                "name": name,
            },
        )

    print("\nEntities successfully written to Neo4j.")

    return state


# ============================================================
# PUBLIC AGENT FUNCTION
# ============================================================

def run_entity_extraction(
    case_id: str,
    evidence_id: str,
    evidence_text: str,
):

    initial_state: EntityExtractionState = {
        "case_id": case_id,
        "evidence_id": evidence_id,
        "evidence_text": evidence_text,
        "entities": [],
        "status": "RUNNING",
    }

    state = extract_entities(initial_state)

    state = write_entities_to_graph(state)

    return state