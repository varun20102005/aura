import os
import glob

test_files = glob.glob('tests/test_*.py')

for f in test_files:
    with open(f, 'r') as file:
        content = file.read()
    
    if "Base.metadata.create_all(bind=engine)" in content:
        content = content.replace(
            "Base.metadata.create_all(bind=engine)",
            "tables = [t for t in Base.metadata.sorted_tables if t.name != 'claim_embeddings']\n    Base.metadata.create_all(bind=engine, tables=tables)"
        )
    
    if "Base.metadata.drop_all(bind=engine)" in content:
        content = content.replace(
            "Base.metadata.drop_all(bind=engine)",
            "tables = [t for t in Base.metadata.sorted_tables if t.name != 'claim_embeddings']\n    Base.metadata.drop_all(bind=engine, tables=tables)"
        )
        
    with open(f, 'w') as file:
        file.write(content)

print("Fixed create_all in tests")
