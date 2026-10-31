# Data Governance & Interoperability Proposal

## Canonical learner/assessment contract

Minimum shared dimensions: pseudonymous learner ID, UDISE+ school code (where authorised), grade, assessment domain, instrument, competency code, raw score, normalised score (if valid), proficiency band, assessment date, reporting period, source system, source schema version and transformation lineage.

Never discard raw values. A normalised score is only comparable where the assessment instrument and mapping support comparability. Attendance must include its denominator and reporting period. Missing values must remain missing, not be converted to zero.

## Source-specific boundaries

- **UDISE+:** use authorised school master and approved aggregate/administrative fields. Do not imply that UDISE+ provides every learner's competency-level assessment record.
- **PARAKH:** use published/authorised assessment frameworks and aggregate results for system benchmarking. Do not fabricate student-level joins from national survey results.
- **ASER:** household survey estimates provide contextual evidence about foundational learning. They are not a school MIS learner roster.
- **State assessment platforms:** potential source of learner-level diagnostic events, subject to state authorisation and compatible identifiers.
- **DIKSHA:** potential teacher resource/catalogue mapping; content recommendation should be aligned to diagnosed competency and language/context.

## Governance controls

1. Purpose limitation: use data for learning support and system improvement, not punitive teacher ranking.
2. Data minimisation: collect only fields needed for intervention; no Aadhaar or unnecessary identifiers in this prototype.
3. Access: teacher sees own school; block sees authorised block aggregate; state sees state aggregate. Production must enforce this at database/query layer.
4. Lineage: record source, upload actor, import time, schema version and validation outcome.
5. Quality: quarantine invalid records, retain rejected-row reasons and support correction workflows.
6. Human oversight: teacher validates the learning gap and selects an intervention; model/rule output is advisory.
7. Security: TLS, encryption at rest, secrets management, backups, monitoring and incident response.
8. Lifecycle: documented retention, archival and deletion rules; access review and audit.

## Prototype limitations

The current build uses synthetic records and simplified demo roles. It is not a compliant government data platform and has not undergone a privacy impact assessment or security audit. Production use requires formal approvals, data-sharing agreements and legal/security review under applicable Indian requirements.


## Demo data provenance (v3.2)

Six school names and UDISE identifiers are sourced from a public school directory that attributes its records to UDISE+; remaining schools and all learner-level records are synthetic. Validate every identifier against the current authorised UDISE+ master before operational use. Public school directory: https://in.knowyourschools.com/directory/uttar-pradesh/gautam-buddha-nagar. DIKSHA FLN discovery reference: https://diksha.gov.in/fln.html.
