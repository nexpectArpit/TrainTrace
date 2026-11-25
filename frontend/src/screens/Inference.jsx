import InferenceImageFields from "../features/inference/InferenceImageFields";
import CheckpointPicker from "../features/inference/CheckpointPicker";
import React, { useId } from "react";
import useCheckpointComparison, {
  MAX_COMPARE_RUNS,
} from "../features/inference/useCheckpointComparison";
import ServingInference from "../features/inference/ServingInference";
import CheckpointComparisonResults from "../features/inference/CheckpointComparisonResults";
import { Panel, RequiredFieldLegend } from "../components/Common";

const ARCH_LABELS = {
  custom_cnn: "Custom CNN",
  resnet18: "ResNet-18",
  mobilenet_v2: "MobileNetV2",
  efficientnet_b0: "EfficientNet-B0",
};

export default function Inference({
  workspace,
  mode = "both",
  preferredRunIds = [],
}) {
  const { online, busy } = workspace;

  const comparison = useCheckpointComparison({
    workspace,
    mode,
    preferredRunIds,
  });
  const {
    candidatesError,
    selectedRunIds,
    compareFile,
    compareBusy,
    compareError,
    compareResult,
    handleCompareSubmit,
  } = comparison;
  const compareHeadingId = useId();

  return (
    <>
      {mode !== "serving" && (
        <Panel
          title="Compare completed run checkpoints"
          headingId={compareHeadingId}
        >
          <p>
            Run one uploaded image across up to {MAX_COMPARE_RUNS} completed
            runs side by side using each run’s SHA-256 verified best checkpoint.
            One image reports prediction, confidence, and optional label match —
            not a dataset accuracy rate. Final-test selection rules and sealed
            test sets are unchanged.
          </p>

          {candidatesError && (
            <div className="error" role="alert">
              {candidatesError}
            </div>
          )}

          <form
            aria-labelledby={compareHeadingId}
            onSubmit={handleCompareSubmit}
          >
            <RequiredFieldLegend />

            <CheckpointPicker
              comparison={comparison}
              architectureLabels={ARCH_LABELS}
            />

            <InferenceImageFields comparison={comparison} />

            {compareError && (
              <div className="error" role="alert">
                {compareError}
              </div>
            )}

            <button
              type="submit"
              className="primary"
              disabled={
                compareBusy ||
                busy ||
                !online ||
                !compareFile ||
                selectedRunIds.length === 0
              }
            >
              {compareBusy
                ? "Running checkpoint comparison…"
                : selectedRunIds.length > 1
                  ? `Compare ${selectedRunIds.length} checkpoints`
                  : "Run checkpoint prediction"}
            </button>
          </form>

          {compareResult && (
            <CheckpointComparisonResults
              compareResult={compareResult}
              architectureLabels={ARCH_LABELS}
            />
          )}
        </Panel>
      )}

      {mode !== "candidates" && (
        <ServingInference workspace={workspace} compareBusy={compareBusy} />
      )}
    </>
  );
}
