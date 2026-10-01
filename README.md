# TrainTrace — Reproducible PyTorch Experiment Tracking Pipeline

> **Formal OJT Project:** Tracked Training Pipeline (TTP)  
> **System Purpose:** An evidence-based PyTorch experiment tracking, decision traceability, and model candidate lifecycle platform.

---

## 📑 Core Documentation Links

* 📄 **[Product Requirements Document (PRD)](docs/PRD/Tracked_Training_Pipeline_PRD.md)** — Defines business goals, product behavior, 11-step decision reasoning chain, functional requirements (`FR-DEC-01` to `FR-DEC-06`), and user stories.
* 📄 **[Product Requirements Document (Word Version)](docs/PRD/Tracked_Training_Pipeline_PRD.docx)**
* 📄 **[Product Requirements Document (PDF Version)](docs/PRD/Tracked_Training_Pipeline_PRD.pdf)**

---

## 🏛️ Project Architecture & Repository Structure

TrainTrace is engineered with a modular, layered architecture to decouple deep learning training loops from persistence, decision tracking, and web API serving.

```
traintrace/
│
├── README.md                 # Master repository documentation & stage roadmap
├── config.py                 # Single source of truth for filesystem paths & config
├── requirements.txt           # Minimal, pinned system dependencies
│
├── docs/                     # System documentation & specs
│   └── PRD/                  # Transferred Product Requirements Documents
│       ├── Tracked_Training_Pipeline_PRD.md
│       ├── Tracked_Training_Pipeline_PRD.docx
│       └── Tracked_Training_Pipeline_PRD.pdf
│
├── core/                     # PyTorch Deep Learning Engine
│   ├── __init__.py
│   ├── dataset.py            # CIFAR-10 data loading, transforms & DataLoader factory
│   ├── models.py             # Custom CNN, ResNet-18, MobileNetV2 & EfficientNet-B0 architectures
│   └── trainer.py            # Autograd batch training loop, loss evaluation & checkpointing
│
├── tracking/                 # Experiment Tracking & Decision Traceability
│   ├── __init__.py
│   ├── tracker.py            # Metric logger & artifact serializer
│   ├── evaluator.py          # Holdout evaluation & Reproducibility Protocols (A & B)
│   └── decision_engine.py    # Decision rationale & Pareto trade-off matrix logger
│
├── db/                       # Storage Infrastructure Layer
│   ├── __init__.py
│   ├── database.py           # SQLite connection manager & WAL schema migrations
│   └── repository.py         # CRUD repository operations for runs, metrics & decisions
│
├── registry/                 # Model Governance Layer
│   ├── __init__.py
│   └── model_registry.py     # Version catalog & lineage provenance graph generator
│
├── api/                      # Application Server Layer
│   ├── __init__.py
│   ├── main.py               # FastAPI application entrypoint
│   └── routers/              # REST API route handlers
│       ├── experiments.py
│       ├── runs.py
│       └── inference.py
│
└── storage/                  # Generated Local Storage Sinks (Git-ignored)
    ├── data/                 # Raw & cached CIFAR-10 datasets
    ├── db/                   # Embedded SQLite database files
    ├── artifacts/            # Checkpoints (.pt), confusion matrix PNGs, JSON reports
    └── registry/             # Promoted production model candidate packages
```

---

## 🧠 Engineering & Learning Philosophy

This project is built following Senior Engineer standards:
1. **One File at a Time:** Every single module is developed sequentially with explicit rationale.
2. **Line-by-Line Commenting:** Every line of code explains *why* it exists and what PyTorch/Python primitive it utilizes.
3. **Zero Over-Engineering:** Clean, readable, robust code without bloated or unnecessary frameworks.
4. **Empirical Verification:** Each stage is verified through automated test suites (`pytest`).

---

## 🚀 Development Roadmap & Stages

- [x] **Stage 1: Foundation & Blueprint Setup** (`requirements.txt`, `config.py`, `README.md`, PRD transfer)
- [x] **Stage 2: PyTorch Model Architectures & Data Ingestion Pipeline** (`core/models.py`, `core/dataset.py`, `core/trainer.py`)
- [x] **Stage 3: Storage Infrastructure & Schema Persistence** (`db/database.py`, `db/repository.py`)
- [ ] **Stage 4: Experiment Tracking & Dual Reproducibility Engine** (`tracking/tracker.py`, `tracking/evaluator.py`)
- [ ] **Stage 6: Model Candidate Governance & Lineage Registry** (`registry/model_registry.py`)
- [ ] **Stage 7: FastAPI REST Backend Engine** (`api/main.py`, `api/routers/`)
- [ ] **Stage 8: Interactive React Frontend Interface**
