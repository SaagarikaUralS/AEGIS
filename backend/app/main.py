from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

import os
import shutil
import uuid

from app.agents.image_evidence import run_image_entity_extraction

from app.knowledge_graph.neo4j_client import neo4j_client
from app.agents.entity_extraction import run_entity_extraction
from app.agents.correlation import run_correlation
from app.agents.lead_intelligence import run_lead_intelligence
from app.agents.victim_safeguarding import run_victim_safeguarding

from app.orchestrator.runner import run_investigation
from app.copilot.assistant import ask_copilot

from app.api.orchestrator import router as orchestrator_router
from app.api import executions, cases
from app.orchestrator.scheduler import scheduler


app = FastAPI(
    title="AEGIS API",
    description="AI-Enabled Evidence & Graph Intelligence System",
    version="0.2.0",
)

@app.on_event("startup")
def start_aegis_scheduler():
    scheduler.start()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(orchestrator_router)
app.include_router(executions.router)
app.include_router(cases.router)

class CopilotRequest(BaseModel):
    question: str


class EntityExtractionRequest(BaseModel):
    case_id: str
    evidence_id: str
    evidence_text: str


@app.get("/")
def root():

    return {
        "system": "AEGIS",
        "status": "online",
        "message": "AI-Enabled Evidence & Graph Intelligence System",
    }


@app.get("/health")
def health_check():

    try:

        connected = neo4j_client.verify_connection()

        return {
            "api": "online",
            "neo4j": "connected" if connected else "disconnected",
        }

    except Exception as error:

        raise HTTPException(
            status_code=503,
            detail=f"Neo4j connection failed: {error}",
        )


@app.get("/cases/{case_id}")
def get_case(case_id: str):

    query = """
    MATCH (c:Case {case_id: $case_id})

    OPTIONAL MATCH (c)-[r]-(connected)

    RETURN
        c,
        type(r) AS relationship,
        connected
    """

    results = neo4j_client.run_query(
        query,
        {"case_id": case_id},
    )

    if not results:

        raise HTTPException(
            status_code=404,
            detail="Case not found",
        )

    return {
        "case_id": case_id,
        "graph": results,
    }


@app.post("/agents/entity-extraction")
def entity_extraction(
    request: EntityExtractionRequest
):

    try:

        result = run_entity_extraction(
            case_id=request.case_id,
            evidence_id=request.evidence_id,
            evidence_text=request.evidence_text,
        )

        return {
            "agent": "Entity Extraction Agent",
            "status": result["status"],
            "case_id": result["case_id"],
            "evidence_id": result["evidence_id"],
            "entities": result["entities"],
        }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )

@app.post("/agents/correlation")
def correlation(case_id: str):

    try:

        result = run_correlation(
            case_id
        )

        return {
            "agent": "Correlation & Pattern Analysis Agent",
            "status": result["status"],
            "case_id": result["case_id"],
            "patterns": result["patterns"],
        }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )

@app.post("/agents/lead-intelligence")
def lead_intelligence(case_id: str):

    try:

        result = run_lead_intelligence(
            case_id
        )

        return {
            "agent": "Lead Intelligence Agent",
            "status": result["status"],
            "case_id": result["case_id"],
            "leads": result["leads"],
        }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )


@app.post("/agents/victim-safeguarding")
def victim_safeguarding(case_id: str):

    try:

        result = run_victim_safeguarding(
            case_id
        )

        return {
            "agent": "Victim Safeguarding Agent",
            "status": result["status"],
            "case_id": result["case_id"],
            "flags": result["flags"],
        }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )



class InvestigationRequest(BaseModel):
    agents: list[str]


@app.post("/investigations/{case_id}/run")
def run_case_investigation(
    case_id: str,
    request: InvestigationRequest,
):
    try:

        result = run_investigation(
            case_id=case_id,
            requested_agents=request.agents,
        )

        return {
            "system": "AEGIS",
            "status": result["execution_status"],
            "execution_id": result["execution_id"],
            "case_id": result["case_id"],
            "requested_agents": request.agents,
            "agent_status": result["agent_status"],
            "execution_log": result["execution_log"],
            "entities_found": len(
                result["entities"]
            ),
            "patterns_found": len(
                result["patterns"]
            ),
            "leads_generated": len(
                result["leads"]
            ),
            "safeguarding_flags": len(
                result["safeguarding_flags"]
            ),
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        )


