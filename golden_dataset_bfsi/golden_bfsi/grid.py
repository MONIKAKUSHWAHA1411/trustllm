"""The corpus grid: the coverage matrix a golden item lives in.

A *cell* is a full assignment of every grid axis (domain, task, risk_tier,
language). A *spec* is a partial assignment used by ``must_cover`` to name a
family of cells regardless of, say, language.
"""

from __future__ import annotations

import itertools
import json
from typing import Dict, Iterable, Iterator, List

from .paths import CORPUS_GRID


def load_grid(path=CORPUS_GRID) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def axes(grid: dict) -> List[str]:
    """Ordered list of dimension names."""
    return list(grid["dimensions"].keys())


def full_grid(grid: dict) -> Iterator[Dict[str, str]]:
    """Yield every cell in the Cartesian product of the dimensions."""
    keys = axes(grid)
    for combo in itertools.product(*(grid["dimensions"][k] for k in keys)):
        yield dict(zip(keys, combo))


def grid_size(grid: dict) -> int:
    size = 1
    for values in grid["dimensions"].values():
        size *= len(values)
    return size


def is_valid_cell(grid: dict, cell: Dict[str, str]) -> bool:
    """True when *cell* names exactly the grid axes with allowed values."""
    dims = grid["dimensions"]
    if set(cell.keys()) != set(dims.keys()):
        return False
    return all(value in dims[key] for key, value in cell.items())


def cell_matches(spec: Dict[str, str], cell: Dict[str, str]) -> bool:
    """True when *cell* satisfies the partial *spec* (every named axis equal)."""
    return all(cell.get(key) == value for key, value in spec.items())


def uncovered_specs(grid: dict, cells: Iterable[Dict[str, str]]) -> List[Dict[str, str]]:
    """Return the ``must_cover`` specs that no cell in *cells* satisfies."""
    cells = list(cells)
    missing = []
    for spec in grid.get("must_cover", []):
        if not any(cell_matches(spec, cell) for cell in cells):
            missing.append(spec)
    return missing
