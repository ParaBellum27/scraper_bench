"""Benchmark grader for Damodaran valuation tasks.

This file intentionally contains only the grading scaffold until the source
workbook has been inspected and expected outputs have been verified.
"""

from math import isclose
from typing import Any, Dict

from .schemas import EvaluationResult, validate_submission_output


def compare_numeric(actual: float, expected: float, rel_tol: float = 1e-6, abs_tol: float = 1e-8) -> bool:
    return isclose(actual, expected, rel_tol=rel_tol, abs_tol=abs_tol)


def grade_output(submission: Dict[str, Any], expected: Dict[str, Any]) -> EvaluationResult:
    """Grade a normalized submission output against verified expectations.

    Numerical fields and weighting will be populated once the workbook-derived
    schema is finalized.
    """
    validate_submission_output(submission)

    if not expected:
        return EvaluationResult(
            executed=True,
            score=0.0,
            details={"status": "grader_not_finalized"},
        )

    raise NotImplementedError("Finalize grading after reference outputs are verified.")
