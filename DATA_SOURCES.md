# Data sources and provenance

## Summary

Every name in the released corpus is **synthetic**. Identities are assembled by
sampling from an inventory of name *components* — given names, surnames,
honorifics, suffixes — and variants are derived from those identities by
declared rules. No entry in this repository is a record of a real person, and
no file here was derived from a register of individuals.

| Artifact | Status | Licence |
| --- | --- | --- |
| `src/indic_name_bench/seeds/data/*.yaml` | Committed. Name components, hand-compiled. | Apache-2.0 (with the repo) |
| `src/indic_name_bench/variants/data/*.yaml` | Committed. Transformation rule tables. | Apache-2.0 |
| `data/generated/snapshot-v0.1.0/` | Committed. Fixed-seed corpus for citability. | CC BY 4.0 |
| `data/seeds/` | **Never committed.** Gitignored cache for sanctions lists. | Per upstream |

## Why the corpus is not seeded from sanctions lists

The original design called for seeding from OFAC SDN, the UN Consolidated List,
the EU Consolidated List and UK OFSI. Those lists are public, and loaders for
them ship in `seeds/sanctions.py` for anyone who wants to regenerate locally.
They are not used for the released corpus, for two reasons.

**Ethics.** Sanctions lists name real individuals. A variant corpus seeded from
them would be an expanded, machine-generated set of spelling variants of real
listed people — which is to say, a de-facto screening list, redistributed under
this project's name and beyond what the issuing authority published. The
project's own data rules forbid that, and the rule is right: publishing
thousands of synthetic misspellings of a real person's name creates a
match-surface that authority never sanctioned.

**Reproducibility.** Sanctions lists change daily and are unversioned at the
URL. A corpus seeded from them is not reproducible from a config and a seed,
which defeats the point of a citable benchmark.

The component inventory has neither problem, and it also gives something the
sanctions lists cannot: controlled coverage across all eleven origin
categories, which the fairness analysis needs.

## Component inventory

**What it is.** ~1,070 name components across 11 origin categories: 697 given
names, 361 surnames, 16 low-information filler tokens, plus honorifics,
community suffixes, relational qualifiers and house-name prefixes.

**Where it came from.** Hand-compiled from general knowledge of South Asian
naming conventions and published reference works on Indic and Arabic/Persian
name romanisation. No scraping. No electoral rolls. No leaked datasets. No
social-network data. Nothing derived from a record of individuals.

**Why that is defensible.** These are generic linguistic tokens. "Sharma" and
"Rahul" are no more personal data than "Smith" and "John". The combinations the
assembler produces are synthetic, and any collision with a real person's name
is coincidental in the same way that any list of common first and last names
collides with real people.

### Known limitation: frequency tiers are not measured

Components carry an ordinal frequency tier (1–4) that controls sampling weight.
**These tiers are hand-assigned judgements, not measured frequencies.** No
openly licensed Indian name-frequency corpus was reachable from the build
environment, so nothing here is calibrated against observed data.

This matters most for the fairness analysis, which compares false-positive
rates across origin categories. If the real frequency distribution within a
category is materially different from the assumed one, the disparity ratios
shift. Findings that depend on the precise shape of the distribution are
labelled provisional in `reports/findings.md`. Findings that depend only on
*variant density* — how many spellings one name has — are more robust, because
variant density is a property of the orthography rather than of the frequency
weights.

Replacing the tiers with measured frequencies is the single highest-value
contribution an outside reader can make.

### Known limitation: origin categories are approximate

Origin categories are a coarse proxy for transliteration convention. They are
not ethnicity, not religion, not nationality. Twenty surnames in the inventory
appear under more than one origin (Sharma, Joshi, Patil, Rao, Das, Nayak,
Varma, Kulkarni, Prasad, Singh and others); the assembler picks one at sample
time and flags the identity as `origin_ambiguous`, and the fairness analysis
reports what fraction of each stratum carries that flag.

## Transformation rule tables

`variants/data/lexical_variants.yaml` enumerates 96 equivalence classes
covering 338 spellings — cases where one name has several spellings that no
character-level rule derives from one another (Mohammed/Mahomed,
Chatterjee/Chattopadhyay, Abdurrahman/Abdul Rahman).

Compiled from published transliteration guidance and standard reference works
on Arabic and Persian name romanisation, cross-checked against the spelling
variants that the public sanctions lists record in their own alias fields —
OFAC SDN and the UN Consolidated List both carry multiple romanisations per
listed name, and those alias groupings are evidence about *orthography*, which
is what was used. No individual's name was copied into this repository.

Classes are checked to be disjoint (`tests/test_variants.py`). Entries that
would have merged genuinely distinct surnames were removed during review —
Patil/Patel, Chavan/Chauhan, Venkatesh/Venkatesan — because labelling those as
one identity would inject false positives directly into the ground truth.

## Optional: regenerating against real sanctions lists

`seeds/sanctions.py` provides loaders for the four public lists. They cache to
`data/seeds/`, which is gitignored. Output of a sanctions-seeded run must not
be committed or redistributed.

| List | Publisher | Terms |
| --- | --- | --- |
| SDN | US Treasury OFAC | US Government work, public domain |
| Consolidated List | UN Security Council | Public, UN terms of use |
| Consolidated List | European Union | Public, EU reuse policy |
| Consolidated List | UK OFSI / HM Treasury | Open Government Licence v3.0 |

**These loaders were not executed when this corpus was built.** The build
environment's egress policy denied all four hosts (HTTP 403 at the proxy), so
no sanctions data was fetched, cached, or used. The loaders are unexercised
code paths; treat them as untested until someone runs them with network access.

## What is deliberately absent

- No scraped data of any kind.
- No electoral rolls, voter lists, or census microdata.
- No leaked or breached datasets.
- No social-network or professional-network profiles.
- No assembled list that could function as a screening list of real people
  beyond what the issuing authorities already publish.
