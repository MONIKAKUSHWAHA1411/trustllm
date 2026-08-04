"""CLI entry point. `gds --help`"""
from __future__ import annotations

from pathlib import Path

import typer

app = typer.Typer(help="Golden dataset builder for BFSI document-fraud detection")


@app.command()
def scan(pdf: Path, bank: str = "HDFC") -> None:
    """Run L0 provenance forensics on a single PDF."""
    from golden_dataset.layers.l0_provenance import l0_provenance

    result = l0_provenance(pdf, expected_bank=bank)
    typer.echo(f"l0_score: {result['l0_score']}  flags: {result['flag_count']}")
    for flag in result["flags"]:
        typer.echo(f"  [{flag['severity']:<6}] {flag['code']}: {flag['evidence']}")


@app.command()
def reconcile(
    input_dir: Path = typer.Option(Path("data/ledgers"), "--input"),
    out: Path = typer.Option(Path("data/reports/l2_reconciliation.json"), "--out"),
) -> None:
    """Run L2 arithmetic reconciliation across a parsed-statement archive. TASKS.md T-02.

    Consumes ``*.ledger.json`` files (the format T-01 ingest emits) and writes a
    report. Any already-approved statement that fails reconciliation as received
    is either a parser bug or a fraud that was already funded — the CTO-visible
    finding this task exists to produce.
    """
    import json

    from golden_dataset.layers.l2_arithmetic import load_archive, reconcile_archive

    report = reconcile_archive(load_archive(input_dir))
    scanned = report["statements_scanned"]
    if scanned == 0:
        typer.echo(
            f"no parsed ledgers found in {input_dir}/ (*.ledger.json). "
            "T-01 ingest must run first — nothing to reconcile yet."
        )
        return

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    typer.echo(
        f"scanned {scanned} statements  hard-fails: {report['hard_fail_count']} "
        f"({report['hard_fail_rate']:.1%})  ->  {out}"
    )
    for rec in report["hard_fail_statements"]:
        typer.echo(f"  HARD-FAIL {rec['statement_id']}  rows={rec['breaking_rows']}")


@app.command()
def generate(
    input_dir: Path = typer.Option(Path("data/raw"), "--input"),
    out: Path = typer.Option(Path("data/corpus"), "--out"),
    workers: int = 8,
) -> None:
    """Generate the corpus grid from a directory of authentic statements. See TASKS.md T-03."""
    raise NotImplementedError(
        "T-03. Requires T-01 (ingest + template classification) first — "
        "BaseDocument objects cannot be built without parsed transaction tables."
    )


if __name__ == "__main__":
    app()
