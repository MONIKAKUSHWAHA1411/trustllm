"""Filesystem locations for the golden BFSI dataset.

All paths resolve relative to this file so the package works regardless of the
current working directory.
"""

from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
ROOT = PACKAGE_DIR.parent

CORPUS_GRID = ROOT / "corpus" / "grid.json"
L0_DATA = ROOT / "data" / "l0.jsonl"
LEDGER = ROOT / "ledger" / "ledger.json"
SCHEMA = ROOT / "schema" / "golden_item.schema.json"
