import React, { useId } from "react";
import { Badge, fmt, Json } from "../../components/Common";

export default function CheckpointComparisonResults({
  compareResult,
  architectureLabels,
}) {
  const compareTableCaptionId = useId();
  const ARCH_LABELS = architectureLabels;
  return (
    <div className="compare-inference-results" role="status" aria-live="polite">
      <p className="inference-compare-note">{compareResult.note}</p>

      <div className="metric-strip">
        <div>
          <span>Checkpoints compared</span>
          <strong>{compareResult.models_compared}</strong>
        </div>
        {compareResult.models_compared > 1 && (
          <div>
            <span>Prediction agreement</span>
            <strong>
              {compareResult.same_dataset
                ? compareResult.agreement
                  ? `All agree (${compareResult.results[0]?.predicted_class})`
                  : "Disagree"
                : "Different datasets"}
            </strong>
          </div>
        )}
        {compareResult.expected_label && (
          <div>
            <span>Single-image match (“{compareResult.expected_label}”)</span>
            <strong>
              {compareResult.correct_count} / {compareResult.evaluable_count}{" "}
              correct
            </strong>
          </div>
        )}
      </div>

      <div
        className="table-wrap table-scroll"
        tabIndex={0}
        role="region"
        aria-labelledby={compareTableCaptionId}
      >
        <table className="compare-inference-table">
          <caption id={compareTableCaptionId}>
            Side-by-side checkpoint predictions on the uploaded image
          </caption>
          <thead>
            <tr>
              <th scope="col">Run / Architecture</th>
              <th scope="col">Dataset</th>
              <th scope="col">Predicted</th>
              <th scope="col">Confidence</th>
              {compareResult.expected_label && (
                <>
                  <th scope="col">Match vs “{compareResult.expected_label}”</th>
                  <th scope="col">True-label conf</th>
                </>
              )}
              <th scope="col">Val acc %</th>
              <th scope="col">Latency ms</th>
            </tr>
          </thead>
          <tbody>
            {compareResult.results.map((item) => (
              <tr key={item.run_id}>
                <th scope="row">
                  <div>{item.approach_name}</div>
                  <small>
                    {ARCH_LABELS[item.model_name] || item.model_name} ·{" "}
                    {item.run_id}
                  </small>
                </th>
                <td>{item.dataset_name}</td>
                <td>
                  <strong>{item.predicted_class}</strong>
                </td>
                <td>{fmt(item.confidence_score * 100)}%</td>
                {compareResult.expected_label && (
                  <>
                    <td>
                      {item.is_correct === true ? (
                        <Badge value="✓ Correct" />
                      ) : item.is_correct === false ? (
                        <Badge value="✕ Incorrect" />
                      ) : (
                        <Badge value="N/A (dataset)" />
                      )}
                    </td>
                    <td>
                      {item.expected_class_confidence != null
                        ? `${fmt(item.expected_class_confidence * 100)}% (#${item.expected_class_rank})`
                        : "—"}
                    </td>
                  </>
                )}
                <td>{fmt(item.validation_accuracy)}%</td>
                <td>{fmt(item.latency_ms)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="grid two compare-inference-cards">
        {compareResult.results.map((item) => {
          const entries = Object.entries(item.all_probabilities).sort(
            (a, b) => b[1] - a[1],
          );
          const shown = entries.length <= 10 ? entries : entries.slice(0, 5);
          return (
            <article className="record" key={item.run_id}>
              <h3>
                <span>{item.approach_name}</span>
                <Badge
                  value={ARCH_LABELS[item.model_name] || item.model_name}
                />
                {item.is_correct === true && <Badge value="✓ Correct" />}
                {item.is_correct === false && <Badge value="✕ Incorrect" />}
              </h3>
              {item.preprocessed_input_preview && (
                <figure className="model-input-preview">
                  <img
                    src={item.preprocessed_input_preview}
                    alt={`Exact ${item.preprocessing_size?.join(" by ")} model input for ${item.approach_name}`}
                  />
                  <figcaption>
                    Model input · {item.preprocessing_size?.join(" × ")} px
                  </figcaption>
                </figure>
              )}
              <p>
                Predicted <strong>{item.predicted_class}</strong> (
                {fmt(item.confidence_score * 100)}%) · {item.dataset_name} ·{" "}
                {fmt(item.latency_ms)} ms
              </p>
              {item.expected_label && item.expected_label_valid && (
                <p>
                  Expected <strong>{item.expected_label}</strong>:{" "}
                  {item.is_correct ? "matched" : "missed"} · assigned{" "}
                  {fmt(item.expected_class_confidence * 100)}% (rank #
                  {item.expected_class_rank})
                </p>
              )}
              <small>
                Best checkpoint · epoch {item.checkpoint_epoch ?? "—"} · val{" "}
                {fmt(item.validation_accuracy)}% · sha256{" "}
                {item.checkpoint_sha256.slice(0, 12)}…
              </small>
              {shown.map(([label, prob]) => {
                const isPredicted = label === item.predicted_class;
                const isExpected =
                  item.expected_label_valid && label === item.expected_label;
                return (
                  <div className="probability" key={label}>
                    <span>
                      {label}
                      {isPredicted ? " (pred)" : ""}
                      {isExpected ? " (true)" : ""}
                    </span>
                    <progress
                      aria-label={`${item.approach_name} ${label} confidence`}
                      value={prob}
                      max="1"
                    />
                    <span>{fmt(prob * 100)}%</span>
                  </div>
                );
              })}
            </article>
          );
        })}
      </div>

      <Json
        data={compareResult}
        label="Comparison provenance and raw probabilities"
      />
    </div>
  );
}
