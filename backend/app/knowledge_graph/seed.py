import json
from pathlib import Path

from app.knowledge_graph.neo4j_client import neo4j_client
from app.knowledge_graph.queries import (
    CREATE_CASE,
    CREATE_EVIDENCE,
    CREATE_PERSON,
    CREATE_ACCOUNT,
    CREATE_DEVICE,
    CREATE_RAW_EVIDENCE,
)

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"


def load_json(filename):
    with open(DATA_DIR / filename, "r", encoding="utf-8") as file:
        return json.load(file)


def seed_database():

    cases = load_json("cases.json")
    evidence = load_json("evidence.json")
    raw_evidence = load_json("raw_evidence.json")

    print("Seeding cases...")

    for case in cases:
        neo4j_client.run_query(
            CREATE_CASE,
            case,
        )

    print("Seeding normal evidence...")

    for item in evidence:
        neo4j_client.run_query(
            CREATE_EVIDENCE,
            item,
        )

    print("Seeding raw evidence...")

    for item in raw_evidence:

        neo4j_client.run_query(
            CREATE_RAW_EVIDENCE,
            {
                "case_id": item["case_id"],
                "evidence_id": item["evidence_id"],
                "description": item["evidence_text"],
            },
        )

        print("Creating synthetic entities...")

    neo4j_client.run_query(
        CREATE_PERSON,
        {
            "case_id": "CASE-001",
            "person_id": "PERSON-001",
            "name": "Subject Alpha",
        },
    )

    neo4j_client.run_query(
        CREATE_ACCOUNT,
        {
            "person_id": "PERSON-001",
            "username": "alpha_synthetic",
        },
    )

    neo4j_client.run_query(
        CREATE_DEVICE,
        {
            "person_id": "PERSON-001",
            "device_id": "DEVICE-001",
            "type": "mobile",
        },
    )

    print("Knowledge Graph seeded successfully.")


if __name__ == "__main__":
    seed_database()