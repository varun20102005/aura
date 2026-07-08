# AURA Portfolio Summary

## 30-Second Project Explanation
AURA is an end-to-end healthcare claim fraud detection platform. Instead of relying on rigid rules, it uses a multi-engine AI approach—combining supervised XGBoost models, Isolation Forest anomalies, semantic duplicate detection, and graph relationships—to score claims. It provides a full UI for investigators to review these AI decisions with transparent SHAP explanations, ensuring trust in the system.

## 1-Minute Technical Explanation
AURA is a full-stack modular monolith built with a React/Vite frontend and a FastAPI backend, backed by PostgreSQL. The core innovation is its Risk Aggregation Engine. When a claim is ingested, it runs concurrently through multiple AI micro-services embedded within the backend: XGBoost predicts fraud probability based on structured patterns, Isolation Forest catches out-of-distribution billing, `MiniLM` embeddings and `RapidFuzz` catch semantic duplicates, and NetworkX graphs flag suspicious entity clusters. The results are aggregated into a single explainable score.

## 2-Minute Architecture Explanation
The system architecture prioritizes ML serving efficiency and workflow state management. 
- **Frontend Layer**: Built with React 19 and Vite. Uses Axios for data fetching and Chart.js/Recharts for rendering SHAP explanations and benchmark distributions.
- **API & Orchestration**: FastAPI manages authentication (JWT/RBAC) and claim ingestion (via REST). Heavy computational tasks (like OCR extraction and graph traversal) are offloaded to FastAPI `BackgroundTasks`.
- **Fraud Intelligence**: At inference time, trained models (persisted via `joblib`) are loaded into memory. We use an ensemble approach where no single model has the final say; an aggregation engine applies business weights to the outputs of the ML models, duplicate detectors, and provider risk profilers.
- **Data Layer**: Relies on PostgreSQL. We utilize `pgvector` for storing and retrieving document embeddings to catch semantic duplicates (e.g., catching identical clinical notes that were slightly reworded).
- **Deployment**: The entire stack is containerized using Docker and orchestrated with Docker Compose, featuring CI pipelines on GitHub Actions for automated testing.

## Top 5 Technical Challenges
1. **Explainable AI in Healthcare**: Providing a high "fraud score" isn't actionable for an auditor. Integrating SHAP (SHapley Additive exPlanations) to break down exactly which features (like high procedure cost or specific diagnosis codes) contributed to the XGBoost score was critical for user trust.
2. **Concurrency with Heavy ML**: Running 6 independent fraud checks (including CPU-intensive semantic embeddings and graph traversals) on a single FastAPI event loop required careful async design and background task isolation.
3. **Semantic vs. Exact Duplicates**: Fraudsters often bypass exact string matching by slightly modifying dates or text. Implementing a Hybrid Duplicate Detection engine that combined RapidFuzz (fuzzy matching) and SentenceTransformers (semantic meaning) solved this.
4. **Context-Aware Benchmarking**: An expensive procedure isn't necessarily fraudulent if it's normal for that specific provider. Building a dynamic Cost Benchmark Engine to calculate interquartile ranges (IQR) on the fly for specific providers was a challenging logic problem.
5. **Database Locking in Testing**: Migrating from SQLite to PostgreSQL was required because concurrent ML writes caused database locks in SQLite during load testing. Ensuring the SQLAlchemy ORM handled the transition cleanly with robust connection pooling was a key learning.

## Top 5 Engineering Decisions
1. **Modular Monolith over Microservices**: Kept the AI engines inside the FastAPI application to reduce network overhead and simplify deployment, deferring a Kubernetes/Microservice split until scaling requires it.
2. **PostgreSQL + pgvector**: Chose standard Postgres with the `pgvector` extension instead of adding a complex dedicated vector database (like Pinecone) to keep the infrastructure footprint small and maintain ACID compliance across claims and their embeddings.
3. **Risk Aggregation Pattern**: Decoupled the ML models from the final business logic. The ML models just emit raw probabilities; the Aggregation Engine applies the business weights.
4. **Stateless JWT Auth**: Used JWTs for fast, stateless authentication, passing RBAC (Role-Based Access Control) scopes in the token to protect administrative endpoints.
5. **Docker Compose for Developer Experience**: Packaged everything into a single `docker-compose up` command so recruiters or engineers can run the complex ML stack without configuring local Python/Node environments.

## Main AI/ML Concepts Demonstrated
- Supervised Classification (XGBoost) vs. Unsupervised Anomaly Detection (Isolation Forest).
- Feature Importance and Model Explainability (SHAP).
- Natural Language Processing & Vector Embeddings (SentenceTransformers).
- Graph Analysis (NetworkX).
- Handling imbalanced datasets (fraud vs. non-fraud) and evaluating beyond raw accuracy.

## Main Backend Concepts Demonstrated
- Asynchronous Python (FastAPI, async endpoints, background tasks).
- ORM design and migrations (SQLAlchemy + Alembic).
- Dependency Injection for database sessions and ML models.
- REST API design and structured validation (Pydantic).

## Main Database Concepts Demonstrated
- Relational schema design (1-to-N relationships between Providers, Claims, and Risk scores).
- Vector databases (using `pgvector` for similarity search).
- ACID compliance and session management.

## Main Security Concepts Demonstrated
- JWT Authentication and Role-Based Access Control (RBAC).
- Secure password hashing (bcrypt).
- Environment variable separation for secrets.
- Input validation (Pydantic preventing injection attacks).

## Main DevOps Concepts Demonstrated
- Containerization (Multi-stage Dockerfiles optimizing image size).
- Orchestration (Docker Compose networking Frontend, Backend, and DB).
- Continuous Integration (GitHub Actions pipeline running tests and builds).
- Dependency management and deterministic builds (`npm ci`, `requirements.txt`).
