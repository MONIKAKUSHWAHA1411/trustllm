from golden_dataset.layers.l0_provenance import l0_provenance
from golden_dataset.tamper.pdf_native import BenignResave, PdfNativeTamper


def test_authentic_scores_zero(fixture_pdf):
    assert l0_provenance(fixture_pdf)["l0_score"] == 0.0


def test_stealth0_tamper_is_caught(fixture_pdf, tmp_path):
    out = tmp_path / "s0.pdf"
    PdfNativeTamper(fixture_pdf).emit(out, [(0, "185000.00", "285000.00")], stealth=0)
    assert l0_provenance(out)["l0_score"] >= 0.9


def test_stealth2_defeats_l0(fixture_pdf, tmp_path):
    """Documents the known limit: ~30s of forger effort zeroes this layer.

    If this test starts FAILING, L0 got stronger and that is good news - update
    the assertion and the table in CLAUDE.md. Do not delete the test.
    """
    out = tmp_path / "s2.pdf"
    PdfNativeTamper(fixture_pdf).emit(out, [(0, "185000.00", "285000.00")], stealth=2)
    assert l0_provenance(out)["l0_score"] == 0.0


def test_benign_resave_looks_identical_to_fraud(fixture_pdf, tmp_path):
    """The reason benign controls are mandatory - CLAUDE.md invariant 1."""
    out = tmp_path / "benign.pdf"
    BenignResave(fixture_pdf).emit(out, "iLovePDF")
    assert l0_provenance(out)["l0_score"] >= 0.9, (
        "a benign re-save scores as high as real tampering; without these in "
        "the corpus L0 becomes a producer-string classifier"
    )


def test_pikepdf_does_not_stamp_itself(fixture_pdf, tmp_path):
    """CLAUDE.md invariant 8. Miss this and the detector learns our generator."""
    import pikepdf
    out = tmp_path / "s1.pdf"
    PdfNativeTamper(fixture_pdf).emit(out, [(0, "185000.00", "285000.00")], stealth=1)
    with pikepdf.open(out) as pdf:
        producer = str(dict(pdf.docinfo).get("/Producer", ""))
    assert "pikepdf" not in producer.lower(), f"generator leaked into /Producer: {producer}"
