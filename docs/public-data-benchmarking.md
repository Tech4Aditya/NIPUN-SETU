# Public evidence and benchmark layer (v3.5)

## What is preloaded

The application seeds a source-attributed benchmark registry from published reports:

- **ASER 2024**: selected all-India rural estimates and 2018/2022/2024 trend points for Std III reading and subtraction, Std V reading and division, plus the Uttar Pradesh Std III government-school reading estimate. These are household-survey estimates, not school census values.
- **PARAKH Rashtriya Sarvekshan 2024**: Grade 3 national competency-level percentages correctly answered, and national survey coverage counts. Coverage counts are not learning outcomes.
- **UDISE+**: official portal/catalog source metadata and existing school-master CSV ingestion; no protected login is bypassed.
- **DIKSHA**: official resource discovery link; no claim of private API access or resource completion tracking.

## Official source references

- ASER 2024 reports and state pages: https://asercentre.org/aser-2024/
- ASER 2024 national findings PDF: https://asercentre.org/wp-content/uploads/2022/12/ASER-2024-National-findings.pdf
- ASER research data access: https://asercentre.org/aser-survey/ (ASER Centre asks researchers to contact them for datasets)
- PARAKH 2024 report portal: https://parakh.ncert.gov.in/prs-reports-2024/
- PARAKH 2024 national report: https://parakh.ncert.gov.in/sites/default/files/2025-07/REPORT_India_IND.pdf
- PARAKH dashboard: https://dashboard.parakh.ncert.gov.in/en
- UDISE+ portal: https://www.udiseplus.gov.in/
- UDISE+ OGD catalog: https://www.data.gov.in/catalog/unified-district-information-system-education-plus-udise-plus
- DIKSHA: https://diksha.gov.in/

## Important comparability rules

1. ASER is a household-based survey in rural India; do not treat an ASER aggregate as a school's census result.
2. PARAKH is a sampled large-scale assessment for Grades 3, 6 and 9; aggregate reports do not provide a child roster.
3. ASER percentages are the share of children reaching a defined task level. PARAKH competency values are the percentage of questions answered correctly. These are different constructs and must not be combined into a common score without a documented linking study.
4. Grade labels and task definitions must be retained exactly as published. Std III ASER ability to read Std II text is not equivalent to a local 0-100 reading score.
5. State/district aggregate CSV rows require an official HTTPS source URL and source page/table reference. Imports are stored in `public_benchmarks`, not learner assessment tables.
6. School-master data and learning outcome aggregates are kept separate. No inference is made that a school participated in ASER or PARAKH.

## Import workflow

1. Sign in as block officer, state admin or admin.
2. Open **Public benchmarks**.
3. Download `nipunsetu_public_aggregate_template.csv`.
4. Populate only published state/district aggregate values; preserve the indicator, year, geography, unit and definition.
5. Cite the official report URL and exact page/table in `source_page`.
6. Upload the CSV. Duplicate rows are ignored and invalid rows are returned with row-level errors.

## Data access reality

There is no unauthenticated universal live API for all ASER/PARAKH/UDISE+ microdata. This product includes a usable published-aggregate registry and CSV adapters. ASER research microdata is requested from ASER Centre; protected UDISE+ exports require the correct portal access; learner-level state assessment data requires the data controller's approval and pseudonymisation.
