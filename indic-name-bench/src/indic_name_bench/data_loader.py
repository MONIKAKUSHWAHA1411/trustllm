"""Packaged YAML data access.

All corpus inputs are shipped inside the package rather than read from a path
relative to the working directory, so that ``indic-name-bench`` behaves the
same installed from a wheel as it does from a checkout. Loads are cached: the
tables are read once per process and treated as immutable thereafter.
"""

from __future__ import annotations

from functools import lru_cache
from importlib import resources
from typing import Any

import yaml


@lru_cache(maxsize=None)
def load(package: str, filename: str) -> dict[str, Any]:
    """Read a YAML file shipped inside ``indic_name_bench.<package>.data``."""
    anchor = f"indic_name_bench.{package}.data"
    text = resources.files(anchor).joinpath(filename).read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError(f"{anchor}/{filename} must contain a YAML mapping")
    return data


def seeds(filename: str) -> dict[str, Any]:
    return load("seeds", filename)


def variant_tables(filename: str) -> dict[str, Any]:
    return load("variants", filename)
