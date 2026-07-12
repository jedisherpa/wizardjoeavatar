from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

from .models import EXPRESSIONS


DEFINITION_FILE = Path(__file__).with_name("definitions") / "expressions.json"


@lru_cache(maxsize=1)
def expressions() -> Dict[str, Dict[str, Any]]:
    with open(DEFINITION_FILE, "r", encoding="utf-8") as handle:
        return json.load(handle)


def get_expression(name: str) -> Dict[str, Any]:
    if name not in EXPRESSIONS:
        raise ValueError(f"Unsupported expression: {name}")
    return expressions()[name]


def expression_mouth(name: str) -> str:
    return str(get_expression(name).get("mouth", "closed"))
