# TrainTrace — Reproducible PyTorch Experiment Tracking Pipeline

> **Formal OJT Project:** Tracked Training Pipeline (TTP)  
> **System Purpose:** An evidence-based PyTorch experiment tracking, hyperparameter evaluation, decision traceability, and model candidate lifecycle platform.

---

## ⚡ Quick Start — How to Run the Project

TrainTrace consists of two decoupled services: the **FastAPI Backend & ML Engine** (Port 8000) and the **React Vite Frontend Dashboard** (Port 3000). They should be run concurrently in two separate terminal windows.

---

### Prerequisites
* **Python**: 3.10+ (macOS Homebrew Python `python3.13` or standard `python3`)
* **Node.js**: v18+ and `npm`
* **Hardware**: Automatically detects Apple Silicon GPU (`mps`), NVIDIA CUDA (`cuda`), or fallback (`cpu`).

---

### Step 1: Start the Backend REST API Server (Terminal 1)

Open a new terminal window and navigate to the backend directory:

```bash
cd traintrace/backend
```

#### Option A: Using Python Virtual Environment (Recommended)
```bash
# 1. Create a virtual environment
python3 -m venv venv

# 2. Activate the virtual environment
source venv/bin/activate       # On macOS/Linux
# .\venv\Scripts\activate      # On Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Launch FastAPI ASGI server with auto-reload
uvicorn api.main:app --reload --port 8000
```

#### Option B: Direct Execution via Homebrew Python (macOS)
If you are using Homebrew's Python environment without virtualenv:
```bash
/opt/homebrew/bin/pip3.13 install -r requirements.txt
/opt/homebrew/bin/uvicorn api.main:app --reload --port 8000
```

