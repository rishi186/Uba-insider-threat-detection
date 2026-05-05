<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/PyTorch-2.10-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white"/>
  <img src="https://img.shields.io/badge/FastAPI-0.128-009688?style=for-the-badge&logo=fastapi&logoColor=white"/>
  <img src="https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=black"/>
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white"/>
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge"/>
</p>

<h1 align="center">🛡️ UBA & Insider Threat Detection System (Enterprise)</h1>

<p align="center">
  <b>An end-to-end enterprise Machine Learning system for detecting anomalous user behavior, physical endpoint breaches, and potential insider threats.</b>
</p>

<p align="center">
  Built with Endpoint Biometrics · LSTM Autoencoders · WebSockets · HMAC Security · FastAPI · React Context
</p>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [System Architecture](#-system-architecture)
- [Enterprise Features](#-enterprise-features)
- [Getting Started](#-getting-started)
- [🎬 End-To-End Demo Flow (User to Admin)](#-end-to-end-demo-flow)
- [ML Models & Risk Engine](#-ml-models--risk-engine)
- [Docker Deployment](#-docker-deployment)
- [Testing](#-testing)
- [License](#-license)

---

## 🔍 Overview

**User Behavior Analytics (UBA) & Insider Threat Detection (ITD)** is a comprehensive security analytics platform that leverages machine learning to identify suspicious user activities. It features a distributed architecture combining centralized ML anomaly detection with **continuous endpoint biometric authentication**.

### The Problem

Insider threats and session hijacking account for over **60% of data breaches**. Traditional rule-based systems generate excessive false positives and fail to detect sophisticated threats where legitimate credentials are stolen while a session is already active (the "unattended laptop" problem).

### The Solution

We use **behavioral baselines, deep learning, and active physical biometrics (mouse tracking)** to continually map what "normal" looks like. The system flags subtle deviations instantly through real-time WebSockets and dispatches automated SIEM webhooks, blocking hostile payloads via enforced HMAC cryptography.

---

## 🏗️ System Architecture

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                            UBA & ITD ENTERPRISE                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   💻 ENDPOINT                ⚙️ PIPELINE                 🧠 INTELLIGENCE    │
│   ────────────               ─────────────               ───────────────    │
│   ┌────────────┐ HMAC Signed ┌───────────┐ WebSockets    ┌─────────────┐    │
│   │   Python   │ ──────────► │  FastAPI  │ ────────────► │ React       │    │
│   │   Agent    │ (60Hz→1Hz)  │  Backend  │ (Live Alert)  │ Dashboard   │    │
│   └────────────┘             └───────────┘               └─────────────┘    │
│         ▲                          │                            │         │
│         │                          ▼                            ▼         │
│   Mouse Physics              ┌───────────┐ Role-Guarded  ┌─────────────┐    │
│   (Velocity,                 │ Hybrid ML │ ◄──────────── │ Risk Matrix │    │
│    Acceleration)             │ & Heuristics              │ Heatmaps    │    │
│                              └───────────┘               └─────────────┘    │
│                                    │                                        │
│                                    ▼                                        │
│                              ┌───────────┐                                  │
│                              │ Datadog/  │                                  │
│                              │ Splunk    │ (SIEM Webhook)                   │
│                              └───────────┘                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## ✨ Enterprise Features

| Feature | Description |
|---------|-------------|
| 🧬 **Continuous Endpoint Authentication** | Physical mouse-movement biometrics mapped locally via edge-computing agents (`endpoint_agent.py`) sending batched physics telemetry. |
| 🛡️ **Zero-Trust HMAC Security** | Prevents man-in-the-middle attacks. All endpoint payload events are signed via SHA-256 HMAC; the backend rejects unsinged vectors instantly (`403 Forbidden`). |
| ⚡ **Live WebSocket Alerts** | The React framework listens to active `ws://` connections. Endpoint anomalies trigger visual "Toast" alerts on the dashboard instantly without refreshing. |
| 🔌 **SIEM Webhook Dispatches** | Natively pushes high-criticality threats (Score >= 75) to external SIEM providers (like Splunk, Elastic, Datadog) asynchronously. |
| 🔐 **Role-Based Access Control** | React Context API handles frontend routing logic, preventing low-tier user roles from viewing specific forensic endpoints. |
| 🤖 **Dual ML Pipeline** | LSTM Autoencoder + Isolation Forest evaluates structural threat models mapped logically to the **MITRE ATT&CK** matrix. |

---

## 🚀 Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/rishi186/uba-insider-threat-detection.git
cd "uba-insider-threat-detection"
```

### 2. Set Up the Python Environment

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Set Up the Frontend

```bash
cd website
npm install
cd ..
```

---

## 🎬 End-To-End Demo Flow

Looking to demonstrate the system? Follow this exact **User ➔ Admin** simulation to watch the entire architecture in action. You will need 3 separate terminal windows.

### Terminal 1: Spin up the Central Nervous System (Admin)
Start the FastAPI intelligence cluster. This will host the ML engine, the WebSocket hub, and the HMAC strict verification endpoints.
```bash
# Ensure your virtual environment is active
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```
> *Observation:* You will see the server cache warmup and report `Application startup complete.`

### Terminal 2: Launch the Threat Operations Dashboard (Admin/Analyst)
Boot up the frontend visually.
```bash
cd website
npm run dev
```
Open `http://localhost:5173` in your browser. 
1. Navigate to the **"Mouse Tracking"** tab.
2. In the top-right corner header, ensure the **ROLE** dropdown is set to `Admin` or `Analyst`. 

### Terminal 3: Launch Endpoint Biometric Tracking (End-User)
Let's simulate the physical laptop of employee `Rishi`. Their machine runs an invisible background python agent that monitors physical behaviors to guarantee it's actually Rishi at the desk.

```bash
# Ensure your virtual environment is active
python agent/endpoint_agent.py --username rishi --password rishi123
```
> *Observation:* You will see `[HMAC SECURED]` logs proving Rishi's packets are authenticating securely with the UBA system.

### 🚨 Trigger an Insider-Threat Breach!
Now, simulate a hostile actor taking over Rishi's unlocked laptop.
1. Hold your mouse and **shake it violently and erratically** across the screen for 10-15 seconds.
2. The anomaly agent will detect massive discrepancies in Velocity and Jerk.
3. Look at your **Dashboard Browser Window**.
4. You will instantly see a **Red WebSocket Toast Notification** fly into the screen reading: `Critical Biometric Anomaly Detected for user rishi [Score: 78]`. 
5. The backend terminal will output that it successfully caught the threat and dispatched a webhook to the connected SIEM structure!

### 🔐 Verify Front-End RBAC Security
In the Dashboard browser, change the **ROLE** dropdown from `Admin` to `Viewer`. 
Try clicking on the **Users** or **Settings** tab. You will be actively intercepted by the physical React `<RoleGuard>` denying unauthorized access to Tier-1 forensics.

---

## 🧠 ML Models & Risk Engine

Raw anomaly scores are evaluated and contextualized via our Risk Scoring Formula:
`Final Risk = Base Risk × Role Multiplier × Time Multiplier × Activity Multiplier`

Alert Thresholds dynamically degrade through exponential decay (`0.9^(days_since_event)`):
- 🟡 **Medium**: 70–84
- 🟠 **High**: 85–94
- 🔴 **Critical**: 95–100 *(Fires SIEM Webhook)*
 
---

## 🐳 Docker Deployment

For enterprise integrations, deploy the entire stack dynamically via native containerization:

```bash
docker-compose up --build
```
- **Backend**: FastAPI + ML Models exposed port `8000`
- **Frontend**: React Dashboard exposed port `5173`

---

## 🧪 Testing

We employ a massive test-driven-development coverage structure (107 Passing tests with 0 failures).

```bash
python -m pytest tests/ -v
```

Coverages include:
- Cryptographic Mock HMAC dependencies.
- Pytest-Async WebSockets transmission parsing.
- Heuristic logic calculations for `After Hours` and `Privilege Multipliers`.

---

<p align="center">
  <b>Built with ❤️ for enterprise cybersecurity</b>
</p>
