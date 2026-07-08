import os

with open('app/routers/claims.py', 'r') as f:
    lines = f.readlines()

search_start = -1
search_end = -1
bulk_start = -1
for i, line in enumerate(lines):
    if line.startswith('@router.get("/search")'):
        search_start = i
    if line.startswith('@router.post("/bulk-upload")'):
        bulk_start = i
        search_end = i

search_code = lines[search_start:search_end]
bulk_code = lines[bulk_start:]
rest_code = lines[:search_start]

# We need to insert search_code BEFORE get_claim
get_claim_idx = -1
for i, line in enumerate(rest_code):
    if line.startswith('@router.get("/{claim_id}")'):
        get_claim_idx = i
        break

new_lines = rest_code[:get_claim_idx] + search_code + rest_code[get_claim_idx:] + bulk_code

with open('app/routers/claims.py', 'w') as f:
    f.writelines(new_lines)
