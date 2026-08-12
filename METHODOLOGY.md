# Methodology

## 1. The Indic phonetic encoder

### 1.1 Why the standard encoders fail on Indian names

Soundex (1918), Metaphone, NYSIIS and Caverphone encode **English** phonology.
Their rule sets were built so that Smith and Smyth collide. Four specific
mismatches make them unsuitable for romanised Indian names:

**`h` is treated as a consonant.** In romanised Indic names `h` is usually an
*aspiration marker* on the preceding stop. `bh`, `dh`, `gh`, `kh`, `ph`, `th`
are single phonemes, not consonant clusters. Soundex happens to give Bhatt and
Batt the same code, but that is luck — with Ghosh/Gosh the `h` falls in a
different position and the codes diverge.

**Vowels are handled backwards.** Indic romanisation varies vowel length almost
freely (Sita/Seeta, Rahul/Raahul) while keeping the consonant skeleton stable.
English encoders keep the first letter verbatim and drop the rest, so a name
beginning with a vowel gets a code driven by the least stable character in it.

**No retroflex/dental or sibilant model.** Latin script cannot express the
retroflex/dental contrast, so romanisers pick arbitrarily. Sanskrit's three
sibilants are merged in most modern speech and written interchangeably. No
English encoder models either.

**`ksh` and `x` are the same sound.** Lakshmi and Laxmi are one name. No
English encoder knows this.

### 1.2 The rule set

Implemented in `matchers/indic.py`, applied in this order.

**Stage 1 — orthographic pre-normalisation.** Unify Latin spelling conventions
before any phoneme mapping:

| Rule | Example |
| --- | --- |
| `x` → `ksh` | Laxmi → Lakshmi |
| `cch` → `ch` | |
| `ck` → `k` | |
| `q` → `k` | Farooq / Farook |
| `w` → `v` | one phoneme in most Indic languages; Dhawan / Dhavan |
| `aye` → `ai` | Ayesha / Aisha — the `y` sits inside the diphthong |
| `f` → `ph` | Farid / Pharid |
| `z` → `j` | Hindi has no native /z/; Zubair and Jubair both occur |

**Stage 2 — final `-y` is a vowel.** Word-final `y` is rewritten to `i`.
Ganguly/Ganguli and Reddy/Reddi are the same name. Only a non-final `y` is the
consonant /j/.

**Stage 3 — retain the initial vowel.** If the token begins with a vowel, its
class (`a`, `i`, `u`, `e`, `o` after length and diphthong collapse) is kept as a
prefix. Word-initial vowels are stable across romanisations; dropping them
would merge Amit with Umesh.

**Stage 4 — digraph to phoneme.** Longest first:

```
ksh → X     chh → C     ngh → N     nh → N      ng → N
ny  → N     gn  → N     bh  → B     ph → P      dh → D
th  → T     gh  → G     kh  → K     jh → J      ch → C
sh  → S     ss  → S     zh  → S
```

Aspiration is consumed here, so it never contributes a separate `h`. `ngh`/`nh`
collapse the aspirated nasal: Singh, Sinh and Sing all reach `SN`.

**Stage 5 — single characters.**

```
k→K  g→G  c→C  j→J  t→T  d→D  p→P  b→B
s→S  h→H  m→M  n→N  l→L  r→R  v→V  y→Y
```

`T` covers both retroflex and dental coronals; `S` covers all three sibilants.

**Stage 6 — degemination, before vowels are dropped.** Adjacent identical
phonemes collapse: Bhatt → Bhat, Siddiqui → Sidiqui.

Order matters here and getting it wrong is subtle. Shashi is /ʃ/-a-/ʃ/-i — two
separate sibilants, not a geminate. Collapsing after the vowels are gone turned
it into the single-character code `S`, which would have collided with a large
fraction of the inventory. Degemination therefore runs while the vowels are
still in place.

**Stage 7 — drop non-initial vowels.** What remains is the consonant skeleton
plus any initial-vowel prefix.

