import React, { useState, useEffect } from 'react';
import './App.css';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [expId, setExpId] = useState('exp_cifar10');
  const [runs, setRuns] = useState([]);
  const [comparison, setComparison] = useState(null);
  const [lineage, setLineage] = useState(null);
  const [loading, setLoading] = useState(false);

  // Run Launch Form State
  const [launchForm, setLaunchForm] = useState({
    run_id: 'run_resnet_02',
    approach_name: 'ResNet-18 Refined LR',
    model_name: 'resnet18',
    epochs: 2,
    batch_size: 128,
    learning_rate: 0.0001,
    seed: 42
  });

  // Decision Form State
  const [decisionForm, setDecisionForm] = useState({
    run_id: 'run_resnet_01',
    status: 'ACCEPTED',
    rationale: 'ResNet-18 residual architecture achieved 66.14% validation accuracy, outperforming Custom CNN.'
  });

  const fetchComparison = async () => {
    try {
      const res = await fetch(`/api/v1/runs/compare/${expId}`);
      if (res.ok) {
        const data = await res.json();
        setComparison(data);
        setRuns(data.comparison_matrix || []);
      }
    } catch (e) {
      console.error('Failed to fetch comparison matrix:', e);
    }
  };

  const fetchLineage = async () => {
    try {
      const res = await fetch('/api/v1/registry/model_CIFAR10_Classifier_v1_0/lineage');
      if (res.ok) {
        const data = await res.json();
        setLineage(data);
      }
    } catch (e) {
      console.error('Failed to fetch lineage:', e);
    }
  };

  // Initial load
  useEffect(() => {
    fetchComparison();
    fetchLineage();
  }, [expId]);

  // Re-fetch on tab change
  useEffect(() => {
    fetchComparison();
  }, [activeTab]);

  // Auto-poll every 3 seconds if any run is currently running
  useEffect(() => {
    const hasRunning = runs.some(r => r.status === 'RUNNING');
    if (!hasRunning) return;

    const interval = setInterval(() => {
      fetchComparison();
    }, 3000);

    return () => clearInterval(interval);
  }, [runs]);

  const handleLaunchRun = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await fetch('/api/v1/runs/launch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...launchForm,
          experiment_id: expId
        })
      });
      if (res.ok) {
        alert(`Run '${launchForm.run_id}' launched successfully in background!`);
        fetchComparison();
      }
    } catch (e) {
      alert('Failed to launch run');
    }
    setLoading(false);
  };

  const handleRecordDecision = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch('/api/v1/experiments/decisions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(decisionForm)
      });
      if (res.ok) {
        alert(`Decision status '${decisionForm.status}' recorded successfully!`);
        fetchComparison();
      }
    } catch (e) {
      alert('Failed to record decision');
    }
  };

  return (
    <div className="app-container">
      <header>
        <div>
          <div className="brand-title">TrainTrace Platform</div>
          <div className="subtitle">Reproducible PyTorch Experiment Tracking & Decision Traceability Workstation</div>
        </div>
        <div style={{ textAlign: 'right', display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <button className="tab-btn" onClick={fetchComparison} style={{ background: 'rgba(255,255,255,0.06)' }}>
            ↻ Refresh Data
          </button>
          <span className="badge badge-accepted">Backend Online (MPS GPU)</span>
        </div>
      </header>

      <nav className="nav-tabs">
        <button
          className={`tab-btn ${activeTab === 'dashboard' ? 'active' : ''}`}
          onClick={() => setActiveTab('dashboard')}
        >
          Overview Dashboard
        </button>
        <button
          className={`tab-btn ${activeTab === 'workstation' ? 'active' : ''}`}
          onClick={() => setActiveTab('workstation')}
        >
          Experiment Workstation
        </button>
        <button
          className={`tab-btn ${activeTab === 'comparison' ? 'active' : ''}`}
          onClick={() => setActiveTab('comparison')}
        >
          Run Trade-Off Matrix
        </button>
        <button
          className={`tab-btn ${activeTab === 'registry' ? 'active' : ''}`}
          onClick={() => setActiveTab('registry')}
        >
          Model Lineage Registry
        </button>
      </nav>

      {/* DASHBOARD OVERVIEW */}
      {activeTab === 'dashboard' && (
        <div>
          <div className="grid-3 mb-4">
            <div className="stat-box">
              <div className="stat-label">Active Experiment</div>
              <div className="stat-val" style={{ fontSize: '1.2rem', color: '#60a5fa' }}>
                {comparison?.experiment_name || 'CIFAR-10 Optimization'}
              </div>
              <div style={{ fontSize: '0.8rem', color: '#9ca3af', marginTop: '0.3rem' }}>
                Objective: {comparison?.objective || 'Find optimal architecture'}
              </div>
            </div>
            <div className="stat-box">
              <div className="stat-label">Total Executed Runs</div>
              <div className="stat-val">{comparison?.total_runs || 0}</div>
              <div style={{ fontSize: '0.8rem', color: '#10b981', marginTop: '0.3rem' }}>
                Logged to SQLite Database
              </div>
            </div>
            <div className="stat-box">
              <div className="stat-label">Compute Accelerator</div>
              <div className="stat-val" style={{ color: '#a78bfa' }}>Apple MPS</div>
              <div style={{ fontSize: '0.8rem', color: '#9ca3af', marginTop: '0.3rem' }}>
                Metal Performance Shaders Active
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-header">11-Step ML Experimentation Reasoning Chain</div>
            <div className="code-block" style={{ color: '#60a5fa' }}>
              Objective / Problem → Approach → Run(s) → Evidence / Results → Limitations → Decision → Decision Reason → Alternative Considered → Why Not Alternative → Next Investigation → Final Selected Approach
            </div>
          </div>
        </div>
      )}

      {/* EXPERIMENT WORKSTATION */}
      {activeTab === 'workstation' && (
        <div className="grid-2">
          <div className="card">
            <div className="card-header">Launch Customized Training Run</div>
            <form onSubmit={handleLaunchRun}>
              <div className="form-group">
                <label>Run Identifier</label>
                <input
                  className="form-input"
                  value={launchForm.run_id}
                  onChange={(e) => setLaunchForm({ ...launchForm, run_id: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>Approach Design Name</label>
                <input
                  className="form-input"
                  value={launchForm.approach_name}
                  onChange={(e) => setLaunchForm({ ...launchForm, approach_name: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>Model Architecture</label>
                <select
                  className="form-input"
                  value={launchForm.model_name}
                  onChange={(e) => setLaunchForm({ ...launchForm, model_name: e.target.value })}
                >
                  <option value="custom_cnn">Custom 3-Layer CNN (Baseline)</option>
                  <option value="resnet18">ResNet-18 (Residual Skip Connections)</option>
                  <option value="mobilenet_v2">MobileNetV2 (Depthwise Separable)</option>
                  <option value="efficientnet_b0">EfficientNet-B0 (Compound Scaling)</option>
                </select>
              </div>
              <div className="grid-2">
                <div className="form-group">
                  <label>Learning Rate</label>
                  <input
                    type="number"
                    step="0.0001"
                    className="form-input"
                    value={launchForm.learning_rate}
                    onChange={(e) => setLaunchForm({ ...launchForm, learning_rate: parseFloat(e.target.value) })}
                  />
                </div>
                <div className="form-group">
                  <label>Batch Size</label>
                  <input
                    type="number"
                    className="form-input"
                    value={launchForm.batch_size}
                    onChange={(e) => setLaunchForm({ ...launchForm, batch_size: parseInt(e.target.value) })}
                  />
                </div>
              </div>
              <div className="grid-2">
                <div className="form-group">
                  <label>Epoch Count</label>
                  <input
                    type="number"
                    className="form-input"
                    value={launchForm.epochs}
                    onChange={(e) => setLaunchForm({ ...launchForm, epochs: parseInt(e.target.value) })}
                  />
                </div>
                <div className="form-group">
                  <label>Random Seed</label>
                  <input
                    type="number"
                    className="form-input"
                    value={launchForm.seed}
                    onChange={(e) => setLaunchForm({ ...launchForm, seed: parseInt(e.target.value) })}
                  />
                </div>
              </div>
              <button type="submit" className="btn-primary" disabled={loading}>
                {loading ? 'Launching Run...' : 'Launch Training Run'}
              </button>
            </form>
          </div>

          <div className="card">
            <div className="card-header">Record Decision Rationale & Candidate Status</div>
            <form onSubmit={handleRecordDecision}>
              <div className="form-group">
                <label>Select Target Run</label>
                <select
                  className="form-input"
                  value={decisionForm.run_id}
                  onChange={(e) => setDecisionForm({ ...decisionForm, run_id: e.target.value })}
                >
                  {runs.map((r) => (
                    <option key={r.run_id} value={r.run_id}>
                      {r.run_id} ({r.model_architecture})
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Decision Status</label>
                <select
                  className="form-input"
                  value={decisionForm.status}
                  onChange={(e) => setDecisionForm({ ...decisionForm, status: e.target.value })}
                >
                  <option value="ACCEPTED">ACCEPTED (Candidate qualified)</option>
                  <option value="SELECTED">SELECTED (Chosen for Production)</option>
                  <option value="REJECTED">REJECTED (Failed target metrics)</option>
                  <option value="SUPERSEDED">SUPERSEDED (Replaced by superior model)</option>
                </select>
              </div>
              <div className="form-group">
                <label>Documented Rationale & Evidence Reason</label>
                <textarea
                  className="form-input"
                  rows={4}
                  value={decisionForm.rationale}
                  onChange={(e) => setDecisionForm({ ...decisionForm, rationale: e.target.value })}
                />
              </div>
              <button type="submit" className="btn-primary">
                Record Decision Rationale
              </button>
            </form>
          </div>
        </div>
      )}

      {/* RUN COMPARISON */}
      {activeTab === 'comparison' && (
        <div className="card">
          <div className="card-header">
            <span>Pareto Run Trade-Off Matrix</span>
            <button className="tab-btn" onClick={fetchComparison} style={{ fontSize: '0.8rem', background: 'rgba(255,255,255,0.06)' }}>
              ↻ Refresh
            </button>
          </div>
          <table>
            <thead>
              <tr>
                <th>Run ID</th>
                <th>Approach Name</th>
                <th>Architecture</th>
                <th>Hyperparameters</th>
                <th>Status</th>
                <th>Best Val Acc</th>
                <th>Final Loss</th>
                <th>Latest Decision</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((r) => (
                <tr key={r.run_id}>
                  <td style={{ fontFamily: 'var(--font-mono)' }}>{r.run_id}</td>
                  <td>{r.approach_name}</td>
                  <td style={{ color: '#60a5fa' }}>{r.model_architecture}</td>
                  <td style={{ fontSize: '0.8rem', color: '#9ca3af' }}>
                    LR={r.hyperparameters.learning_rate}, Batch={r.hyperparameters.batch_size}, Seed={r.hyperparameters.seed}
                  </td>
                  <td>
                    <span className={`badge ${r.status === 'COMPLETED' ? 'badge-accepted' : 'badge-superseded'}`}>
                      {r.status}
                    </span>
                  </td>
                  <td style={{ fontWeight: '600', color: '#10b981' }}>
                    {r.best_val_accuracy ? `${r.best_val_accuracy.toFixed(2)}%` : 'N/A'}
                  </td>
                  <td style={{ color: '#9ca3af' }}>
                    {r.final_val_loss ? r.final_val_loss.toFixed(4) : 'N/A'}
                  </td>
                  <td>
                    {r.latest_decision ? (
                      <span className={`badge badge-${r.latest_decision.status.toLowerCase()}`}>
                        {r.latest_decision.status}
                      </span>
                    ) : (
                      <span style={{ color: '#6b7280' }}>Pending</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* MODEL REGISTRY */}
      {activeTab === 'registry' && (
        <div className="card">
          <div className="card-header">Model Registry Catalog & 11-Step Lineage Graph</div>
          {lineage ? (
            <div>
              <div className="grid-2 mb-4">
                <div className="stat-box">
                  <div className="stat-label">Registered Model Version</div>
                  <div className="stat-val" style={{ fontSize: '1.2rem', color: '#10b981' }}>
                    {lineage.model_version_info?.name} ({lineage.model_version_info?.version})
                  </div>
                  <div style={{ fontSize: '0.8rem', color: '#9ca3af', marginTop: '0.3rem' }}>
                    Status: {lineage.model_version_info?.status}
                  </div>
                </div>
                <div className="stat-box">
                  <div className="stat-label">Originating Run ID</div>
                  <div className="stat-val" style={{ fontSize: '1.2rem', color: '#60a5fa' }}>
                    {lineage.originating_run?.run_id}
                  </div>
                  <div style={{ fontSize: '0.8rem', color: '#9ca3af', marginTop: '0.3rem' }}>
                    Architecture: {lineage.originating_run?.model_architecture}
                  </div>
                </div>
              </div>
              <div className="card-header" style={{ fontSize: '1rem' }}>Complete Lineage JSON Payload</div>
              <pre className="code-block">{JSON.stringify(lineage, null, 2)}</pre>
            </div>
          ) : (
            <div style={{ color: '#9ca3af' }}>Loading registry lineage provenance data...</div>
          )}
        </div>
      )}
    </div>
  );
}
