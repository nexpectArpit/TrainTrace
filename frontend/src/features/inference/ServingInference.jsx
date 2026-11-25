import React, { useId } from "react";
import { request } from "../../services/api";
import { fmt, Json, Panel, RequiredFieldLegend } from "../../components/Common";

export default function ServingInference({ workspace, compareBusy = false }) {
  const {
    models,
    activeModel,
    online,
    busy,
    file,
    setFile,
    prediction,
    setPrediction,
    act,
  } = workspace;
  const servingHeadingId = useId();
  const servingFileId = useId();
  const servingFileHelpId = useId();
  const activeModelObj = models.find((model) => model.id === activeModel);
  return (
    <Panel
      title="Predict with the active registered version"
      headingId={servingHeadingId}
    >
      <p>
        Active version:{" "}
        <strong>
          {activeModelObj?.name || "None"} {activeModelObj?.version || ""}
        </strong>
        {activeModelObj
          ? ". Upload an image to predict with this release."
          : ". Activate a verified version above before serving predictions."}
      </p>
      <form
        aria-labelledby={servingHeadingId}
        onSubmit={(e) => {
          e.preventDefault();
          act(async () => {
            const data = new FormData();
            data.append("file", file);
            setPrediction(null);
            setPrediction(
              await request(
                `/inference/predict?model_id=${activeModel}`,
                "POST",
                data,
              ),
            );
          });
        }}
      >
        <RequiredFieldLegend />
        <div className="field">
          <label htmlFor={servingFileId}>
            Image file
            <span className="required-indicator" aria-hidden="true">
              *
            </span>
          </label>
          <input
            id={servingFileId}
            name="file"
            type="file"
            accept="image/png,image/jpeg"
            aria-describedby={servingFileHelpId}
            onChange={(e) => {
              setFile(e.target.files[0] || null);
              setPrediction(null);
            }}
            required
          />
          <small id={servingFileHelpId}>
            PNG or JPEG · at most 5 MB / 16 megapixels · resized using the
            registered model’s frozen preprocessing manifest
          </small>
        </div>
        <button
          type="submit"
          className="primary"
          disabled={busy || compareBusy || !online || !activeModel || !file}
        >
          Predict image
        </button>
      </form>
      {prediction && (
        <article className="record" role="status" aria-live="polite">
          <h3>
            {prediction.predicted_class} · {prediction.dataset_name} ·{" "}
            {fmt(prediction.confidence_score * 100)}%
          </h3>
          <p>
            {fmt(prediction.latency_ms)} ms · version {prediction.version} ·
            originating run {prediction.run_id}
          </p>
          {prediction.preprocessed_input_preview && (
            <figure className="model-input-preview">
              <img
                src={prediction.preprocessed_input_preview}
                alt={`Exact model input, ${prediction.preprocessing_size?.join(" by ")} pixels`}
              />
              <figcaption>
                Model input · {prediction.preprocessing_size?.join(" × ")} px
              </figcaption>
            </figure>
          )}
          {Object.entries(prediction.all_probabilities)
            .sort((a, b) => b[1] - a[1])
            .map(([label, p]) => (
              <div className="probability" key={label}>
                <span>{label}</span>
                <progress
                  aria-label={`${label} confidence`}
                  value={p}
                  max="1"
                />
                <span>{fmt(p * 100)}%</span>
              </div>
            ))}
          <Json
            data={prediction}
            label="Prediction provenance and top-k classes"
          />
        </article>
      )}
    </Panel>
  );
}