Surviving `h` is a genuine /h/ — the aspirated stops were consumed in stage 4 —
so it is kept: Rahul → `RHL`, Hussain → `HSN`.

**Stage 8 — optional voicing merge (`dravidian` mode).** `G→K`, `J→C`, `D→T`,
`B→P`. Tamil, Telugu, Kannada and Malayalam scripts do not mark voicing on
stops, so Venkatesh/Vengadesh and Kadam/Katam are the same name. Off by default
because merging voicing everywhere costs discrimination on names from languages
that do mark it. Both settings are benchmarked; neither is asserted correct.

### 1.3 What the encoder deliberately gives up

Dropping non-initial vowels is a recall-favouring trade with real costs, all
measured rather than argued away:

| Collision | Status |
| --- | --- |
| Rahul / Rahil → `RHL` | different names, merged |
| Patel / Patil → `PTL` | different surnames, merged |
| Mohammed / Mahmud → `MHMD` | different names, same skeleton |
| Kumar / Kumari → `KMR` | related forms, merged |

These are why the encoder is scored against the same hard negatives as
everything else. An encoder evaluated on positives alone would look far better
and mean far less.

The encoder also cannot help with **Bengali anglicisation**
(Chatterjee/Chattopadhyay) because that divergence is historical rather than
phonological, or with **abbreviation** (Mohammed/Md), or with **cross-script**
pairs. The results report each of these as a distinct failure.

### 1.4 The comparison strategy, and why it is benchmarked separately

The encoder is half the method. `IndicPhoneticMatcher` adds:

- honorific stripping, and truncation at a relational qualifier (`S/o`, `W/o`) —
  everything after one belongs to a different person;
- greedy best-match token alignment, so name-order inversion costs nothing;
- initials matched against any token whose code starts with the same phoneme,
  scored at 0.55 rather than 1.0 — an initial is *consistent with* an expansion,
  not evidence for it;
- low-information tokens (Kumar, Devi, Singh, Das) weighted at 0.25;
- normalisation by the **heavier** side's total weight.

That last choice was originally the *lighter* side, so that an added patronymic
would not sink the score. It made "Gurpreet Gill" and "Gurpreet Singh Gill"
score exactly 1.0 — indistinguishable from a true variant match — so no
threshold separated the suffix-only hard negatives and recall at a 1%
false-positive budget was **zero**, however good the phonology. Normalising by
the heavier side keeps a genuine variant at 1.0 and puts a subset match near
0.89.

`IndicPhoneticExactMatcher` is the ablation: same encoder, no alignment, no
weighting, order-sensitive. The gap between the two prices the comparison layer
separately from the phonology.

Every phonetic baseline is wrapped in the **same** alignment and weighting.
Scoring Soundex positionally while scoring the Indic encoder with alignment
would credit the alignment to the phonology.

## 2. Corpus construction

### 2.1 Seeds

Synthetic identities assembled from ~1,070 hand-compiled name **components**
across 11 origin categories, using per-origin structure templates. Not seeded
from sanctions lists — see `DATA_SOURCES.md` for the reasoning and the
limitations of the frequency tiers.

Per-origin templates matter: Indian naming is not one system. A Tamil name may
be an initial plus a personal name with no family name; a Telugu name leads
with a house name; a Punjabi name carries Singh or Kaur in a slot that is
neither given nor family. Generating everything as given-plus-surname would
erase the structural variation the benchmark exists to measure.

### 2.2 Transformations

43 rules in 7 families. Each application records family, rule id, and
before/after text; the per-transformation breakdown is a groupby over those
records, and the provenance chain is asserted in the tests.

**Scope.** Each rule declares `ALL` or `ONE`. `ALL` models a consistent
transliterator — someone who writes "Batt" for "Bhatt" drops the other
aspirates too. `ONE` models a local accident: typos, OCR damage, single
hypercorrections. Conflating them would make severity mean different things in
different families without saying so.

