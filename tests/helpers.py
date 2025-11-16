"""Test helpers for safely coercing contract-derived values used by tests.

Keep tests defensive: when a MappingContract field is Optional, tests that
assign its value to an internal mapper attribute should coerce to a dict
to avoid assigning None to attributes typed as non-Optional.
"""
from typing import Any, Dict


def safe_coerce_dict(value: Any) -> Dict:
    """Return a dict if value is a dict, else return an empty dict.

Used by tests before assigning contract-derived dicts to mapper internals.
"""
    return value if isinstance(value, dict) else {}
