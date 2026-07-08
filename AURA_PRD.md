# AURA — Product Requirements Document (PRD)

**Product:** AURA (Automated Risk & Audit Analyzer)
**Category:** Healthcare Claim Fraud Detection & Investigation Platform
**Document Version:** 1.0 (Final)
**Status:** Approved for Planning
**Owner:** Product Team

---

## 1. Executive Summary

AURA is an end-to-end healthcare claim fraud detection and investigation platform that combines document intelligence (OCR), supervised and unsupervised machine learning, explainable AI, fuzzy duplicate detection, graph relationship analysis, generative AI summarization, and a human-in-the-loop investigation workflow.

The platform currently provides a working full-stack foundation (React + FastAPI) covering claim submission, OCR extraction, risk scoring, explainability, investigation, audit logging, and PDF reporting. This PRD documents the current product as-built, and defines a prioritized set of **feasible, realistic enhancements** that extend AURA toward a production-grade fraud intelligence platform — without introducing speculative or unrelated technology.

AURA is explicitly positioned as a **decision-support system**: model outputs (risk scores, anomalies, duplicate signals, relationship flags) are investigation triggers, not automatic fraud determinations. Final decisions remain with authorized human investigators.

---

## 2. Product Vision

To give insurance and healthcare payer teams a single, traceable workspace where a claim moves from **upload → extraction → multi-signal risk analysis → explanation → human investigation → decision → audit → report** — replacing manual, single-signal screening with a defensible, evidence-linked process that reduces investigator workload while improving detection consistency.

---

## 3. Problem Statement

Healthcare claim review today is difficult because:

- Evidence commonly arrives as scanned invoices, images, and PDFs rather than structured data.
- Manually entered claim values may not match what the supporting document actually states.
- Fraudulent or erroneous claims often resemble prior submissions in ways that are hard to spot manually.
- Unusual billing behavior is only visible with historical/contextual comparison, which is impractical to do by hand.
- Traditional ML fraud scores are often black-box, making them hard for investigators and auditors to trust or defend.

AURA addresses this with a traceable pipeline that keeps every step — extraction, scoring, explanation, and human judgment — visible and auditable.

---

## 4. Target Users / Personas

| Persona | Role | Primary Needs |
|---|---|---|
| **Claims Officer** | Submits claims and supporting documents | Fast, simple submission; clear confirmation of receipt |
| **Fraud Investigator** | Reviews flagged claims | Consolidated evidence, explainable risk signals, ability to annotate and decide |
| **Investigation Supervisor** | Oversees case load | Workload visibility, case assignment, escalation tracking |
| **Compliance / Auditor** | Reviews closed cases | Full audit trail, exportable reports, defensible decision history |
| **System Administrator** | Manages platform | User/role management, model health visibility, configuration |

---

## 5. Current Product Scope (Implemented)

### 5.1 Core Workflow
1. Authenticated officer submits a claim with a supporting proof document.
2. Backend stores the claim and file.
3. OCR (EasyOCR, pytesseract fallback) extracts text from the document.
4. Extracted text is converted to structured metadata where supported.
5. Manual vs. OCR-extracted values can be checked for discrepancies.
6. XGBoost produces a supervised fraud-risk score.
7. Isolation Forest produces an unsupervised anomaly signal.
8. RapidFuzz checks for fuzzy/near-duplicate claims.
9. NetworkX evaluates entity relationships (patients, doctors, hospitals).
10. SHAP explains feature-level contributions to the model output.
11. Results surface in the investigation workflow.
12. Investigators review evidence, scores, and explanations; add notes.
13. Authorized users update claim status.
14. All activity is logged to an audit trail.
15. PDF audit reports can be generated on demand.
16. Dashboard analytics summarize operational and risk trends.

### 5.2 Implemented Frontend Features
- Analytics dashboard (metric cards, risk trend chart, AI summary panel)
- Dark sidebar navigation
- Claim submission form with mandatory proof-file upload
- Investigation panel (claim detail, status actions, redirect behavior)
- Error boundary for safer runtime behavior
- Authenticated, protected routing throughout the app

### 5.3 Implemented Backend Features
- JWT-based authentication and role-based access control
- Claim routes: upload, list, retrieve, notes, status change
- OCR service and background worker
- Gemini-based LLM summary helper (active when API key configured)
- Analytics API for dashboard data
- Admin APIs for model metrics and audit logs
- PDF report generation (ReportLab)

### 5.4 Current Product Strengths
- Complete full-stack workflow, not a standalone model notebook
- Multiple complementary analytical signals (supervised, unsupervised, duplicate, graph)
- Human-in-the-loop investigation with notes and audit logging
- Explainability built in via SHAP
- Generative AI used as an assistive summarization layer, not a decision engine