**Origin gating.** Sanskritic processes (schwa retention and deletion, ksha/x)
skip Arabic/Persian tokens, and Sanskritic filler (Kumar, Devi, Lal) is not
attached to Arabic/Persian identities. Without this the generator manufactures
variant density in precisely the category the fairness analysis measures,
turning a modelling error into the headline finding.

**Phonotactic constraint.** Rules are constrained so they do not emit strings no
romanisation system produces. `Bhatht`, `Lakhshmi`, `Sidhdiqui`, `Kreeshna`,
`Hussaain` and `Rames` were all generated by earlier versions and are now
regression tests. Impossible inputs are invisible in aggregate metrics — they
just make every matcher look worse against data that never occurs.

Rules are phonotactically constrained but not *lexically* filtered, so some
generated variants are plausible-but-unattested (Ganguly → Ghanguly is the same
operation as Gosh → Ghosh, which is attested). This is a known property, not a
bug: screening systems meet novel spellings too.

### 2.3 Severity

Severity 1–5 is the number of **distinct rule applications** stacked onto the
seed, drawn preferentially from distinct families. It is an ordinal
construction parameter, not a distance — severity 4 does not mean "twice as
different as 2".

Every variant records `surface_distance` (normalised Levenshtein from the seed)
so the relationship can be **checked** rather than assumed. It rises
monotonically, roughly 0.24 → 0.60 across severities 1–5, with substantial
spread within each level.

A target-edit-distance band was considered as an alternative definition and
rejected: it would make severity a function of the matcher's own metric, so the
degradation curve of any edit-distance matcher would be partly definitional.

**Backfill and rejection.** Most rules do not apply to most names. Sampling
`severity` rules and applying whichever stick left the majority of severity-1
requests with zero transforms applied — variants identical to their seed. Those
are not easy positives, they are degenerate ones. The generator now backfills
from the wider pool, holding the token/string level split fixed so the family
mix stays as sampled, and re-draws when inverse rules (collapse + insertion)
cancel out.

### 2.4 Splits

| Split | Contents | Purpose |
| --- | --- | --- |
| `degradation` | mixed-family variants, severity 1–5 | degradation curve |
| `family` | single-family variants, severity 1–3, from eligible identities only | per-transformation breakdown |
| `cross_script` | curated native-script pairs | script-independence floor |
| `negatives` | 5 hard constructions + easy calibration pairs | discrimination |

The `family` split exists because natural firing rates are wildly uneven:
`transliteration` fires on over 60% of a mixed corpus, `bengali_anglicisation`
on about 1.4%. Per-family attribution from the mixed split would rest on a few
dozen samples in some cells. Restricting the registry to one family and drawing
only from eligible identities gives every family a comparable sample and makes
attribution exact rather than inferred from co-occurring rules.

`cross_script` is separate because Latin-only matchers score zero on it by
construction; folding it into the aggregate would swamp every other signal.

### 2.5 Negatives

| Construction | What it probes |
| --- | --- |
| `same_given_diff_surname` | token-set matchers that weight all tokens equally |
| `same_surname_diff_given` | both given names high-frequency |
| `shared_initials` | "R. Venkatesh" vs "Rajagopal Venkatesh" — willingness to expand an initial |
| `suffix_only_difference` | affix stripping: fixes false negatives, creates false positives |
| `identical_collision` | the name-only ceiling |

`identical_collision` pairs have **identical strings**, so no name-only method
separates them at any threshold. They are excluded from headline metrics and
reported separately. Their share of the negative set would otherwise set a
precision ceiling determined by a sampling choice rather than by any algorithm.
The ceiling is a real operational fact — it is why screening needs date of
birth and address — but it is not a property of the matchers.

Two constructions were wrong in the first implementation and are now asserted
in tests: `shared_initials` initialled *both* sides, producing identical strings
that duplicated `identical_collision`; `same_surname_diff_given` fired on
initial-led Dravidian names with no surname at all.

## 3. Evaluation

