# FloatChat — Advanced ARGO Oceanographic Intelligence System

FloatChat is an end-to-end oceanographic intelligence and conversational analytics platform designed for researchers, marine scientists, and oceanographers. It enables natural language exploration of autonomous ARGO profiling float datasets by unifying high-dimensional scientific data ingestion (NetCDF), dual-tier synchronized storage (PostgreSQL + ChromaDB), a self-healing Hybrid RAG engine (NL-to-SQL + Vector Search), and interactive geospatial/oceanographic visualizations.

---

## Architecture Overview

FloatChat utilizes a multi-tiered architecture that bridges unstructured semantic search and strict scientific tabular querying:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        React Frontend (Port 3000)                      │
│   ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  ┌────────────┐  │
│   │   Chat UI    │  │   Admin DB   │  │ Researcher  │  │ Testing    │  │
│   │ & Visualizer │  │  Dashboard   │  │  Analytics  │  │ Dashboard  │  │
│   └──────┬───────┘  └──────┬───────┘  └──────┬──────┘  └─────┬──────┘  │
└──────────┼─────────────────┼─────────────────┼───────────────┼─────────┘
           │                 │                 │               │
           ▼                 ▼                 ▼               ▼
┌────────────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend (Port 8000)                       │
│   ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  ┌────────────┐  │
│   │   chat.py    │  │   admin.py   │  │researcher.py│  │ system.py  │  │
│   └──────┬───────┘  └──────┬───────┘  └──────┬──────┘  └─────┬──────┘  │
│          └─────────────────┴────────┬────────┴───────────────┘         │
│                                     ▼                                  │
│                       routers/deps.py (Singletons)                     │
│          ┌──────────────────────────┼────────────────────────┐         │
│          ▼                          ▼                        ▼         │
│   ChatbotService         TwoPhaseCoordinator          VectorStore     │
│   (NL-to-SQL + RAG)    (PostgreSQL + ChromaDB Sync)   (ChromaDB Index) │
└──────────┬──────────────────────────┬────────────────────────┬─────────┘
           │                          │                        │
           ▼                          ▼                        ▼
    ┌──────────────┐           ┌──────────────┐         ┌──────────────┐
    │  PostgreSQL  │           │   ChromaDB   │         │  Google LLM  │
    │  (Relational │           │ (Embeddings  │         │  Gemini 2.0  │
    │ Raw Metrics) │           │ all-mpnet-v2)│         │    Flash     │
    └──────────────┘           └──────────────┘         └──────────────┘
```

---

## Key Capabilities & Core Pipeline

### 1. High-Fidelity NetCDF Ingestion
- **Real WMO Float IDs**: Direct parsing of `PLATFORM_NUMBER` character arrays to prevent cross-profile contamination across floats.
- **TEOS-10 Pressure-to-Depth Conversion**: Converts sea pressure ($p$ in dbar) to true ocean depth ($z$ in meters) using `gsw.z_from_p(pressure, latitude)`.
- **Cryptographic Deduplication**: Computes SHA-256 file fingerprints and MD5 record keys (`MD5(float_id + lat + lon + date + depth)`) to prevent duplicate storage.
- **Multi-File Batch Upload**: Seamless concurrent or sequential drag-and-drop batch upload in the admin portal.

### 2. Two-Phase Coordinated Transaction System
- Guarantees transactional integrity across relational and vector stores.
- **Phase 1 (PostgreSQL)**: Bulk chunked ingestion (100 measurements/chunk) with automatic fallback to single-row isolation on constraints.
- **Phase 2 (ChromaDB)**: Syncs corresponding document embeddings into vector collections only after relational commits succeed.

### 3. Hybrid RAG & Self-Healing NL-to-SQL
- **Query Classification & Unified Parameter Extraction**: Parses natural language into structured constraints across 7 primary dimensions:
  - Coordinate bounding boxes (50+ global oceans, seas, and gulfs)
  - Depth ranges (meters)
  - Pressure ranges (dbar)
  - Temperature ranges (°C)
  - Salinity ranges (PSU)
  - Temporal patterns (regex-driven 1900–2099 calendar year recognition)
  - Platform/Float identifiers (WMO IDs)
- **Metadata Pre-filtered Vector Search**: Restricts semantic search spaces in ChromaDB using extracted structured parameters prior to cosine distance ranking.
- **Self-Healing SQL**: Validates executed SQL query outputs against requested user constraints (e.g., verifying sample boundaries). Automatically patches missing `WHERE` clauses and re-executes if anomalies are detected.
- **Session Memory Management**: Sliding window capped at 5 recent exchange pairs with automatic background LLM summarization.

### 4. Interactive Oceanographic Visualizations
- **Interactive Geospatial Maps**: Leaflet-based trajectory and profile maps with depth-coded color scales and marker clustering.
- **Dual-Axis Depth Profiles**: Salinity (PSU) and Temperature (°C) plotted against depth (m).
- **Automated Plotly Generation**: Fallback and rule-driven generation of time series, anomaly distributions, histograms, and scatter plots.

### 5. Developer Testing & Benchmark Dashboard
- Comprehensive evaluation suite accessible at `/admin/testing`.
- Measures step-by-step latency across: classification, parameter extraction, ChromaDB retrieval, SQL generation, SQL execution, consistency validation, and LLM synthesis.
- Benchmarking history with run-to-run regression tracking saved in browser `localStorage`.

---

## Tech Stack

| Component | Technology | Description |
|---|---|---|
| **Frontend** | React 19, TypeScript, Vite, Tailwind CSS | High-performance responsive single-page web client |
| **Mapping & Charts** | Leaflet, React-Leaflet, Plotly.js | Interactive oceanographic maps and profile charts |
| **Backend API** | FastAPI, Uvicorn, Pydantic | Asynchronous RESTful API with modular routing |
| **Relational DB** | PostgreSQL, SQLAlchemy, psycopg2 | Primary source of truth for tabular measurements |
| **Vector DB** | ChromaDB (`all-mpnet-base-v2`) | Semantic embeddings (768-dimensional dense vectors) |
| **Oceanographic Math** | `gsw` (TEOS-10), `netCDF4`, `xarray` | Standard thermodynamic equation of seawater & grid processing |
| **Language Model** | Google Gemini 2.0 Flash | Semantic query parsing, NL-to-SQL, and synthesis |

---

## Directory Structure

```
floatchat/
├── apps/
│   ├── client/                      # React + TypeScript Frontend
│   │   ├── src/
│   │   │   ├── components/
│   │   │   │   ├── admin/           # Admin & Developer Testing dashboards
│   │   │   │   ├── chat/            # Chat interface & query suggestions
│   │   │   │   ├── visualizations/  # Leaflet maps, depth profiles & charts
│   │   │   │   └── common/          # Drag-and-drop file uploaders
│   │   │   ├── hooks/               # Custom React hooks (useUpload, useChat)
│   │   │   └── services/            # Axios API client integrations
│   │   └── package.json
│   │
│   └── server/                      # FastAPI Backend
│       ├── src/
│       │   ├── chat_bot/            # End-to-end chat orchestration
│       │   ├── database/            # SQLAlchemy models, Two-Phase Coordinator
│       │   ├── rag_pipeline/        # RAG Engine, VectorStore, SQL Generator,
│       │   │                        # Query Classifier, Consistency Validator
│       │   ├── routers/             # admin.py, chat.py, researcher.py, system.py
│       │   ├── utils/               # NetCDF parser, query examples generator
│       │   └── main.py              # Application entrypoint & CORS config
│       ├── requirements.txt
│       └── setup_db.py              # Database initialization script
│
├── rebuild_vector_store.py          # Standalone PostgreSQL → ChromaDB sync script
├── PROJECT_DOCUMENTATION.md         # In-depth architectural & implementation reference
└── README.md
```

---

## Prerequisites

Before starting, ensure you have the following installed:
- **Node.js** (v18.x or v20.x+) and `npm`
- **Python** (v3.10, v3.11, or v3.12)
- **PostgreSQL** (v14+ recommended)
- **Google Gemini API Key** ([Google AI Studio](https://aistudio.google.com/))

---

## Setup & Installation

### 1. Clone Repository
```bash
git clone https://github.com/your-username/floatchat.git
cd floatchat
```

### 2. Configure Environment Variables

#### Backend (`apps/server/.env`)
Create `apps/server/.env` based on `apps/server/.env.example`:
```ini
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=floatchat
DB_USER=postgres
DB_PASSWORD=your_postgres_password

