export function filterRuns(runs, filters) {
  const {
    query,
    datasetFilter,
    archFilter,
    optimizerFilter,
    depthFilter,
    statusFilter,
    seedFilter,
    validationMin,
    validationMax,
  } = filters;
  const search = query.toLowerCase();

  return runs.filter((run) => {
    const dataset =
      run.config?.dataset_name ||
      run.dataset?.dataset_name ||
      run.dataset?.name ||
      "";
    const searchable = [
      run.id,
      run.approach_name,
      run.model_architecture,
      run.dataset?.name,
      run.config?.dataset_name,
      JSON.stringify(run.config || {}),
    ]
      .join(" ")
      .toLowerCase();

    return (
      (!search || searchable.includes(search)) &&
      (!datasetFilter || dataset === datasetFilter) &&
      (!archFilter || run.model_architecture === archFilter) &&
      (!optimizerFilter || run.config?.optimizer === optimizerFilter) &&
      (!depthFilter ||
        (run.model_architecture === "custom_cnn" &&
          String(run.config?.architecture_config?.depth || "") ===
            depthFilter)) &&
      (!statusFilter ||
        run.status === statusFilter ||
        run.latest_decision?.status === statusFilter) &&
      (!seedFilter || String(run.seed) === seedFilter) &&
      (validationMin === "" ||
        (run.best_val_accuracy != null &&
          run.best_val_accuracy >= Number(validationMin))) &&
      (validationMax === "" ||
        (run.best_val_accuracy != null &&
          run.best_val_accuracy <= Number(validationMax)))
    );
  });
}
