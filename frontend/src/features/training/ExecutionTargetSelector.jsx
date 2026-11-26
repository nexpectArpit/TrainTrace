import React from "react";
import { request } from "../../services/api";
import InfoTooltip from "../../components/InfoTooltip";

export default function ExecutionTargetSelector({
  setup,
  setSetup,
  info,
  cloudStatus,
  setCloudStatus,
}) {
  const [showByokInput, setShowByokInput] = React.useState(false);
  const [byokToken, setByokToken] = React.useState("");
  const [byokConnecting, setByokConnecting] = React.useState(false);
  const [byokError, setByokError] = React.useState("");
  const [cloudWarning, setCloudWarning] = React.useState("");
  return (
    <div className="execution-target-selector">
      <div className="execution-target-row">
        <label className="execution-target-heading">
          Execution Target
          <InfoTooltip label="Execution target">
            Train locally on your machine or dispatch to a free cloud NVIDIA
            Tesla T4 GPU on Kaggle (30 hrs/week free quota).
          </InfoTooltip>
        </label>
        <div
          className="execution-segmented"
          role="radiogroup"
          aria-label="Execution target"
        >
          <button
            type="button"
            role="radio"
            aria-checked={setup.execution_target !== "kaggle"}
            className={`execution-seg-btn${setup.execution_target !== "kaggle" ? " is-active" : ""}`}
            onClick={() => setSetup({ ...setup, execution_target: "local" })}
          >
            <span className="execution-seg-dot" aria-hidden="true" />
            <span>Local Compute</span>
            <small>{info?.hardware?.name || "CPU / MPS"}</small>
          </button>
          <button
            type="button"
            role="radio"
            aria-checked={setup.execution_target === "kaggle"}
            className={`execution-seg-btn${setup.execution_target === "kaggle" ? " is-active" : ""}`}
            onClick={() => setSetup({ ...setup, execution_target: "kaggle" })}
          >
            <span className="execution-seg-dot" aria-hidden="true" />
            <span>Kaggle Cloud GPU</span>
            <small>
              {cloudStatus?.authenticated
                ? `@${cloudStatus.username}`
                : cloudStatus?.configured
                  ? "Auth needed"
                  : "BYOK"}
            </small>
          </button>
        </div>
      </div>

      {setup.execution_target === "kaggle" && (
        <div className="cloud-status-inline">
          {cloudStatus?.authenticated && !showByokInput ? (
            <div className="cloud-inline-summary">
              <span className="cloud-inline-ok">
                Connected to Kaggle as <code>@{cloudStatus.username}</code> ·
                NVIDIA Tesla T4 ready
              </span>
              <button
                type="button"
                className="link"
                onClick={() => setShowByokInput(true)}
                title="Switch or update Kaggle API key"
              >
                Change key
              </button>
            </div>
          ) : (
            <div
              className="byok-inline-form"
              role="region"
              aria-label="Kaggle API Key Configuration"
            >
              <div className="byok-input-row">
                <input
                  type="password"
                  className="byok-token-input"
                  placeholder="Paste Kaggle API Token (e.g. KGAT_...)"
                  value={byokToken}
                  onChange={(e) => {
                    setByokToken(e.target.value);
                    setByokError("");
                  }}
                  disabled={byokConnecting}
                />
                <button
                  type="button"
                  className="primary byok-connect-btn"
                  disabled={byokConnecting || !byokToken.trim()}
                  onClick={async () => {
                    setByokConnecting(true);
                    setByokError("");
                    try {
                      const res = await request("/cloud/configure", "POST", {
                        token: byokToken.trim(),
                      });
                      setCloudStatus({
                        configured: true,
                        authenticated: true,
                        username: res.username,
                      });
                      setCloudWarning(res.warning || "");
                      setShowByokInput(false);
                      setByokToken("");
                    } catch (err) {
                      setByokError(
                        err.message || "Failed to authenticate with Kaggle.",
                      );
                    } finally {
                      setByokConnecting(false);
                    }
                  }}
                >
                  {byokConnecting ? "Connecting..." : "Connect GPU"}
                </button>
                {cloudStatus?.configured && (
                  <button
                    type="button"
                    className="byok-cancel-btn"
                    onClick={() => {
                      setShowByokInput(false);
                      setByokError("");
                    }}
                  >
                    Cancel
                  </button>
                )}
              </div>
              {byokError && (
                <div className="byok-error-banner">{byokError}</div>
              )}
              <div className="byok-footer-hint">
                <span>
                  In Kaggle: Settings &gt; API &gt; Generate New Token.
                </span>
              </div>
            </div>
          )}
          {cloudWarning && (
            <div className="byok-error-banner" role="status">
              {cloudWarning}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
