import os
import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta

def generate_synthetic_data(num_records=5000):
    np.random.seed(42)
    random.seed(42)

    data = []
    providers = [f"PRV_{i:04d}" for i in range(100)]
    patients = [f"PAT_{i:05d}" for i in range(1000)]
    procedures = ["99213", "99214", "99284", "80053", "85025", "71045", "93000", "J3490", "E0601", "A0427"]

    # Base pricing for procedures
    base_prices = {
        "99213": 75.0, "99214": 110.0, "99284": 300.0, "80053": 15.0, 
        "85025": 10.0, "71045": 45.0, "93000": 25.0, "J3490": 50.0, 
        "E0601": 250.0, "A0427": 450.0
    }

    start_date = datetime(2025, 1, 1)

    for i in range(num_records):
        provider = random.choice(providers)
        patient = random.choice(patients)
        procedure = random.choice(procedures)
        
        # 5% chance of anomalous billing (fraud signal)
        is_fraud = np.random.rand() < 0.05
        
        base_amt = base_prices[procedure]
        if is_fraud:
            # High variation in billed amount
            billed_amount = base_amt * np.random.uniform(3.0, 10.0)
            # Sometimes impossible combinations (e.g. A0427 Ambulance with E0601 CPAP) - simplified here
        else:
            # Normal variation
            billed_amount = base_amt * np.random.uniform(0.9, 1.2)
            
        date = start_date + timedelta(days=random.randint(0, 365))

        data.append({
            "claim_id": f"CLM_{i:06d}",
            "patient_ref": patient,
            "provider_ref": provider,
            "procedure_code": procedure,
            "billed_amount": round(billed_amount, 2),
            "date": date.strftime("%Y-%m-%d"),
            "is_fraud": int(is_fraud)
        })

    df = pd.DataFrame(data)
    
    # Introduce duplicates (Fuzzy matching signal)
    # 2% of claims are near-duplicates
    num_dupes = int(num_records * 0.02)
    dupes = df.sample(num_dupes).copy()
    dupes['claim_id'] = [f"CLM_{(num_records + i):06d}" for i in range(num_dupes)]
    # Slight fuzzing of amount
    dupes['billed_amount'] = dupes['billed_amount'] * np.random.uniform(0.98, 1.02)
    dupes['billed_amount'] = dupes['billed_amount'].round(2)
    dupes['is_fraud'] = 1 # We consider these deliberate duplicates as fraud
    
    df = pd.concat([df, dupes], ignore_index=True)
    
    # Save dataset
    os.makedirs("data", exist_ok=True)
    df.to_csv("data/synthetic_claims.csv", index=False)
    print(f"Generated {len(df)} synthetic claims to data/synthetic_claims.csv")

if __name__ == "__main__":
    generate_synthetic_data()
