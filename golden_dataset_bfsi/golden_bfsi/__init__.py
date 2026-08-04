"""golden_bfsi — a golden BFSI evaluation dataset scaffold.

Pieces:
- corpus grid   (corpus/grid.json)  : the coverage matrix of domain x task x risk_tier x language
- L0 seed items (data/l0.jsonl)     : the smallest golden layer, one item per line
- ledger        (ledger/ledger.json): content-addressed manifest of every item, for integrity/drift
- invariant tests (tests/)          : assertions the dataset must always satisfy

Everything here is standard-library only so the dataset can be validated
anywhere without heavyweight dependencies.
"""

__version__ = "0.1.0"
