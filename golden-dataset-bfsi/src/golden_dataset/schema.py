"""Label schema, tamper taxonomy, and the expected-detecting-layer map."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Taxonomy
# ---------------------------------------------------------------------------

class ManipulationType(str, Enum):
    BALANCE_MODIFICATION = "BALANCE_MODIFICATION"
    TXN_AMOUNT_EDIT = "TXN_AMOUNT_EDIT"
    SALARY_INFLATION = "SALARY_INFLATION"
    TXN_DELETION = "TXN_DELETION"
    TXN_INSERTION = "TXN_INSERTION"
    PAGE_SUBSTITUTION = "PAGE_SUBSTITUTION"
    PAGE_REORDER = "PAGE_REORDER"
    CROSS_STATEMENT_SPLICE = "CROSS_STATEMENT_SPLICE"
    DATE_SHIFT = "DATE_SHIFT"
    PERIOD_EXTENSION = "PERIOD_EXTENSION"
    IDENTITY_SUBSTITUTION = "IDENTITY_SUBSTITUTION"
    NONE = "NONE"                      # benign control


class GenerationMethod(str, Enum):
    PDF_TEXT_EDIT = "PDF_TEXT_EDIT"           # A - content-stream edit
    RASTER_INPAINT = "RASTER_INPAINT"         # B - render, edit pixels, re-embed
    COPY_MOVE = "COPY_MOVE"                   # C - splice from same/other doc
    AI_INPAINT = "AI_INPAINT"                 # D - diffusion/VLM edit
    PRINT_SCAN = "PRINT_SCAN"                 # E - physical loop simulation
    BENIGN_RESAVE = "BENIGN_RESAVE"           # control - re-saved, NOT tampered


class Difficulty(str, Enum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"
    ADVERSARIAL = "ADVERSARIAL"


# Which detection layer *should* fire.
#
# Keyed on (method, downstream_recomputed, stealth). Stealth MATTERS and an
# earlier version of this map ignored it - measured on the reference corpus,
# L0 scores 1.0 at stealth=0 and exactly 0.0 at stealth>=1. Restoring the
# producer string takes a forger about thirty seconds and defeats provenance
# forensics completely.
#
# Read the empty lists below as a warning, not a bug: (PDF_TEXT_EDIT, True, 2)
# has NO reliable detector in this architecture. Those samples belong in the
# ADVERSARIAL slice and their recall is the number that tells you what the
# system is actually worth against a competent adversary.
EXPECTED_LAYERS: dict[tuple[GenerationMethod, bool, int], list[str]] = {
    (GenerationMethod.PDF_TEXT_EDIT, False, 0): ["L0", "L2"],
    (GenerationMethod.PDF_TEXT_EDIT, True,  0): ["L0"],
    (GenerationMethod.PDF_TEXT_EDIT, False, 1): ["L2"],
    (GenerationMethod.PDF_TEXT_EDIT, True,  1): [],          # <- no detector
    (GenerationMethod.PDF_TEXT_EDIT, False, 2): ["L2"],
    (GenerationMethod.PDF_TEXT_EDIT, True,  2): [],          # <- no detector
    (GenerationMethod.RASTER_INPAINT, False, 0): ["L1", "L2"],
    (GenerationMethod.RASTER_INPAINT, True,  0): ["L1"],
    (GenerationMethod.RASTER_INPAINT, False, 2): ["L1", "L2"],
    (GenerationMethod.RASTER_INPAINT, True,  2): ["L1"],
    (GenerationMethod.COPY_MOVE, False, 0): ["L1", "L2"],
    (GenerationMethod.COPY_MOVE, True,  0): ["L1"],
    (GenerationMethod.AI_INPAINT, False, 2): ["L2"],         # L1 near-blind
    (GenerationMethod.AI_INPAINT, True,  2): ["L4"],         # behavioural only
    (GenerationMethod.PRINT_SCAN, False, 0): ["L2"],
    (GenerationMethod.PRINT_SCAN, True,  0): ["L4"],
    (GenerationMethod.BENIGN_RESAVE, False, 0): [],          # nothing should fire
}


# KNOWN GENERATOR LIMITATION - read before trusting your L0 metrics
# -----------------------------------------------------------------
# pikepdf (qpdf) always writes a FULL rewrite. It cannot produce a true
# incremental update, so samples from this engine never carry the multi-%%EOF
# / /Prev-chain signature that a real Acrobat "Save" leaves behind.
#
# Consequence: L0_INCREMENTAL_SAVE and L0_XREF_PREV_CHAIN will look useless
# when evaluated on this corpus and highly informative in production. Do not
# drop those features on the basis of synthetic evidence.
#
# To generate realistic incremental saves you must either drive a real editor
# (Acrobat Action Wizard / headless LibreOffice) or hand-append the update:
# original bytes + new objects + new xref carrying /Prev <original_startxref>
# + second %%EOF. Budget about two days for the hand-rolled version and treat
# it as a required deliverable, not a nice-to-have.


@dataclass
class Manipulation:
    type: ManipulationType
    generation_method: GenerationMethod
    page: int
    bbox: list[float]                       # [x0, y0, x1, y1] in PDF user space
    field: str
    original_value: str | None
    tampered_value: str | None
    downstream_recomputed: bool = False
    stealth: int = 0
    notes: str = ""


@dataclass
class SampleLabel:
    sample_id: str
    dataset_version: str
    tier: str                                # A_SYNTHETIC | B_REAL_CONSENTED | C_ADVERSARIAL
    source_document_id: str                  # hash of the AUTHENTIC base - split key
    borrower_id_hash: str | None             # second split key - prevents borrower leakage
    source_bank: str
    document_type: str
    is_authentic: bool
    fraud_class: list[str]
    manipulations: list[Manipulation]
    difficulty: Difficulty
    expected_detecting_layers: list[str]
    pixel_mask_uri: str | None
    pii_status: str
    annotator_id: str | None = None
    annotation_confidence: float = 1.0
    split: str = "UNASSIGNED"
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_json(self) -> str:
        d = asdict(self)
        d["manipulations"] = [
            {k: (v.value if isinstance(v, Enum) else v) for k, v in m.items()}
            for m in d["manipulations"]
        ]
        d["difficulty"] = self.difficulty.value
        return json.dumps(d, indent=2, default=str)


# ---------------------------------------------------------------------------
# Label construction
# ---------------------------------------------------------------------------

def make_label(
    *,
    source_pdf: Path,
    source_bank: str,
    manipulations: list[Manipulation],
    difficulty: Difficulty,
    dataset_version: str,
    tier: str = "B_REAL_CONSENTED",
    borrower_id_hash: str | None = None,
    mask_uri: str | None = None,
) -> SampleLabel:
    source_doc_id = hashlib.sha256(Path(source_pdf).read_bytes()).hexdigest()[:16]

    layers: list[str] = []
    for m in manipulations:
        layers += EXPECTED_LAYERS.get(
            (m.generation_method, m.downstream_recomputed, m.stealth), []
        )

    is_authentic = all(m.type == ManipulationType.NONE for m in manipulations)

    return SampleLabel(
        sample_id=f"gds_{uuid.uuid4().hex[:12]}",
        dataset_version=dataset_version,
        tier=tier,
        source_document_id=source_doc_id,
        borrower_id_hash=borrower_id_hash,
        source_bank=source_bank,
        document_type="BANK_STATEMENT",
        is_authentic=is_authentic,
        fraud_class=[] if is_authentic else ["F1_TAMPERING"],
        manipulations=manipulations,
        difficulty=difficulty,
        expected_detecting_layers=sorted(set(layers)),
        pixel_mask_uri=mask_uri,
        pii_status="REAL_DEIDENTIFIED" if tier == "B_REAL_CONSENTED" else "SYNTHETIC_NO_PII",
    )
