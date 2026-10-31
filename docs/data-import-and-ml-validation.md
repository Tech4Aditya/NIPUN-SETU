# NIPUNSetu v3.3 — Assessment ingestion and outcome validation

## What changed

- Added a versioned learner-assessment observation store with competency codes, source system, source row ID, assessment date, import batch and attendance snapshot.
- Added CSV import with a 10 MB limit, required-column checks, date/domain/score validation, UDISE school lookup, pseudonymous learner mapping, grade/school consistency checks, row-level rejection reasons and idempotency on `(source_system, source_record_id)`.
- Restricted the new state-assessment import to block officer, state admin and admin roles. Teachers cannot bulk import district/state records.
- Added import batch audit endpoints and a CSV template endpoint.
- Added competency-level paired progress summaries and intervention-linked reassessment summaries.
- Replaced the misleading same-feature proxy classifier endpoint with a baseline-to-future-gain logistic regression. It predicts whether a learner-domain pair gains at least 8 points between first and latest observations. Entire schools are held out together to reduce school leakage.
- Fixed learner grade filter handling for empty/all sentinel values.

## Run

From the repository root in PowerShell:

```powershell
.venv\Scripts\activate
pip install -r backend/requirements.txt
python backend/run.py
```

Frontend:

```powershell
python -m http.server 8080 --directory frontend
```

## Import contract

Required CSV columns:

`learner_id,school_udise_code,grade,assessment_date,domain,competency_code,score,source_system,source_record_id`

Optional: `attendance_pct`.

Use a state-approved pseudonymous learner identifier. The learner must already exist in the authorised roster and be mapped to the given school and grade. UDISE code must exist in the local school master. Scores are interpreted on a 0–100 scale; do not combine different source scales without a documented transformation and retained raw score.

A synthetic import example is at `docs/samples/state_assessment_demo.csv`. It is deliberately labelled `SYNTHETIC_IMPORT_DEMO`; it is not a government export.

## New endpoints

- `GET /api/import/template`
- `POST /api/import/state-assessment` (multipart CSV; block/state/admin only)
- `GET /api/import/batches` (non-teacher)
- `GET /api/analytics/competency-outcomes`
- `GET /api/analytics/intervention-effectiveness`
- `GET /api/analytics/ml-validation`

## Model validation protocol

- Features: baseline score in target domain, baseline score in other domain, attendance snapshot, grade and domain indicator.
- Outcome: at least 8-point change from earliest to latest observed assessment for the same learner-domain pair.
- Split: deterministic school-held-out split; all learner-domain records from a school stay in one partition.
- Metrics: accuracy, precision, recall, F1, Brier score and confusion matrix.
- If the held-out partition lacks both classes, the endpoint returns `insufficient_class_balance` instead of manufacturing a score.

### Limits

The included history is synthetic. The score change outcome is observational and is not evidence that an intervention caused improvement. The model is an engineering demonstration, not a validated decision model. External validation requires an authorised dataset, a frozen model, later-term outcomes from unseen schools, calibration checks, subgroup error analysis, independent review and human oversight. Predictions must never determine eligibility, grading, discipline or denial of support.

## Source and governance boundary

This release does not connect to UDISE+, PARAKH, ASER or a state assessment server. A government data-sharing agreement, approved API/export, current school master, documented field mappings and security review are prerequisites. ASER and PARAKH aggregates remain aggregate evidence and are not converted into individual learner records.
