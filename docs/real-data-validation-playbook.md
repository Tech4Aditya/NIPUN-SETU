# NIPUNSetu: real-data onboarding and validation playbook

## What can be connected now

1. **School master:** upload an 11-digit UDISE+ school code, school name, block, district and state using `POST /api/import/school-master`. The endpoint upserts school metadata and records an audit event. It does not import enrolment or learning outcomes.
2. **Pseudonymous roster:** upload `POST /api/import/authorised-roster` with `learner_id, school_udise_code, grade, attendance_pct` and a data-sharing approval reference. The endpoint creates/updates only minimal pseudonymous roster records; it does not accept names or direct identifiers. Keep any re-identification key with the data controller, outside NIPUNSetu.
3. **State assessment observations:** use `POST /api/import/state-assessment` with the v2 canonical CSV contract in `data-import-and-ml-validation.md` and provide the approval/reference ID. Each row must preserve source system, source record ID, date, domain and competency code. Batches without an approval reference are rejected.
4. **Validation:** `GET /api/validation/readiness` reports coverage and source labels. `GET /api/analytics/ml-validation` refuses to report metrics unless it has enough paired observations and can create a strict unseen-school + future-time holdout.

## Important source boundaries

- **UDISE+** is suitable for school master and system/school context subject to the applicable access terms and permissions. The official microdata portal requires login/data request for restricted data. Public aggregate reports are not learner-level assessment records.
- **PARAKH Rashtriya Sarvekshan 2024** is a sample-based system assessment. Its official operational guidance says reporting is at district/state/national level and it does not provide individual student or school performance scores. Do not infer individual learners or treat PARAKH aggregate results as longitudinal classroom records.
- **ASER** is a household survey and its published findings are survey estimates. Use the published reports for contextual district/state benchmarking where available; do not fabricate student-level records from them.
- **State assessment systems** are the appropriate candidate source for repeated learner-level competency observations, only where the state/data controller authorises that use and provides a lawful sharing basis.

## Required canonical assessment columns

`learner_id, school_udise_code, grade, assessment_date, domain, competency_code, score, source_system, source_record_id, attendance_pct`

- `learner_id` must be pseudonymous and stable across terms, but not directly identifying.
- `score` must be 0–100 only after the source assessment scale is mapped and documented. If source scales differ, preserve raw score and use a documented equating/mapping process; do not silently rescale.
- `competency_code` must preserve the source competency identifier. A broad reading/numeracy label is not a substitute for competency equivalence.
- Duplicate source rows are idempotently ignored using `(source_system, source_record_id)`.

## Model validation protocol

The model target is an observed gain of at least 8 points between the first two observations for the same learner-domain-competency pair, separated by at least 14 days. Features are baseline score, baseline attendance, grade and domain indicator.

The validation endpoint only reads observations attached to an import batch with an entered authorisation reference. This is a workflow gate, not independent proof of permission; an administrator must verify the underlying approval document. The validation endpoint applies a dual holdout:
- Training: earlier outcome dates from schools not assigned to the holdout group.
- Test: later outcome dates from held-out schools only.

Metrics include accuracy, precision, recall, F1, Brier score, ROC AUC and majority-class baseline. If sample count or class balance is inadequate, the API returns an `insufficient_*` status instead of weakening the split or manufacturing metrics.

This is predictive validation, not causal impact evaluation. To estimate whether an intervention caused improvement, use a pre-registered comparison design (for example, a stepped-wedge or matched comparison with baseline balance checks), document assignment and dosage, and account for clustering by school/classroom. Never use a risk score to deny support or punish learners.

## Minimum governance checklist before real deployment

- Written approval/data-sharing agreement from the relevant state/data controller.
- Purpose limitation, retention period, access matrix and deletion process.
- Data protection impact assessment and security review.
- Pseudonymisation performed by the data controller; re-identification key kept separately.
- Role-scoped access, encryption in transit/at rest, secrets rotation, backups and audit review.
- Assessment comparability, missingness, language and disability-related fairness review.
- Independent validation on a later term and schools never used for training or model selection.

## Official references

- PARAKH 2024 dashboard: https://dashboard.parakh.ncert.gov.in/en
- PARAKH 2024 operational guidance / reports: https://parakh.ncert.gov.in/prs-reports-2024
- PARAKH 2024 national report: https://parakh.ncert.gov.in/sites/default/files/2025-07/REPORT_India_IND.pdf
- UDISE+ data sharing portal: https://microdata.udiseplus.gov.in/
- UDISE+ publications: https://udiseplus.gov.in/
- Open Government Data UDISE+ catalog: https://www.data.gov.in/catalog/unified-district-information-system-education-plus-udise-plus
- DIKSHA FLN: https://diksha.gov.in/fln.html
