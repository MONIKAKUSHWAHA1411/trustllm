"""
golden_dataset.tamper.raster
============================
Method B (raster inpaint), Method C (copy-move), Method E (print-scan loop),
and the pixel-mask writer that every tampered sample must carry.

Why raster tampering matters even though PDF-native editing is more common:
a forger who rasterises the statement destroys every L0 signal. Producer
strings, xref chains and XMP history all vanish, because the output is a fresh
PDF wrapping a JPEG. Detection then rests entirely on L1 pixel forensics and
L2 arithmetic. If the corpus has no raster-tampered samples, L1 never learns
anything and the system has a hole exactly where the competent forgers operate.
"""

from __future__ import annotations

import io
import math
import random
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pypdfium2 as pdfium
from PIL import Image, ImageDraw, ImageFilter, ImageFont


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render_page(pdf_path: Path, page_index: int, dpi: int = 200) -> Image.Image:
    """Render one PDF page to RGB. pypdfium2 is Apache/BSD - no AGPL exposure."""
    doc = pdfium.PdfDocument(str(pdf_path))
    try:
        page = doc[page_index]
        bitmap = page.render(scale=dpi / 72.0)
        return bitmap.to_pil().convert("RGB")
    finally:
        doc.close()


def pdf_bbox_to_px(bbox: list[float], page_height_pt: float, dpi: int = 200) -> tuple[int, int, int, int]:
    """
    PDF user space has origin bottom-left; raster has origin top-left.
    Getting this flip wrong silently produces masks that point at the wrong
    row, and the model then learns nothing. Assert your masks visually on the
    first 50 samples before generating 40,000.
    """
    s = dpi / 72.0
    x0, y0, x1, y1 = bbox
    return (
        int(x0 * s),
        int((page_height_pt - y1) * s),
        int(x1 * s),
        int((page_height_pt - y0) * s),
    )


# ---------------------------------------------------------------------------
# Method B — raster inpaint
# ---------------------------------------------------------------------------

@dataclass
class InpaintResult:
    image: Image.Image
    mask: Image.Image          # mode "L", 255 = tampered pixel
    bbox_px: tuple[int, int, int, int]


