import React from "react";
import { request } from "../services/api";
import { fmt, Panel, Json } from "../components/Common";
export default function Inference({ workspace }) {
  const {
    models,
    activeModel,
    online,
    busy,
    file,
    setFile,
    prediction,
    setPrediction,
    run,
    act,
  } = workspace;
  return (
    <Panel title="Predict with the active registered version">
      <p>
        Active version:{" "}
        <strong>
          {models.find((m) => m.id === activeModel)?.name || "None"}{" "}
          {models.find((m) => m.id === activeModel)?.version || ""}
        </strong>
        . Activate a verified version in Registry first.
      </p>
      <form
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
        <label className="field">
          <span>
            PNG or JPEG · at most 5 MB / 16 megapixels · resized to 32×32
          </span>
          <input
            type="file"
            accept="image/png,image/jpeg"
            onChange={(e) => {
              setFile(e.target.files[0] || null);
              setPrediction(null);
            }}
            required
          />
        </label>
        <button
          className="primary"
          disabled={busy || !online || !activeModel || !file}
        >
          Predict image
        </button>
      </form>
      {prediction && (
        <article className="record">
          <h3>
            {prediction.predicted_class} ·{" "}
            {fmt(prediction.confidence_score * 100)}%
          </h3>
          <p>
            {fmt(prediction.latency_ms)} ms · version {prediction.version} ·
            originating run {prediction.run_id}
          </p>
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
