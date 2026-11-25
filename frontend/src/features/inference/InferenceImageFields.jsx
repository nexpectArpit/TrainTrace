import React, { useId } from "react";
import { fmt } from "../../components/Common";

export default function InferenceImageFields({ comparison }) {
  const {
    compareFile,
    setCompareFile,
    comparePreviewUrl,
    expectedLabel,
    setExpectedLabel,
    setCompareResult,
    setCompareError,
    isDigitDataset,
    availableClasses,
    useLabelSelect,
  } = comparison;
  const compareFileId = useId();
  const compareFileHelpId = useId();
  const expectedLabelId = useId();
  const expectedLabelHelpId = useId();
  const expectedDatalistId = useId();
  return (
    <div className="grid two">
      <div className="field">
        <label htmlFor={compareFileId}>
          Image file
          <span className="required-indicator" aria-hidden="true">
            *
          </span>
        </label>
        <input
          id={compareFileId}
          name="file"
          type="file"
          accept="image/png,image/jpeg"
          aria-describedby={compareFileHelpId}
          onChange={(e) => {
            setCompareFile(e.target.files[0] || null);
            setCompareResult(null);
            setCompareError("");
          }}
          required
        />
        <small id={compareFileHelpId}>
          PNG or JPEG · at most 5 MB / 16 megapixels · preprocessed using each
          run’s recorded dataset transform
        </small>
        {compareFile && comparePreviewUrl && (
          <div className="upload-preview">
            <img
              src={comparePreviewUrl}
              alt={`Uploaded preview: ${compareFile.name}`}
            />
            <div>
              <strong>{compareFile.name}</strong>
              <small>{fmt(compareFile.size / 1024, 1)} KB</small>
            </div>
          </div>
        )}
      </div>

      <div className="field">
        <label htmlFor={expectedLabelId}>
          {isDigitDataset
            ? "Correct digit (optional)"
            : "Correct class label (optional)"}
        </label>
        {useLabelSelect ? (
          <select
            id={expectedLabelId}
            name="expected_label"
            value={expectedLabel}
            aria-describedby={expectedLabelHelpId}
            onChange={(e) => {
              setExpectedLabel(e.target.value);
              setCompareResult(null);
              setCompareError("");
            }}
          >
            <option value="">
              Not provided (prediction &amp; confidence only)
            </option>
            {availableClasses.map((label) => (
              <option key={label} value={label}>
                {label}
              </option>
            ))}
          </select>
        ) : (
          <>
            <input
              id={expectedLabelId}
              name="expected_label"
              type="text"
              list={expectedDatalistId}
              value={expectedLabel}
              placeholder={
                availableClasses.length
                  ? `e.g. ${availableClasses.slice(0, 3).join(", ")}`
                  : "Enter expected class label"
              }
              autoComplete="off"
              autoCorrect="off"
              autoCapitalize="none"
              spellCheck={false}
              aria-describedby={expectedLabelHelpId}
              onChange={(e) => {
                setExpectedLabel(e.target.value);
                setCompareResult(null);
                setCompareError("");
              }}
            />
            <datalist id={expectedDatalistId}>
              {availableClasses.map((label) => (
                <option key={label} value={label} />
              ))}
            </datalist>
          </>
        )}
        <small id={expectedLabelHelpId}>
          Provide the true label to check whether each checkpoint got this image
          right.
        </small>
      </div>
    </div>
  );
}
