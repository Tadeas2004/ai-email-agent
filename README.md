# ✉️ AI Email Agent: Secure Orchestration Pipeline

An intelligent Gmail orchestration system that performs structured two-step analysis on incoming communications using **Google Gemini 2.0 Flash Lite**. The agent converts raw email threads into actionable data points through a high-fidelity reasoning chain.

## 🔗 Live Demo

**Interact with the deployed application here:**
👉 [https://ai-email-agent-9n28.onrender.com](https://ai-email-agent-9n28.onrender.com)

---

## 🛡️ Privacy & Demo Architecture

> **Important for reviewers:** For security and privacy, this application defaults to a **production-safe Demo Mode** in all public deployments.

| Mode          | Trigger                                            | Behavior                             |
| ------------- | -------------------------------------------------- | ------------------------------------ |
| **Demo Mode** | Deployed on Render, or no local `credentials.json` | Runs a high-quality mock data engine |
| **Live Mode** | Valid OAuth 2.0 credentials present locally        | Full Gmail REST API synchronisation  |

The mock data layer lets recruiters and reviewers evaluate the AI's analytical depth, date normalisation logic, and UI responsiveness — without access to a private Gmail account or exposure of any sensitive communications. The same codebase powers both modes without modification.

---

## 🚀 Key Features

### Two-Step AI Pipeline

1. **Fact Extraction** — anchors context and normalises relative dates (e.g. `"this Sunday"`, `"nedělním"`) into absolute ISO 8601 format (`YYYY-MM-DD`) using real-time system clock context.
2. **Strategic Analysis** — maps extracted facts into strict **Pydantic schemas**, ensuring 100% structural integrity and eliminating LLM schema drift.

### Additional Capabilities

- **Smart Deduplication** — a local SQLite layer cross-references `Message-IDs` to prevent redundant AI processing and optimise token usage.
- **High-Fidelity UI** — modern dashboard with custom CSS component rendering: semantic badges, confidence progress bars, and a data-dense layout.
- **Temporal Intelligence** — handles multilingual relative time references and maps them to concrete calendar events based on the processing timestamp.

---

## 🛠️ Tech Stack

| Layer              | Technology                                              |
| ------------------ | ------------------------------------------------------- |
| **LLM**            | Google Gemini 2.0 Flash Lite (500 RPD tier)             |
| **Frontend**       | Streamlit + Atomic HTML/CSS Component Rendering         |
| **Logic**          | Python 3.12, Pydantic (type safety & schema validation) |
| **Database**       | SQLite (relational persistence & deduplication)         |
| **Infrastructure** | Docker, Gmail REST API (OAuth 2.0)                      |

---

## ⚙️ Setup & Installation

### 1. Environment Variables

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_api_key_here
```

### 2. Running with Docker _(Recommended)_

Launches the application in **Secure Demo Mode**:

```bash
docker compose up --build --force-recreate
```

Navigate to `http://localhost:8501` to view the dashboard.

### 3. Local Development _(Live Gmail Sync)_

To enable live Gmail synchronisation, place your `credentials.json` in the root directory, then run:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py          # Runs the backend sync test
streamlit run app.py    # Launches the dashboard
```

---

## 🧠 Strategic Decisions

**Model selection** — migrated to Gemini 2.0 Flash Lite to leverage expanded daily quotas (500 RPD) and its superior performance in structured JSON extraction compared to earlier model versions.

**Defensive programming** — implemented a normalisation layer in the database service to safely handle edge cases where the LLM returns inconsistent data types, preventing silent schema failures downstream.

**UI performance** — bypassed Streamlit's standard Markdown parsing limitations using inline CSS overrides to ensure long text metrics (e.g. `"Marketing/Promotional"`) render without truncation across all viewport sizes.

---

_Developed by **Tadeáš Mutina** as a demonstration of AI Automation and Process Optimisation._
