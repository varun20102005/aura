# AURA — Technical Requirements Document (TRD)

**Product:** AURA (Automated Risk & Audit Analyzer)
**Category:** Healthcare Claim Fraud Detection & Investigation Platform
**Document Version:** 1.0 (Final)
**Status:** Approved for Engineering Planning
**Companion Document:** AURA_PRD.md

---

## 1. Purpose

This TRD translates the product requirements in AURA_PRD.md into an engineering-level specification: architecture, data model, APIs, ML/AI components, security, and a phased technical implementation plan. It covers both the **current implemented system** and the **new, feasible feature set** approved in the PRD.

---

## 2. Current Architecture (As-Built)

```
React Frontend (Vite, Tailwind, Chart.js)
        │  Axios REST calls (JSON, multipart for uploads)
        ▼
FastAPI Backend
   ├─ Auth (JWT, RBAC)
   ├─ Claims Router (upload, list, detail, notes, status)
   ├─ OCR Service + Worker (EasyOCR → pytesseract fallback)
   ├─ ML Layer (XGBoost, Isolation Forest)
   ├─ Duplicate Detection (RapidFuzz)
   ├─ Graph Analysis (NetworkX)
   ├─ Explainability (SHAP)
   ├─ LLM Helper (Gemini, optional)
   ├─ Analytics API
   ├─ Admin API (model metrics, audit logs)
   └─ Reporting (ReportLab → PDF)
        │
        ▼
PostgreSQL (production) / SQLite (dev fallback)
+ Model artifact storage (filesystem)
```

**Frontend responsibilities:** user interaction, dashboards, forms, filtering, charts, protected navigation, investigation views.

**Backend responsibilities:** authentication, validation, persistence, document processing, fraud analytics, explanations, investigation records, audit logs, report generation.

---

## 3. Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React, Vite, Tailwind CSS, Axios, Chart.js / react-chartjs-2, Lucide icons |
| Backend | FastAPI, Python, Pydantic, SQLAlchemy |
| Database | PostgreSQL (prod), SQLite (dev fallback) |
| Auth | JWT, password hashing, RBAC, protected routes |
| OCR | EasyOCR (primary), pytesseract (fallback) |
| Supervised ML | XGBoost |
| Unsupervised ML | Isolation Forest (scikit-learn) |
| Explainability | SHAP |
| Duplicate Detection | RapidFuzz |
| Graph Analytics | NetworkX |
| Generative AI | Gemini API (optional, key-gated) |
| Reporting | ReportLab (PDF generation) |
| Communication | REST over Axios |

### 3.1 Proposed Additions for New Features

| Addition | Purpose | Justification |
|---|---|---|
| **pgvector (PostgreSQL extension)** | Store & query embedding vectors for semantic claim similarity | Native extension of existing PostgreSQL; avoids introducing a separate vector DB |
| **Sentence-embedding model** (e.g., a lightweight open embedding model run server-side) | Generate claim-text embeddings for semantic similarity | Runs alongside existing Python ML stack; no new language/runtime |
| **APScheduler / Celery (or existing worker pattern extended)** | Scheduled jobs for drift checks, provider risk recomputation, notification digesting | Consistent with existing OCR worker pattern already in the codebase |
| **Model registry table + artifact directory versioning** | Track model versions, metrics, promotion state | Extends existing model-artifact storage, no new infra class |
| **Notification service (email via SMTP/provider API + in-app table)** | Deliver investigator/supervisor alerts | Standard, low-risk addition |
| **Rate-limiting middleware (e.g., `slowapi`)** | Protect public endpoints | Drop-in FastAPI middleware |
| **TOTP 2FA library (e.g., `pyotp`)** | Admin account 2FA | Standard, well-supported library |

No new frontend framework, no new backend language, and no unproven infrastructure is introduced — all additions are incremental to the existing stack.

---

## 4. Data Model (High-Level)

