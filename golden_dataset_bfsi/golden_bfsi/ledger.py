"""The ledger: a content-addressed manifest of every golden item.

Each entry pins an item's id, level and cell to a SHA-256 of its canonical
JSON. A ``corpus_digest`` fingerprints the whole set. Rebuilding the ledger
from ``data/`` and comparing digests is how the invariant tests detect silent
drift between the data and its manifest.

The stored ledger also carries volatile metadata (``generated_at``) that is
*not* part of the integrity core, so regenerating it does not spuriously fail
the drift check.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List

from . import __version__
from .grid import load_grid
from .items import load_items
from .paths import LEDGER

DATASET = "golden-dataset-bfsi"


def _canonical(obj: Any) -> str:
    """Deterministic JSON: sorted keys, no incidental whitespace."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def item_hash(item: Dict[str, Any]) -> str:
    digest = hashlib.sha256(_canonical(item).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def build_entries(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    entries = [
        {
            "id": item["id"],
            "level": item["level"],
            "cell": item["cell"],
            "hash": item_hash(item),
        }
        for item in items
    ]
    entries.sort(key=lambda entry: entry["id"])
    return entries


def corpus_digest(entries: List[Dict[str, Any]]) -> str:
    joined = "\n".join(f"{entry['id']}:{entry['hash']}" for entry in entries)
    digest = hashlib.sha256(joined.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def build_integrity(items: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    """The reproducible core of the ledger: entries + corpus digest."""
    items = load_items() if items is None else items
    entries = build_entries(items)
    return {"entries": entries, "corpus_digest": corpus_digest(entries)}


def build_ledger(items: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    """The full ledger: integrity core plus descriptive metadata."""
    grid = load_grid()
    core = build_integrity(items)
    return {
        "dataset": DATASET,
        "schema_version": __version__,
        "grid_version": grid["version"],
        "level": "L0",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "item_count": len(core["entries"]),
        "corpus_digest": core["corpus_digest"],
        "entries": core["entries"],
    }


def load_ledger(path=LEDGER) -> Dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def write_ledger(ledger: Dict[str, Any] | None = None, path=LEDGER) -> Dict[str, Any]:
    ledger = build_ledger() if ledger is None else ledger
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(ledger, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return ledger


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the golden-dataset-bfsi ledger.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify the stored ledger matches the data instead of rewriting it.",
    )
    args = parser.parse_args(argv)

    if args.check:
        stored = load_ledger()
        fresh = build_integrity()
        ok = (
            stored.get("entries") == fresh["entries"]
            and stored.get("corpus_digest") == fresh["corpus_digest"]
        )
        if ok:
            print(f"ledger OK — {len(fresh['entries'])} items, {fresh['corpus_digest']}")
            return 0
        print("ledger DRIFT — stored ledger does not match data/. Run `make ledger`.")
        return 1

    ledger = write_ledger()
    print(
        f"wrote {LEDGER.name}: {ledger['item_count']} items, "
        f"digest {ledger['corpus_digest']}"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