class RasterInpainter:
    """
    Replace the text inside a bounding box with different text, matched to the
    local background and font metrics.

    The realism levers that actually matter, in order of impact:

      1. Background sampling. Take the median colour of the box border, not
         pure white. Bank statements have tinted alternating rows; painting
         white over a tinted row is visible to a human and trivially detectable.

      2. Sub-pixel offset. Real edits almost never land on the exact original
         baseline. Jitter by +/- 1px. Counter-intuitively this makes the sample
         HARDER, not easier - a model trained on pixel-perfect replacements
         learns to look for perfect alignment, which real forgeries lack.

      3. Recompression. Save the whole page as JPEG at a quality DIFFERENT from
         the original after editing. This is what creates the double-compression
         signature L1 keys on. Vary the quantisation table across the corpus:
         detectors trained on a narrow QF range collapse on unseen tables.
    """

    def __init__(self, font_path: str | None = None, seed: int | None = None):
        self.font_path = font_path
        self.rng = random.Random(seed)

    def _bg_colour(self, img: Image.Image, box: tuple[int, int, int, int]) -> tuple[int, int, int]:
        x0, y0, x1, y1 = box
        pad = 3
        region = img.crop((max(0, x0 - pad), max(0, y0 - pad), x1 + pad, y1 + pad))
        arr = np.asarray(region).reshape(-1, 3)
        # Median of the brightest 40% ~= the paper, not the ink.
        lum = arr.mean(axis=1)
        thresh = np.percentile(lum, 60)
        paper = arr[lum >= thresh]
        return tuple(int(v) for v in np.median(paper, axis=0))

    def _fit_font(self, text: str, box_h: int, box_w: int) -> ImageFont.FreeTypeFont:
        size = max(6, int(box_h * 0.82))
        while size > 5:
            try:
                f = (ImageFont.truetype(self.font_path, size)
                     if self.font_path else ImageFont.load_default(size))
            except Exception:
                f = ImageFont.load_default()
                return f
            if f.getbbox(text)[2] <= box_w:
                return f
            size -= 1
        return ImageFont.load_default()

    def inpaint(
        self,
        img: Image.Image,
        box_px: tuple[int, int, int, int],
        new_text: str,
        align: str = "right",
        jitter: bool = True,
    ) -> InpaintResult:
        img = img.copy()
        mask = Image.new("L", img.size, 0)
        x0, y0, x1, y1 = box_px

        bg = self._bg_colour(img, box_px)
        draw = ImageDraw.Draw(img)
        mdraw = ImageDraw.Draw(mask)

        # 1. paint out the original
        draw.rectangle([x0, y0, x1, y1], fill=bg)

        # 2. render the replacement
        font = self._fit_font(new_text, y1 - y0, x1 - x0)
        tb = font.getbbox(new_text)
        tw, th = tb[2] - tb[0], tb[3] - tb[1]

        dx = self.rng.randint(-1, 1) if jitter else 0
        dy = self.rng.randint(-1, 1) if jitter else 0
        tx = (x1 - tw - 2 + dx) if align == "right" else (x0 + 2 + dx)
        ty = y0 + max(0, ((y1 - y0) - th) // 2) - tb[1] + dy

        draw.text((tx, ty), new_text, font=font, fill=(20, 20, 22))
        mdraw.rectangle([x0, y0, x1, y1], fill=255)

        return InpaintResult(image=img, mask=mask, bbox_px=(x0, y0, x1, y1))


# ---------------------------------------------------------------------------
# Method C — copy-move
# ---------------------------------------------------------------------------

def copy_move(
    img: Image.Image,
    src_box: tuple[int, int, int, int],
    dst_box: tuple[int, int, int, int],
    feather: int = 2,
) -> InpaintResult:
    """
    Duplicate a region of the page elsewhere on the page — the classic way to
    fabricate an extra salary credit by cloning a real one.

    Feathering the paste edge matters. A hard-edged paste leaves a step
    discontinuity in the noise residual that L1 detects almost perfectly, which
    makes the sample too easy and inflates your metrics.
    """
    out = img.copy()
    mask = Image.new("L", img.size, 0)
    patch = img.crop(src_box)
    dw, dh = dst_box[2] - dst_box[0], dst_box[3] - dst_box[1]
    patch = patch.resize((dw, dh), Image.LANCZOS)

    blend = Image.new("L", (dw, dh), 255)
    if feather > 0:
        blend = blend.filter(ImageFilter.GaussianBlur(feather))
    out.paste(patch, dst_box[:2], blend)
    ImageDraw.Draw(mask).rectangle(list(dst_box), fill=255)
    return InpaintResult(image=out, mask=mask, bbox_px=dst_box)


# ---------------------------------------------------------------------------
# Method E — print / scan loop simulation
# ---------------------------------------------------------------------------

def print_scan(
    img: Image.Image,
    seed: int | None = None,
    strength: float = 1.0,
) -> Image.Image:
    """
    Simulate print -> physically alter -> rescan.

    Applied AFTER tampering, this is the strongest realism augmentation in the
    whole pipeline, because it destroys the clean synthetic artifacts that a
    model would otherwise latch onto. If your detector's accuracy collapses once
    you turn this on, the detector was reading your generator, not the forgery.

    Apply it to authentic samples too, at the same rate. Otherwise the model
    learns "scanned == fraud".
    """
    rng = random.Random(seed)
    a = np.asarray(img).astype(np.float32)
    h, w = a.shape[:2]

    # illumination gradient (scanner lamp falloff)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy = w * rng.uniform(0.3, 0.7), h * rng.uniform(0.3, 0.7)
    rad = np.sqrt(((xx - cx) / w) ** 2 + ((yy - cy) / h) ** 2)
    a *= (1.0 - 0.16 * strength * rad)[..., None]

    # paper texture
    a += rng.uniform(-3, 3) * strength
    a += np.random.normal(0, 2.2 * strength, a.shape)

    out = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))

    # slight rotation + blur
    out = out.rotate(rng.uniform(-0.5, 0.5) * strength, resample=Image.BICUBIC,
                     fillcolor=(252, 251, 249), expand=False)
    out = out.filter(ImageFilter.GaussianBlur(rng.uniform(0.2, 0.6) * strength))

    # rescan JPEG at a varied quality factor
    buf = io.BytesIO()
    out.save(buf, "JPEG", quality=rng.choice([72, 78, 84, 88, 92]))
    buf.seek(0)
    return Image.open(buf).convert("RGB")


def recompress(img: Image.Image, quality: int) -> Image.Image:
    """Second compression pass — creates the double-compression signature."""
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=quality)
    buf.seek(0)
    return Image.open(buf).convert("RGB")


# ---------------------------------------------------------------------------
# Mask QA — run this before generating at scale
# ---------------------------------------------------------------------------

def mask_sanity(mask: Image.Image, min_frac: float = 1e-5, max_frac: float = 0.25) -> tuple[bool, str]:
    """
    Catch the two mask failures that silently destroy a corpus:
      - empty mask (tamper applied but never recorded) -> model trains on a
        tampered image labelled as having no tampered pixels
      - runaway mask (>25% of the page) -> the mask is the whole page and the
        localisation head learns to predict everything
    """
    arr = np.asarray(mask) > 127
    frac = arr.mean()
    if frac < min_frac:
        return False, f"mask empty or near-empty (frac={frac:.2e})"
    if frac > max_frac:
        return False, f"mask covers {frac:.1%} of page - likely a bbox error"
    return True, f"ok (frac={frac:.4%})"