# Server Host/Port
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000
FRONTEND_HOST=localhost
FRONTEND_PORT=3000

# AI Configuration
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.0-flash

# ChromaDB Embedding Model
CHROMA_EMBEDDING_MODEL=all-mpnet-base-v2
```

#### Frontend (`apps/client/.env`)
Create `apps/client/.env`:
```ini
VITE_API_BASE_URL=http://localhost:8000
```

### 3. Setup PostgreSQL Database
Make sure PostgreSQL is running on your machine, then initialize the tables:
```bash
cd apps/server
python -m venv venv

# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
python setup_db.py
```

### 4. Run the Backend Server
```bash
# Inside apps/server with venv activated
python src/main.py
```
*API will run at `http://localhost:8000` with interactive Swagger docs at `http://localhost:8000/docs`.*

### 5. Run the Frontend Client
Open a separate terminal:
```bash
cd apps/client
npm install
npm run dev
```
*Client application will be accessible at `http://localhost:3000`.*

---

## Database Resynchronization Utility

If you load raw data directly into PostgreSQL or want to rebuild your vector store from scratch:
```bash
# Inside project root with backend venv activated
python rebuild_vector_store.py
```
This utility:
1. Re-initializes the `argo_data_enhanced` collection in ChromaDB.
2. Performs a primary-key indexed query against PostgreSQL.
3. Batches records into scientific document strings and regenerates `all-mpnet-base-v2` dense embeddings.
4. Executes validation checks across major ocean regions.

---

## Architectural Evolution (Interview Commit Summary)

| Commit Group | Key Highlights | Core Impact |
|---|---|---|
| **Data Quality** | Real WMO Float IDs via NetCDF char arrays & TEOS-10 `gsw` depth conversion | Prevents profile mixing and replaces unscientific `depth = pressure` assumptions |
| **Reliability & Performance** | Self-Healing SQL query patching & removal of artificial delays | Eliminates query latency bloat and guarantees filter enforcement |
| **Retrieval & Memory** | ChromaDB upgrade to `all-mpnet-base-v2`, dynamic regex years, session history capping | Dramatically improves semantic oceanographic retrieval and controls token costs |
| **Query Intelligence** | 50+ global ocean bounding boxes & metadata pre-filtering | Filters vector search space before similarity ranking for higher speed and precision |
| **Architecture** | Modular FastAPI routers (`admin`, `chat`, `researcher`, `system`) with shared singletons | Eliminates monolithic dependencies and enables isolated testing |

*For complete implementation specs, code flows, and parameter mappings, see [PROJECT_DOCUMENTATION.md](file:///PROJECT_DOCUMENTATION.md).*

---

## License

This project is licensed under the MIT License.
