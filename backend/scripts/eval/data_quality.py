import pandas as pd
import json

df = pd.read_csv("data/synthetic_claims.csv")

quality_report = {
    "total_rows": len(df),
    "columns": list(df.columns),
    "missing": df.isnull().sum().to_dict(),
    "unique": df.nunique().to_dict(),
    "label_distribution": df['is_fraud'].value_counts(normalize=True).to_dict()
}

# Check negatives or zeros
quality_report["zero_or_negative_amounts"] = int((df['billed_amount'] <= 0).sum())

with open("quality_report_out.json", "w") as f:
    json.dump(quality_report, f)
