# AURA Screenshot Checklist

To make the GitHub repository visually impressive and credible, please capture the following screenshots and save them in the `docs/screenshots/` directory (create the directory if it doesn't exist).

Ensure you use a consistent browser window size (e.g., 1440x900) and consider using a modern dark mode theme if supported.

- [ ] **`dashboard.png`**
  - **What to show**: The main analytics dashboard.
  - **Focus**: Key metrics, charts showing risk distribution, and overall platform health.

- [ ] **`claim_submission.png`**
  - **What to show**: The single claim upload or manual entry form.
  - **Focus**: The UI where OCR or manual data entry occurs.

- [ ] **`bulk_upload.png`**
  - **What to show**: The bulk upload interface (e.g., uploading a CSV/PDF batch).
  - **Focus**: Progress bars or status indicators of bulk processing.

- [ ] **`claims_register.png`**
  - **What to show**: The paginated list/table of all claims.
  - **Focus**: Columns showing Claim ID, Provider, Status, and Risk Score. Show a mix of high and low-risk claims.

- [ ] **`investigation_panel.png`**
  - **What to show**: The detailed view of a single high-risk claim.
  - **Focus**: The split view showing claim details alongside the ML investigation tools.

- [ ] **`shap_explanation.png`**
  - **What to show**: The SHAP waterfall or bar chart section inside the investigation panel.
  - **Focus**: Clear visibility of how specific features pushed the fraud probability up or down.

- [ ] **`cost_benchmarks.png`**
  - **What to show**: The Cost Benchmark Engine UI.
  - **Focus**: A chart or table showing how a specific claim's procedure cost compares to historical interquartile ranges (IQR).

- [ ] **`provider_profile.png`**
  - **What to show**: A specific provider's risk profile page.
  - **Focus**: Overall provider risk score, historical claim volume, and flags for suspicious billing behavior.

- [ ] **`duplicate_detection.png`**
  - **What to show**: The duplicate detection modal or section on a claim.
  - **Focus**: Showing matched historical claims and similarity percentages (Hybrid/Semantic similarity modes).

- [ ] **`risk_aggregate_engine.png`** (Optional but recommended)
  - **What to show**: The breakdown of the Aggregate Risk Score.
  - **Focus**: Visual representation of the weighted components (Fraud + Anomaly + Graph + Duplicate + Cost).
