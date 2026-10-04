"""Shared input/output schema definitions for the benchmark evaluator.

The concrete fields will be finalized after fcff2st.xls is inspected.
"""

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class EvaluationResult:
    executed: bool
    score: float
    details: Dict[str, Any]


def validate_submission_output(output: Dict[str, Any]) -> None:
    """Validate the submission output shape.

    Placeholder until the workbook-derived output schema is frozen.
    """
    if not isinstance(output, dict):
        raise TypeError("Submission output must be a dictionary.")
