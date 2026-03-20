# UBA & Insider Threat Detection System - Complete Documentation

> **User Behavior Analytics (UBA) & Insider Threat Detection (ITD)**  
> A comprehensive system for detecting anomalous user behavior and potential insider threats using Machine Learning.

---

## 1. System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         UBA & ITD SYSTEM                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   📦 DATA LAYER              ⚙️ PROCESSING              🧠 ML MODELS   │
│   ─────────────              ─────────────              ─────────────   │
│   ┌─────────────┐            ┌─────────────┐            ┌───────────┐   │
│   │  Raw CSVs   │ ────────►  │ Normalization│ ────────► │  LSTM     │   │
│   │  (logon,    │            │ (Parquet)   │            │ Autoenc.  │   │
│   │   file,     │            └─────────────┘            └───────────┘   │
│   │   http,     │                                             │         │
│   │   device)   │                                             ▼         │
│   └─────────────┘                                       ┌───────────┐   │
│                                                         │ Isolation │   │
│                                                         │ Forest    │   │
│                                                         └───────────┘   │
│                                                               │         │
│   🎯 RISK ENGINE             🔌 API LAYER              🖥️ FRONTEND    │
│   ─────────────              ─────────────              ─────────────   │
│   ┌─────────────┐            ┌─────────────┐            ┌───────────┐   │
│   │  Scoring    │ ◄───────── │  FastAPI    │ ◄───────── │  React    │   │
│   │  Engine     │            │  Endpoints  │            │  Dashboard│   │
│   └─────────────┘            └─────────────┘            └───────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Dataset Details

### 2.1 Raw Data Files (Synthetic CERT-like Dataset)

| File | Description | Key Columns | Records |
|------|-------------|-------------|---------|
| `logon.csv` | Login/Logout events | `id`, `user`, `date`, `pc`, `activity` | ~2,600 |
| `file.csv` | File access events | `id`, `user`, `date`, `pc`, `filename`, `activity`, `to_removable_media` | ~4,000 |
| `http.csv` | Web browsing events | `id`, `user`, `date`, `pc`, `url`, `content` | ~12,000 |
| `device.csv` | USB device connections | `id`, `user`, `date`, `pc`, `activity` | ~100 |
| `users.csv` | User metadata | `id`, `role`, `dept`, `pc` | 50 |

### 2.2 User Personas
- **50 users** with roles:
  - 80% Employees
  - 10% Admins (higher privilege)
  - 10% Contractors
  
### 2.3 Injected Insider Threat Scenario
User **U105** performs **data exfiltration** after day 25:
- Bulk file copies (20 files) with "CONFIDENTIAL_" prefix
- Copies to removable media (USB)
- Activity occurs just before logout (suspicious timing)

---

## 3. Data Pipeline

### 3.1 Data Generation (`src/data_pipeline/generator.py`)

**Purpose**: Creates synthetic CERT-like security logs for 30 days of activity.

```python
# Key Configuration
NUM_USERS = 50
START_DATE = datetime(2024, 1, 1)
DAYS_TO_SIMULATE = 30
```

**Key Features**:
- **Time-based behavior**: Employees work 8-10 AM to 5-6 PM
- **Weekend filtering**: Reduced activity on weekends
- **Noise injection**: 5% of Employees may have after-hours activity

### 3.2 Data Normalization (`src/data_pipeline/normalization.py`)

**Purpose**: Unifies all event logs into a single timeline.

**Processing Steps**:
1. Load all CSVs with Polars (fast)
2. Add 'source' column (Logon, File, Http, Device)
3. Handle missing data (fill nulls)
4. Merge into master_timeline.parquet
5. Sort by timestamp

**Output**: `data/processed/master_timeline.parquet` (~18,765 events)

---

## 4. Machine Learning Models

### 4.1 Baseline Models (`src/models/baseline.py`)

**Purpose**: Traditional anomaly detection for comparison/fallback.

| Model | Algorithm | How It Works |
|-------|-----------|--------------|
| **Isolation Forest** | Ensemble Tree | Isolates anomalies by random recursive partitioning. Anomalies need fewer splits to isolate. |
| **One-Class SVM** | Support Vector | Learns a boundary around "normal" data. Points outside are anomalies. |

**Features Used**:
- `hour` (0-23)
- `day_of_week` (0-6)

**Training**:
```bash
python -m src.models.train_baseline --model isolation_forest
```

**Saved Model**: `models/baseline/isolation_forest.joblib`

### 4.2 LSTM Autoencoder (`src/models/lstm_autoencoder.py`)

**Purpose**: Deep learning model for sequence-based anomaly detection.

