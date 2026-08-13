import { useEffect, useState } from "react";
import "./App.css";

const API = "http://127.0.0.1:8000";

const AGENTS = [
  {
    id: "entity_extraction",
    name: "Entity Extraction",
    short: "ENTITY",
  },
  {
    id: "correlation",
    name: "Correlation & Pattern Analysis",
    short: "CORRELATION",
  },
  {
    id: "lead_intelligence",
    name: "Lead Intelligence",
    short: "LEADS",
  },
  {
    id: "victim_safeguarding",
    name: "Victim Safeguarding",
    short: "SAFEGUARDING",
  },
];

function App() {
  const [caseId] = useState("CASE-001");

  const [overview, setOverview] = useState(null);

  const [agentStatus, setAgentStatus] = useState({
    entity_extraction: "NOT_REQUESTED",
    correlation: "NOT_REQUESTED",
    lead_intelligence: "NOT_REQUESTED",
    victim_safeguarding: "NOT_REQUESTED",
  });

  const [running, setRunning] = useState(false);

  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [copilotLoading, setCopilotLoading] = useState(false);

  const [image, setImage] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [imageResult, setImageResult] = useState(null);
  const [imageLoading, setImageLoading] = useState(false);

  async function loadOverview() {
    try {
      const response = await fetch(
        `${API}/cases/${caseId}/overview`
      );

      if (response.ok) {
        const data = await response.json();
        setOverview(data);
      }
    } catch (error) {
      console.error(error);
    }
  }

  useEffect(() => {
    loadOverview();
  }, []);

  async function runInvestigation() {
    setRunning(true);

    try {
      const response = await fetch(
        `${API}/investigations/${caseId}/run`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            agents: AGENTS.map((agent) => agent.id),
          }),
        }
      );

      const data = await response.json();

      setAgentStatus(data.agent_status);

      await loadOverview();
    } catch (error) {
      console.error(error);
      alert("Investigation failed.");
    }

    setRunning(false);
  }

  async function askCopilot() {
    if (!question.trim()) return;

    setCopilotLoading(true);
    setAnswer("");

    try {
      const response = await fetch(
        `${API}/copilot/${caseId}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            question,
          }),
        }
      );

      const data = await response.json();

      setAnswer(data.answer || data.detail || "No answer.");
    } catch (error) {
      console.error(error);
      setAnswer("Unable to reach the Case Intelligence Assistant.");
    }

    setCopilotLoading(false);
  }

  function handleImageChange(event) {
    const selected = event.target.files[0];

    if (!selected) return;

    setImage(selected);
    setImagePreview(URL.createObjectURL(selected));
    setImageResult(null);
  }

  async function uploadEvidence() {
    if (!image) return;

    setImageLoading(true);

    const formData = new FormData();

    formData.append("case_id", caseId);
    formData.append("file", image);

    try {
      const response = await fetch(
        `${API}/agents/entity-extraction/image?case_id=${caseId}`,
        {
          method: "POST",
          body: formData,
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail);
      }

      setImageResult(data);

      await loadOverview();
    } catch (error) {
      console.error(error);
      alert(error.message || "Evidence processing failed.");
    }

    setImageLoading(false);
  }

  const people = overview?.people || [];
  const accounts = overview?.accounts || [];
  const findings = overview?.findings || [];
  const leads = overview?.leads || [];
  const flags = overview?.safeguarding_flags || [];

  return (
    <div className="app">

      {/* HEADER */}

      <header className="topbar">

        <div>
          <div className="brand">
            AEGIS
          </div>

          <div className="subtitle">
            AI-Enabled Evidence & Graph Intelligence System
          </div>
        </div>

        <div className="case-badge">
          <span>CASE</span>
          {caseId}
        </div>

      </header>


      {/* MAIN */}

      <main className="dashboard">

        {/* CASE OVERVIEW */}

        <section className="case-header">

          <div>
            <div className="eyebrow">
              ACTIVE INVESTIGATION
            </div>

            <h1>
              {overview?.title || "Digital Investigation"}
            </h1>

            <p>
              Shared investigative context powered by the
              AEGIS Knowledge Graph.
            </p>
          </div>

          <button
            className="run-button"
            onClick={runInvestigation}
            disabled={running}
          >
            {running
              ? "Running Investigation..."
              : "Run Investigation"}
          </button>

        </section>


        {/* AGENTS */}

        <section className="panel">

          <div className="panel-title">
            <span>AGENT ORCHESTRATION</span>

            <span className="live">
              ● LIVE
            </span>
          </div>

          <div className="agent-grid">

            {AGENTS.map((agent) => {

              const status =
                agentStatus[agent.id] ||
                "NOT_REQUESTED";

              return (
                <div
                  className="agent-card"
                  key={agent.id}
                >

                  <div className="agent-icon">
                    {agent.short[0]}
                  </div>

                  <div className="agent-info">

                    <strong>
                      {agent.name}
                    </strong>

                    <span
                      className={`status ${status.toLowerCase()}`}
                    >
                      {status}
                    </span>

                  </div>

                </div>
              );
            })}

          </div>

        </section>


        {/* INTELLIGENCE CARDS */}

        <section className="stats">

          <div className="stat-card">
            <span>PEOPLE</span>
            <strong>{people.length}</strong>
          </div>

          <div className="stat-card">
            <span>ACCOUNTS</span>
            <strong>{accounts.length}</strong>
          </div>

          <div className="stat-card">
            <span>FINDINGS</span>
            <strong>{findings.length}</strong>
          </div>

          <div className="stat-card">
            <span>LEADS</span>
            <strong>{leads.length}</strong>
          </div>

          <div className="stat-card warning">
            <span>SAFEGUARDING</span>
            <strong>{flags.length}</strong>
          </div>

        </section>


        {/* TWO COLUMN AREA */}

        <div className="two-column">

          {/* EVIDENCE */}

          <section className="panel">

            <div className="panel-title">
              <span>EVIDENCE INGESTION</span>
            </div>

            <div className="upload-area">

              {imagePreview ? (
                <img
                  src={imagePreview}
                  className="evidence-preview"
                />
              ) : (
                <div className="upload-placeholder">
                  <div className="upload-symbol">
                    +
                  </div>

                  <strong>
                    Upload digital evidence
                  </strong>

                  <span>
                    Screenshot / image evidence
                  </span>
                </div>
              )}

              <input
                type="file"
                accept="image/*"
                onChange={handleImageChange}
              />

              <button
                className="secondary-button"
                onClick={uploadEvidence}
                disabled={!image || imageLoading}
              >
                {imageLoading
                  ? "Analysing..."
                  : "Analyse Evidence"}
              </button>

            </div>


            {imageResult && (
              <div className="evidence-result">

                <div className="result-label">
                  EXTRACTION RESULT
                </div>

                <div className="result-name">
                  {imageResult.contact?.contact_name ||
                    "Unknown contact"}
                </div>

                <div className="result-meta">
                  {imageResult.contact?.last_seen ||
                    "No last-seen information detected"}
                </div>

                <p>
                  {imageResult.summary}
                </p>

                <div className="entity-list">

                  {(imageResult.entities || []).map(
                    (entity, index) => (
                      <span
                        className="entity-chip"
                        key={index}
                      >
                        {entity.type}: {entity.value}
                      </span>
                    )
                  )}

                </div>

              </div>
            )}

          </section>


          {/* COPILOT */}

          <section className="panel copilot">

            <div className="panel-title">
              <span>CASE INTELLIGENCE ASSISTANT</span>

              <span className="ai-badge">
                AI
              </span>
            </div>

            <div className="copilot-intro">
              Ask questions about the investigative
              context stored in the Knowledge Graph.
            </div>

            <div className="question-box">

              <textarea
                value={question}
                onChange={(event) =>
                  setQuestion(event.target.value)
                }
                placeholder="e.g. What connections have been identified in this case?"
              />

              <button
                className="run-button"
                onClick={askCopilot}
                disabled={
                  copilotLoading ||
                  !question.trim()
                }
              >
                {copilotLoading
                  ? "Thinking..."
                  : "Ask AEGIS"}
              </button>

            </div>

            {answer && (
              <div className="copilot-answer">

                <div className="result-label">
                  AEGIS RESPONSE
                </div>

                <p>
                  {answer}
                </p>

              </div>
            )}

          </section>

        </div>


        {/* FINDINGS */}

        <section className="panel">

          <div className="panel-title">
            <span>INVESTIGATIVE FINDINGS</span>
          </div>

          {findings.length === 0 ? (
            <div className="empty">
              No findings available yet.
            </div>
          ) : (
            <div className="finding-list">

              {findings.map((finding) => (
                <div
                  className="finding"
                  key={finding.finding_id}
                >

                  <span className="finding-type">
                    {finding.type}
                  </span>

                  <span>
                    {finding.description}
                  </span>

                </div>
              ))}

            </div>
          )}

        </section>


        {/* LEADS + SAFEGUARDING */}

        <div className="two-column">

          <section className="panel">

            <div className="panel-title">
              <span>INVESTIGATIVE LEADS</span>
            </div>

            {leads.length === 0 ? (
              <div className="empty">
                No leads generated yet.
              </div>
            ) : (
              leads.map((lead) => (
                <div
                  className="lead"
                  key={lead.lead_id}
                >

                  <div className="lead-header">

                    <strong>
                      {lead.subject}
                    </strong>

                    <span
                      className={`priority ${String(
                        lead.priority
                      ).toLowerCase()}`}
                    >
                      {lead.priority}
                    </span>

                  </div>

                  <p>
                    {lead.reason}
                  </p>

                  <small>
                    Direction:{" "}
                    {lead.recommended_direction}
                  </small>

                </div>
              ))
            )}

          </section>


          <section className="panel">

            <div className="panel-title">
              <span>VICTIM SAFEGUARDING</span>
            </div>

            {flags.length === 0 ? (
              <div className="empty">
                No safeguarding flags.
              </div>
            ) : (
              flags.map((flag) => (
                <div
                  className="flag"
                  key={flag.flag_id}
                >

                  <div className="lead-header">

                    <strong>
                      {flag.type}
                    </strong>

                    <span
                      className={`priority ${String(
                        flag.severity
                      ).toLowerCase()}`}
                    >
                      {flag.severity}
                    </span>

                  </div>

                  <p>
                    {flag.description}
                  </p>

                  <small>
                    Recommended action:{" "}
                    {flag.recommended_action}
                  </small>

                </div>
              ))
            )}

          </section>

        </div>

      </main>

    </div>
  );
}

export default App;