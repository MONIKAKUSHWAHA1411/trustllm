"""Corpus construction: identities, variants, and labelled pairs.

Reproducibility contract
------------------------
A corpus is a pure function of :class:`CorpusConfig`. Same config, same bytes.
The manifest records the config, its hash, the library version and the
inventory counts, so a reported number can be traced back to the exact corpus
that produced it.

Splits
------
``degradation``
    Mixed-family variants at severities 1-5. Feeds the degradation curve.

``family``
    Single-family variants at severities 1-3, generated only from identities
    eligible for that family. Feeds the per-transformation breakdown.

    This split exists because the natural firing rate of the families is wildly
    uneven -- ``bengali_anglicisation`` needs a Bengali surname and fires on
    about 1.4% of a mixed corpus, against ``transliteration`` at over 60%.
    Attributing performance per family from the mixed split would rest on
    forty-odd samples for some cells. Restricting the registry to one family at
    a time, and drawing only from eligible identities, gives every family a
    comparable sample and makes attribution exact rather than inferred from
    co-occurring rules.

``cross_script``
    Kept apart because Latin-only matchers score zero on it by construction,
    and folding that into the aggregate would swamp every other signal.

Base rate
---------
Pairs are labelled once; the base rate is applied at evaluation time as an
importance weight (see ``eval/metrics.py``), which makes sweeping 10^-2 through
10^-6 free.

The assumption this rests on, stated plainly: reweighting treats the sampled
hard negatives as representative of the unsampled negative tail. They are not a
uniform sample of it -- they are deliberately drawn from the confusable region,
which is the hard end. Reweighted false-positive estimates are therefore
**conservative** relative to a true uniform draw at the same base rate.
Absolute alert volumes should be read as upper bounds rather than point
estimates. Relative comparisons between matchers are unaffected, because every
matcher is scored against the same negative set.
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .names import ParsedName
from .negatives import DISCRIMINABLE_TYPES, HardNegativeBuilder, HardNegativeType, NegativePair
from .seeds.assemble import Identity, IdentityAssembler
from .seeds.inventory import inventory_summary
from .variants import Family, GeneratedVariant, TransformRegistry, VariantGenerator
from .variants import cross_script as cross_script_module
from .variants import default_registry

#: Families that get their own single-family split. Cross-script is excluded
#: because it has its own split.
BREAKDOWN_FAMILIES: tuple[Family, ...] = (
    Family.TRANSLITERATION,
    Family.ARABIC_PERSIAN,
    Family.BENGALI_ANGLICISATION,
    Family.STRUCTURE,
    Family.AFFIX,
    Family.NOISE,
)


@dataclass(frozen=True)
class CorpusConfig:
    """Everything that determines the corpus. Serialised into the manifest."""

    seed: int = 20260811
    n_identities: int = 4000

    #: degradation split
    severities: tuple[int, ...] = (1, 2, 3, 4, 5)
    variants_per_identity_per_severity: int = 1

    #: family split
    family_variants_per_family: int = 900
    family_severities: tuple[int, ...] = (1, 2, 3)

    #: cross-script split
    cross_script_variants: int = 800

    #: negatives
    hard_negatives_per_type: int = 1500
    easy_negatives: int = 4000

    def fingerprint(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, default=list)
        return hashlib.sha256(payload.encode()).hexdigest()[:16]


@dataclass(frozen=True, slots=True)
class LabelledPair:
    """One evaluation pair."""

    left: str
    right: str
    label: int
    pair_type: str
    subtype: str
    severity: int
    origin_left: str
    origin_right: str
    identity_id: str = ""
    rule_ids: str = ""
    surface_distance: float = 0.0
    unsatisfiable: bool = False
    origin_ambiguous: bool = False

    def to_row(self) -> dict[str, object]:
        return {
            "left": self.left,
            "right": self.right,
            "label": self.label,
            "pair_type": self.pair_type,
            "subtype": self.subtype,
            "severity": self.severity,
            "origin_left": self.origin_left,
            "origin_right": self.origin_right,
            "identity_id": self.identity_id,
            "rule_ids": self.rule_ids,
            "surface_distance": round(self.surface_distance, 4),
            "unsatisfiable": self.unsatisfiable,
            "origin_ambiguous": self.origin_ambiguous,
        }


@dataclass
class Corpus:
    """A built corpus, held in memory."""

    config: CorpusConfig
    identities: list[Identity] = field(default_factory=list)
    pairs: dict[str, list[LabelledPair]] = field(default_factory=dict)

    def split(self, name: str) -> list[LabelledPair]:
        return self.pairs.get(name, [])

    def all_pairs(self) -> list[LabelledPair]:
        out: list[LabelledPair] = []
        for key in sorted(self.pairs):
            out.extend(self.pairs[key])
        return out

    def summary(self) -> dict[str, object]:
        counts = {k: len(v) for k, v in sorted(self.pairs.items())}
        positives = sum(1 for p in self.all_pairs() if p.label == 1)
        negatives = sum(1 for p in self.all_pairs() if p.label == 0)
        unsatisfiable = sum(1 for p in self.all_pairs() if p.unsatisfiable)
        return {
            "identities": len(self.identities),
            "pairs_by_split": counts,
            "total_pairs": sum(counts.values()),
            "positives": positives,
            "negatives": negatives,
            "unsatisfiable_negatives": unsatisfiable,
        }


def _positive(
    identity: Identity, variant: GeneratedVariant, split_subtype: str
) -> LabelledPair:
    """A positive pair: the clean list entry against the messy record.

    Canonical-vs-variant rather than variant-vs-variant, because that is the
    screening shape: a sanctions list holds one curated spelling and the
    incoming transaction holds whatever the originating system produced.
    Variant-vs-variant is strictly harder and is left for a later split rather
    than silently mixed in here.
    """
    return LabelledPair(
        left=identity.canonical,
        right=variant.text,
        label=1,
        pair_type="positive",
        subtype=split_subtype,
        severity=variant.severity,
        origin_left=identity.origin,
        origin_right=identity.origin,
        identity_id=identity.identity_id,
        rule_ids="|".join(variant.rule_ids),
        surface_distance=variant.surface_distance,
        origin_ambiguous=identity.origin_ambiguous,
    )


def _from_negative(pair: NegativePair) -> LabelledPair:
    return LabelledPair(
        left=pair.left,
        right=pair.right,
        label=0,
        pair_type="easy_negative" if pair.subtype == "easy" else "hard_negative",
        subtype=pair.subtype,
        severity=0,
        origin_left=pair.origin_left,
        origin_right=pair.origin_right,
        unsatisfiable=pair.unsatisfiable,
    )


def _eligible_for(
    identities: list[Identity], registry: TransformRegistry, rng: random.Random
) -> list[Identity]:
    """Identities on which at least one rule in ``registry`` actually fires."""
    generator = VariantGenerator(registry)
    out = []
    for identity in identities:
        variant = generator.generate(identity.name, identity.identity_id, 1, rng)
        if variant.severity > 0 and variant.text != variant.canonical:
            out.append(identity)
    return out


def build(config: CorpusConfig | None = None) -> Corpus:
    """Build the full corpus."""
    config = config or CorpusConfig()
    corpus = Corpus(config=config)

    # Each stage gets its own generator seeded off the master seed, so adding
    # a stage does not shift the output of the stages before it.
    def stream(tag: str) -> random.Random:
        digest = hashlib.sha256(f"{config.seed}|{tag}".encode()).hexdigest()[:16]
        return random.Random(int(digest, 16))

    corpus.identities = IdentityAssembler().assemble_many(
        config.n_identities, stream("identities")
    )

    # -- degradation split ------------------------------------------------
    mixed = VariantGenerator(default_registry(include_cross_script=False))
    rng = stream("degradation")
    degradation: list[LabelledPair] = []
    for identity in corpus.identities:
        for severity in config.severities:
            for _ in range(config.variants_per_identity_per_severity):
                variant = mixed.generate(
                    identity.name, identity.identity_id, severity, rng
                )
                degradation.append(_positive(identity, variant, "mixed"))
    corpus.pairs["degradation"] = degradation

    # -- family split -----------------------------------------------------
    family_pairs: list[LabelledPair] = []
    for family in BREAKDOWN_FAMILIES:
        registry = default_registry(include_cross_script=False).only(family)
        if len(registry) == 0:
            continue
        rng = stream(f"family:{family.value}")
        eligible = _eligible_for(corpus.identities, registry, stream(f"elig:{family.value}"))
        if not eligible:
            continue
        generator = VariantGenerator(registry, prefer_distinct_families=False)
        for i in range(config.family_variants_per_family):
            identity = eligible[i % len(eligible)]
            severity = config.family_severities[i % len(config.family_severities)]
            variant = generator.generate(
                identity.name, identity.identity_id, severity, rng
            )
            if variant.severity == 0:
                continue
            family_pairs.append(_positive(identity, variant, family.value))
    corpus.pairs["family"] = family_pairs

    # -- cross-script split ----------------------------------------------
    registry = TransformRegistry().add(*cross_script_module.build())
    rng = stream("cross_script")
    eligible = _eligible_for(corpus.identities, registry, stream("elig:cross_script"))
    generator = VariantGenerator(registry, prefer_distinct_families=False)
    cross: list[LabelledPair] = []
    if eligible:
        for i in range(config.cross_script_variants):
            identity = eligible[i % len(eligible)]
            variant = generator.generate(identity.name, identity.identity_id, 1, rng)
            if variant.severity == 0:
                continue
            cross.append(_positive(identity, variant, Family.CROSS_SCRIPT.value))
    corpus.pairs["cross_script"] = cross

    # -- negatives --------------------------------------------------------
    builder = HardNegativeBuilder(corpus.identities)
    negatives: list[LabelledPair] = []
    for subtype in HardNegativeType:
        rng = stream(f"neg:{subtype.value}")
        for pair in builder.build(subtype, config.hard_negatives_per_type, rng):
            negatives.append(_from_negative(pair))
    for pair in builder.build_easy(config.easy_negatives, stream("neg:easy")):
        negatives.append(_from_negative(pair))
    corpus.pairs["negatives"] = negatives

    return corpus


def write(corpus: Corpus, directory: Path) -> Path:
    """Write the corpus to ``directory`` as JSONL plus a manifest."""
    directory.mkdir(parents=True, exist_ok=True)

    for split, pairs in sorted(corpus.pairs.items()):
        path = directory / f"{split}.jsonl"
        with path.open("w", encoding="utf-8") as handle:
            for pair in pairs:
                handle.write(json.dumps(pair.to_row(), ensure_ascii=False) + "\n")

    identities_path = directory / "identities.jsonl"
    with identities_path.open("w", encoding="utf-8") as handle:
        for identity in corpus.identities:
            handle.write(json.dumps(identity.to_row(), ensure_ascii=False) + "\n")

    manifest = {
        "config": asdict(corpus.config),
        "config_fingerprint": corpus.config.fingerprint(),
        "summary": corpus.summary(),
        "inventory": inventory_summary(),
        "cross_script_coverage": cross_script_module.coverage_report(),
        "notes": {
            "positives": "canonical (clean list entry) vs variant (messy record)",
            "base_rate": "applied at evaluation time as importance weights, not materialised",
            "unsatisfiable_negatives": (
                "identical_collision pairs have identical strings and are excluded "
                "from headline metrics; they set the name-only precision ceiling"
            ),
        },
    }
    manifest_path = directory / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest_path


def load(directory: Path) -> list[LabelledPair]:
    """Read every split back from ``directory``."""
    out: list[LabelledPair] = []
    for path in sorted(directory.glob("*.jsonl")):
        if path.name == "identities.jsonl":
            continue
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                row = json.loads(line)
                out.append(
                    LabelledPair(
                        left=row["left"],
                        right=row["right"],
                        label=row["label"],
                        pair_type=row["pair_type"],
                        subtype=row["subtype"],
                        severity=row["severity"],
                        origin_left=row["origin_left"],
                        origin_right=row["origin_right"],
                        identity_id=row.get("identity_id", ""),
                        rule_ids=row.get("rule_ids", ""),
                        surface_distance=row.get("surface_distance", 0.0),
                        unsatisfiable=row.get("unsatisfiable", False),
                        origin_ambiguous=row.get("origin_ambiguous", False),
                    )
                )
    return out


__all__ = [
    "BREAKDOWN_FAMILIES",
    "Corpus",
    "CorpusConfig",
    "DISCRIMINABLE_TYPES",
    "LabelledPair",
    "build",
    "load",
    "write",
]
