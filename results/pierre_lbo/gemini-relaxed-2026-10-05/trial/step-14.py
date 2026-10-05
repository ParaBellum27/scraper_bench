import json

with open('inputs/base_case.json') as f:
    inputs = json.load(f)

# Modify inputs to force a liquidity shortfall
test_inputs = json.loads(json.dumps(inputs))
# e.g., huge capex or low revolver commitment
test_inputs['revolver']['commitment'] = 0.0
test_inputs['scenarios'][0]['capex'][0] = 50000.0  # huge capex in period 1

# Let's run our model logic on test_inputs
# and check if status becomes liquidity_shortfall
from io import StringIO
import sys

# We can import run_model if defined, or define it here
# Let's inspect test_inputs behavior
