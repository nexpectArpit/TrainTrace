import React, { useState, useEffect, useRef, useCallback } from "react";
import { request } from "./services/api";
import {
  freshRun,
  emptyExperiment,
  emptyDecision,
  fmt,
  Badge,
  Field,
  Select,
} from "./components/Common";
import Investigations from "./screens/Investigations";
import Training from "./screens/Training";
import Compare from "./screens/Compare";
import Audits from "./screens/Audits";
import Decisions from "./screens/Decisions";
import History from "./screens/History";
import Registry from "./screens/Registry";
import Inference from "./screens/Inference";
import "./App.css";
const tabs = [
  "Investigations",
  "Training",
  "Compare",
  "Audits",
  "Decisions",
  "History",
  "Registry",
  "Inference",
];

export default function App() {
  const [tab, setTab] = useState(() =>
    tabs.includes(localStorage.getItem("traintrace-tab"))
      ? localStorage.getItem("traintrace-tab")
      : "Investigations",
  );
  const [expId, setExpId] = useState(
    () => localStorage.getItem("traintrace-investigation") || "",
  );
  const [runId, setRunId] = useState(
    () => localStorage.getItem("traintrace-run") || "",
  );
  const [experiments, setExperiments] = useState([]),
    [runs, setRuns] = useState([]),
    [models, setModels] = useState([]),
    [jobs, setJobs] = useState([]);
  const [activeModel, setActiveModel] = useState(null),
    [info, setInfo] = useState(null),
    [online, setOnline] = useState(false);
  const [connectionError, setConnectionError] = useState("");
  const [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [busy, setBusy] = useState(false),
    [query, setQuery] = useState("");
  const [setup, setSetup] = useState(freshRun),
    [newExp, setNewExp] = useState(emptyExperiment),
    [editExp, setEditExp] = useState(null);
  const [decision, setDecision] = useState(emptyDecision),
    [seeds, setSeeds] = useState("42, 101, 2024, 7, 99");
  const [release, setRelease] = useState({ name: "", version: "v1.0.0" }),
    [lineage, setLineage] = useState(null),
    [lineageId, setLineageId] = useState("");
  const [file, setFile] = useState(null),
    [prediction, setPrediction] = useState(null),
    [compare, setCompare] = useState([]);
  const [archFilter, setArchFilter] = useState(""),
    [statusFilter, setStatusFilter] = useState(""),
    [seedFilter, setSeedFilter] = useState(""),
    [accuracyMin, setAccuracyMin] = useState("");
  const [live, setLive] = useState(null),
    [events, setEvents] = useState([]);
  const requestSeq = useRef(0),
    eventCursor = useRef(0);
  const experiment = experiments.find((e) => e.id === expId),
    run = runs.find((r) => r.id === runId);
  const refresh = useCallback(async () => {
    const seq = ++requestSeq.current;
    try {
      const [e, s, m, j] = await Promise.all([
        request("/experiments/"),
        request("/system/info"),
        request("/registry/models"),
        request("/runs/jobs"),
      ]);
      const validInvestigation = e.experiments.some((row) => row.id === expId);
      const c = validInvestigation
        ? await request(`/runs/compare/${encodeURIComponent(expId)}`)
        : { comparison_matrix: [] };
      if (seq !== requestSeq.current) return;
      if (expId && !validInvestigation) {
        setExpId("");
        setRunId("");
      }
      setConnectionError("");
      setExperiments(e.experiments);
      setInfo(s);
      setModels(m.models);
      setActiveModel(m.active_model_id);
      setJobs(j.jobs);
      setRuns(c.comparison_matrix);
      setOnline(true);
      if (!expId && e.experiments.length)
        setExpId(
          e.experiments.find((e) => !e.archived)?.id || e.experiments[0].id,
        );
    } catch (e) {
      if (seq === requestSeq.current) {
        setOnline(false);
        setConnectionError(e.message);
      }
    }
  }, [expId]);
  useEffect(() => {
    refresh();
    return () => {
      requestSeq.current++;
    };
  }, [refresh]);
  useEffect(() => {
    localStorage.setItem("traintrace-tab", tab);
    localStorage.setItem("traintrace-investigation", expId);
    localStorage.setItem("traintrace-run", runId);
  }, [tab, expId, runId]);
  useEffect(() => {
    if (!notice) return;
    const timer = setTimeout(() => setNotice(""), 8000);
    return () => clearTimeout(timer);
  }, [notice]);
  useEffect(() => {
    setDecision(emptyDecision);
    setLive(null);
    setEvents([]);
    eventCursor.current = 0;
    setPrediction(null);
  }, [runId]);
  useEffect(() => {
    setPrediction(null);
  }, [activeModel]);
  useEffect(() => {
    if (!runId || tab !== "Training") return;
    let disposed = false,
      pending = false,
      timer = null;
    const poll = async () => {
      if (pending || disposed) return;
      pending = true;
      try {
        const data = await request(
          `/runs/${encodeURIComponent(runId)}/live-status?after=${eventCursor.current}`,
        );
        if (!disposed) {
          setLive(data);
          eventCursor.current = data.next_cursor;
          setEvents((prev) => [...prev, ...data.events].slice(-300));

          const isActive =
            data.status === "RUNNING" ||
            data.status === "PENDING" ||
            data.status === "QUEUED";

          if (isActive) {
            if (!timer) {
              timer = setInterval(poll, 1000);
            }
          } else {
            if (timer) {
              clearInterval(timer);
              timer = null;
            }
            refresh();
          }
        }
      } catch (e) {
        if (!disposed) {
          setError(e.message);
          if (timer) {
            clearInterval(timer);
            timer = null;
          }
        }
      } finally {
        pending = false;
      }
    };
    poll();
    return () => {
      disposed = true;
      if (timer) clearInterval(timer);
    };
  }, [runId, tab, refresh]);
  const act = async (fn) => {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await fn();
      await refresh();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };
  const switchExperiment = (id) => {
    setExpId(id);
    setRunId("");
    setRuns([]);
    setCompare([]);
    setEditExp(null);
    setLineage(null);
    setSetup(freshRun());
    setPrediction(null);
  };
  const visibleRuns = runs.filter(
    (r) =>
      (!query ||
        (r.id + " " + r.approach_name)
          .toLowerCase()
          .includes(query.toLowerCase())) &&
      (!archFilter || r.model_architecture === archFilter) &&
      (!statusFilter ||
        r.status === statusFilter ||
        r.latest_decision?.status === statusFilter) &&
      (!seedFilter || String(r.seed) === seedFilter) &&
      (accuracyMin === "" ||
        r.evaluation?.test_accuracy >= Number(accuracyMin)),
  );
  const chosen = runs.filter((r) => compare.includes(r.id)).slice(0, 4);
  const metrics =
    live?.run_id === runId ? live.all_metrics : run?.metrics || [];
  const executionStatus = live?.run_id === runId ? live.status : run?.status;
  const branch = (r) => {
    setSetup({
      ...freshRun(),
      predecessor_run_id: r.id,
      motivating_reason: r.latest_decision?.details?.limitations || "",
    });
    setTab("Training");
    setNotice(
      "Successor is linked to " +
        r.id +
        ". Describe the new approach and launch it.",
    );
  };
  const stop = (id) =>
    act(async () => {
      const result = await request(`/runs/jobs/${id}/stop`, "POST");
      setNotice(result.message);
    });
  const loadLineage = (id) =>
    act(async () => {
      setLineage(null);
      setLineageId(id);
      setLineage(await request(`/registry/${id}/lineage`));
    });
  const workspace = {
    tab,
    setTab,
    expId,
    setExpId,
    runId,
    setRunId,
    experiments,
    setExperiments,
    runs,
    setRuns,
    models,
    setModels,
    jobs,
    setJobs,
    activeModel,
    setActiveModel,
    info,
    setInfo,
    online,
    setOnline,
    error,
    setError,
    notice,
    setNotice,
    busy,
    setBusy,
    query,
    setQuery,
    setup,
    setSetup,
    newExp,
    setNewExp,
    editExp,
    setEditExp,
    decision,
    setDecision,
    seeds,
    setSeeds,
    release,
    setRelease,
    lineage,
    setLineage,
    lineageId,
    setLineageId,
    file,
    setFile,
    prediction,
    setPrediction,
    compare,
    setCompare,
    archFilter,
    setArchFilter,
    statusFilter,
    setStatusFilter,
    seedFilter,
    setSeedFilter,
    accuracyMin,
    setAccuracyMin,
    live,
    setLive,
    events,
    setEvents,
    requestSeq,
    eventCursor,
    experiment,
    run,
    refresh,
    act,
    switchExperiment,
    visibleRuns,
    chosen,
    metrics,
    executionStatus,
    branch,
    stop,
    loadLineage,
  };
  return (
    <div className="app-shell">
      <aside>
        <a href="#main" className="skip">
          Skip to content
        </a>
        <div className="brand">
          <span className="brand-mark">T</span>
          <div>
            TrainTrace<small>Evidence-led ML investigations</small>
          </div>
        </div>
        <nav aria-label="Workspace">
          {tabs.map((t) => (
            <button
              key={t}
              aria-current={tab === t ? "page" : undefined}
              onClick={() => setTab(t)}
            >
              {t}
            </button>
          ))}
        </nav>
        <div className="sidebar-status">
          <Badge value={online ? "API ONLINE" : "API OFFLINE"} />
          <p>
            {online
              ? info?.hardware?.name
              : "Connect the backend to load verified state."}
          </p>
          <small>
            Worker:{" "}
            {online ? (info?.worker_online ? "online" : "offline") : "unknown"}{" "}
            · {online ? (info?.queued_jobs ?? "—") : "—"} queued
          </small>
        </div>
      </aside>
      <main id="main">
        <header>
          <div>
            <div className="eyebrow">TRACKED TRAINING PIPELINE</div>
            <h1>{tab}</h1>
          </div>
          <button onClick={refresh} disabled={busy}>
            Refresh
          </button>
        </header>
        <div aria-live="polite">
          {notice && <div className="notice">{notice}</div>}
        </div>
        {connectionError && (
          <div className="error" role="alert">
            {connectionError}
          </div>
        )}
        {error && (
          <div className="error" role="alert">
            {error}
            <button aria-label="Dismiss error" onClick={() => setError("")}>
              ×
            </button>
          </div>
        )}
        {tab !== "Investigations" && (
          <>
            <div className="context-bar">
              {tab !== "Registry" && tab !== "Inference" && (
                <Select
                  label="Investigation"
                  value={expId}
                  onChange={switchExperiment}
                >
                  <option value="">Choose investigation</option>
                  {experiments
                    .filter(
                      (e) =>
                        !query ||
                        e.name.toLowerCase().includes(query.toLowerCase()) ||
                        e.id === expId,
                    )
                    .map((e) => (
                      <option key={e.id} value={e.id}>
                        {e.name}
                        {e.archived ? " (archived)" : ""}
                      </option>
                    ))}
                </Select>
              )}
              {(tab === "Audits" ||
                tab === "Decisions" ||
                tab === "Training") && (
                <Select label="Candidate run" value={runId} onChange={setRunId}>
                  <option value="">Choose a run</option>
                  {runs.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.approach_name} · {r.status}
                    </option>
                  ))}
                </Select>
              )}
              <Field
                label="Search investigations / runs / models"
                value={query}
                onChange={setQuery}
                placeholder="Name or run ID"
              />
            </div>
            {experiment && tab !== "Registry" && tab !== "Inference" && (
              <div className="investigation-summary">
                <strong>{experiment.name}</strong>
                <p>{experiment.objective}</p>
                <small>
                  Hypothesis:{" "}
                  {experiment.hypothesis || "Unknown (legacy record)"} ·
                  Targets: {fmt(experiment.target_accuracy)}% accuracy /{" "}
                  {fmt(experiment.target_latency_ms)} ms
                </small>
                {!!experiment.archived && <Badge value="ARCHIVED" />}
              </div>
            )}
          </>
        )}
        {tab === "Investigations" && <Investigations workspace={workspace} />}
        {tab === "Training" && <Training workspace={workspace} />}
        {tab === "Compare" && <Compare workspace={workspace} />}
        {tab === "Audits" && <Audits workspace={workspace} />}
        {tab === "Decisions" && <Decisions workspace={workspace} />}
        {tab === "History" && <History workspace={workspace} />}
        {tab === "Registry" && <Registry workspace={workspace} />}
        {tab === "Inference" && <Inference workspace={workspace} />}
        <footer>
          TrainTrace · Local single-user workspace ·{" "}
          {online
            ? `${jobs.filter((j) => j.status === "RUNNING").length} active job, ${jobs.filter((j) => j.status === "QUEUED").length} queued`
            : "Backend unavailable"}{" "}
          · Missing evidence is shown as unknown.
        </footer>
      </main>
    </div>
  );
}
