"""L0 - deterministic provenance and file forensics. No model. ~5ms per document.

Measured on the reference corpus: scores 1.00 at stealth=0 and 0.00 at
stealth>=1. Restoring the producer string takes a forger ~30 seconds and
defeats this layer completely. L0 is a cheap first filter, not a defence.
"""

from __future__ import annotations

from pathlib import Path

import pikepdf


BANK_PRODUCERS = {
    "HDFC": ["Finacle", "iText", "HDFC"],
    "ICICI": ["FIS", "iText"],
    "SBI": ["CBS", "Crystal Reports"],
}

CONSUMER_EDITORS = [
    "acrobat", "ilovepdf", "smallpdf", "foxit", "nitro", "pdfelement",
    "print to pdf", "quartz", "ghostscript", "pdftk", "libreoffice",
    "microsoft word", "canva", "sejda", "pdfescape",
]


def l0_provenance(pdf_path: Path, expected_bank: str = "HDFC") -> dict:
    """
    Deterministic, no model, ~5ms. This is where most casual tampering dies.

    Every flag returns evidence, because a RED_FLAG that an analyst cannot
    justify in writing is useless under the RBI show-cause requirement.
    """
    flags: list[dict] = []
    raw = pdf_path.read_bytes()

    with pikepdf.open(pdf_path) as pdf:
        info = {str(k).lstrip("/"): str(v) for k, v in (dict(pdf.docinfo) if pdf.docinfo else {}).items()}
        producer = info.get("Producer", "")
        creator = info.get("Creator", "")

        allow = BANK_PRODUCERS.get(expected_bank, [])
        if allow and not any(a.lower() in producer.lower() for a in allow):
            flags.append({
                "code": "L0_PRODUCER_MISMATCH", "severity": "HIGH",
                "evidence": {"producer": producer, "expected_contains": allow},
            })
        for ed in CONSUMER_EDITORS:
            if ed in producer.lower() or ed in creator.lower():
                flags.append({
                    "code": "L0_CONSUMER_EDITOR", "severity": "HIGH",
                    "evidence": {"producer": producer, "creator": creator, "matched": ed},
                })
                break

        if "CreationDate" in info and "ModDate" in info:
            if info["CreationDate"] != info["ModDate"]:
                flags.append({
                    "code": "L0_MOD_AFTER_CREATE", "severity": "MEDIUM",
                    "evidence": {"created": info["CreationDate"], "modified": info["ModDate"]},
                })

    # Incremental save chain: >1 EOF marker means the file was re-saved on top
    # of itself. Bank statements are written once.
    eof_count = raw.count(b"%%EOF")
    if eof_count > 1:
        flags.append({
            "code": "L0_INCREMENTAL_SAVE", "severity": "HIGH",
            "evidence": {"eof_markers": eof_count},
        })

    if b"/Prev" in raw:
        flags.append({
            "code": "L0_XREF_PREV_CHAIN", "severity": "MEDIUM",
            "evidence": {"prev_offsets": raw.count(b"/Prev")},
        })

    # Font subset proliferation: a tampered field often introduces a second
    # subset of the same face.
    with pikepdf.open(pdf_path) as pdf:
        subsets: dict[str, set[str]] = {}
        for page in pdf.pages:
            fonts = page.get("/Resources", {}).get("/Font", {})
            for _, fobj in dict(fonts).items():
                bn = str(fobj.get("/BaseFont", ""))
                base = bn.split("+")[-1]
                subsets.setdefault(base, set()).add(bn)
        for base, tags in subsets.items():
            if len(tags) > 1:
                flags.append({
                    "code": "L0_FONT_SUBSET_SPLIT", "severity": "MEDIUM",
                    "evidence": {"base_font": base, "subsets": sorted(tags)},
                })

    severity_weight = {"HIGH": 0.45, "MEDIUM": 0.18, "LOW": 0.06}
    score = min(1.0, sum(severity_weight[f["severity"]] for f in flags))
    return {"l0_score": round(score, 3), "flag_count": len(flags), "flags": flags}


