import os

print("Files in inputs:", os.listdir('inputs'))
with open('inputs/base_case.json') as f:
    print("base_case.json content keys:")
    import json
    data = json.load(f)
    for k, v in data.items():
        if isinstance(v, list):
            print(f"  {k}: list of len {len(v)}")
        elif isinstance(v, dict):
            print(f"  {k}: dict with keys {list(v.keys())}")
        else:
            print(f"  {k}: {v}")
