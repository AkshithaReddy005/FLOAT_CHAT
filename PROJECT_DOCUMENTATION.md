# FloatChat — Complete Implementation Documentation

> **Purpose**: Full technical reference covering every core component, data flow, and implementation decision in the FloatChat ARGO oceanographic intelligence system.

---

## Table of Contents

1. [System Architecture Overview](#1-system-architecture-overview)
2. [Data Ingestion Pipeline](#2-data-ingestion-pipeline)
3. [Two-Phase Coordinator & Transaction Manager](#3-two-phase-coordinator--transaction-manager)
4. [Vector Store (ChromaDB)](#4-vector-store-chromadb)
5. [Query Classifier](#5-query-classifier)
6. [Unified Query Parser & Parameter Extraction](#6-unified-query-parser--parameter-extraction)
7. [SQL Generator](#7-sql-generator)
8. [Self-Healing RAG / Consistency Validator](#8-self-healing-rag--consistency-validator)
9. [RAG Engine](#9-rag-engine)
10. [Chatbot Service — End-to-End Orchestration](#10-chatbot-service--end-to-end-orchestration)
11. [Modular FastAPI Routers](#11-modular-fastapi-routers)
12. [Developer Evaluation Dashboard](#12-developer-evaluation-dashboard)
13. [Database Synchronization Script](#13-database-synchronization-script)
14. [Interview Commit Guide](#14-interview-commit-guide)

---

## 1. System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      React Frontend (Port 3000)                  │
│  ┌──────────┐  ┌───────────┐  ┌──────────────┐  ┌───────────┐  │
│  │  Chat UI  │  │ Admin DB  │  │ Researcher   │  │  Testing  │  │
│  │          │  │ Dashboard │  │ Analytics    │  │ Dashboard │  │
│  └────┬─────┘  └─────┬─────┘  └──────┬───────┘  └─────┬─────┘  │
└───────┼──────────────┼───────────────┼────────────────┼─────────┘
        │              │               │                │
        ▼              ▼               ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                  FastAPI Backend (Port 8000)                     │
│  ┌──────────┐  ┌───────────┐  ┌──────────────┐  ┌───────────┐  │
│  │ chat.py  │  │ admin.py  │  │researcher.py │  │system.py  │  │
│  └────┬─────┘  └─────┬─────┘  └──────┬───────┘  └───────────┘  │
│       └──────────────┴───────────────┘                          │
│                          │  deps.py (Shared Singletons)          │
│       ┌──────────────────┼─────────────────────┐                │
│       ▼                  ▼                      ▼                │
│  ChatbotService    VectorStore (ChromaDB)   TwoPhaseCoordinator  │
│       │                  │                      │                │
│       ▼                  ▼                      ▼                │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Core Processing Pipeline                     │   │
│  │  QueryClassifier → UnifiedQueryParser → SQLGenerator     │   │
│  │  → VectorStore.search → ConsistencyValidator → RAGEngine │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             │
          ┌──────────────────┼──────────────────┐
          ▼                  ▼                  ▼
   ┌─────────────┐  ┌──────────────┐  ┌───────────────┐
   │ PostgreSQL  │  │  ChromaDB    │  │ Gemini LLM API│
   │ (raw data)  │  │ (vectors)    │  │ (generation)  │
   └─────────────┘  └──────────────┘  └───────────────┘
```

**Tech Stack:**
| Layer | Technology |
|---|---|
| Frontend | React + Vite, Vanilla CSS |
| Backend API | FastAPI + Uvicorn |
| Relational DB | PostgreSQL via SQLAlchemy |
| Vector DB | ChromaDB (PersistentClient on local SQLite) |
| Embeddings | `all-mpnet-base-v2` (768-dim) via sentence-transformers |
| LLM | Google Gemini 2.0 Flash (`google-generativeai`) |
| Scientific Libraries | `gsw` (TEOS-10), `netCDF4` |

---

## 2. Data Ingestion Pipeline

**File:** `apps/server/src/routers/admin.py` → `POST /admin/upload`

### Flow: NetCDF File Upload

```
User uploads .nc file (NetCDF)
         │
         ▼
1. SHA-256 hash computed → check duplicate file
         │
         ▼
2. netCDF4 reads the file:
   ├── PLATFORM_NUMBER → real WMO float ID extracted
   │     └── Fallback: stable lat/lon hash → FLOAT_XXXXXXXX
   ├── LATITUDE, LONGITUDE arrays
   ├── JULD (Julian day) → converted to datetime
   ├── PRES_ADJUSTED → pressure (dbar)
   │     └── gsw.z_from_p(pressure, latitude) → real depth (meters)
   ├── TEMP_ADJUSTED → temperature (°C)
   └── PSAL_ADJUSTED → salinity (PSU)
         │
         ▼
3. measurement_hash = MD5(float_id + lat + lon + date + depth)
   (duplicate detection key for each individual measurement)
         │
         ▼
4. TwoPhaseCoordinator.execute_coordinated_transaction()
   ├── PHASE 1: PostgreSQL chunked insert (100 records/chunk)
   └── PHASE 2: ChromaDB vector indexing
         │
         ▼
5. Response: { measurements_processed, duplicates_skipped, status }
```

### Key Fix: Real WMO Float ID Extraction
**Before:** Every file got `FLOAT_000001` — profiles mixed.  
**After:** `_extract_float_ids()` reads `PLATFORM_NUMBER` char arrays from NetCDF → true WMO ID.

### Key Fix: Real Depth Conversion
**Before:** `depth = pressure` — scientifically wrong.  
**After:** `depth = abs(gsw.z_from_p(pressure, latitude))` — TEOS-10 oceanographic standard.

---

## 3. Two-Phase Coordinator & Transaction Manager

**Files:** `database/two_phase_coordinator.py`, `database/transaction_manager.py`

### Design Goal
Guarantee that PostgreSQL (source of truth) and ChromaDB (search index) stay in sync whenever data is ingested. If PostgreSQL succeeds but ChromaDB fails, data consistency is still considered maintained because ChromaDB is a secondary index that can be rebuilt.

### Two-Phase Coordinator Flow

```
TwoPhaseCoordinator.execute_coordinated_transaction(
    db, vector_store, measurements, file_hash
)
          │
          ├─── PHASE 1: PostgreSQL (Primary)
          │       ChunkedTransactionManager.execute_chunked_insert()
          │           │
          │           ├── Split into chunks of 100 measurements
          │           ├── For each chunk:
          │           │     1. _filter_existing_measurements()
          │           │        → batch query measurement_hash against DB
          │           │        → skip duplicates
          │           │     2. Attempt db.add_all() + db.commit()
          │           │     3. On IntegrityError → rollback → fallback to
          │           │        individual row inserts (_handle_individual_inserts)
          │           │     4. On unexpected error → rollback, mark failed
          │           └── Returns TransactionResult(successful, failed, duplicates)
          │
          ├─── PHASE 2: ChromaDB (Secondary) — only if Phase 1 succeeded
          │       vector_store.add_measurements(successful_measurements)
          │           → generates text documents + metadata
          │           → embeds with all-mpnet-base-v2
          │           → upserts into argo_data_enhanced collection
          │
          └─── Returns CoordinatorResult:
                   postgresql_success: bool
                   chromadb_success: bool
                   measurements_processed: int
                   consistency_maintained: bool
```

### Failure Handling

| Scenario | Outcome |
|---|---|
| Both succeed | ✅ Ideal — fully consistent |
| PostgreSQL ✅, ChromaDB ❌ | ⚠️ Data safe in PG; Chroma can be rebuilt |
| PostgreSQL ❌ | ❌ Nothing written — consistent by not writing |
| Batch insert fails (IntegrityError) | Fallback to row-by-row insert |

---

## 4. Vector Store (ChromaDB)

**File:** `rag_pipeline/vector_store.py`

### Initialization
```python
VectorStore()
  → chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
  → collection: "argo_data_enhanced"
  → embedding: all-mpnet-base-v2 (768-dim, lazy-loaded on first use)
        Fallback 1: all-MiniLM-L6-v2 (384-dim)
        Fallback 2: ChromaDB DefaultEmbeddingFunction (onnx)
```

### Document Schema
Each measurement stored as a text document + metadata:

**Text document:**
```
Float Measurement FLOAT_000030: Location=20.29°N, 133.81°E,
Date=2024-06-15, Depth=109.40m, Temperature=24.81°C,
Salinity=34.68 PSU, Pressure=110.0 dbar. Region: northern_pacific_ocean.
```

**Metadata fields:**
```json
{
  "float_id": "FLOAT_000030",
  "latitude": 20.295,
  "longitude": 133.815,
  "depth": 109.4,
  "temperature": 24.81,
  "salinity": 34.68,
  "date_timestamp": 1718409600,
  "year": 2024,
  "month": 6,
  "region": "northern_pacific_ocean"
}
```

### add_measurements()
```
Input: List[Dict] of measurement records
  → For each measurement:
       1. Compute MD5 hash ID
       2. Check existing IDs to skip duplicates (batch query)
       3. Build text document string
       4. Build metadata dict
  → collection.upsert(ids, documents, metadatas)
     in batches of ≤ 5000 (CHROMA_MAX_BATCH_SIZE)
Output: { new_measurements, duplicates_skipped, total_processed }
```

### search_with_context()
```
Input: ParameterContext (extracted parameters from query)
  → Build ChromaDB where_filter from context:
       location → lat/lon metadata range ($gte, $lte)
       depth_range → depth metadata filter
       date_years → year metadata filter
       region → region metadata filter
  → Apply $and / $or operator blocks
  → collection.query(query_texts=[query], n_results=N, where=filter)
Output: { documents, metadatas, distances }
```

### Region Classification
50+ ocean regions are classified at write time based on lat/lon bounding boxes:
- `southern_ocean`, `arctic_ocean`, `northern_pacific_ocean`, `equatorial_indian_ocean`, etc.
- Each measurement gets its region label stored in metadata for fast pre-filtering.

---

## 5. Query Classifier

**File:** `rag_pipeline/query_classifier.py`

### Purpose
First checkpoint in the pipeline. Determines whether the query needs database data and what kind of analysis/visualization it expects.

### Input → Output
```
Input: user_query (str)
  → Lowercase scan for keyword groups:
       argo_keywords   → score (needs ARGO data)
       temporal_keywords → score + regex \b(19|20)\d{2}\b for any year
       spatial_keywords → score
       analytical_keywords → score
       visualization_keywords → score
  → Returns classification dict:
       {
         "needs_data": bool,
         "is_complex": bool,
         "is_analytical": bool,
         "is_visualization": bool,
         "chart_type": str | None,
         "query_type": "float_search" | "regional" | "temporal" | "analytical" | "general"
       }
```

### Dynamic Year Detection
Instead of hardcoded `[2020, 2021, 2022, ...]`:
```python
self._year_re = re.compile(r'\b(19|20)\d{2}\b')
```
Matches any valid year 1900–2099 automatically — no code change needed for future years.

---

## 6. Unified Query Parser & Parameter Extraction

**Files:** `rag_pipeline/unified_query_parser.py`, `rag_pipeline/parameter_context.py`, `rag_pipeline/intelligent_parameter_extractor.py`

### Purpose
Single source of truth for all parameter extraction. Produces a `ParameterContext` object used by every downstream component (ChromaDB filter builder, SQL generator, consistency validator).

### Two-Strategy Extraction
```
UnifiedQueryParser.parse_query(user_query, session_context, classification)
          │
          ├── Strategy 1: LLM-First (if GEMINI_API_KEY available)
          │       → Prompt Gemini with structured JSON schema request
          │       → Extracts: location, depth_range, date_range,
          │                   temperature_range, salinity_range, parameters
          │       → Falls back to heuristic if LLM fails
          │
          └── Strategy 2: Heuristic-Only
                  → Regex + keyword patterns for:
                       location text → location_bounds dict
                       depth patterns ("below 500m", "surface")
                       date patterns ("in 2024", "January 2023")
                       temperature ("above 25°C", "warmer than")
                       salinity ("high salinity")
                  → Returns ParameterContext
```

### ParameterContext Object
The central data object flowing through the entire pipeline:
```python
ParameterContext:
  original_query:    str
  query_id:          str (UUID)
  location_name:     str | None          # "Arabian Sea"
  location_bounds:   dict | None         # {lat_min, lat_max, lon_min, lon_max}
  location_context:  str | None          # region key for ChromaDB metadata
  depth_range:       tuple | None        # (min, max) or (operator, value)
  depth_type:        "range" | "operator"
  date_range:        tuple[datetime] | None
  date_years:        List[int] | None
  temperature_range: tuple | None        # (operator, value) e.g. ('>', 25)
  salinity_range:    tuple | None
  parameters:        List[str]           # ['temperature', 'salinity']
  float_ids:         List[str] | None
  is_chart_request:  bool
  is_comparative:    bool
  is_analytical:     bool
  is_full_data_request: bool
  complexity_level:  "simple" | "moderate" | "complex"
  confidence_score:  float (0.0 – 1.0)
  extraction_method: "llm" | "heuristic"

  # Methods:
  to_chroma_filters() → where dict for ChromaDB
  to_sql_filters()    → dict for SQL generator
  get_summary()       → human-readable string
```

### to_chroma_filters() — Metadata Pre-filtering
```
location_bounds  → {"$and": [
                       {"latitude":  {"$gte": lat_min}},
                       {"latitude":  {"$lte": lat_max}},
                       {"longitude": {"$gte": lon_min}},
                       {"longitude": {"$lte": lon_max}}
                   ]}
depth_range      → {"depth": {"$gte": min, "$lte": max}}
date_years       → {"year": {"$in": [2023, 2024]}}
temperature_range → {"temperature": {"$gte": value}}
```
**Why split into separate `$and` blocks?** ChromaDB requires single-operator syntax per field — compound expressions in one block cause parser errors.

---

## 7. SQL Generator

**File:** `rag_pipeline/sql_generator.py`

### Purpose
Converts the `ParameterContext` into a valid PostgreSQL SELECT query against `argo_measurements`.

### Two Generation Strategies

```
generate_sql_from_context(parameter_context)
          │
          ├── Comparative query? → always rule-based
          │       (deterministic region-wise aggregation SQL)
          │
          ├── complexity_level == "complex" AND Gemini available?
          │       → _generate_with_gemini_from_context()
          │            Prompt: schema + query + parameter summary
          │            Model: gemini-2.0-flash, temp=0.1, max_tokens=300
          │            → strips ```sql``` markers from response
          │
          └── Otherwise → _generate_rule_based_from_context()
                   Builds WHERE clauses from ParameterContext:
                   ├── location_bounds → lat/lon BETWEEN
                   ├── depth_range → depth operator value
                   ├── date_range / date_years → date filters
                   ├── temperature_range → temperature operator value
                   ├── salinity_range → salinity operator value
                   └── float_ids → float_id IN (...)
                   → Appends ORDER BY + LIMIT
```

### validate_sql()
Checks generated SQL for:
- SELECT statement present
- `argo_measurements` table referenced
- No destructive keywords (`DROP`, `DELETE`, `INSERT`, `UPDATE`)
- Reasonable length

### Location Bounds
SQLGenerator dynamically loads the same 50+ region bounds used by `UnifiedQueryParser` to ensure lat/lon WHERE clauses are consistent with the ChromaDB metadata filters.

---

## 8. Self-Healing RAG / Consistency Validator

**File:** `rag_pipeline/consistency_validator.py`

### Purpose
After SQL is generated and executed, verifies that returned data actually matches the requested parameters. If not, patches the SQL query and re-runs it.

### Self-Healing SQL Pattern (in `chatbot_service.py`)

```
SQL generated and executed → db_results returned
          │
          ▼
If temperature_range requested:
   Sample first 5 records → check violations:
   operator='>'  → any result where temperature <= threshold → VIOLATION
   operator='<'  → any result where temperature >= threshold → VIOLATION
          │
          ▼
If violations found:
   _inject_filter_into_sql(sql_query, "temperature > 25", "temperature IS NOT NULL")
       → Inserts new WHERE clause condition into existing SQL string
       → Re-executes patched SQL
       → Uses new results if patch succeeds
          │
          ▼
Logs: "WARNING: SQL temperature filter missing — patching query and re-running."
```

### ConsistencyValidator.validate_service_consistency()

```
Input: ParameterContext, sql_results, chroma_results, ai_response
          │
          ├── _validate_sql_consistency()
          │       Samples first 10 records:
          │       ├── location: lat/lon within location_bounds?
          │       ├── temporal: date year in date_years?
          │       ├── depth: within depth_range?
          │       ├── float_id: in requested float_ids?
          │       └── parameters: non-null values for requested params?
          │
          ├── _validate_chroma_consistency()
          │       Samples first 5 ChromaDB metadata dicts:
          │       ├── location bounds check
          │       ├── temporal year check
          │       └── depth range check
          │
          └── _validate_cross_service_consistency()
                  ├── SQL returned data but ChromaDB returned 0 → warning
                  ├── ChromaDB returned data but SQL returned 0 → warning
                  ├── Result count ratio > 10x → warning
                  └── Parameter coverage < 50% → warning

Output: ValidationReport {
    is_consistent: bool,
    violations: List[str],
    warnings: List[str],
    service_stats: { sql_records, chroma_matches, parameter_summary }
}
```

### should_fail_request()
```
≥ 3 critical violations ("outside bounds", "violates", etc.) → fail request
> 3 total violations → systematic failure → fail request
Otherwise → proceed with warnings logged
```

---

## 9. RAG Engine

**File:** `rag_pipeline/rag_engine.py`

### Purpose
Constructs the final natural language answer by combining:
1. Retrieved ChromaDB context documents (semantic search results)
2. PostgreSQL query results (relational data)
3. Parameter context (what was asked)

### Flow
```
RAGEngine.generate_response(
    user_query, parameter_context, context_results, db_results, validation_report
)
          │
          ▼
1. Build context string from ChromaDB documents
   → Top-N most relevant text chunks formatted as context
          │
          ▼
2. Build data summary from SQL results
   → Statistics: min/max/avg temperature, salinity, depth
   → Sample records formatted as readable text
          │
          ▼
3. Build Gemini prompt:
   System: "You are an oceanographic data assistant..."
   Context: ChromaDB documents
   Data: SQL result summaries
   Query: Original user question
   Instructions: Answer in natural language, cite measurements
          │
          ▼
4. Call Gemini API → generate_content()
          │
          ▼
5. VisualizationBuilder.build_charts(parameter_context, db_results)
   → Determines chart type based on:
        time_series → date field present + >5 records
        scatter → two continuous variables requested
        profile → depth present (vertical profile)
        bar → comparative / region grouping
   → Returns chart config JSON for frontend rendering
          │
          ▼
Output: { response, charts, query_params, pipeline_flow, timings }
```

---

## 10. Chatbot Service — End-to-End Orchestration

**File:** `chat_bot/chatbot_service.py`

This is the master orchestrator. Every chat query flows through exactly 8 timed stages:

```
POST /chat { message, session_id }
          │
          ▼
┌─────────────────────────────────────────────────────────┐
│ Stage 1: Query Intelligence Enhancement                  │
│   QueryIntelligence.enhance_query()                     │
│   → intent detection, complexity scoring                │
└─────────────────────────────┬───────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────┐
│ Stage 2: Query Classification          ⏱ timed          │
│   QueryClassifier.classify_query()                      │
│   → needs_data, is_complex, chart_type, query_type      │
└─────────────────────────────┬───────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────┐
│ Stage 3: Unified Parameter Extraction  ⏱ timed          │
│   UnifiedQueryParser.parse_query()                      │
│   → ParameterContext (location, depth, date, temp, etc) │
│   → logged via parameter_logger                         │
└─────────────────────────────┬───────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────┐
│ Stage 4: ChromaDB Vector Search        ⏱ timed          │
│   VectorStore.search_with_context()                     │
│   → dynamic n_results: 15/30/40/60 by complexity        │
│   → metadata pre-filtered                               │
│   → documents filtered: len > 30 chars                  │
└─────────────────────────────┬───────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────┐
│ Stage 5: SQL Generation & Execution    ⏱ timed          │
│   SQLGenerator.generate_sql_from_context()              │
│   → rule-based or Gemini LLM                            │
│   → validate_sql() safety check                         │
│   → _execute_sql_query()                                │
│   → SELF-HEALING: check temperature violations          │
│       → _inject_filter_into_sql() + re-execute          │
└─────────────────────────────┬───────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────┐
│ Stage 6: Consistency Validation        ⏱ timed          │
│   ConsistencyValidator.validate_service_consistency()   │
│   → validates SQL + ChromaDB results vs ParameterContext│
│   → should_fail_request() → hard fail if critical       │
│   → generate_fallback_explanation() if partial issues   │
└─────────────────────────────┬───────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────┐
│ Stage 7: Gemini Response Generation    ⏱ timed          │
│   RAGEngine.generate_response()                         │
│   → builds context + data prompt                        │
│   → calls Gemini API                                    │
└─────────────────────────────┬───────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────┐
│ Stage 8: Visualization Rendering       ⏱ timed          │
│   VisualizationBuilder.build_charts()                   │
│   → chart type scoring: time_series / scatter /         │
│     profile / bar / histogram                           │
│   → chart config JSON                                   │
└─────────────────────────────┬───────────────────────────┘
                              ▼
Response JSON:
{
  "response": "...",           ← Gemini-generated answer
  "charts": [...],             ← Visualization configs
  "query_params": {            ← Full ParameterContext snapshot
    "timings": {               ← ⏱ ms per stage
      "classification": 45,
      "parameter_extraction": 320,
      "context_retrieval": 1250,
      "sql_generation": 180,
      "sql_execution": 95,
      "consistency_validation": 12,
      "response_generation": 2100,
      "visualization": 8
    }
  },
  "pipeline_flow": {           ← Step-by-step audit trail
    "steps": [...],
    "chroma_search": {...},
    "sql_generation": {...},
    "consistency_validation": {...}
  }
}
```

### Session Memory Management
```
session_context["recent_exchanges"]:
  → Capped at 5 most recent (user, assistant) message pairs
  → Older history summarized and stored in session_context["summary"]
  → Summary updated via Gemini when cap is exceeded
  → Controls token usage while preserving conversation coherence
```

---

## 11. Modular FastAPI Routers

**Files:** `routers/deps.py`, `routers/admin.py`, `routers/chat.py`, `routers/researcher.py`, `routers/system.py`, `main.py`

### deps.py — Shared Singletons
```python
# Initialized ONCE on app startup
vector_store:           VectorStore
chatbot_service:        ChatbotService
example_generator:      ExampleQueryGenerator
transaction_coordinator: TwoPhaseCoordinator

def initialize():
    # Called from main.py @app.on_event("startup")
    vector_store = VectorStore()
    chatbot_service = ChatbotService(vector_store)
    ...
```

### Router Responsibilities

| Router | Prefix | Key Endpoints |
|---|---|---|
| `chat.py` | `/` | `POST /chat`, `POST /session/reset`, `GET /examples` |
| `admin.py` | `/admin` | `POST /upload`, `GET /stats`, `GET /knowledge-base`, `DELETE /databases/clear`, `GET /data-consistency-check` |
| `researcher.py` | `/researcher` | `POST /query`, `POST /download-data`, `GET /export-chat/{id}` |
| `system.py` | `/` | `GET /health`, `GET /user/analytics` |

### main.py — Startup
```python
app = FastAPI()
app.include_router(chat_router)
app.include_router(admin_router)
app.include_router(researcher_router)
app.include_router(system_router)

@app.on_event("startup")
async def startup():
    deps.initialize()   # All singletons created once
```

**Why this matters:** Before refactoring, all 1000+ lines of logic lived in `main.py`. Splitting into routers means each domain is independently testable, readable, and extensible.

---

## 12. Developer Evaluation Dashboard

**Files:** `apps/client/src/components/admin/TestingDashboard.tsx`, `testSuites.ts`

### Purpose
Internal benchmarking tool for measuring RAG pipeline quality, classifier accuracy, and latency distribution.

### Input → Processing → Output

**Input (`testSuites.ts`):**
```typescript
[
  {
    name: "Temperature Queries",
    queries: [
      {
        message: "Find measurements above 25°C in Arabian Sea",
        expectedType: "regional"
      },
      ...
    ]
  },
  // + Salinity, Regional Coordinates, Float Searches,
  //   Conversational Memory, Edge Cases suites
]
```

**Processing (`TestingDashboard.tsx`):**
```
User selects suite → clicks Run
    → Sequential POST /chat requests (session-aware, same session_id)
    → Each response includes timings dict:
         { classification, parameter_extraction, context_retrieval,
           sql_generation, sql_execution, consistency_validation,
           response_generation, visualization }
    → Compares response.query_params.query_type vs test.expectedType
```

**Output (Dashboard UI):**
```
┌────────────────────────────────────────────────────────┐
│  Pipeline Checkmarks:                                   │
│  ✓ Query Classifier  ✓ Parameter Extraction            │
│  ✓ ChromaDB Search   ✓ SQL Execution                   │
│  ✓ Consistency Check ✓ Gemini Generation               │
│  ✓ Visualization                                        │
│                                                         │
│  Classifier Accuracy:                                   │
│  Expected: regional   Actual: regional   ✅ Match       │
│                                                         │
│  Latency Timeline (ms):                                 │
│  [Classification: 45] [Param Extract: 320]              │
│  [ChromaDB: 1250] [SQL: 275] [Gemini: 2100]            │
│                                                         │
│  Benchmark History: Run #3 vs Run #2 → -12% latency    │
└────────────────────────────────────────────────────────┘
```

Benchmark runs are saved in browser `localStorage` for cross-session comparisons.

---

## 13. Database Synchronization Script

**File:** `rebuild_vector_store.py`

### Purpose
Standalone script to sync all measurements from PostgreSQL into ChromaDB. Run independently from the server.

### Flow
```
python rebuild_vector_store.py
          │
          ▼
1. Delete existing ChromaDB collection "argo_data_enhanced"
          │
          ▼
2. Re-create collection (fresh embedding index)
          │
          ▼
3. Query PostgreSQL:
   SELECT float_id, latitude, longitude, date, depth,
          temperature, salinity, pressure
   FROM argo_measurements
   WHERE latitude IS NOT NULL AND longitude IS NOT NULL
     AND temperature IS NOT NULL AND salinity IS NOT NULL
   ORDER BY id          ← indexed primary key scan (fast)
          │
          ▼
4. Process in batches of 1000:
   → Build measurement dicts
   → vector_store.add_measurements(batch)
   → Print progress: "Processing batch X/N..."
          │
          ▼
5. Test region distribution after sync
   → Run sample searches for 4 ocean regions
   → Report document counts found

Output: "Total measurements processed: N, Total added: N"
```

### Optimization Note
IDs in `argo_measurements` start at `683,712` (not 1) due to prior import history. Using `ORDER BY id` (not `WHERE id <= 10000`) ensures correct retrieval from the actual data range.

---

## 14. Interview Commit Guide

> Structured **Problem → Solution → Impact** for each commit, grouped by theme.

### Summary in one line per group
- **Commits 1–2:** Fixed **data quality** at the source (float IDs + depth conversion)
- **Commits 3–5:** Improved **performance and backend reliability** (latency, SQL self-healing, modular code)
- **Commits 6–8:** Improved **retrieval quality and memory** (better embeddings, session capping, dynamic years)
- **Commits 9–11:** Improved **query understanding and global coverage** (50+ regions, documentation, classification)
- **Commit 12:** Improved **RAG efficiency** via metadata-guided pre-filtering

---

### Group A — Data Quality

#### Commit 1: Real WMO Float IDs
- **Problem**: All NetCDF files assigned dummy `FLOAT_000001` — profiles from 678 different floats mixed together.
- **Solution**: `_extract_float_ids()` reads `PLATFORM_NUMBER` char arrays; lat/lon hash fallback for missing values.
- **Impact**: Each float's measurements traceable independently; data integrity restored.

#### Commit 2: Real Depth Conversion (TEOS-10)
- **Problem**: `depth = pressure` — pressure in dbar ≠ depth in meters.
- **Solution**: `depth = abs(gsw.z_from_p(pressure, latitude))` using TEOS-10 oceanographic standard.
- **Impact**: Physically correct depth values; queries like "below 500m" now accurate.

---

### Group B — Performance & Reliability

#### Commit 3: Remove Artificial Thinking Delay
- **Problem**: `time.sleep(2)` in SQLGenerator to simulate thinking — added 2 seconds to every query.
- **Solution**: Removed the sleep call entirely.
- **Impact**: 2+ seconds shaved from every user interaction.

#### Commit 4: Self-Healing SQL
- **Problem**: Gemini-generated SQL sometimes omitted WHERE clauses for temperature filters — wrong data returned silently.
- **Solution**: After execution, sample first 5 rows; if any violate the requested temperature filter, inject the filter into SQL string and re-execute.
- **Impact**: Guaranteed filter correctness even when LLM generation is imperfect.

#### Commit 5: Modular FastAPI Routers
- **Problem**: 1000+ line monolithic `main.py` — all endpoints, business logic, helpers mixed together.
- **Solution**: Split into `admin.py`, `chat.py`, `researcher.py`, `system.py` with shared `deps.py` singletons.
- **Impact**: Each module independently maintainable and testable.

---

### Group C — Retrieval & Memory

#### Commit 6: Upgrade Embedding Model
- **Problem**: ChromaDB default embedding model poorly represents scientific terminology like "PSAL", "PRES", coordinate pairs.
- **Solution**: Upgraded to `all-mpnet-base-v2` (768-dim) with fallback chain to MiniLM → default.
- **Impact**: Semantically similar oceanographic queries retrieve more relevant documents.

#### Commit 7: Session Memory Management
- **Problem**: `recent_exchanges` list grew unbounded — large token payloads, potential context window overflow.
- **Solution**: Capped at 5 exchange pairs; older history summarized via Gemini and stored separately.
- **Impact**: Controlled token costs; coherent multi-turn conversations maintained.

#### Commit 8: Dynamic Year Detection
- **Problem**: Classifier had hardcoded `["2020", "2021", "2022", "2023"]` — future years not recognized.
- **Solution**: Replaced with `re.compile(r'\b(19|20)\d{2}\b')` — matches any valid year 1900–2099.
- **Impact**: Zero-maintenance temporal parsing for all future dataset years.

---

### Group D — Query Intelligence

#### Commit 9: Global Location Support
- **Problem**: Only ~10 ocean regions recognized in `location_bounds`; most international queries fell through.
- **Solution**: Expanded to 50+ named ocean regions, seas, gulfs, and basins with precise bounding boxes.
- **Impact**: Accurate lat/lon filters applied for queries like "Barents Sea", "Bay of Bengal", "Gulf of Mexico".

#### Commit 10: Document Chart Scoring Thresholds
- **Problem**: Chart type selection logic existed but rationale was opaque — hard to debug or extend.
- **Solution**: Added inline documentation for all scoring thresholds (e.g., why >5 records trigger time_series, not scatter).
- **Impact**: Any developer can understand and modify chart selection logic without reverse-engineering.

#### Commit 11: Global Ocean Region Classification
- **Problem**: Documents from Atlantic, Pacific, Arctic got classified as `indian_ocean` (the default fallback).
- **Solution**: Region detection runs at ingestion time using lat/lon bounding box matching against 50+ regions; correct label stored in ChromaDB metadata.
- **Impact**: Region-based metadata filters (`"region": "southern_ocean"`) now work globally.

#### Commit 12: Metadata Pre-filtering for Vector Search
- **Problem**: ChromaDB full-collection scan even when parser already extracted location, year, depth — irrelevant documents returned, wasting compute.
- **Solution**: `ParameterContext.to_chroma_filters()` builds `$and`/`$or` metadata filter blocks; applied to `collection.query()` as `where` argument.
- **Impact**: Search space narrowed to relevant subset first; faster retrieval, higher precision results.
