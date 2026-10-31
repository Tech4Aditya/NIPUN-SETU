# NIPUNSetu — Local-to-public benchmark comparison (v3.6)

## Purpose

The comparison workspace puts school-level assessment observations beside published ASER/PARAKH/state evidence while preventing false equivalence between different measures.

## Two separate data layers

1. **Local school observations** (`local_benchmark_observations`): pseudonymous, school-level aggregate observations imported from an authorised assessment export. No learner names are required. The importer requires a provenance/approval reference, grade, indicator, value/unit, population, administration mode, instrument, sampling design, assessment date and sample size.
2. **Aligned public references** (`aligned_public_references`): published aggregate rows with official source URL and the same measurement-contract metadata. The importer only accepts recognised education source IDs and official HTTPS source domains.

Existing seeded ASER/PARAKH observations remain in the public benchmark registry. They intentionally remain **contextual** because the seed does not carry a complete measurement contract for every indicator.

## Direct-comparison rule

A direct descriptive difference is produced only when all of these fields match exactly:

- Grade and domain
- Indicator identifier
- Unit
- Target population
- Assessment administration mode
- Assessment instrument/protocol
- Sampling design

If any field differs or is missing, the public figure is displayed as contextual only. The engine does not subtract local mean scores from ASER task-attainment prevalence or PARAKH percent-correct figures.

Even an exact protocol match does not establish statistical equivalence or causality. Users must review sample sizes, sampling frame, weighting, confidence intervals, non-response, assessment dates and data quality before using differences for policy decisions. The current prototype displays descriptive differences only; it does not calculate confidence intervals or significance tests.

## API

- `GET /api/comparison/overview?school_id=SCH001&grade=3&domain=reading`
- `GET /api/comparison/template` — local observation CSV template
- `POST /api/comparison/import-local` — approved local school observations
- `GET /api/comparison/reference-template` — aligned public reference CSV template
- `POST /api/comparison/import-reference` — published source reference with protocol metadata

Both imports are restricted to block officer, state administrator and admin roles. CSV size is capped at 5 MB; row errors and duplicates are reported. Imports are audit logged.

## Demo caveat

The included school/learner database is demonstration data. The prototype does not have authenticated UDISE+, ASER, PARAKH or SCERT access. Do not treat demo learner means as real school results. Do not enter identifiable child data. Use only authorised, appropriately minimised records.
