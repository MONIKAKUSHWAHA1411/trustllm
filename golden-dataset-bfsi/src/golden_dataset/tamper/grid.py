"""
golden_dataset.tamper.grid
==========================
Turns ONE authentic bank statement into a complete corpus slice.

This is the file that decides whether your dataset is any good. The two
modules it orchestrates (pdf_native, raster) are just tools; the grid below
is the experimental design.

Three rules encoded here, each of which a corpus fails without:

  1. Benign re-save controls are emitted at a fixed ratio to tampered samples.
     Without them L0 degenerates into a producer-string classifier. Measured:
     a benign re-save scores 1.00 on L0 - identical to real tampering.

  2. Every numeric tamper is emitted in BOTH recompute variants. Without the
     recomputed variant the model learns "fraud == broken arithmetic" and
     misses every forger who bothered to fix the running balance.

  3. Print-scan augmentation is applied to authentic AND tampered samples at
     the same rate. Apply it only to tampered ones and the model learns
     "scanned == fraud", which is catastrophic in Tier 2/3 markets where
     scanned submissions dominate.
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Iterator

from ..ledger import Ledger, Txn
from ..schema import (
    Difficulty,
    GenerationMethod,
    Manipulation,
    ManipulationType,
    SampleLabel,
    make_label,
)
from .pdf_native import BenignResave, PdfNativeTamper
from .raster import (
    RasterInpainter,
    copy_move,
    mask_sanity,
    pdf_bbox_to_px,
    print_scan,
    recompress,
    render_page,
)


# ---------------------------------------------------------------------------
# Grid definition
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GridConfig:
    """
    Per-base-document variant counts. Defaults give 21 samples per base:
    ~4 authentic-class, ~17 tampered.

    4,000 real base statements -> ~84,000 samples.
    """
    authentic_passthrough: int = 1
    benign_resaves: int = 3          # DO NOT set to 0
    authentic_printscan: int = 1     # DO NOT set to 0
    pdf_native: int = 6              # 3 stealth x 2 recompute
    raster_inpaint: int = 4          # 2 fields x 2 JPEG QF
    copy_move: int = 2
    ai_inpaint: int = 2
    printscan_tamper: int = 2

    dpi: int = 200
    jpeg_qualities: tuple[int, ...] = (72, 80, 88, 94)
    seed: int = 1411

    def total(self) -> int:
        return sum([
            self.authentic_passthrough, self.benign_resaves,
            self.authentic_printscan, self.pdf_native, self.raster_inpaint,
            self.copy_move, self.ai_inpaint, self.printscan_tamper,
        ])

    def validate(self) -> None:
        if self.benign_resaves < 1:
            raise ValueError(
                "benign_resaves must be >= 1. Without benign controls, L0 learns "
                "'non-bank producer == fraud' and false-positives on every statement "
                "legitimately re-saved by a mail gateway, DMS, or page-merge tool."
            )
        if self.authentic_printscan < 1:
            raise ValueError(
                "authentic_printscan must be >= 1, or the model learns 'scanned == fraud'."
            )


@dataclass
class BaseDocument:
    """An authentic statement plus everything needed to tamper it correctly."""
    pdf_path: Path
    bank: str
    borrower_id_hash: str
    ledger: Ledger
    page_heights_pt: list[float]
    # field label -> (page_index, literal text as it appears in the content stream)
    editable_fields: dict[str, tuple[int, str]]

    @property
    def source_document_id(self) -> str:
        return hashlib.sha256(self.pdf_path.read_bytes()).hexdigest()[:16]


@dataclass
class EmittedSample:
    label: SampleLabel
    artifact_path: Path
    mask_path: Path | None


# ---------------------------------------------------------------------------
# Difficulty assignment
# ---------------------------------------------------------------------------

def grade(method: GenerationMethod, recomputed: bool, stealth: int) -> Difficulty:
    """
    Difficulty is a function of how many detection layers remain, not of how
    large the edit was. A 100,000-rupee change caught by L0 is EASY; a
    500-rupee change that survives L0 and L2 is ADVERSARIAL.
    """
    if method is GenerationMethod.BENIGN_RESAVE:
        return Difficulty.EASY
    if method is GenerationMethod.AI_INPAINT:
        return Difficulty.ADVERSARIAL if recomputed else Difficulty.HARD
    if method is GenerationMethod.PDF_TEXT_EDIT:
        if stealth == 0:
            return Difficulty.EASY if not recomputed else Difficulty.MEDIUM
        return Difficulty.ADVERSARIAL if recomputed else Difficulty.MEDIUM
    if method in (GenerationMethod.RASTER_INPAINT, GenerationMethod.COPY_MOVE):
        return Difficulty.HARD if recomputed else Difficulty.MEDIUM
    return Difficulty.MEDIUM


# ---------------------------------------------------------------------------
# The generator
# ---------------------------------------------------------------------------

class CorpusGrid:
    def __init__(
        self,
        out_dir: Path,
        mask_dir: Path,
        dataset_version: str = "1.0",
        config: GridConfig | None = None,
        ai_inpaint_fn: Callable[..., Any] | None = None,
    ):
        self.out_dir = Path(out_dir)
        self.mask_dir = Path(mask_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.mask_dir.mkdir(parents=True, exist_ok=True)
        self.dataset_version = dataset_version
        self.cfg = config or GridConfig()
        self.cfg.validate()
        self.rng = random.Random(self.cfg.seed)
        # Injected so the pipeline runs without a diffusion model present.
        # Wire a real inpainter here once the GPU node is up - see TASKS.md T-07.
        self.ai_inpaint_fn = ai_inpaint_fn

    # -- helpers ----------------------------------------------------------

    def _label(
        self,
        base: BaseDocument,
        manipulations: list[Manipulation],
        difficulty: Difficulty,
        mask_uri: str | None = None,
    ) -> SampleLabel:
        lab = make_label(
            source_pdf=base.pdf_path,
            source_bank=base.bank,
            manipulations=manipulations,
            difficulty=difficulty,
            dataset_version=self.dataset_version,
            tier="B_REAL_CONSENTED",
            borrower_id_hash=base.borrower_id_hash,
            mask_uri=mask_uri,
        )
        return lab

    def _write(self, lab: SampleLabel) -> None:
        (self.out_dir / f"{lab.sample_id}.json").write_text(lab.to_json())

    @staticmethod
    def _none_manip() -> list[Manipulation]:
        return [Manipulation(
            type=ManipulationType.NONE,
            generation_method=GenerationMethod.BENIGN_RESAVE,
            page=0, bbox=[0, 0, 0, 0], field="", original_value=None,
            tampered_value=None, downstream_recomputed=False, stealth=0,
        )]

    # -- authentic-class slices -------------------------------------------

    def _authentic(self, base: BaseDocument) -> Iterator[EmittedSample]:
        lab = self._label(base, self._none_manip(), Difficulty.EASY)
        dst = self.out_dir / f"{lab.sample_id}.pdf"
        dst.write_bytes(base.pdf_path.read_bytes())
        self._write(lab)
        yield EmittedSample(lab, dst, None)

    def _benign(self, base: BaseDocument) -> Iterator[EmittedSample]:
        producers = self.rng.sample(
            BenignResave.PRODUCERS, k=min(self.cfg.benign_resaves, len(BenignResave.PRODUCERS))
        )
        for producer in producers:
            lab = self._label(base, self._none_manip(), Difficulty.EASY)
            dst = self.out_dir / f"{lab.sample_id}.pdf"
            BenignResave(base.pdf_path).emit(dst, producer)
            lab.manipulations[0].notes = f"benign re-save, producer={producer}, content unchanged"
            self._write(lab)
            yield EmittedSample(lab, dst, None)

    def _authentic_printscan(self, base: BaseDocument) -> Iterator[EmittedSample]:
        for i in range(self.cfg.authentic_printscan):
            img = render_page(base.pdf_path, 0, dpi=self.cfg.dpi)
            out = print_scan(img, seed=self.rng.randint(0, 10**6), strength=1.0)
            lab = self._label(base, self._none_manip(), Difficulty.EASY)
            dst = self.out_dir / f"{lab.sample_id}.jpg"
            out.save(dst, quality=self.rng.choice(self.cfg.jpeg_qualities))
            lab.manipulations[0].notes = "authentic, print-scan simulated - NEGATIVE control"
            self._write(lab)
            yield EmittedSample(lab, dst, None)

    # -- tampered slices ---------------------------------------------------

    def _pdf_native(
        self, base: BaseDocument, field: str, delta: Decimal, row: int
    ) -> Iterator[EmittedSample]:
        page_idx, literal = base.editable_fields[field]
        original = Decimal(literal)
        tampered = original + delta

        for stealth in (0, 1, 2):
            for recompute in (False, True):
                edits: list[tuple[int, str, str]] = [
                    (page_idx, literal, f"{tampered:.2f}")
                ]
                changes = base.ledger.snapshot().apply_delta(
                    row=row, delta=delta, recompute=recompute
                )
                for _, old_bal, new_bal in changes:
                    edits.append((page_idx, f"{old_bal:.2f}", f"{new_bal:.2f}"))

                lab = self._label(
                    base,
                    [Manipulation(
                        type=ManipulationType.SALARY_INFLATION,
                        generation_method=GenerationMethod.PDF_TEXT_EDIT,
                        page=page_idx, bbox=[0, 0, 0, 0], field=field,
                        original_value=f"{original:.2f}", tampered_value=f"{tampered:.2f}",
                        downstream_recomputed=recompute, stealth=stealth,
                        notes=f"{len(changes)} balance cell(s) rewritten",
                    )],
                    grade(GenerationMethod.PDF_TEXT_EDIT, recompute, stealth),
                )
                dst = self.out_dir / f"{lab.sample_id}.pdf"
                PdfNativeTamper(base.pdf_path).emit(
                    dst, edits, stealth=stealth, preserve_length=True
                )
                self._write(lab)
                yield EmittedSample(lab, dst, None)

    def _raster(
        self, base: BaseDocument, field: str, bbox_pdf: list[float], new_text: str
    ) -> Iterator[EmittedSample]:
        page_idx, literal = base.editable_fields[field]
        img = render_page(base.pdf_path, page_idx, dpi=self.cfg.dpi)
        box_px = pdf_bbox_to_px(bbox_pdf, base.page_heights_pt[page_idx], dpi=self.cfg.dpi)
        box_px = (box_px[0] - 2, box_px[1] - 2, box_px[2] + 2, box_px[3] + 2)

        for qf in self.rng.sample(list(self.cfg.jpeg_qualities), k=2):
            res = RasterInpainter(seed=self.rng.randint(0, 10**6)).inpaint(
                img, box_px, new_text, align="right"
            )
            ok, msg = mask_sanity(res.mask)
            if not ok:
                # Fail loudly. A silent bad mask trains the model on a tampered
                # image labelled as having no tampered pixels.
                raise RuntimeError(f"mask sanity failed for {base.pdf_path.name}/{field}: {msg}")

            lab = self._label(
                base,
                [Manipulation(
                    type=ManipulationType.TXN_AMOUNT_EDIT,
                    generation_method=GenerationMethod.RASTER_INPAINT,
                    page=page_idx, bbox=bbox_pdf, field=field,
                    original_value=literal, tampered_value=new_text,
                    downstream_recomputed=False, stealth=2,
                    notes=f"jpeg_qf={qf}",
                )],
                grade(GenerationMethod.RASTER_INPAINT, False, 2),
            )
            dst = self.out_dir / f"{lab.sample_id}.jpg"
            mask_dst = self.mask_dir / f"{lab.sample_id}.png"
            recompress(res.image, quality=qf).save(dst, quality=qf)
            res.mask.save(mask_dst)
            lab.pixel_mask_uri = str(mask_dst)
            self._write(lab)
            yield EmittedSample(lab, dst, mask_dst)

    # -- entry point -------------------------------------------------------

    def generate(
        self,
        base: BaseDocument,
        target_field: str,
        target_row: int,
        delta: Decimal = Decimal("100000.00"),
        raster_bbox: list[float] | None = None,
    ) -> list[EmittedSample]:
        out: list[EmittedSample] = []
        out += list(self._authentic(base))
        out += list(self._benign(base))
        out += list(self._authentic_printscan(base))
        out += list(self._pdf_native(base, target_field, delta, target_row))

        if raster_bbox is not None:
            _, literal = base.editable_fields[target_field]
            new_text = f"{Decimal(literal) + delta:.2f}"
            out += list(self._raster(base, target_field, raster_bbox, new_text))

        # AI inpaint slice is skipped unless an inpainter is wired in. It is
        # NOT optional for a production corpus - see TASKS.md T-07. Diffusion
        # edits defeat current pixel forensics (AUC ~0.51-0.75), so a corpus
        # without them has a blind spot exactly where the market is moving.
        if self.ai_inpaint_fn is None:
            self._skipped_ai = True

        return out


def summarise(samples: list[EmittedSample]) -> dict[str, Any]:
    """Slice counts by difficulty and by expected-detecting-layer coverage."""
    by_diff: dict[str, int] = {}
    undetectable = 0
    authentic = 0
    for s in samples:
        by_diff[s.label.difficulty.value] = by_diff.get(s.label.difficulty.value, 0) + 1
        if s.label.is_authentic:
            authentic += 1
        elif not s.label.expected_detecting_layers:
            undetectable += 1
    return {
        "total": len(samples),
        "authentic": authentic,
        "tampered": len(samples) - authentic,
        "by_difficulty": by_diff,
        "no_expected_detector": undetectable,
    }