@app.post("/agents/entity-extraction/image")
async def extract_entities_from_image(
    case_id: str,
    file: UploadFile = File(...),
):
    try:

        # ----------------------------------------------------
        # Create temporary upload location
        # ----------------------------------------------------

        upload_directory = "data/uploads"

        os.makedirs(
            upload_directory,
            exist_ok=True,
        )

        filename = (
            f"{uuid.uuid4()}"
            f"_{file.filename}"
        )

        image_path = os.path.join(
            upload_directory,
            filename,
        )

        # ----------------------------------------------------
        # Save uploaded screenshot
        # ----------------------------------------------------

        with open(image_path, "wb") as buffer:

            shutil.copyfileobj(
                file.file,
                buffer,
            )

        # ----------------------------------------------------
        # Generate synthetic evidence ID
        # ----------------------------------------------------

        evidence_id = (
            f"IMG-{uuid.uuid4().hex[:8]}"
        )

        # ----------------------------------------------------
        # Run image evidence pipeline
        # ----------------------------------------------------

        result = run_image_entity_extraction(
            case_id=case_id,
            evidence_id=evidence_id,
            image_path=image_path,
        )

        return {
            "status": "COMPLETED",
            "case_id": case_id,
            "evidence_id": evidence_id,
            "filename": file.filename,
            "contact": result["header"],
            "entities": result["entities"],
            "summary": result["summary"],
            "ocr_text": result["ocr_text"],
            "profile_picture": result["profile_picture"],
        }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )


@app.post("/copilot/{case_id}")
def copilot(
    case_id: str,
    request: CopilotRequest,
):
    try:

        result = ask_copilot(
            case_id=case_id,
            question=request.question,
        )

        if "error" in result:
            raise HTTPException(
                status_code=404,
                detail=result["error"],
            )

        return result

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        )


CASE_OVERVIEW_QUERY = """
MATCH (c:Case {case_id: $case_id})

OPTIONAL MATCH (c)-[:INVOLVES]->(p:Person)
WITH c,
     collect(DISTINCT {
         id: p.person_id,
         name: p.name
     }) AS people

OPTIONAL MATCH (c)-[:CONTAINS_ACCOUNT]->(a:Account)
WITH c, people,
     collect(DISTINCT {
         username: a.username
     }) AS accounts

OPTIONAL MATCH (c)-[:CONTAINS_DEVICE]->(d:Device)
WITH c, people, accounts,
     collect(DISTINCT {
         device_id: d.device_id,
         type: d.type
     }) AS devices

OPTIONAL MATCH (c)-[:HAS_FINDING]->(f:Finding)
WITH c, people, accounts, devices,
     collect(DISTINCT {
         finding_id: f.finding_id,
         type: f.type,
         description: f.description
     }) AS findings

OPTIONAL MATCH (c)-[:HAS_LEAD]->(l:Lead)
WITH c, people, accounts, devices, findings,
     collect(DISTINCT {
         lead_id: l.lead_id,
         subject: l.subject,
         priority: l.priority,
         confidence: l.confidence,
         reason: l.reason,
         recommended_direction: l.recommended_direction
     }) AS leads

OPTIONAL MATCH (c)-[:HAS_SAFEGUARDING_FLAG]->(s:SafeguardingFlag)

RETURN
    c.case_id AS case_id,
    c.title AS title,
    c.status AS status,
    people,
    accounts,
    devices,
    findings,
    leads,
    collect(DISTINCT {
        flag_id: s.flag_id,
        type: s.type,
        severity: s.severity,
        subject: s.subject,
        description: s.description,
        recommended_action: s.recommended_action,
        status: s.status
    }) AS safeguarding_flags
"""


@app.get("/cases/{case_id}/overview")
def get_case_overview(case_id: str):

    try:

        results = neo4j_client.run_query(
            CASE_OVERVIEW_QUERY,
            {
                "case_id": case_id,
            },
        )

        if not results:
            raise HTTPException(
                status_code=404,
                detail="Case not found",
            )

        return results[0]

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        )