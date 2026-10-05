import json

with open('inputs/base_case.json') as f:
    data = json.load(f)

for k, v in data.items():
    if isinstance(v, dict):
        print(f"{k}: dict with keys {list(v.keys())}")
    elif isinstance(v, list):
        print(f"{k}: list of length {len(v)}: first item {v[0]}")
    else:
        print(f"{k}: {v}")