### 4.1 Existing Core Entities (inferred from current API surface)
- **User** — id, email, hashed_password, role, created_at
- **Claim** — id, submitted_by, patient_ref, provider_ref, procedure_code(s), billed_amount, document_ref, status, created_at, updated_at
- **ClaimDocument** — id, claim_id, file_path, ocr_text, ocr_confidence
- **ModelScore** — id, claim_id, model_type (xgboost / isolation_forest), score, generated_at
- **DuplicateMatch** — id, claim_id, matched_claim_id, similarity_score, method
- **GraphRelationship** — entities and edges among patients/providers/hospitals (NetworkX-derived, persisted or computed on demand)
- **ShapExplanation** — id, claim_id, feature, contribution_value
- **InvestigationNote** — id, claim_id, author_id, note_text, created_at
- **AuditLog** — id, actor_id, action, entity_type, entity_id, timestamp, metadata
- **Report** — id, claim_id, generated_by, file_path, generated_at

### 4.2 New Entities Required for Feasible Feature Set

| New Table | Purpose | Related Feature |
|---|---|---|
| `provider_risk_profile` | provider_id, rolling_risk_score, verified_outcomes_count, last_computed_at | Provider Risk Profiles |
| `cost_benchmark` | procedure_code, region, provider_id (nullable), median, p25, p75, iqr, sample_size, confidence, computed_at | Cost Benchmark Engine |
| `procedure_validation_flag` | claim_id, code, flag_type, description | Procedure & Code Validation |
| `claim_embedding` | claim_id, embedding vector (pgvector), model_version | Semantic Similarity |
| `risk_aggregate` | claim_id, fraud_score, anomaly_score, duplicate_score, graph_score, cost_score, provider_score, aggregate_score, weighting_version | Risk Aggregation Engine |
| `model_registry` | model_id, model_type, version, metrics_json, status (candidate/active/retired), created_at, promoted_at | Model Versioning |
| `drift_report` | model_id, feature_or_prediction, drift_metric, value, threshold, flagged, computed_at | Drift Monitoring |
| `case_assignment` | claim_id, investigator_id, assigned_by, assigned_at, sla_due_at | Case Assignment |
| `notification` | id, recipient_id, type, payload, read_at, created_at | Notifications |
| `risk_threshold_config` | risk_band, lower_bound, upper_bound, updated_by, updated_at | Configurable Thresholds |

---

## 5. API Specification

### 5.1 Current API Surface (Implemented)

**Authentication**
```
POST /auth/register
POST /auth/login
```

**Claims**
```
POST /claims/upload
GET  /claims
GET  /claims/{id}
POST /claims/{id}/notes
POST /claims/{id}/status
```

**Reports**
```
GET /reports/pdf/{id}
```

**Analytics & Admin**
```
GET /dashboard/analytics
GET /admin/model-metrics
GET /admin/audit-logs
```

**Development Diagnostic** *(to be relocated out of the production service — see §8.4)*
```
GET /mcp/check
```

### 5.2 New Endpoints — Feasible Feature Set

**Cost Benchmarking**
```
GET /analytics/cost-benchmark?procedure_code=&provider_id=&region=
```

**Provider Risk**
```
GET /providers/{id}/risk-profile
GET /admin/providers/risk-profiles          # bulk view
```

**Procedure Validation**
```
GET /claims/{id}/procedure-validation
```

**Similarity Search**
```
GET /claims/{id}/similar?method=hybrid|fuzzy|semantic
```

**Risk Aggregation**
```
GET /claims/{id}/risk-aggregate
PUT /admin/risk-aggregate/weights           # configure aggregation weights
```

**Case Management**
```
POST /claims/{id}/assign
GET  /investigators/{id}/workload
GET  /claims/search?query=&status=&risk_band=&assigned_to=&date_from=&date_to=
POST /claims/bulk-upload
GET  /audit-logs/export?format=csv|pdf&from=&to=
```

**Notifications**
```
GET  /notifications
POST /notifications/{id}/read
```

**Model Operations**
```
GET  /admin/models
POST /admin/models/{id}/promote
POST /admin/models/{id}/rollback
GET  /admin/models/{id}/drift-report
GET  /admin/models/evaluation-report
```

**Security**
```
POST /auth/2fa/setup
POST /auth/2fa/verify
```

All new endpoints inherit the existing JWT + RBAC middleware and are subject to the new rate-limiting middleware (§8.3).

---

## 6. ML / AI Component Specifications

### 6.1 Existing Components

