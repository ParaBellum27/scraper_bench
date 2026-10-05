import json

with open('inputs/base_case.json') as f:
    bc = json.load(f)

print("scenarios[0]:", bc['scenarios'][0])