### 5.5 Current Known Limitations
- Development and testing rely on synthetic seeded claim data; no real-data evaluation yet
- No dedicated cost-benchmarking engine
- No dynamic provider risk profiling
- No procedure/code-level validation beyond raw extraction
- No semantic (embedding-based) claim similarity — duplicate detection is fuzzy-text only
- No formal model versioning, promotion, or rollback process
- No model drift monitoring
- No explicitly documented strategy for aggregating fraud, anomaly, duplicate, and graph signals into one prioritized risk view
- MCP developer diagnostics (`/mcp/check`) exist in the backend but are development tooling, not a product feature, and should not ship in the production fraud-processing service

---

## 6. New Feature Additions (Feasible & Realistic)

The features below are assessed as **buildable with the current stack** (React/FastAPI/PostgreSQL/XGBoost/SHAP/NetworkX/RapidFuzz) and are natural extensions of the existing architecture — no unproven or unrelated technology is introduced. They are grouped by theme and prioritized.

### 6.1 Risk Intelligence Enhancements

| Feature | Description | Why Feasible |
|---|---|---|
| **Smart Cost Benchmark Engine** | Flags claims whose billed cost deviates from expected cost using median, P25/P75, IQR bands, with hierarchical fallback (procedure → provider → region) when data is sparse | Pure statistics over existing claim data already in PostgreSQL |
| **Provider Risk Profiles** | Rolling, leakage-safe risk score per provider based on historical verified outcomes (upheld vs. overturned investigations) | Reuses existing claim/investigation history; no new data source needed |
| **Procedure & Code Validation** | Validates procedure/diagnosis codes for format validity, description consistency, and flags statistically unusual code combinations | Rule-based + frequency analysis on existing structured claim fields |
| **Hybrid Claim Similarity Search** | Combines existing RapidFuzz fuzzy matching with semantic embedding similarity (pgvector on PostgreSQL) to catch paraphrased or reworded duplicate claims | PostgreSQL already in stack; pgvector is a standard, low-risk extension |
| **Explicit Risk Aggregation Engine** | Normalizes and combines fraud score, anomaly score, duplicate signal, graph signal, and (new) cost/provider signals into one documented, configurable priority score | Formalizes logic that is currently implicit; no new infrastructure |

### 6.2 Investigation & Case Management

| Feature | Description | Why Feasible |
|---|---|---|
| **Case Assignment & Workload View** | Supervisors assign flagged claims to specific investigators; dashboard shows per-investigator open case load | Extends existing role model and claim status schema |
| **Advanced Search & Filtering** | Filter/search claims by provider, patient, date range, risk band, status, and assigned investigator | Standard query-layer addition on existing claims table |
| **Bulk Claim Upload** | Allow officers to submit multiple claims/documents in one batch (e.g., CSV manifest + document set) | Extension of existing single-claim upload endpoint |
| **Side-by-Side Duplicate Comparison View** | UI to visually compare a claim against its top fuzzy/semantic matches | Presentation layer on top of existing RapidFuzz output |
| **In-App & Email Notifications** | Notify investigators/supervisors when a new high-risk claim is assigned or an SLA is at risk | Standard notification service; no new ML needed |
| **Audit Trail Export (CSV/PDF)** | Export full audit history for a claim or date range for compliance review | Extension of existing audit-log and PDF reporting components |

### 6.3 Model Operations (MLOps)

| Feature | Description | Why Feasible |
|---|---|---|
| **Real-Data Evaluation Harness** | Adapters to run AURA's pipeline against public/anonymized healthcare claims datasets and produce transparent precision/recall reports | Uses existing model pipeline; adds evaluation scripts and reporting |
| **Model Versioning & Registry** | Store model artifacts with version metadata, enable candidate comparison before promotion | Standard MLOps pattern; storage already exists for model artifacts |
| **Controlled Promotion & Rollback** | Admin-controlled promotion of a new model version to production with rollback to prior version | Builds directly on model versioning above |
| **Model Drift Monitoring** | Track feature and prediction distribution drift over time; alert when retraining is warranted | Statistical monitoring on already-logged prediction data |
| **Admin Model-Health Dashboard** | Surface model version, evaluation metrics, and drift status to admins | Frontend addition consuming existing/extended admin APIs |
| **Configurable Risk Thresholds** | Allow admins to tune risk-band thresholds without a code deployment | Simple config table + admin UI |

### 6.4 Platform & Security Hardening

| Feature | Description | Why Feasible |
|---|---|---|
| **Expanded Role-Based Access Control** | Formalize distinct roles (Officer, Investigator, Supervisor, Auditor, Admin) with scoped permissions | Extension of existing JWT/RBAC foundation |
| **Two-Factor Authentication for Admin Accounts** | Adds TOTP-based 2FA for elevated-privilege accounts | Standard, well-supported addition to existing auth flow |
| **API Rate Limiting & Throttling** | Protects upload and analytics endpoints from abuse | Standard FastAPI middleware addition |
| **Separation of Developer Diagnostics** | Move `/mcp/check` and similar tooling out of the production fraud-processing service into a separate internal/dev-only service | Reduces production attack surface; no functional change to fraud pipeline |

