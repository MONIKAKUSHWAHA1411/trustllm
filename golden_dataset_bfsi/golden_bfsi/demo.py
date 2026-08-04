"""`make demo` — a read-only tour of the golden BFSI dataset.

Prints the corpus-grid shape, L0 coverage against ``must_cover``, a per-domain
breakdown, and a live ledger-integrity check. No network, no side effects.
"""

from __future__ import annotations

from collections import Counter

from . import __version__
from .grid import cell_matches, grid_size, load_grid, uncovered_specs
from .items import load_items, load_schema, validate_item
from .ledger import build_integrity, load_ledger
from .paths import LEDGER


def _rule(title: str) -> None:
    print(f"\n\033[1m{title}\033[0m")
    print("-" * len(title))


def run() -> int:
    grid = load_grid()
    items = load_items()
    schema = load_schema()

    print(f"golden-dataset-bfsi  v{__version__}")
    print(grid["disclaimer"])

    _rule("Corpus grid")
    dims = grid["dimensions"]
    for axis, values in dims.items():
        print(f"  {axis:10s}: {', '.join(values)}")
    print(f"  full grid : {grid_size(grid)} cells "
          f"({' x '.join(str(len(v)) for v in dims.values())})")
    print(f"  L0 items  : {len(items)} occupying "
          f"{len({tuple(sorted(i['cell'].items())) for i in items})} distinct cells")

    _rule("Schema conformance")
    bad = 0
    for item in items:
        errors = validate_item(item, schema)
        if errors:
            bad += 1
            print(f"  ✗ {item.get('id', '?')}: {errors[0]}")
    print(f"  {len(items) - bad}/{len(items)} items conform to golden_item.schema.json")

    _rule("must_cover coverage")
    missing = uncovered_specs(grid, (i["cell"] for i in items))
    for spec in grid.get("must_cover", []):
        hits = sum(1 for i in items if cell_matches(spec, i["cell"]))
        mark = "✓" if hits else "✗"
        label = "/".join(f"{k}={v}" for k, v in spec.items())
        print(f"  {mark} {label:52s} {hits} item(s)")
    print(f"  {len(grid['must_cover']) - len(missing)}/{len(grid['must_cover'])} "
          "required cells covered")

    _rule("Breakdown")
    by_domain = Counter(i["cell"]["domain"] for i in items)
    for domain in grid["dimensions"]["domain"]:
        print(f"  {domain:10s}: {by_domain.get(domain, 0)}")
    refusals = sum(1 for i in items if i["must_refuse"])
    print(f"  refusal items requiring must_refuse=true: {refusals}")

    _rule("Ledger integrity")
    fresh = build_integrity(items)
    try:
        stored = load_ledger()
        drift = (
            stored.get("entries") != fresh["entries"]
            or stored.get("corpus_digest") != fresh["corpus_digest"]
        )
        status = "DRIFT — run `make ledger`" if drift else "OK — matches data/"
    except FileNotFoundError:
        status = f"missing {LEDGER.name} — run `make ledger`"
        drift = True
    print(f"  corpus_digest : {fresh['corpus_digest']}")
    print(f"  ledger        : {status}")

    ok = bad == 0 and not missing and not drift
    _rule("Result")
    print("  ALL INVARIANTS HELD" if ok else "  INVARIANTS VIOLATED — see above")
    return 0 if ok else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(run())
