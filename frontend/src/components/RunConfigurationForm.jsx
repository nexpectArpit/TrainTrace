import RunSetupFields from "../features/training/RunSetupFields";
import React from "react";
import { request } from "../services/api";
import InfoTooltip from "./InfoTooltip";
import ExecutionTargetSelector from "../features/training/ExecutionTargetSelector";
import { activeStates, Panel, RequiredFieldLegend } from "./Common";

import { validateRunConfiguration } from "../features/training/runFormSchema";

export default function RunConfigurationForm({ workspace }) {
  const {
    expId,
    setRunId,
    runs,
    info,
    online,
    setNotice,
    busy,
    setup,
    setSetup,
    experiment,
    run,
    act,
    executionStatus,
  } = workspace;
  const runInProgress = activeStates.includes(executionStatus);
  const { trainingConfigValid, invalidFields, advancedInvalid } =
    validateRunConfiguration(setup);
  const configurationLocked = busy || runInProgress;
  const [cloudStatus, setCloudStatus] = React.useState(null);
  React.useEffect(() => {
    if (!online) return;
    request("/cloud/status")
      .then(setCloudStatus)
      .catch((error) =>
        setCloudStatus({
          configured: false,
          authenticated: false,
          connection_error: error.message,
        }),
      );
  }, [online]);

  const queueDisabledReason = !online
    ? "Connect to the backend before queuing a run."
    : !experiment
      ? "Choose an active investigation first."
      : experiment.archived
        ? "This investigation is archived. Unarchive it to add runs."
        : setup.execution_target === "kaggle" && !cloudStatus?.authenticated
          ? cloudStatus?.connection_error ||
            (cloudStatus
              ? "Connect your Kaggle API token (BYOK) below before launching cloud training."
              : "Checking Kaggle connection…")
          : !info?.worker_online && setup.execution_target !== "kaggle"
            ? "The training worker is offline. Restart the backend to bring it online."
            : "";
  return (
    <details
      className="run-config-disclosure"
      key={run ? "inspect" : "create"}
      defaultOpen={!run}
    >
      <summary>Configure a new approach</summary>
      <Panel
        title={
          <span>
            Configure an approach
            <InfoTooltip label="About training runs">
              Configure a reproducible run using a supported dataset. Training
              and validation data are used during iteration; the official test
              split stays sealed until a candidate is selected. Runs are queued
              and processed sequentially.
            </InfoTooltip>
          </span>
        }
      >
        <form
          className="training-form"
          onSubmit={(e) => {
            e.preventDefault();
            act(async () => {
              await request("/runs/launch", "POST", {
                ...setup,
                experiment_id: expId,
              });
              setRunId(setup.run_id);
              setNotice("Run queued. Live state appears below.");
            });
          }}
        >
          <fieldset
            className="training-config-fields"
            disabled={configurationLocked}
          >
            <RunSetupFields
              setup={setup}
              setSetup={setSetup}
              runs={runs}
              advancedInvalid={advancedInvalid}
            />
            <ExecutionTargetSelector
              setup={setup}
              setSetup={setSetup}
              info={info}
              cloudStatus={cloudStatus}
              setCloudStatus={setCloudStatus}
            />
            <button
              className="primary"
              disabled={
                configurationLocked ||
                !!queueDisabledReason ||
                !trainingConfigValid
              }
            >
              {busy
                ? "Working..."
                : setup.execution_target === "kaggle"
                  ? "Launch on Kaggle Cloud GPU"
                  : "Queue training run"}
            </button>
          </fieldset>
          {runInProgress && (
            <p className="queue-disabled-reason" role="status">
              Configuration is locked while run {run?.id || setup.run_id} is{" "}
              {String(executionStatus).toLowerCase()}. It will be editable again
              when this run finishes.
            </p>
          )}
          {queueDisabledReason ? (
            <p className="queue-disabled-reason" role="status">
              {queueDisabledReason}
            </p>
          ) : !trainingConfigValid ? (
            <p className="queue-disabled-reason" role="status">
              Fix {invalidFields.join(", ") || "the required configuration"}{" "}
              before queuing.
            </p>
          ) : null}
        </form>
      </Panel>
    </details>
  );
}
