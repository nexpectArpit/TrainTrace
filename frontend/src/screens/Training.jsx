import RunExecutionPanel from "../features/training/RunExecutionPanel";
import React, { useEffect } from "react";
import RunList from "../components/RunList";
import RunConfigurationForm from "../components/RunConfigurationForm";
import {
  activeStates,
  DEFAULT_ARCHITECTURE_CONFIG,
  freshRun,
} from "../components/Common";

export default function Training({ workspace }) {
  const { setRunId, runs, setNotice, setup, setSetup, run, executionStatus } =
    workspace;
  const runInProgress = activeStates.includes(executionStatus);
  useEffect(() => {
    const config = run?.config;
    if (!runInProgress || !config || setup.run_id === run.id) return;
    setSetup({
      run_id: run.id,
      approach_name: run.approach_name || config.approach_name || "",
      dataset_name: config.dataset_name || "cifar10",
      model_name: config.model_name || run.model_architecture || "custom_cnn",
      architecture_config: {
        ...DEFAULT_ARCHITECTURE_CONFIG,
        ...(config.architecture_config || {}),
      },
      epochs: config.epochs ?? 2,
      batch_size: config.batch_size ?? 128,
      learning_rate: config.learning_rate ?? 0.001,
      seed: config.seed ?? 42,
      split_seed: config.split_seed ?? 42,
      pretrained: config.pretrained ?? false,
      scheduler_type: config.scheduler_type || "constant",
      optimizer: config.optimizer || "adamw",
      weight_decay: config.weight_decay ?? 0.0001,
      predecessor_run_id: config.predecessor_run_id || null,
      initialize_from_run_id: config.initialize_from_run_id || null,
      tags: run.tags || config.tags || {},
      motivating_reason: config.motivating_reason || "",
    });
  }, [run, runInProgress, setSetup, setup.run_id]);
  useEffect(() => {
    if (
      run &&
      run.id === setup.run_id &&
      ["COMPLETED", "FAILED", "STOPPED"].includes(executionStatus)
    ) {
      setSetup((current) => ({ ...current, run_id: freshRun().run_id }));
      setNotice(
        "Run finished. Its settings are preserved with a fresh ID for your next run.",
      );
    }
  }, [executionStatus, run, setNotice, setSetup, setup.run_id]);
  return (
    <div className="training-page">
      <RunList
        runs={runs}
        selectedId={run?.id}
        onOpen={(item) => setRunId(item.id)}
        onCompare={(item) => {
          workspace.setCompare([item.id]);
          workspace.setTab("Compare");
        }}
      />
      <RunConfigurationForm workspace={workspace} />
      <RunExecutionPanel workspace={workspace} />
    </div>
  );
}
