import { useEffect, useMemo, useRef, useState } from "react";
import { request } from "../../services/api";

export const MAX_COMPARE_RUNS = 6;

/** Candidate loading, selection, image preview and inference request state. */
export default function useCheckpointComparison({
  workspace,
  mode,
  preferredRunIds,
}) {
  const { expId, online, refreshing } = workspace;
  const [candidates, setCandidates] = useState([]);
  const [candidatesLoading, setCandidatesLoading] = useState(false);
  const [candidatesError, setCandidatesError] = useState("");
  const [expFilter, setExpFilter] = useState("");
  const [selectedRunIds, setSelectedRunIds] = useState([]);
  const [compareFile, setCompareFile] = useState(null);
  const [comparePreviewUrl, setComparePreviewUrl] = useState("");
  const [expectedLabel, setExpectedLabel] = useState("");
  const [compareBusy, setCompareBusy] = useState(false);
  const [compareError, setCompareError] = useState("");
  const [compareResult, setCompareResult] = useState(null);
  const didInitializeSelection = useRef(false);

  useEffect(() => {
    if (!online || mode === "serving") return;
    let cancelled = false;
    setCandidatesLoading(true);
    setCandidatesError("");
    request("/inference/candidates")
      .then((res) => {
        if (cancelled) return;
        const rows = res.candidates || [];
        setCandidates(rows);
        setSelectedRunIds((prev) =>
          prev.filter((id) => rows.some((item) => item.run_id === id)),
        );
        if (!didInitializeSelection.current && rows.length) {
          didInitializeSelection.current = true;
          const activeExpRows = expId
            ? rows.filter((item) => item.experiment_id === expId)
            : [];
          const initialPool = activeExpRows.length ? activeExpRows : rows;
          if (activeExpRows.length) setExpFilter(expId);
          const firstDataset = initialPool[0]?.dataset_key;
          const sameDatasetInitial = initialPool
            .filter((item) => item.dataset_key === firstDataset)
            .slice(0, 2)
            .map((item) => item.run_id);
          setSelectedRunIds(sameDatasetInitial);
        }
      })
      .catch((err) => {
        if (!cancelled) setCandidatesError(err.message);
      })
      .finally(() => {
        if (!cancelled) setCandidatesLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [online, expId, refreshing, mode]);

  useEffect(() => {
    if (mode === "serving" || !preferredRunIds.length || !candidates.length)
      return;
    const eligible = preferredRunIds
      .filter((id) => candidates.some((candidate) => candidate.run_id === id))
      .slice(0, MAX_COMPARE_RUNS);
    if (eligible.length) {
      setSelectedRunIds(eligible);
      setCompareResult(null);
    }
  }, [preferredRunIds, candidates, mode]);

  useEffect(() => {
    if (!compareFile) {
      setComparePreviewUrl("");
      return;
    }
    const url = URL.createObjectURL(compareFile);
    setComparePreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [compareFile]);

  const investigationOptions = useMemo(() => {
    const map = new Map();
    for (const item of candidates) {
      if (!map.has(item.experiment_id)) {
        map.set(item.experiment_id, item.experiment_name);
      }
    }
    return Array.from(map.entries());
  }, [candidates]);

  const visibleCandidates = useMemo(
    () =>
      expFilter
        ? candidates.filter((item) => item.experiment_id === expFilter)
        : candidates,
    [candidates, expFilter],
  );

  const selectedCandidates = useMemo(
    () =>
      selectedRunIds
        .map((id) => candidates.find((item) => item.run_id === id))
        .filter(Boolean),
    [selectedRunIds, candidates],
  );

  const selectedDatasetKeys = useMemo(
    () => Array.from(new Set(selectedCandidates.map((c) => c.dataset_key))),
    [selectedCandidates],
  );

  const isSingleDataset = selectedDatasetKeys.length === 1;
  const isDigitDataset =
    isSingleDataset && ["mnist", "svhn"].includes(selectedDatasetKeys[0]);

  const availableClasses = useMemo(() => {
    if (!selectedCandidates.length) return [];
    if (isSingleDataset) return selectedCandidates[0].classes || [];
    const merged = new Set();
    for (const item of selectedCandidates) {
      for (const label of item.classes || []) merged.add(label);
    }
    return Array.from(merged);
  }, [selectedCandidates, isSingleDataset]);

  const useLabelSelect =
    isSingleDataset &&
    availableClasses.length > 0 &&
    availableClasses.length <= 10;

  useEffect(() => {
    if (
      expectedLabel &&
      availableClasses.length > 0 &&
      !availableClasses.some(
        (label) => label.toLowerCase() === expectedLabel.trim().toLowerCase(),
      )
    ) {
      setExpectedLabel("");
    }
  }, [availableClasses, expectedLabel]);

  const toggleRun = (runId, checked) => {
    setCompareResult(null);
    setCompareError("");
    setSelectedRunIds((prev) => {
      if (checked) {
        if (prev.includes(runId) || prev.length >= MAX_COMPARE_RUNS)
          return prev;
        return [...prev, runId];
      }
      return prev.filter((id) => id !== runId);
    });
  };

  const handleCompareSubmit = async (e) => {
    e.preventDefault();
    if (!compareFile || !selectedRunIds.length) return;
    setCompareBusy(true);
    setCompareError("");
    setCompareResult(null);
    try {
      const data = new FormData();
      data.append("file", compareFile);
      for (const id of selectedRunIds) {
        data.append("run_ids", id);
      }
      if (expectedLabel.trim()) {
        data.append("expected_label", expectedLabel.trim());
      }
      const res = await request("/inference/compare-runs", "POST", data);
      setCompareResult(res);
    } catch (err) {
      setCompareError(err.message);
    } finally {
      setCompareBusy(false);
    }
  };

  return {
    candidates,
    candidatesLoading,
    candidatesError,
    expFilter,
    setExpFilter,
    selectedRunIds,
    setSelectedRunIds,
    compareFile,
    setCompareFile,
    comparePreviewUrl,
    expectedLabel,
    setExpectedLabel,
    compareBusy,
    compareError,
    setCompareError,
    compareResult,
    setCompareResult,
    investigationOptions,
    visibleCandidates,
    selectedCandidates,
    selectedDatasetKeys,
    isDigitDataset,
    availableClasses,
    useLabelSelect,
    toggleRun,
    handleCompareSubmit,
  };
}