> Explicitly excluded as *not* feasible/realistic for this roadmap: fully autonomous auto-adjudication of claims without human review, and any feature that would let AI-generated summaries directly change claim status without investigator action. These are excluded to preserve the human-in-the-loop, decision-support design principle.

---

## 7. Non-Functional Requirements

| Category | Requirement |
|---|---|
| **Reliability** | Core claim submission and investigation workflows must degrade gracefully if OCR, LLM, or graph services are unavailable (claim still saved, flagged for reprocessing) |
| **Security** | JWT auth, hashed passwords, RBAC, audit logging of all status changes and data access to sensitive claim data |
| **Traceability** | Every risk score must be traceable to its inputs and, where applicable, its SHAP explanation |
| **Performance** | Claim upload + OCR acknowledgment within a few seconds under normal load; full risk pipeline result available within a bounded, documented time window |
| **Auditability** | All investigator actions (notes, status changes, report generation) must be immutable in the audit log |
| **Extensibility** | New risk signals (cost, provider, procedure) must plug into the aggregation engine without rewriting existing models |
| **Data Privacy** | Claim and patient data access restricted by role; export/reporting actions logged |

---

## 8. Success Metrics (KPIs)

- **Investigation efficiency:** average time from claim submission to investigator decision
- **Signal usefulness:** proportion of high-aggregate-risk claims confirmed as fraud/error after investigation (precision of the risk ranking)
- **Duplicate catch rate:** confirmed duplicates detected by fuzzy + semantic matching vs. missed
- **Model health:** frequency and magnitude of detected drift; time-to-retrain after drift alert
- **Auditability:** percentage of closed cases with a complete, exportable audit trail
- **Adoption:** percentage of flagged claims actioned by investigators within SLA

---

## 9. Roadmap (Phased)

| Phase | Theme | Key Deliverables |
|---|---|---|
| **Phase 1** | Cost Intelligence | Smart Cost Benchmark Engine |
| **Phase 2** | Provider Intelligence | Provider Risk Profiles |
| **Phase 3** | Coding Integrity | Procedure & Code Validation |
| **Phase 4** | Similarity | Hybrid (fuzzy + semantic) Claim Similarity Search |
| **Phase 5** | Decisioning | Explicit Risk Aggregation Engine, Configurable Thresholds |
| **Phase 6** | Evaluation | Real public/anonymized dataset adapters, transparent evaluation reports |
| **Phase 7** | MLOps Foundations | Model versioning, candidate comparison, promotion, rollback |
| **Phase 8** | MLOps Monitoring | Drift monitoring, admin model-health dashboard |
| **Phase 9** | Case Management | Case assignment, workload view, notifications, bulk upload, advanced search |
| **Phase 10** | Platform Hardening | Expanded RBAC, 2FA for admins, rate limiting, dev-tooling separation |
| **Phase 11** | Frontend Integration | Surface all of the above (cost, provider, procedure, similarity, model ops) in the dashboard and investigation UI |

---

## 10. Risks & Assumptions

- **Data availability:** Provider risk and cost benchmarking require sufficient historical claim volume per provider/procedure to be statistically meaningful; sparse categories fall back hierarchically.
- **Leakage risk:** Provider risk features must be constructed using only information available *before* the outcome of the case being scored, to avoid target leakage.
- **LLM dependency:** Gemini-based summaries are optional and gated by API key configuration; the platform must remain fully functional without them.
- **Regulatory scope:** Handling of healthcare claim data implies data-privacy obligations; specific regulatory requirements (e.g., HIPAA or local equivalents) are assumed to be addressed at the infrastructure/legal level and are out of scope for this PRD.

---

## 11. Out of Scope

- Fully autonomous claim adjudication without human review
- Payment processing or claim disbursement
- Direct integration with external insurance core systems (assumed to be a future, separate integration project)
- Mobile native applications (current scope is responsive web only)

---

## 12. Interview-Style Summary

AURA is a full-stack healthcare claim fraud investigation platform. A claim and supporting document are submitted through a React interface; FastAPI manages the workflow and OCR extracts invoice information using EasyOCR with a Tesseract fallback. The claim is analyzed using XGBoost for supervised fraud risk, Isolation Forest for anomaly detection, RapidFuzz for duplicate patterns, and NetworkX for relationship analysis. SHAP explains the model prediction, while Gemini converts structured evidence into an investigator-friendly summary. Officers review claims, add notes, update status, and generate PDF audit reports. The dashboard provides operational metrics and risk trends. The system is decision support: a high score or anomaly alone is never treated as proof of fraud.