| Component | Input | Output | Notes |
|---|---|---|---|
| XGBoost Fraud Scorer | Structured claim features | Fraud-risk probability | Supervised; trained offline, inference only at request time |
| Isolation Forest | Structured claim features | Anomaly score | Unsupervised; flags statistical outliers |
| SHAP | Trained model + feature vector | Per-feature contribution values | Applied to XGBoost output for transparency |
| RapidFuzz | Claim text fields | Similarity score vs. historical claims | Token/edit-distance based fuzzy matching |
| NetworkX | Entities (patient, provider, hospital) + relations | Graph metrics (e.g., centrality, shared-entity clusters) | Computed from claim-derived relationship data |
| Gemini LLM Helper | Structured claim data, OCR text, risk indicators, SHAP output | Natural-language investigator summary | Optional; requires `GEMINI_API_KEY`; assistive only |

### 6.2 New Components

**Cost Benchmark Engine**
- Computes median, P25, P75, IQR per (procedure, provider, region) tuple.
- Hierarchical fallback order: procedure+provider+region → procedure+region → procedure only.
- Confidence derived from sample size at the level used.

**Provider Risk Profile Builder**
- Rolling aggregation job (scheduled) over verified investigation outcomes.
- **Leakage-safety rule:** only outcomes finalized *before* the timestamp of the claim being scored are included in that claim's provider-risk feature.

**Procedure & Code Validator**
- Rule-based checks: code format/validity against a reference code list; description-to-code consistency (string/semantic check); frequency-based flag for statistically rare code combinations.

**Semantic Similarity Service**
- Generates an embedding per claim's normalized text (OCR + structured fields) using a lightweight embedding model.
- Stores vector in `claim_embedding` (pgvector).
- Hybrid score = weighted combination of RapidFuzz score and cosine similarity from pgvector nearest-neighbor query.

**Risk Aggregation Engine**
- Normalizes each component signal (fraud, anomaly, duplicate, graph, cost, provider) to a common 0–1 scale.
- Combines via configurable weighted sum (default weights defined at launch); weights stored in `risk_aggregate.weighting_version` for auditability.
- Aggregation logic and weights must be documented and versioned — this directly resolves the current limitation of an undocumented aggregation strategy.

**Model Registry & Drift Monitor**
- Every trained model version is logged with evaluation metrics before promotion.
- Drift monitor computes distributional distance (e.g., population stability index or similar) between recent live feature/prediction distributions and the training baseline; flags when threshold exceeded.
- Promotion/rollback are explicit, logged admin actions (never automatic).

---

## 7. End-to-End Technical Workflow (Updated)

1. Officer authenticates (JWT) and submits claim + document(s) — single or bulk.
2. Backend persists claim and document(s); triggers OCR worker.
3. OCR extracts text (EasyOCR → pytesseract fallback); structured metadata parsed where supported.
4. Parallel signal generation:
   - XGBoost fraud score
   - Isolation Forest anomaly score
   - RapidFuzz + semantic embedding similarity (hybrid duplicate score)
   - NetworkX relationship signal
   - Cost benchmark deviation
   - Provider risk profile lookup
   - Procedure/code validation flags
5. SHAP explanation generated for the XGBoost output.
6. Risk Aggregation Engine normalizes and combines all signals into one documented aggregate score and risk band.
7. Claim appears in dashboard/investigation queue, optionally auto-assigned per case-assignment rules; notification sent to assigned investigator.
8. Investigator reviews evidence, scores, SHAP explanation, similarity matches, and optional Gemini summary.
9. Investigator adds notes and updates status (human decision required — no automatic status change).
10. Audit log entry recorded for every read/write action of consequence.
11. PDF/CSV report generated on demand or on case closure.
12. Dashboard and admin model-health view reflect updated operational and model metrics.
13. Scheduled jobs periodically recompute provider risk, cost benchmarks, and drift reports.

---

## 8. Non-Functional / Cross-Cutting Requirements

### 8.1 Security
- JWT auth with short-lived access tokens and refresh flow.
- RBAC roles: Officer, Investigator, Supervisor, Auditor, Admin — enforced at route level.
- TOTP-based 2FA required for Admin role.
- All file uploads validated for type/size before OCR processing.
- Audit logging is append-only and covers authentication events, claim access, status changes, note additions, report generation, and admin/model actions.

