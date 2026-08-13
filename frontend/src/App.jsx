import { useEffect, useState } from "react";
import "./App.css";

const API = "http://localhost:8000";

const AGENT_LABELS = {
  entity_extraction: "Entity Extraction",
  correlation: "Correlation",
  lead_intelligence: "Lead Intelligence",
  victim_safeguarding: "Victim Safeguarding",
};

const AGENT_ICONS = {
  entity_extraction: "◈",
  correlation: "⌘",
  lead_intelligence: "✦",
  victim_safeguarding: "◇",
};

function App() {
  const [view, setView] = useState("case");
  const [caseId, setCaseId] = useState(null);

  const [cases, setCases] = useState([]);
  const [casesLoading, setCasesLoading] = useState(false);

  const [tasks, setTasks] = useState([]);
  const [status, setStatus] = useState(null);
  const [executions, setExecutions] = useState([]);
  const [overview, setOverview] = useState(null);

  const [command, setCommand] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [selectedTask, setSelectedTask] = useState(null);

  const [copilotQuestion, setCopilotQuestion] = useState("");
  const [copilotAnswer, setCopilotAnswer] = useState("");
  const [copilotLoading, setCopilotLoading] = useState(false);

  async function loadCases() {
    setCasesLoading(true);

    try {
      const response = await fetch(`${API}/cases`);

      if (!response.ok) {
        throw new Error(await response.text());
      }

      const data = await response.json();
      setCases(data.cases || []);
    } catch (error) {
      console.error("Case loading failed:", error);
    } finally {
      setCasesLoading(false);
    }
  }
  
  async function loadDashboard() {
    try {
      const tasksUrl = caseId
        ? `${API}/orchestrator/tasks?case_id=${caseId}`
        : `${API}/orchestrator/tasks`;

      const executionsUrl = caseId
        ? `${API}/executions?case_id=${caseId}`
        : `${API}/executions`;

      const requests = [
        fetch(tasksUrl),
        fetch(`${API}/orchestrator/status`),
        fetch(executionsUrl),
      ];

      if (caseId) {
        requests.push(
          fetch(`${API}/cases/${caseId}/overview`)
        );
      }

      const responses = await Promise.all(requests);

      const [tasksRes, statusRes, executionsRes, overviewRes] =
        responses;

      if (tasksRes.ok) {
        const data = await tasksRes.json();
        setTasks(data.tasks || []);
      }

      if (statusRes.ok) {
        const data = await statusRes.json();
        setStatus(data);
      }

      if (executionsRes.ok) {
        const data = await executionsRes.json();
        setExecutions(data.executions || []);
      }

      if (overviewRes?.ok) {
        const data = await overviewRes.json();
        setOverview(data);
      }
    } catch (error) {
      console.error("Dashboard refresh failed:", error);
    }
  }

  useEffect(() => {
    loadCases();
  }, []);

  useEffect(() => {
    loadDashboard();

    const interval = setInterval(loadDashboard, 1500);

    return () => clearInterval(interval);
  }, [caseId]);

  function openCase(selectedCaseId) {
    setCaseId(selectedCaseId);
    setView("case");
  }

  function backToCases() {
    setCaseId(null);
    setView("case");
    loadCases();
  }

  async function submitCommand(event) {
    event.preventDefault();

    if (!command.trim() || submitting) {
      return;
    }

    setSubmitting(true);

    try {
      const response = await fetch(`${API}/orchestrator/command`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          command: command.trim(),
          default_case_id: caseId,
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText);
      }

      setCommand("");

      await loadDashboard();
    } catch (error) {
      console.error("Command failed:", error);
      alert("Could not submit investigation command.");
    } finally {
      setSubmitting(false);
    }
  }

  async function retryTask(taskId) {
    try {
      const response = await fetch(
        `${API}/orchestrator/tasks/${taskId}/retry`,
        {
          method: "POST",
        }
      );

      if (!response.ok) {
        throw new Error(await response.text());
      }

      await loadDashboard();
    } catch (error) {
      console.error("Retry failed:", error);
      alert("Could not retry task.");
    }
  }

  async function askCopilot(event) {
    event.preventDefault();

    if (!copilotQuestion.trim() || copilotLoading) {
      return;
    }

    setCopilotLoading(true);

    try {
      const response = await fetch(`${API}/copilot/${caseId}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question: copilotQuestion.trim(),
        }),
      });

      if (!response.ok) {
        throw new Error(await response.text());
      }

      const data = await response.json();

      setCopilotAnswer(
        data.answer ||
          data.response ||
          "No answer was returned."
      );

      setCopilotQuestion("");
    } catch (error) {
      console.error("Copilot failed:", error);
      setCopilotAnswer(
        "Copilot could not answer this question."
      );
    } finally {
      setCopilotLoading(false);
    }
  }

  const counts = {
    ready: tasks.filter((t) => t.status === "READY").length,
    waiting: tasks.filter((t) => t.status === "WAITING").length,
    running: tasks.filter((t) => t.status === "RUNNING").length,
    completed: tasks.filter((t) => t.status === "COMPLETED").length,
    failed: tasks.filter((t) => t.status === "FAILED").length,
    humanReview: tasks.filter(
      (t) => t.status === "HUMAN_REVIEW"
    ).length,
    blocked: tasks.filter((t) => t.status === "BLOCKED").length,
  };

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">A</div>

          <div>
            <div className="brand-name">AEGIS</div>
            <div className="brand-subtitle">
              AI-Enabled Evidence & Graph Intelligence System
            </div>
          </div>
        </div>

        <div className="system-status">
          <span className="status-dot" />
          SYSTEM OPERATIONAL
        </div>
      </header>

      <div className="main-layout">
        <aside className="sidebar">
          <div className="sidebar-section">
            <div className="sidebar-label">INVESTIGATION</div>

            <button
              className={
                view === "case"
                  ? "nav-button active"
                  : "nav-button"
              }
              onClick={() => {
                setCaseId(null);
                setView("case");
                loadCases();
              }}
            >
              <span>▣</span>
              Case Workspace
            </button>

            <button
              className={
                view === "orchestrator"
                  ? "nav-button active"
                  : "nav-button"
              }
              onClick={() => {
                setView("orchestrator");
                loadDashboard();
              }}
            >
              <span>◫</span>
              Orchestrator
            </button>
          </div>
          
          <div className="sidebar-footer">
            <div className="human-control">
              <span className="control-icon">✓</span>

              <div>
                <strong>Human-in-the-loop</strong>
                <span>Investigator control enabled</span>
              </div>
            </div>
          </div>
        </aside>

        <main className="content">
          {view === "case" && !caseId && (
            <CaseBrowser
              cases={cases}
              loading={casesLoading}
              onOpenCase={openCase}
            />
          )}

          {view === "case" && caseId && (
            <CaseWorkspace
              caseId={caseId}
              overview={overview}
              onBack={backToCases}
              tasks={tasks}
              counts={counts}
              status={status}
              executions={executions}
              copilotQuestion={copilotQuestion}
              setCopilotQuestion={setCopilotQuestion}
              copilotAnswer={copilotAnswer}
              copilotLoading={copilotLoading}
              askCopilot={askCopilot}
            />
          )}

          {view === "orchestrator" && (
            <OrchestratorView
              tasks={tasks}
              counts={counts}
              status={status}
              executions={executions}
              selectedTask={selectedTask}
              setSelectedTask={setSelectedTask}
              retryTask={retryTask}
              command={command}
              setCommand={setCommand}
              submitCommand={submitCommand}
              submitting={submitting}
            />
          )}
        </main>
      </div>
    </div>
  );
}

function CaseBrowser({ cases, loading, onOpenCase }) {
  const [search, setSearch] = useState("");

  const filteredCases = cases.filter((item) => {
    const text = `
      ${item.case_id}
      ${item.title}
      ${item.status}
      ${item.last_modified_by}
    `.toLowerCase();

    return text.includes(search.toLowerCase());
  });
  return (
    <div className="case-browser">
      <div className="page-heading">
        <div>
          <div className="eyebrow">INVESTIGATIONS</div>
          <h1>Case Workspace</h1>
          <p className="page-subtitle">
            Select an investigation to view its complete intelligence,
            evidence, findings, leads, and agent activity.
          </p>
        </div>

        <div className="case-count">
          {cases.length} {cases.length === 1 ? "case" : "cases"}
        </div>
      </div>

      <div className="case-toolbar">
        <div className="case-search">
          <span>⌕</span>
          <input
            type="text"
            placeholder="Search cases..."
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>
      </div>

      <div className="case-list">
        <div className="case-list-header">
          <span>CASE</span>
          <span>STATUS</span>
          <span>LAST MODIFIED BY</span>
          <span>LAST MODIFIED</span>
        </div>

        {loading ? (
          <div className="case-empty">
            Loading investigations...
          </div>
        ) : cases.length === 0 ? (
          <div className="case-empty">
            No investigations found.
          </div>
        ) : (
          filteredCases.map((item) => (
            <button
              key={item.case_id}
              className="case-row"
              onClick={() => onOpenCase(item.case_id)}
            >
              <div className="case-main">
                <div className="case-icon">📁</div>

                <div>
                  <div className="case-name">
                    {item.case_id}
                  </div>

                  <div className="case-title">
                    {item.title}
                  </div>
                </div>
              </div>

              <div>
                <StatusBadge status={item.status} />
              </div>

              <div className="case-modified-by">
                {item.last_modified_by || "AEGIS"}
              </div>

              <div className="case-modified">
                {formatDate(item.last_modified_at)}
              </div>
            </button>
          ))
        )}
      </div>
    </div>
  );
}

function CaseWorkspace({
  caseId,
  overview,
  tasks,
  onBack,
  executions,
  counts,
  copilotQuestion,
  setCopilotQuestion,
  copilotAnswer,
  copilotLoading,
  askCopilot,
}) {
  const people = overview?.people || [];
  const accounts = overview?.accounts || [];
  const devices = overview?.devices || [];
  const findings = overview?.findings || [];
  const leads = overview?.leads || [];
  const safeguardingFlags = overview?.safeguarding_flags || [];

  return (
    <>
      <button
        className="back-to-cases"
        onClick={onBack}
      >
        ← All Cases
      </button>
      <div className="page-header">
        <div>
          <div className="eyebrow">CASE WORKSPACE</div>
          <h1>{overview?.title || "Investigation Workspace"}</h1>
          <p>
            {caseId} · Investigator-controlled case intelligence
          </p>
        </div>

        <div className="case-status">
          <span className="status-dot" />
          {overview?.status || "LOADING"}
        </div>
      </div>

      {/* Case metrics */}
      <div className="metric-grid">
        <MetricCard
          label="Tasks"
          value={counts.ready + counts.waiting + counts.running +
            counts.completed + counts.failed + counts.humanReview +
            counts.blocked}
          hint={`${counts.completed} completed`}
        />

        <MetricCard
          label="Entities"
          value={people.length + accounts.length + devices.length}
          hint={`${people.length} people · ${accounts.length} accounts`}
        />

        <MetricCard
          label="Findings"
          value={findings.length}
          hint="Correlation patterns"
        />

        <MetricCard
          label="Active Leads"
          value={leads.length}
          hint="AI-generated investigative leads"
        />
      </div>

      {/* Intelligence overview */}
      <div className="section-heading">
        <div>
          <div className="eyebrow">INVESTIGATIVE INTELLIGENCE</div>
          <h2>Case Intelligence</h2>
        </div>
      </div>

      <div className="intelligence-grid">

        {/* Entities */}
        <section className="panel">
          <PanelHeader
            title="Entities"
            subtitle="Entities identified from evidence"
          />

          <div className="entity-group">
            <div className="entity-label">PEOPLE</div>

            {people.length === 0 ? (
              <EmptyState text="No people identified." />
            ) : (
              people.map((person, index) => (
                <div className="entity-row" key={`person-${index}`}>
                  <div className="entity-icon">P</div>

                  <div className="entity-content">
                    <strong>{person.name}</strong>
                    <span>{person.id}</span>
                  </div>
                </div>
              ))
            )}
          </div>

          <div className="entity-group">
            <div className="entity-label">ACCOUNTS</div>

            {accounts.length === 0 ? (
              <EmptyState text="No accounts identified." />
            ) : (
              accounts.map((account, index) => (
                <div className="entity-row" key={`account-${index}`}>
                  <div className="entity-icon">@</div>

                  <div className="entity-content">
                    <strong>{account.username}</strong>
                    <span>Account</span>
                  </div>
                </div>
              ))
            )}
          </div>

          <div className="entity-group">
            <div className="entity-label">DEVICES</div>

            {devices.length === 0 ? (
              <EmptyState text="No devices identified." />
            ) : (
              devices.map((device, index) => (
                <div className="entity-row" key={`device-${index}`}>
                  <div className="entity-icon">D</div>

                  <div className="entity-content">
                    <strong>{device.device_id}</strong>
                    <span>{device.type || "Device"}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </section>

        {/* Findings */}
        <section className="panel">
          <PanelHeader
            title="Patterns & Findings"
            subtitle="Cross-entity correlations identified by AEGIS"
          />

          {findings.length === 0 ? (
            <EmptyState text="No correlation findings yet." />
          ) : (
            <div className="finding-list">
              {findings.map((finding) => (
                <div className="finding-card" key={finding.finding_id}>
                  <div className="finding-top">
                    <span className="finding-type">
                      {finding.type}
                    </span>

                    <span className="finding-id">
                      {finding.finding_id}
                    </span>
                  </div>

                  <p>{finding.description}</p>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Leads */}
        <section className="panel">
          <PanelHeader
            title="Priority Leads"
            subtitle="AI-generated investigative directions"
          />

          {leads.length === 0 ? (
            <EmptyState text="No leads generated yet." />
          ) : (
            <div className="lead-list">
              {leads.map((lead) => (
                <div className="lead-card" key={lead.lead_id}>
                  <div className="lead-header">
                    <div>
                      <div className="lead-subject">
                        {lead.subject}
                      </div>

                      <div className="lead-meta">
                        Confidence {Math.round(lead.confidence * 100)}%
                      </div>
                    </div>

                    <StatusBadge status={lead.priority} />
                  </div>

                  <p>{lead.reason}</p>

                  <div className="lead-direction">
                    <span>RECOMMENDED DIRECTION</span>
                    <strong>{lead.recommended_direction}</strong>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Safeguarding */}
        <section className="panel">
          <PanelHeader
            title="Safeguarding Alerts"
            subtitle="Potential victim-safety concerns requiring review"
          />

          {safeguardingFlags.length === 0 ? (
            <EmptyState text="No safeguarding alerts." />
          ) : (
            <div className="safeguard-list">
              {safeguardingFlags.map((flag) => (
                <div className="safeguard-card" key={flag.flag_id}>
                  <div className="safeguard-header">
                    <div>
                      <div className="safeguard-type">
                        {flag.type}
                      </div>

                      <div className="safeguard-subject">
                        {flag.subject}
                      </div>
                    </div>

                    <StatusBadge status={flag.severity} />
                  </div>

                  <p>{flag.description}</p>

                  <div className="safeguard-action">
                    <span>RECOMMENDED ACTION</span>
                    <strong>{flag.recommended_action}</strong>
                  </div>

                  <div className="safeguard-status">
                    STATUS · {flag.status}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>

      {/* Investigation activity */}
      <div className="section-heading">
        <div>
          <div className="eyebrow">ORCHESTRATOR ACTIVITY</div>
          <h2>Investigation Activity</h2>
        </div>
      </div>

      <div className="case-grid">

        <section className="panel">
          <PanelHeader
            title="Tasks"
            subtitle="Investigation tasks for this case"
          />

          {tasks.length === 0 ? (
            <EmptyState text="No investigation tasks yet." />
          ) : (
            <div className="activity-list">
              {tasks.slice(0, 8).map((task) => (
                <TaskRow
                  key={task.task_id}
                  task={task}
                />
              ))}
            </div>
          )}
        </section>

        <section className="panel">
          <PanelHeader
            title="Execution History"
            subtitle="Agent executions for this case"
          />

          {executions.length === 0 ? (
            <EmptyState text="No agent executions yet." />
          ) : (
            <div className="activity-list">
              {executions.slice(0, 8).map((execution) => (
                <ExecutionRow
                  key={execution.execution_id}
                  execution={execution}
                />
              ))}
            </div>
          )}
        </section>
      </div>

      {/* Copilot */}
      <section className="panel copilot-panel">
        <PanelHeader
          title="Case Intelligence Assistant"
          subtitle="Ask questions about the current investigation"
        />

        <form className="copilot-form" onSubmit={askCopilot}>
          <input
            className="copilot-input"
            value={copilotQuestion}
            onChange={(event) =>
              setCopilotQuestion(event.target.value)
            }
            placeholder="Ask about entities, findings, leads, or relationships..."
          />

          <button
            className="primary-button"
            type="submit"
            disabled={copilotLoading}
          >
            {copilotLoading ? "ANALYZING..." : "ASK AEGIS"}
          </button>
        </form>

        {copilotAnswer && (
          <div className="copilot-answer">
            <div className="copilot-answer-label">
              AEGIS RESPONSE
            </div>

            <div className="copilot-answer-text">
              {copilotAnswer}
            </div>
          </div>
        )}
      </section>
    </>
  );
}


function OrchestratorView({
  command,
  setCommand,
  submitCommand,
  submitting,
  status,
  tasks,
  executions,
  selectedTask,
  setSelectedTask,
  retryTask,
  counts,
}) {
  return (
    <>
      <div className="page-header">
        <div>
          <div className="eyebrow">AEGIS ORCHESTRATOR</div>

          <h1>Investigation Control</h1>

          <p>
            Schedule, coordinate and monitor specialist agents.
          </p>
        </div>

        <div className="scheduler-status">
          <span className="status-dot" />

          {status?.scheduler?.status || "CONNECTING"}
        </div>
      </div>

      <section className="command-panel">
        <div className="command-heading">
          <div>
            <div className="panel-title">
              New Investigation Task
            </div>

            <div className="panel-subtitle">
              Describe what you want AEGIS to investigate.
            </div>
          </div>

          <span className="command-tag">
            HUMAN INITIATED
          </span>
        </div>

        <form
          className="command-form"
          onSubmit={submitCommand}
        >
          <input
            value={command}
            onChange={(event) =>
              setCommand(event.target.value)
            }
            placeholder='e.g. "Run correlation on CASE-001"'
          />

          <button
            type="submit"
            disabled={submitting}
          >
            {submitting ? "Scheduling..." : "Schedule"}
          </button>
        </form>
      </section>

      <section>
        <div className="section-heading">
          <div>
            <div className="panel-title">
              Agent Capacity
            </div>

            <div className="panel-subtitle">
              Current execution availability
            </div>
          </div>
        </div>

        <div className="agent-grid">
          {(status?.agents || []).map((agent) => (
            <AgentCard
              key={agent.agent_id}
              agent={agent}
            />
          ))}
        </div>
      </section>

      <section className="queue-section">
        <div className="section-heading">
          <div>
            <div className="panel-title">
              Investigation Queue
            </div>

            <div className="panel-subtitle">
              {tasks.length} tasks · {counts.running} running ·{" "}
              {counts.waiting} waiting
            </div>
          </div>
        </div>

        <div className="queue-grid">
          <TaskColumn
            title="READY"
            tasks={tasks.filter(
              (task) => task.status === "READY"
            )}
            onSelect={setSelectedTask}
          />

          <TaskColumn
            title="WAITING"
            tasks={tasks.filter(
              (task) => task.status === "WAITING"
            )}
            onSelect={setSelectedTask}
          />

          <TaskColumn
            title="RUNNING"
            tasks={tasks.filter(
              (task) => task.status === "RUNNING"
            )}
            onSelect={setSelectedTask}
          />

          <TaskColumn
            title="COMPLETED"
            tasks={[...tasks]
              .filter((task) => task.status === "COMPLETED")
              .sort(
                (a, b) =>
                  new Date(b.completed_at || 0) -
                  new Date(a.completed_at || 0)
              )}
            onSelect={setSelectedTask}
          />
        </div>

        {(counts.failed ||
          counts.humanReview ||
          counts.blocked) > 0 && (
          <div className="exception-row">
            {tasks
              .filter((task) =>
                [
                  "FAILED",
                  "HUMAN_REVIEW",
                  "BLOCKED",
                ].includes(task.status)
              )
              .map((task) => (
                <div
                  className="exception-card"
                  key={task.task_id}
                >
                  <TaskRow task={task} />

                  {["FAILED", "HUMAN_REVIEW", "BLOCKED"].includes(
                    task.status
                  ) && (
                    <button
                      className="retry-button"
                      onClick={() =>
                        retryTask(task.task_id)
                      }
                    >
                      Retry
                    </button>
                  )}
                </div>
              ))}
          </div>
        )}
      </section>

      <section className="panel execution-panel">
        <PanelHeader
          title="Execution History"
          subtitle="Latest orchestrator activity"
        />

        {executions.length === 0 ? (
          <EmptyState text="No executions recorded yet." />
        ) : (
          <div className="execution-list">
            {executions.slice(0, 10).map((execution) => (
              <ExecutionRow
                key={execution.execution_id}
                execution={execution}
              />
            ))}
          </div>
        )}
      </section>

      {selectedTask && (
        <TaskDetail
          task={selectedTask}
          onClose={() => setSelectedTask(null)}
        />
      )}
    </>
  );
}


function MetricCard({ label, value, detail }) {
  return (
    <div className="metric-card">
      <div className="metric-label">{label}</div>

      <div className="metric-value">{value}</div>

      <div className="metric-detail">{detail}</div>
    </div>
  );
}


function AgentCard({ agent }) {
  const label =
    AGENT_LABELS[agent.agent_id] || agent.agent_id;

  const icon =
    AGENT_ICONS[agent.agent_id] || "○";

  return (
    <div className="agent-card">
      <div className="agent-icon">{icon}</div>

      <div className="agent-info">
        <div className="agent-name">{label}</div>

        <div className="agent-capacity">
          {agent.running} / {agent.capacity} active
        </div>
      </div>

      <div
        className={
          agent.status === "BUSY"
            ? "agent-state busy"
            : "agent-state"
        }
      >
        {agent.status}
      </div>
    </div>
  );
}


function TaskColumn({
  title,
  tasks,
  onSelect,
}) {
  return (
    <div className="task-column">
      <div className="column-header">
        <span>{title}</span>
        <span className="column-count">
          {tasks.length}
        </span>
      </div>

      <div className="column-body">
        {tasks.length === 0 ? (
          <div className="column-empty">
            No tasks
          </div>
        ) : (
          tasks.map((task) => (
            <TaskCard
              key={task.task_id}
              task={task}
              onClick={() => onSelect(task)}
            />
          ))
        )}
      </div>
    </div>
  );
}


function TaskCard({ task, onClick }) {
  const label =
    AGENT_LABELS[task.agent_id] || task.agent_id;

  return (
    <button
      className="task-card"
      onClick={onClick}
    >
      <div className="task-card-top">
        <span className="task-agent">
          {label}
        </span>

        <StatusBadge status={task.status} />
      </div>

      <div className="task-description">
        {task.description}
      </div>

      <div className="task-meta">
        <span>{task.case_id}</span>

        <span>
          {task.attempts || 0}/{task.max_retries || 0}
        </span>
      </div>
    </button>
  );
}


function TaskRow({ task }) {
  const label =
    AGENT_LABELS[task.agent_id] || task.agent_id;

  return (
    <div className="task-row">
      <div className="task-row-icon">
        {AGENT_ICONS[task.agent_id] || "○"}
      </div>

      <div className="task-row-main">
        <div className="task-row-title">
          {label}
        </div>

        <div className="task-row-description">
          {task.description}
        </div>

        <div className="task-row-meta">
          {task.case_id} · {task.task_id}
        </div>
      </div>

      <StatusBadge status={task.status} />
    </div>
  );
}


function ExecutionRow({ execution }) {
  const agentExecutions =
    execution.agent_executions || [];

  return (
    <div className="execution-row">
      <div className="execution-main">
        <div className="execution-id">
          {execution.execution_id}
        </div>

        <div className="execution-case">
          {execution.case_id}
        </div>
      </div>

      <div className="execution-agents">
        {agentExecutions.map((agent) => (
          <span
            className="execution-agent"
            key={agent.agent_execution_id}
          >
            {AGENT_LABELS[agent.agent_id] ||
              agent.agent_id}
          </span>
        ))}
      </div>

      <StatusBadge status={execution.status} />
    </div>
  );
}


function StatusBadge({ status }) {
  return (
    <span
      className={`status-badge status-${String(
        status || ""
      ).toLowerCase()}`}
    >
      {status}
    </span>
  );
}


function TaskDetail({ task, onClose }) {
  const label =
    AGENT_LABELS[task.agent_id] || task.agent_id;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="task-detail"
        onClick={(event) =>
          event.stopPropagation()
        }
      >
        <div className="detail-header">
          <div>
            <div className="eyebrow">
              TASK DETAILS
            </div>

            <h2>{task.task_id}</h2>
          </div>

          <button
            className="close-button"
            onClick={onClose}
          >
            ×
          </button>
        </div>

        <div className="detail-status">
          <StatusBadge status={task.status} />
        </div>

        <div className="detail-grid">
          <DetailItem
            label="Agent"
            value={label}
          />

          <DetailItem
            label="Case"
            value={task.case_id}
          />

          <DetailItem
            label="Attempts"
            value={`${task.attempts || 0} / ${
              task.max_retries || 0
            }`}
          />

          <DetailItem
            label="Priority"
            value={task.priority}
          />

          <DetailItem
            label="Created"
            value={formatDate(task.created_at)}
          />

          <DetailItem
            label="Started"
            value={formatDate(task.started_at)}
          />

          <DetailItem
            label="Completed"
            value={formatDate(task.completed_at)}
          />

          <DetailItem
            label="Dependencies"
            value={
              task.depends_on?.length
                ? task.depends_on.join(", ")
                : "None"
            }
          />
        </div>

        <div className="detail-description">
          <div className="detail-label">
            DESCRIPTION
          </div>

          <p>{task.description}</p>
        </div>

        {task.error && (
          <div className="error-box">
            <div className="detail-label">
              ERROR
            </div>

            <p>{task.error}</p>
          </div>
        )}
      </div>
    </div>
  );
}


function DetailItem({ label, value }) {
  return (
    <div className="detail-item">
      <div className="detail-label">{label}</div>
      <div className="detail-value">
        {value || "—"}
      </div>
    </div>
  );
}


function PanelHeader({ title, subtitle }) {
  return (
    <div className="panel-header">
      <div className="panel-title">{title}</div>
      <div className="panel-subtitle">{subtitle}</div>
    </div>
  );
}


function EmptyState({ text }) {
  return (
    <div className="empty-state">
      {text}
    </div>
  );
}


function formatDate(value) {
  if (!value) {
    return "—";
  }

  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}


export default App;