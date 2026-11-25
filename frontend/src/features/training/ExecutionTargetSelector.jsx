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
      <label className="execution-target-heading">
        Execution Target
        <InfoTooltip label="Execution target">
          Train locally on your machine or dispatch to a free cloud NVIDIA Tesla
          T4 GPU on Kaggle (30 hrs/week free quota).
        </InfoTooltip>
      </label>
      <div className="execution-target-options">
        <label
          className={`execution-target-card ${
            setup.execution_target !== "kaggle" ? "is-selected" : ""
          }`}
        >
          <input
            type="radio"
            name="execution_target"
            value="local"
            checked={setup.execution_target !== "kaggle"}
            onChange={() => setSetup({ ...setup, execution_target: "local" })}
          />
          <div className="execution-target-card-content">
            <span className="execution-target-name">Local Compute</span>
            <small className="execution-target-subtext">
              {info?.hardware?.name || "Local CPU / Accelerator"}
            </small>
          </div>
        </label>
        <label
          className={`execution-target-card ${
            setup.execution_target === "kaggle" ? "is-selected" : ""
          }`}
        >
          <input
            type="radio"
            name="execution_target"
            value="kaggle"
            checked={setup.execution_target === "kaggle"}
            onChange={() => setSetup({ ...setup, execution_target: "kaggle" })}
          />
          <div className="execution-target-card-content">
            <span className="execution-target-name">Kaggle Cloud GPU</span>
            <small className="execution-target-subtext">
              {cloudStatus?.authenticated ? (
                <span className="cloud-status-connected">
                  Connected (@{cloudStatus.username})
                </span>
              ) : (
                <span className="cloud-status-warning">
                  {cloudStatus?.configured
                    ? "Kaggle authentication needs attention"
                    : "Key not connected"}
                </span>
              )}
            </small>
          </div>
        </label>
      </div>
      {setup.execution_target === "kaggle" && (
        <div className="cloud-byok-container">
          {cloudStatus?.authenticated && !showByokInput ? (
            <div className="cloud-connected-banner">
              <div className="cloud-connected-info">
                <div>
                  <strong>Connected to Kaggle Cloud GPU</strong>
                  <p>
                    Authenticated as <code>@{cloudStatus.username}</code> -
                    NVIDIA Tesla T4 accelerator when available on your Kaggle
                    account.
                  </p>
                </div>
              </div>
              <button
                type="button"
                className="byok-action-btn"
                onClick={() => setShowByokInput(true)}
                title="Switch or update Kaggle API key"
              >
                Change Key
              </button>
            </div>
          ) : (
            <div
              className="byok-form-card"
              role="region"
              aria-label="Kaggle API Key Configuration"
            >
              <div className="byok-header">
                <strong>Bring Your Own Key (BYOK) - Free Cloud GPU</strong>
                <p>
                  Paste your Kaggle API token below to execute models on a free
                  cloud NVIDIA Tesla T4 GPU.
                </p>
              </div>
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
                  Need a key? In Kaggle, go to Settings &gt; API &gt; Generate
                  New Token and paste it here.
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