```
┌─────────────────────────────────────────────────────────────────┐
│                     LSTM AUTOENCODER                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   INPUT                    ENCODER                LATENT        │
│   [t1, t2, ..., t10]  ───► LSTM (2 layers) ───►  Vector [32]   │
│                            Hidden: 32                           │
│                                  │                              │
│                                  ▼                              │
│   OUTPUT                   DECODER                              │
│   [t1', t2', ..., t10'] ◄─ LSTM (2 layers) ◄── Repeat z        │
│                                                                 │
│   LOSS = MSE(Input, Output)                                     │
│   High Loss = Anomaly                                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Features Used**:
- `hour` (scaled)
- `day_of_week` (scaled)
- `source_idx` (Logon=0, File=1, Http=2, Device=3)

**Hyperparameters**:
| Parameter | Value |
|-----------|-------|
| SEQ_LEN | 10 |
| HIDDEN_DIM | 32 |
| NUM_LAYERS | 2 |
| BATCH_SIZE | 64 |
| EPOCHS | 10 |
| LEARNING_RATE | 0.001 |

**Training**:
```bash
python -m src.models.train_lstm
```

**Saved Models**:
- `models/lstm/lstm_ae.pth` (PyTorch state dict)
- `models/lstm/scaler.joblib` (StandardScaler)

**Anomaly Detection**:
- Reconstruction error = MSE between input and output
- High error → Sequence doesn't match learned "normal" patterns → Anomaly

---

## 5. Risk Scoring Engine

### 5.1 Core Logic (`src/risk_engine/scoring.py`)

**Purpose**: Transforms raw anomaly scores into actionable Risk Scores (0-100).

#### Base Score Mapping
```python
# LSTM scores: Mean=0.16, Std=0.12, Threshold=0.41
deviation = max(0, anomaly_score - 0.16)
base_risk = min(100, deviation * 250)
```

#### Contextual Multipliers

| Factor | Condition | Multiplier |
|--------|-----------|------------|
| **User Role** | Admin | 1.5x |
| | Contractor | 1.2x |
| | Employee | 1.0x |
| **Time of Day** | Before 7 AM or After 8 PM | 1.5x |
| **Activity Type** | File Copy | 3.0x - 4.0x |
| | USB Connect | 3.0x |
| | File Delete | 2.0x |

#### Final Risk Calculation
```python
final_risk = base_risk × role_multiplier × time_multiplier × activity_multiplier
```

### 5.2 User-Level Aggregation

```python
# Risk Decay: 10% per day
decayed_score = score × (0.9 ^ days_since_event)

# Hybrid Score:
total_risk = max_risk + (sum_of_decayed_scores × 0.1)
```

### 5.3 Running the Pipeline (`src/risk_engine/run_risk.py`)

```bash
python -m src.risk_engine.run_risk
```

**Output Files**:
| File | Contents |
|------|----------|
| `risk_report_users.csv` | User ID, Total Risk Score |
| `risk_report_events.csv` | All events with risk scores |

---

## 6. Backend API (FastAPI)

### 6.1 Architecture

```
src/api/
├── main.py            # FastAPI app entry point
├── config.py          # Settings (paths, CORS)
├── routers/
│   ├── stats.py       # GET /api/stats
│   ├── users.py       # GET /api/users/risk
│   └── events.py      # GET /api/events/risk
├── schemas/
│   └── responses.py   # Pydantic models
└── services/
    └── data_loader.py # CSV reading logic
```

### 6.2 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/api/stats` | GET | Dashboard statistics |
| `/api/users/risk` | GET | Top risky users |
| `/api/events/risk` | GET | Risky events |

### 6.3 Running the Backend
```bash
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 7. Frontend (React + Vite)

### 7.1 Pages

| Page | Route | Description |
|------|-------|-------------|
| **Dashboard** | `/` | Stats, alerts, trend charts |
| **Risk Heatmap** | `/heatmap` | User × Hour risk visualization |
| **Forensics** | `/forensics` | User investigation with timeline |
| **Alerts** | `/alerts` | Alert queue with filtering |
| **Users** | `/users` | Ranked user risk table |
| **Settings** | `/settings` | Low-power mode, notifications |

### 7.2 Running the Frontend
```bash
cd website
npm install
npm run dev
```

---

## 8. Complete Workflow

### Step-by-Step Execution
```bash
# 1. Generate Data
python -m src.data_pipeline.generator

# 2. Normalize/Process Data
python -m src.data_pipeline.normalization

# 3. Train LSTM Model
python -m src.models.train_lstm

# 4. Run Risk Scoring
python -m src.risk_engine.run_risk

# 5. Start Backend
python -m uvicorn src.api.main:app --port 8000

# 6. Start Frontend
cd website && npm run dev
```

---

## 9. Technology Stack

| Layer | Technology |
|-------|------------|
| **Data Processing** | Polars, Pandas |
| **ML Framework** | PyTorch, scikit-learn |
| **Backend** | FastAPI, Uvicorn |
| **Frontend** | React, Vite, Recharts |
| **Serialization** | Parquet, CSV, Joblib |

---

## 10. File Structure

```
UBA ITD/
├── src/
│   ├── api/                    # FastAPI Backend
│   ├── data_pipeline/          # Data Generation & Processing
│   ├── models/                 # ML Models
│   └── risk_engine/            # Risk Scoring
├── data/
│   ├── raw/                    # Generated CSVs
│   ├── processed/              # Parquet files
│   └── risk_output/            # Risk reports
├── models/
│   ├── baseline/               # Saved IF/OCSVM models
│   └── lstm/                   # Saved LSTM model + scaler
├── website/                    # React Frontend
└── PROJECT_PLAN.md             # Original requirements
```