#### 🔍 Backend Verification URLs
* 🌐 **Interactive Swagger API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
* 📖 **ReDoc Documentation:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
* 🩺 **Backend Health Check:** [http://localhost:8000/](http://localhost:8000/)

---

### Step 2: Start the Frontend React Web Dashboard (Terminal 2)

Open a second terminal window and navigate to the frontend directory:

```bash
cd traintrace/frontend

# 1. Install frontend dependencies (First time only)
npm install

# 2. Launch Vite development server
npm run dev
```

#### 🖥️ Interactive Web Dashboard
* Open your browser and navigate to: **[http://localhost:3000](http://localhost:3000)**

---

## 🧪 Quick Smoke Test & CLI Verification

You can verify the backend is running and execute a quick test run directly from your terminal:

### 1. Health Check
```bash
curl -X GET http://localhost:8000/
# Expected response: {"status":"healthy","system":"TrainTrace Engine v1.0",...}
```

### 2. Create an Experiment via CLI
```bash
curl -X POST http://localhost:8000/api/v1/experiments/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "CIFAR-10 Baseline Exploration",
    "description": "Evaluating initial CNN architectures under standard SGD and AdamW",
    "target_metric": "val_accuracy",
    "target_threshold": 0.70
  }'
```

### 3. Launch a Training Run via CLI (Async Background Execution)
```bash
curl -X POST http://localhost:8000/api/v1/runs/launch \
  -H "Content-Type: application/json" \
  -d '{
    "experiment_id": "EXP-001",
    "model_architecture": "custom_cnn",
    "hyperparameters": {
      "lr": 0.001,
      "batch_size": 64,
      "optimizer": "adamw",
      "weight_decay": 0.0001
    },
    "epochs": 3,
    "seed": 42
  }'
```

### 4. Fetch Comparative Matrix
```bash
curl -X GET http://localhost:8000/api/v1/runs/compare/EXP-001
```

---

## 📑 Core Documentation Links

* 📊 **[System Metrics, Dataset Specs & Runtime Numbers](SYSTEM_METRICS.md)** — Complete breakdown of CIFAR-10 data sizes, batch mathematics, model parameter counts, and VRAM memory footprints.
* 📄 **[Product Requirements Document (PRD)](docs/PRD/Tracked_Training_Pipeline_PRD.md)** — Defines business goals, product behavior, 11-step decision reasoning chain, functional requirements (`FR-DEC-01` to `FR-DEC-06`), and user stories.
* 📄 **[Product Requirements Document (Word Version)](docs/PRD/Tracked_Training_Pipeline_PRD.docx)**
* 📄 **[Product Requirements Document (PDF Version)](docs/PRD/Tracked_Training_Pipeline_PRD.pdf)**

---

## 🏛️ System Architecture & Directory Layout

TrainTrace follows strict **Separation of Concerns** across a modular architecture:

```
traintrace/                           # REPOSITORY ROOT
│
├── .gitignore                        # Standard git ignore file
├── .env.example                      # Environment variables template
├── README.md                         # Master repository README & roadmap
│
├── docs/                             # Project documentation
│   └── PRD/                          # Product Requirements Documents
│
├── backend/                          # PYTHON BACKEND & ML ENGINE
│   ├── config.py                     # Path configuration & hardware GPU auto-detection
│   ├── requirements.txt              # System dependencies
│   │
│   ├── core/                         # PyTorch ML Engine
│   │   ├── models.py                 # CustomCNN, ResNet-18, MobileNetV2, EfficientNet-B0
│   │   ├── dataset.py                # CIFAR-10 transforms & DataLoader factories
│   │   └── trainer.py                # Autograd batch training loop & checkpointer (.pt)
│   │
│   ├── tracking/                     # Experiment Tracking & Reproducibility
│   │   ├── tracker.py                # Metric logger & experiment orchestrator
│   │   └── evaluator.py              # Holdout evaluator & Protocol A/B auditor
│   │
│   ├── db/                           # Relational Storage Layer
│   │   ├── database.py               # SQLite WAL connection manager & 5 schema tables
│   │   └── repository.py             # CRUD helper functions
│   │
│   ├── registry/                     # Model Governance Layer
│   │   └── model_registry.py         # Version catalog & lineage graph generator
│   │
│   ├── api/                          # FastAPI Web Application Server
│   │   ├── main.py                   # FastAPI entrypoint & CORS middleware
│   │   └── routers/                  # REST API endpoints
│   │       ├── experiments.py        # Experiment workspace & decision logging
│   │       ├── runs.py               # Hyperparameter run launch & comparison matrix
│   │       ├── registry.py           # Model promotion & lineage provenance queries
│   │       └── inference.py          # Real-time PyTorch model prediction serving
│   │
│   └── storage/                      # Local Storage Sinks (Git-ignored)
│       ├── data/                     # Raw CIFAR-10 dataset downloads
│       ├── db/                       # Embedded SQLite database (traintrace.db)
│       ├── artifacts/                # PyTorch checkpoints (.pt) & JSON reports
│       └── registry/                 # Promoted production model packages
│
└── frontend/                         # FRONTEND SERVICE (React Single Page App)
    ├── package.json                  # Node dependencies & Vite build scripts
    ├── vite.config.js                # Port 3000 server & API proxy config
    └── src/
        ├── App.jsx                   # Master dashboard, workstation & matrix components
        ├── App.css                   # Glassmorphic dark-mode design system
        └── main.jsx                  # React DOM entrypoint
```

---

## 🌐 FastAPI REST API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | System health check and Swagger docs link |
| `POST` | `/api/v1/experiments/` | Create a new experiment parent workspace |
| `GET` | `/api/v1/experiments/{exp_id}` | Fetch experiment details and objective target |
| `POST` | `/api/v1/runs/launch` | Launch a customized training run (Hyperparameters, Seed, Arch) |
| `GET` | `/api/v1/runs/compare/{exp_id}` | Side-by-side run comparison matrix & metric curves |
| `GET` | `/api/v1/experiments/{exp_id}/runs/{run_id}/metrics` | Fetch per-epoch loss and accuracy progression |
| `POST` | `/api/v1/experiments/decisions` | Record 11-step decision rationale & candidate status |
| `POST` | `/api/v1/registry/promote` | Promote a model candidate to versioned release (v1.0) |
| `GET` | `/api/v1/registry/{model_id}/lineage` | Fetch complete 11-step lineage & provenance graph |
| `POST` | `/api/v1/inference/predict` | Real-time PyTorch forward-pass prediction (Sanity check) |

---

## 🎯 End-to-End User Workflow Guide

1. **Create Experiment Workspace**: In the UI, navigate to **Experiment Workstation**, enter a title (e.g. `CIFAR-10 Optimizer Benchmark`), target metric (`val_accuracy`), and target threshold (`0.75`).
2. **Launch Comparative Runs**: Configure run variations across model architectures (`CustomCNN`, `ResNet-18`, `MobileNetV2`), learning rates, batch sizes, optimizers (`SGD`, `AdamW`), and seeds. Runs execute asynchronously on the hardware accelerator.
3. **Analyze Pareto Trade-Offs**: Open the **Comparative Matrix** to inspect accuracy vs training duration, test loss, and per-epoch convergence curves.
4. **Audit Reproducibility**:
   * **Protocol A**: Click Deterministic Audit to verify exact bitwise repeatability under identical seeds.
   * **Protocol B**: Execute Sensitivity Analysis to quantify standard deviation across varying random seeds.
5. **Log Engineering Decisions**: Document the justification for selecting the candidate model (e.g. why ResNet-18 was preferred over CustomCNN despite higher training time).
6. **Promote to Registry**: Promote the winning candidate with semantic versioning (`v1.0.0`) and explore the complete interactive **Lineage Provenance Graph**.
7. **Sanity Check Inference**: Upload any sample image to test the forward-pass output probabilities against the CIFAR-10 classes.

---

## 🚀 Development Roadmap & Stage Status

- [x] **Stage 1: Foundation & Blueprint Setup** (`requirements.txt`, `config.py`, `README.md`, PRD transfer)
- [x] **Stage 2: PyTorch Model Architectures & Data Ingestion Pipeline** (`core/models.py`, `core/dataset.py`, `core/trainer.py`)
- [x] **Stage 3: Storage Infrastructure & Schema Persistence** (`db/database.py`, `db/repository.py`)
- [x] **Stage 4: Experiment Tracking & Dual Reproducibility Engine** (`tracking/tracker.py`, `tracking/evaluator.py`)
- [x] **Stage 5: FastAPI REST Backend Engine** (`api/main.py`, `api/routers/`)
- [x] **Stage 6: Model Candidate Governance & Lineage Registry** (`registry/model_registry.py`, `api/routers/registry.py`)
- [x] **Stage 7: Interactive React Frontend Interface** (`frontend/`)