### 3.1 Base rate

Pairs are labelled once. The base rate enters only where it belongs:

```
precision(pi) = pi*TPR / (pi*TPR + (1-pi)*FPR)
alerts per N  = N * (pi*TPR + (1-pi)*FPR)
```

TPR and FPR are conditional on the true class and do **not** vary with base
rate. Precision, alert volume and analyst cost do, dramatically. Sweeping
10⁻² through 10⁻⁶ is therefore exact and free.

**The assumption, stated plainly.** Hard negatives are drawn from the
confusable region, not uniformly from all possible pairs. Measured FPR is
therefore higher than a uniform draw at the same base rate would give, and
absolute alert volumes should be read as **upper bounds**. Relative comparisons
between matchers are unaffected — every matcher is scored against the same
negative set.

### 3.2 Metrics

**Recall at a fixed false-positive budget** (0.1%, 1%, 5%) is the primary
metric. Alert capacity is fixed, so the operational question is never "what is
the F1" but "how many true matches do we catch inside the budget we have".

**AUC-PR** is reported alongside, computed at the sample's own base rate — so
comparable across matchers here, but not to a number from a corpus with
different class balance.

Ties are handled block-wise. Walking tied scores item by item consumes them in
input order, and since the evaluation set is built positives-then-negatives,
that credited every tied positive first. Coarse matchers emit almost nothing but
ties, so the effect was not marginal: plain string equality scored AUC-PR
**1.000** while recovering 2.8% of positives.

**Alert volume** converts an accuracy delta into analyst-hours at a stated
**4 minutes per alert**. That figure is an assumption, not a measurement; every
analyst-hour number scales linearly with it.

**Latency** is wall-clock per pair. Implementations are the ones anyone would
deploy — the C Levenshtein where available, batched embedding transforms —
because timing a teaching implementation would misreport deployability.

### 3.3 Fairness

False-positive rate stratified by name-origin at **one global threshold**, set
from the pooled data at a 1% FPR budget. A global threshold is the point:
production systems set one, and if it is mis-calibrated per community then some
groups absorb more false positives through a purely technical mechanism. Using
per-origin optimal thresholds would hide exactly the effect under test.

Disparity ratios are reported against the lowest-FPR origin, with intervals
built from Wilson bounds on each rate rather than a delta-method approximation
on the log ratio — the latter behaves badly when either rate is near zero, which
is routine at a 0.1% budget.

### 3.4 Tier sensitivity

The frequency tiers are hand-assigned, and the per-origin disparity depends on
the collision structure they produce, so `benchmarks/tier_sensitivity.py` tests
whether the finding survives them being wrong. It re-runs corpus generation and
the fairness analysis with tier labels permuted within each origin (preserving
each origin's histogram, randomising which names are common) and with all tiers
flattened to 1.

The mechanism is `inventory.set_tier_override()`, which invalidates
`load_components`, `components_for` and `ambiguous_forms`. That invalidation is
load-bearing: a stale cache would return unperturbed components and the analysis
would report that nothing changed, which reads as a reassuring result rather
than as the bug it is.

Findings §6.2–6.4 report the outcome. The disparity survives all three regimes;
the *mechanism* originally proposed for it did not.

Limitations are in `reports/findings.md` and `DATA_SOURCES.md`, and they are
substantial. The most important: origin categories are a proxy for
transliteration convention rather than for any group identity, and the
frequency tiers driving the corpus distribution are hand-assigned rather than
measured.

## 4. Reproducibility

Every number comes from `benchmarks/run_all.py`, which is a pure function of
`CorpusConfig` plus a fixed seed. The manifest in the released snapshot records
the config, its SHA-256 fingerprint, the library version and the inventory
counts.

Random seeds are derived per stage (`sha256(seed | stage_tag)`) so that adding a
stage does not shift the output of earlier ones. The SVD in the character
embedding matcher is seeded explicitly; an unseeded one would make every
reported number irreproducible from the committed config.
