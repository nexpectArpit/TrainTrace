import { useState, useEffect, useRef, useCallback } from "react";
import { request } from "../services/api";
import { freshRun, emptyExperiment, emptyDecision } from "../components/Common";
import { tabs } from "./config";
import useLiveRun from "./useLiveRun";
import useTagSearch from "./useTagSearch";
import { filterRuns } from "./runFilters";

function tabFromLocation() {
  const pathPart = location.pathname.startsWith("/dashboard")
    ? location.pathname.replace(/^\/dashboard\/?/, "")
    : location.hash.startsWith("#/dashboard")
      ? location.hash.replace(/^#\/dashboard\/?/, "")
      : "";
  const segment = pathPart.split("/")[0];
  return tabs.find((t) => t.toLowerCase() === segment.toLowerCase()) || null;
}

export default function useWorkspace() {
  const [tab, setTabState] = useState(() => {
    const matched = tabFromLocation();
    if (matched) return matched;
    return tabs.includes(localStorage.getItem("traintrace-tab"))
      ? localStorage.getItem("traintrace-tab")
      : "Investigations";
  });
  const setTab = useCallback((nextTab) => {
    setTabState(nextTab);
    localStorage.setItem("traintrace-tab", nextTab);
    const nextPath = `/dashboard/${nextTab.toLowerCase()}`;
    if (location.pathname !== nextPath) {
      window.history.pushState(null, "", nextPath);
    }
  }, []);

  useEffect(() => {
    const handleNav = () => {
      const matched = tabFromLocation();
      if (matched) {
        setTabState(matched);
        localStorage.setItem("traintrace-tab", matched);
      }
    };
    window.addEventListener("popstate", handleNav);
    window.addEventListener("hashchange", handleNav);
    return () => {
      window.removeEventListener("popstate", handleNav);
      window.removeEventListener("hashchange", handleNav);
    };
  }, []);
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
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [busy, setBusy] = useState(false),
    [query, setQuery] = useState("");
  const tagSearchResults = useTagSearch(query);
  const [setup, setSetup] = useState(freshRun),
    [newExp, setNewExp] = useState(emptyExperiment),
    [editExp, setEditExp] = useState(null);
  const [decision, setDecision] = useState(emptyDecision),
    [seeds, setSeeds] = useState("42, 101, 2024, 7, 99");
  const [release, setRelease] = useState({
      name: "",
      version: "v1.0.0",
      tags: {},
    }),
    [lineage, setLineage] = useState(null),
    [lineageId, setLineageId] = useState("");
  const [file, setFile] = useState(null),
    [prediction, setPrediction] = useState(null),
    [compare, setCompare] = useState([]);
  const [archFilter, setArchFilter] = useState(""),
    [statusFilter, setStatusFilter] = useState(""),
    [seedFilter, setSeedFilter] = useState(""),
    [validationMin, setValidationMin] = useState(""),
    [validationMax, setValidationMax] = useState(""),
    [datasetFilter, setDatasetFilter] = useState(""),
    [optimizerFilter, setOptimizerFilter] = useState(""),
    [depthFilter, setDepthFilter] = useState("");
  const requestSeq = useRef(0);
  const experiment = experiments.find((e) => e.id === expId),
    run = runs.find((r) => r.id === runId);
  const refresh = useCallback(async () => {
    const seq = ++requestSeq.current;
    setRefreshing(true);
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
      if (runId && !c.comparison_matrix.some((row) => row.id === runId)) {
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
    } finally {
      if (seq === requestSeq.current) setRefreshing(false);
    }
  }, [expId, runId]);
  useEffect(() => {
    refresh();
    return () => {
      requestSeq.current++;
    };
  }, [refresh, tab]);
  const pendingFinalEvaluation = runs.some((row) =>
    ["QUEUED", "RUNNING"].includes(row.final_evaluation_status),
  );
  useEffect(() => {
    if (!pendingFinalEvaluation) return;
    const timer = setInterval(refresh, 2000);
    return () => clearInterval(timer);
  }, [pendingFinalEvaluation, refresh]);
  useEffect(() => {
    localStorage.setItem("traintrace-tab", tab);
    localStorage.setItem("traintrace-investigation", expId);
    localStorage.setItem("traintrace-run", runId);
  }, [tab, expId, runId]);
  useEffect(() => {
    setQuery("");
  }, [tab, expId]);
  useEffect(() => {
    if (!notice) return;
    const timer = setTimeout(() => setNotice(""), 8000);
    return () => clearTimeout(timer);
  }, [notice]);
  useEffect(() => {
    setDecision(emptyDecision);
    setPrediction(null);
  }, [runId]);
  useEffect(() => {
    setPrediction(null);
  }, [activeModel]);
  const { live, liveSamples, events, liveError } = useLiveRun({
    runId,
    tab,
    refresh,
    setTab,
    setNotice,
  });
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
  const visibleRuns = filterRuns(runs, {
    query,
    datasetFilter,
    archFilter,
    optimizerFilter,
    depthFilter,
    statusFilter,
    seedFilter,
    validationMin,
    validationMax,
  });
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
    connectionError,
    notice,
    setNotice,
    busy,
    setBusy,
    query,
    setQuery,
    tagSearchResults,
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
    validationMin,
    setValidationMin,
    validationMax,
    setValidationMax,
    datasetFilter,
    setDatasetFilter,
    optimizerFilter,
    setOptimizerFilter,
    depthFilter,
    setDepthFilter,
    live,
    liveSamples,
    liveError,
    events,
    experiment,
    run,
    refresh,
    refreshing,
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
  return workspace;
}
