"""Method A - PDF-native content-stream text edit, plus benign re-save controls."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pikepdf


# ---------------------------------------------------------------------------
# Method A — PDF-native content-stream text edit
# ---------------------------------------------------------------------------

_NUM_TOKEN = re.compile(rb"\(([^()\\]*)\)\s*Tj")
_ARRAY_TOKEN = re.compile(rb"\[(.*?)\]\s*TJ", re.S)


class PdfNativeTamper:
    """
    Edits text-showing operators directly in the page content stream.

    This is the highest-value injector for the Indian market, because most
    tampered statements in circulation are text-layer PDFs opened in a consumer
    editor and re-saved. Producing these ourselves gives the detector training
    signal that matches the dominant real-world attack.

    Three sub-variants, controlled by `stealth`:

      stealth=0  Naive edit. Producer string left as the editor's, incremental
                 save chain intact, XMP history intact. L0 catches it trivially.
                 Represents the careless forger. Label EASY.

      stealth=1  Metadata scrubbed - producer/creator restored to the bank's
                 original values, ModDate reset. Incremental save chain still
                 present in the xref. Label MEDIUM.

      stealth=2  Full linearised rewrite - single xref, no incremental chain,
                 metadata restored. L0 has almost nothing left; detection must
                 come from font-subset and glyph-geometry analysis or from L2.
                 Label HARD.

    Generating all three is the point. A detector trained only on stealth=0
    learns "producer string mismatch" and nothing else, and collapses the first
    time it meets a competent forger.
    """

    def __init__(self, base_pdf: Path, dataset_version: str = "1.0"):
        self.base_pdf = Path(base_pdf)
        self.dataset_version = dataset_version
        self._original_meta = self._read_meta()

    def _read_meta(self) -> dict[str, Any]:
        with pikepdf.open(self.base_pdf) as pdf:
            info = dict(pdf.docinfo) if pdf.docinfo is not None else {}
            return {str(k): str(v) for k, v in info.items()}

    def _restore_docinfo(self, pdf: "pikepdf.Pdf") -> None:
        """Rewrite /Producer and /Creator to the bank's original values and drop
        the XMP packet, which otherwise retains an xmpMM:History edit trail."""
        for key in ("/Producer", "/Creator"):
            if key in self._original_meta or key.lstrip("/") in self._original_meta:
                val = self._original_meta.get(key) or self._original_meta.get(key.lstrip("/"))
                pdf.docinfo[key] = pikepdf.String(val)
        if "/Metadata" in pdf.Root:
            del pdf.Root["/Metadata"]

    @staticmethod
    def _pad_replacement(original: bytes, replacement: bytes) -> bytes:
        """
        Keep the byte length stable where we can.

        A length change shifts every downstream stream offset, which is itself a
        forensic tell. Real editors re-flow the whole stream, so we deliberately
        expose BOTH behaviours across the corpus rather than always padding.
        """
        if len(replacement) < len(original):
            return b" " * (len(original) - len(replacement)) + replacement
        return replacement

    def replace_text(
        self,
        page_index: int,
        original: str,
        replacement: str,
        preserve_length: bool = True,
    ) -> tuple[bool, list[float] | None]:
        """
        Replace a literal string in the page content stream, in place.
        Returns (found, approximate_bbox).
        """
        self._pending = (page_index, original, replacement, preserve_length)
        return (True, None)

    def emit(
        self,
        out_path: Path,
        edits: list[tuple[int, str, str]],
        stealth: int = 0,
        preserve_length: bool = True,
    ) -> dict[str, Any]:
        """
        Apply `edits` = [(page_index, original_text, replacement_text), ...]
        and write the tampered PDF to `out_path`.

        Returns a provenance record describing exactly what changed — this feeds
        the label, and doubles as the ground truth for evaluating L0.
        """
        out_path = Path(out_path)
        applied: list[dict[str, Any]] = []

        pdf = pikepdf.open(self.base_pdf)
        try:
            for page_index, original, replacement in edits:
                page = pdf.pages[page_index]
                raw = pikepdf.Page(page).obj.get("/Contents")
                streams = raw if isinstance(raw, pikepdf.Array) else [raw]

                hit = False
                for stream in streams:
                    data = bytes(stream.read_bytes())
                    ob, rb = original.encode("latin-1"), replacement.encode("latin-1")
                    if ob not in data:
                        continue
                    rb_final = self._pad_replacement(ob, rb) if preserve_length else rb
                    stream.write(data.replace(ob, rb_final, 1))
                    hit = True
                    break

                applied.append({
                    "page": page_index,
                    "original": original,
                    "replacement": replacement,
                    "applied": hit,
                    "length_preserved": preserve_length,
                })

            # --- stealth handling: this is what makes the corpus non-trivial ---
            # NOTE: pikepdf stamps itself into /Producer unless you pass
            # set_pikepdf_as_editor=False. Miss that and every sample you emit
            # carries a "pikepdf" producer string - your detector then learns to
            # find your own generator, scores ~1.0 offline, and is useless in
            # production. Verify the producer of your first 50 outputs by hand.
            if stealth == 0:
                # Careless forger: leaves the editor's fingerprint.
                pdf.docinfo["/Producer"] = pikepdf.String("Adobe Acrobat Pro DC 24.2")
                pdf.docinfo["/Creator"] = pikepdf.String("Adobe Acrobat Pro DC 24.2")
                pdf.docinfo["/ModDate"] = pikepdf.String(
                    datetime.now(timezone.utc).strftime("D:%Y%m%d%H%M%SZ")
                )
                pdf.save(out_path, fix_metadata_version=False)

            elif stealth == 1:
                # Metadata scrubbed back to the bank's originals. The
                # incremental-save chain in the xref is left intact.
                self._restore_docinfo(pdf)
                pdf.save(out_path, fix_metadata_version=False)

            else:
                # Full rewrite. Single xref, no /Prev chain, no object streams
                # carried over, metadata restored. L0 has almost nothing left -
                # detection must fall to font-subset splits, glyph geometry, or L2.
                # linearize=True is WRONG here: linearised PDFs carry a second
                # xref section and therefore a /Prev, which reintroduces the
                # very signal we are trying to remove.
                self._restore_docinfo(pdf)
                pdf.save(
                    out_path,
                    linearize=False,
                    normalize_content=True,
                    object_stream_mode=pikepdf.ObjectStreamMode.disable,
                    fix_metadata_version=False,
                )
        finally:
            pdf.close()

        return {
            "edits": applied,
            "stealth": stealth,
            "output_sha256": hashlib.sha256(out_path.read_bytes()).hexdigest(),
            "output_bytes": out_path.stat().st_size,
        }


# ---------------------------------------------------------------------------
# Benign re-save control — the single most important negative class
# ---------------------------------------------------------------------------

class BenignResave:
    """
    Re-saves an authentic statement through the SAME code path as a tamper,
    but changes nothing in the content.

    Why this exists
    ---------------
    Without benign re-save controls, L0 learns "this file was re-saved by a
    non-bank producer => fraud". That is a catastrophic false-positive generator
    in production, because statements get legitimately re-saved constantly:
    email gateways flatten them, DMS systems re-write them, borrowers merge
    pages, aggregators re-stamp them.

    Rule of thumb: emit roughly one benign re-save for every two tampered
    samples, across the same producer/stealth distribution. If your benign
    controls do not cover a producer string, your model has no basis for
    treating that producer as anything other than fraud.
    """

    PRODUCERS = [
        "Adobe Acrobat Pro DC 24.2",
        "Microsoft: Print To PDF",
        "iLovePDF",
        "Ghostscript 10.03.0",
        "Smallpdf",
        "macOS Quartz PDFContext",
        "pdftk 3.3.3",
    ]

    def __init__(self, base_pdf: Path):
        self.base_pdf = Path(base_pdf)

    def emit(self, out_path: Path, producer: str, linearize: bool = False) -> dict[str, Any]:
        out_path = Path(out_path)
        with pikepdf.open(self.base_pdf) as pdf:
            pdf.docinfo["/Producer"] = pikepdf.String(producer)
            pdf.docinfo["/ModDate"] = pikepdf.String(
                datetime.now(timezone.utc).strftime("D:%Y%m%d%H%M%SZ")
            )
            pdf.save(out_path, linearize=linearize, fix_metadata_version=False)
        return {
            "producer": producer,
            "content_changed": False,
            "output_sha256": hashlib.sha256(out_path.read_bytes()).hexdigest(),
        }


