import json

with open('inputs/base_case.json') as f:
    bc = json.load(f)

print("Number of scenarios in json:", len(bc['scenarios']))
for idx, sc in enumerate(bc['scenarios']):
    print(f"Scenario {idx + 1}:")
    for k, v in sc.items():
        print(f"  {k}: len={len(v)}, first 2={v[:2]}")
