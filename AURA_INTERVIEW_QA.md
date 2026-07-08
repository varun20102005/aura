# AURA Interview Q&A

This document contains expected interview questions regarding the architecture, ML decisions, and engineering trade-offs made in the AURA platform, along with technically accurate answers based on the actual implementation.

---

### **1. Why did you build AURA?**
**Answer:** I built AURA to solve a specific problem in healthcare technology: the gap between black-box AI predictions and the operational needs of human fraud investigators. Traditional systems rely on rigid, easily bypassed rules. Pure AI systems often output a single probability score that investigators don't trust because it lacks context. AURA bridges this gap by using a multi-engine approach (supervised learning, anomaly detection, graph analysis) and surfacing the *reasoning* behind the scores using SHAP explainability. It serves as a comprehensive demonstration of my skills in Full-Stack Engineering, System Architecture, and MLOps.

### **2. Why did you choose XGBoost for the primary fraud prediction?**
**Answer:** XGBoost was chosen because it performs exceptionally well on tabular, structured data—which is exactly what healthcare claims are (billing codes, provider IDs, amounts). Unlike deep learning models, tree-based models like XGBoost handle missing data gracefully, are robust to non-linear relationships, and, most importantly, are easily interpretable using tree-based SHAP explainers. This interpretability is a hard requirement for an auditing platform.

### **3. Why include Isolation Forest in addition to XGBoost?**
**Answer:** XGBoost is a supervised model, meaning it is only as good as the historical fraud labels it was trained on. It struggles to detect *novel* or *zero-day* fraud schemes that haven't been seen before. Isolation Forest is an unsupervised anomaly detection algorithm. It isolates out-of-distribution data points. By running both, AURA catches known fraud patterns (XGBoost) while also flagging statistically bizarre claims that don't match historical norms (Isolation Forest).

### **4. How does SHAP work in your project?**
**Answer:** After XGBoost generates a fraud probability for a claim, the claim features are passed to a `shap.TreeExplainer`. SHAP calculates the marginal contribution of every single feature (e.g., `billed_amount`, `diagnosis_code_severity`) to that specific claim's final score. In the UI, this is visualized so the investigator can see exactly *why* a claim received an 85% risk score (e.g., "The score was pushed up by +20% because the procedure cost was unusually high for this specific zip code").

### **5. How do you avoid treating every expensive hospital bill as fraud?**
**Answer:** High cost alone does not equal fraud. AURA mitigates false positives using the **Cost Benchmark Engine** and the **Risk Aggregation Engine**. The benchmark engine evaluates the claim's cost against the interquartile range (IQR) for that specific procedure *by that specific provider* historically. Furthermore, the aggregation engine ensures that cost is only one component of the final score; if the provider has a stellar trust profile and there are no graph anomalies, the high cost alone won't trigger a severe fraud alert.

### **6. How does provider-aware cost benchmarking work?**
**Answer:** The system dynamically queries historical claims matching the incoming claim's `procedure_code` and `provider_id`. It calculates the 25th (Q1) and 75th (Q3) percentiles to establish an Interquartile Range (IQR). If the incoming claim's billed amount exceeds a threshold (e.g., `Q3 + 1.5 * IQR`), it is flagged as a cost anomaly. This ensures a specialized surgeon isn't flagged simply because they charge more than a general practitioner.

### **7. Why use PostgreSQL instead of only MongoDB?**
**Answer:** Healthcare claims, provider profiles, and risk scores are highly relational data with strict schema requirements. We need ACID compliance to ensure that when a claim status is updated by an investigator, the audit trail is perfectly consistent. Furthermore, PostgreSQL allows us to use the `pgvector` extension, enabling us to store and query high-dimensional embeddings for semantic duplicate detection directly alongside our relational data, removing the need to manage a separate vector database stack.

### **8. Where would a vector database fit?**
**Answer:** We are essentially using PostgreSQL as our vector database via the `pgvector` extension. When a claim's text fields (like clinical notes) are ingested, a `SentenceTransformer` (MiniLM) generates a dense vector embedding. This embedding is stored in a `VECTOR` column in Postgres. We can then perform Cosine Similarity searches directly via SQLAlchemy to find semantically similar historical claims. If the system scaled to hundreds of millions of records, we might migrate this specific workload to a dedicated distributed vector database like Pinecone or Milvus.

### **9. How does semantic duplicate detection differ from fuzzy matching?**
**Answer:** Fuzzy matching (using RapidFuzz in AURA) relies on string edit distance (Levenshtein distance). It detects if a fraudster submitted "Treatmt for leg" instead of "Treatment for leg". Semantic matching (using vector embeddings) goes further—it understands *meaning*. It can detect that "Patient presented with lower extremity fracture" is a duplicate of "Broken leg treated in ER," even though they share almost no exact words. AURA implements a Hybrid approach, using both.

### **10. How does graph analysis detect suspicious relationships?**
**Answer:** Using `NetworkX`, AURA models entities (Providers, Patients, Clinics) as nodes and transactions (Claims) as edges. By analyzing this graph structure, we can detect suspicious topologies, such as a "star pattern" where multiple seemingly unrelated patients all suddenly submit high-value claims to a single new provider within a 24-hour window. This detects coordinated fraud rings that look completely normal when viewed as isolated individual claims.

### **11. How are multiple risk signals combined?**
**Answer:** The **Risk Aggregation Engine** normalizes all incoming scores (XGBoost probability, IsoForest anomaly score, Duplicate similarity percentage, Cost deviation, Graph risk) to a standard 0-100 scale. It then applies a configurable weighting matrix (e.g., ML Fraud = 40%, Duplicates = 20%, Provider Risk = 15%, etc.) to compute a single `Aggregate Risk Score`.

### **12. How does new claim data affect XGBoost? Why should the model not retrain after every new claim?**
**Answer:** New claims are strictly used for inference (scoring) and are saved to the database. The XGBoost model does *not* retrain immediately. Retraining on every claim is computationally disastrous and opens the system to "Data Poisoning" (where a fraudster intentionally submits normal-looking fraud to slowly shift the model's baseline). Instead, AURA assumes a batch-retraining MLOps lifecycle where the model is evaluated periodically (e.g., monthly) against verified, audited claims before being promoted to production.

### **13. What are the limitations of synthetic data?**
**Answer:** Because AURA was trained heavily on synthetic data for portfolio purposes, the model predictions are not clinically validated. Real healthcare data contains immense noise, coding errors, and regional legislative biases that synthetic data fails to capture perfectly. While the *architecture* and *ML pipeline design* are production-grade, the specific model weights would need retraining on millions of real payer records to be used in a live insurance setting.

### **14. How would you scale the project? What would you change for real production use?**
**Answer:**
1.  **Extract Background Tasks**: I would move the Heavy ML processing (Graph traversals, embedding generation) out of FastAPI's background tasks and into a dedicated `Celery` worker cluster backed by `Redis` or `Kafka/RabbitMQ`.
2.  **Graph Database**: I would replace the in-memory `NetworkX` implementation with a dedicated graph database like `Neo4j` for real-time, multi-hop queries at massive scale.
3.  **Cloud Native Storage**: I would migrate local PDF and evidence uploads to AWS S3 / Google Cloud Storage.
4.  **Model Registry**: I would implement MLflow to track model versions, parameters, and A/B testing of the fraud algorithms rather than relying on local `joblib` files.
