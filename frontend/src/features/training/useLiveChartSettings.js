import { useEffect, useState } from "react";
import { liveChartDefinitions } from "./chartDefinitions";

const savedChartSettings = () => {
  try {
    return JSON.parse(
      localStorage.getItem("traintrace-live-chart-settings") || "{}",
    );
  } catch {
    return {};
  }
};

/** Own chart preferences, pause state, ordering, and CSV export. */
export default function useLiveChartSettings({ run, liveSamples, metrics }) {
  const [chartSearch, setChartSearch] = useState("");
  const [chartAxis, setChartAxis] = useState(
    () => savedChartSettings().axis || "step",
  );
  const [expandedChart, setExpandedChart] = useState(null);
  const [smoothing, setSmoothing] = useState(
    () => savedChartSettings().smoothing || 1,
  );
  const [logScale, setLogScale] = useState(() =>
    Boolean(savedChartSettings().logScale),
  );
  const chartType = "line";
  const [chartPaused, setChartPaused] = useState(false);
  const [pausedSamples, setPausedSamples] = useState([]);
  const [chartOrder, setChartOrder] = useState(() => {
    const savedOrder = savedChartSettings().order;
    const initialOrder = savedOrder || [
      "batch_loss",
      "running_acc",
      "samples_per_sec",
      "device_memory_mb",
      "gpu_utilization_pct",
      "gpu_memory_utilization_pct",
      "gpu_temperature_c",
      "gpu_power_watts",
      "train_loss",
      "val_acc",
    ];
    const acceleratorMetrics = [
      "gpu_utilization_pct",
      "gpu_memory_utilization_pct",
      "gpu_temperature_c",
      "gpu_power_watts",
    ];
    return [...new Set([...initialOrder, ...acceleratorMetrics])];
  });
  const [hiddenCharts, setHiddenCharts] = useState(
    () => savedChartSettings().hidden || [],
  );
  const [newChartField, setNewChartField] = useState("");
  useEffect(() => {
    localStorage.setItem(
      "traintrace-live-chart-settings",
      JSON.stringify({
        axis: chartAxis,
        smoothing,
        logScale,
        chartType,
        order: chartOrder,
        hidden: hiddenCharts,
      }),
    );
  }, [chartAxis, smoothing, logScale, chartType, chartOrder, hiddenCharts]);
  const chartSamples = chartPaused ? pausedSamples : liveSamples;
  const hasRecordedMetric = (chart) =>
    (chart.source === "epoch" ? metrics : chartSamples).some(
      (sample) =>
        sample[chart.field] !== null &&
        sample[chart.field] !== undefined &&
        Number.isFinite(Number(sample[chart.field])),
    );
  const downloadChartData = () => {
    const source = chartSamples.length ? chartSamples : metrics;
    const columns = chartSamples.length
      ? [
          "epoch",
          "batch_idx",
          "total_batches",
          "batch_loss",
          "running_acc",
          "samples_per_sec",
          "device_memory_mb",
          "worker_cpu_percent",
          "peak_rss_mb",
          "gpu_utilization_pct",
          "gpu_memory_used_mb",
          "gpu_memory_total_mb",
          "gpu_memory_utilization_pct",
          "gpu_temperature_c",
          "gpu_power_watts",
          "observed_at",
        ]
      : [
          "epoch",
          "train_loss",
          "train_acc",
          "val_loss",
          "val_acc",
          "learning_rate",
          "epoch_time_sec",
        ];
    const csv = [
      columns.join(","),
      ...source.map((sample) =>
        columns.map((column) => sample[column] ?? "").join(","),
      ),
    ].join("\n");
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = `${run?.id || "run"}-live-metrics.csv`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  const moveChart = (field, offset) =>
    setChartOrder((current) => {
      const next = [...current];
      const index = next.indexOf(field);
      const target = index + offset;
      if (target < 0 || target >= next.length) return current;
      [next[index], next[target]] = [next[target], next[index]];
      return next;
    });
  const placeChart = (source, target) =>
    setChartOrder((current) => {
      if (
        !current.includes(source) ||
        !current.includes(target) ||
        source === target
      )
        return current;
      const next = current.filter((field) => field !== source);
      next.splice(next.indexOf(target), 0, source);
      return next;
    });
  return {
    chartSearch,
    setChartSearch,
    chartAxis,
    setChartAxis,
    expandedChart,
    setExpandedChart,
    smoothing,
    setSmoothing,
    logScale,
    setLogScale,
    chartType,
    chartPaused,
    setChartPaused,
    pausedSamples,
    setPausedSamples,
    chartOrder,
    setChartOrder,
    hiddenCharts,
    setHiddenCharts,
    newChartField,
    setNewChartField,
    chartSamples,
    hasRecordedMetric,
    downloadChartData,
    moveChart,
    placeChart,
  };
}