### 8.2 Performance
- Claim upload acknowledgment target: low-second response.
- Full risk pipeline (OCR + ML + graph + aggregation) should complete within a documented bounded window; long-running steps (OCR, graph analysis) execute asynchronously via the existing worker pattern, with claim status reflecting "processing" until complete.

### 8.3 Reliability & Resilience
- If OCR fails, claim is saved with a "pending OCR" flag rather than blocking submission.
- If Gemini API is unavailable or unconfigured, the LLM summary panel degrades gracefully (hidden or shows a clear "unavailable" state) — Gemini is never a blocking dependency.
- Rate limiting (`slowapi` or equivalent) applied to upload and public-facing endpoints to prevent abuse.

### 8.4 Environment Separation
- `/mcp/check` and any editor/MCP diagnostic tooling must be moved to a separate internal/dev-only service or disabled by default in production builds, so the production fraud-processing service exposes only product-relevant endpoints.

### 8.5 Observability
- Structured logging across backend services.
- Admin model-health dashboard surfaces: active model version, last evaluation metrics, drift status, last retrain date.
- Alerting (via the new notification service) on drift threshold breach and SLA-at-risk cases.

---

## 9. Testing Strategy

| Layer | Approach |
|---|---|
| Unit | Backend services (OCR parsing, scoring functions, aggregation math, cost benchmark statistics) |
| Integration | API contract tests for all endpoints (existing + new), including auth/RBAC enforcement |
| ML Evaluation | Offline evaluation harness against real/anonymized public datasets; precision/recall/AUC reporting per model version |
| Regression | Model registry candidate comparison against currently active model before promotion |
| Frontend | Component tests for dashboard, submission, and investigation views; end-to-end flow tests for the full claim lifecycle |
| Security | RBAC boundary tests, 2FA flow tests, rate-limit enforcement tests |

---

## 10. Phased Technical Implementation Plan

| Phase | Engineering Scope |
|---|---|
| **Phase 1** | `cost_benchmark` table, benchmark computation job, `/analytics/cost-benchmark` endpoint |
| **Phase 2** | `provider_risk_profile` table, leakage-safe rolling aggregation job, `/providers/{id}/risk-profile` |
| **Phase 3** | `procedure_validation_flag` table, validation rule engine, `/claims/{id}/procedure-validation` |
| **Phase 4** | pgvector setup, embedding generation service, `claim_embedding` table, hybrid similarity endpoint |
| **Phase 5** | `risk_aggregate` table, aggregation engine, admin weight-configuration endpoint |
| **Phase 6** | Public/anonymized dataset adapters, evaluation report generator |
| **Phase 7** | `model_registry` table, versioning + promotion/rollback endpoints and admin controls |
| **Phase 8** | Drift computation job, `drift_report` table, admin model-health dashboard (frontend) |
| **Phase 9** | `case_assignment`, `notification` tables; assignment, workload, search, bulk-upload, audit-export endpoints |
| **Phase 10** | RBAC role expansion, 2FA (`pyotp`), rate-limiting middleware, relocation of `/mcp/check` out of production service |
| **Phase 11** | Frontend integration: cost/provider/procedure/similarity panels, model-health dashboard, notifications UI, case assignment UI |

---

## 11. Key Files (Current Codebase Reference)

**Frontend**
```
frontend/src/pages/Dashboard.jsx
frontend/src/components/DashboardSidebar.jsx
frontend/src/components/MetricsCards.jsx
frontend/src/components/RiskChart.jsx
frontend/src/components/LLMSummary.jsx
frontend/src/components/ErrorBoundary.jsx
frontend/src/pages/ClaimSubmission.jsx
frontend/src/pages/InvestigationPanel.jsx
```

**Backend**
```
backend/app/main.py
backend/app/mcp/router.py
backend/app/config.py
backend/app/claims/router.py
backend/app/ocr/service.py
backend/app/ocr/worker.py
backend/app/utils/llm_helper.py
```

---

## 12. Open Technical Questions

- What is the target sample-size threshold below which the cost-benchmark hierarchical fallback should trigger?
- Which embedding model best balances accuracy vs. latency for semantic similarity given expected claim-text length?
- What SLA windows should drive case-assignment notifications (per risk band)?
- What drift metric (e.g., PSI vs. KL-divergence) and threshold should trigger a retrain alert?
- What retention policy applies to audit logs and generated reports for compliance purposes?
