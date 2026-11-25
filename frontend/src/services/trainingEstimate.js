// epoch_time_sec is measured by the worker across training and validation.
// Estimates are anchored at the last completed epoch, never a synthetic countdown.
export function estimateTraining(metrics, totalEpochs) {
  const epochs = new Map();
  for (const metric of metrics || []) {
    const epoch = Number(metric.epoch);
    if (Number.isInteger(epoch) && epoch > 0) epochs.set(epoch, metric);
  }
  const completed = epochs.size;
  const durations = [...epochs.values()].map((metric) =>
    Number(metric.epoch_time_sec),
  );
  if (
    !completed ||
    durations.some((seconds) => !Number.isFinite(seconds) || seconds <= 0)
  )
    return null;
  const total = Number(totalEpochs);
  if (!Number.isInteger(total) || total < completed) return null;
  // Missing epochs would make the remaining work ambiguous.
  if ([...epochs.keys()].some((epoch) => epoch > completed)) return null;
  const measuredSeconds = durations.reduce((sum, seconds) => sum + seconds, 0);
  const meanSeconds = measuredSeconds / completed;
  const remainingEpochs = total - completed;
  return {
    completed,
    measuredSeconds,
    meanSeconds,
    remainingEpochs,
    remainingSeconds: meanSeconds * remainingEpochs,
  };
}

export function formatDuration(seconds) {
  const minutes = Math.ceil(seconds / 60);
  if (seconds < 60) return `${Math.ceil(seconds)} s`;
  if (minutes < 60) return `${minutes} min`;
  return `${Math.floor(minutes / 60)} h ${minutes % 60} min`;
}
