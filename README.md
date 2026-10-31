# NIPUNSetu 3.3 — FLN Decision-Support Platform

A hackathon prototype for the Theme 2 problem: turning existing school records into teacher actions and administrative feedback.

## Run locally (Windows PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r backend/requirements.txt
$env:NIPUNSETU_SECRET = "replace-with-a-long-random-secret"
python backend/run.py
```

In a second terminal, from the project root:

```powershell
python -m http.server 8080 --directory frontend
```

Open http://localhost:8080. API docs: http://localhost:8000/docs. Health: http://localhost:8000/api/health.

## Demo accounts

| Role | Email | Password | Scope |
|---|---|---|---|
| Teacher | teacher@demo.in | teacher123 | Assigned school only |
| Block officer | block@demo.in | block123 | Gautam Buddha Nagar demo district |
| State admin | state@demo.in | state123 | Demo state view |
| Admin | admin@demo.in | admin123 | Prototype-wide access |

**Important:** The teacher role intentionally sees one assigned school in learner, school and map views. Sign out and use `block@demo.in` to inspect the multi-school / multi-block network. This is role-scoped access, not missing seed data.

## What is included

- 30 school records across the four Gautam Buddha Nagar education blocks represented in the public directory: Visrakh, Dadri, Dankaur and Jewar.
- 6 named government schools with UDISE identifiers taken from a public directory that attributes records to UDISE+; other 24 schools are explicitly synthetic demo schools.
- 440 synthetic learner records, 1,600 synthetic assessment observations and generated interventions. Learner scores, attendance, names and intervention history are not real school records.
- Learner search, grade/risk filters, reassessment, intervention tracking, block-level aggregation, CSV import/export, audit trail and role-based access.
- 61 competency-aligned activity plans. These are curated/teacher-use activity plans with a link to the official DIKSHA FLN discovery page; they are not claimed to be 60 live DIKSHA catalogue items.
- Provenance-aware assessment observation store and authorised state-assessment CSV adapter with row-level validation, duplicate protection and import audit batches.
- Competency-level longitudinal progress analytics and intervention-linked reassessment summaries.
- Baseline-to-future learning-gain logistic regression with school-held-out evaluation, Brier score and majority-class baseline comparison. Synthetic results are engineering checks, not real-world validation.

## ML validation honesty

`GET /api/analytics/ml-validation` trains a small binary logistic regression using reading, numeracy, attendance and grade features. The synthetic target is defined as `reading < 50 OR numeracy < 45 OR attendance < 75`; it uses a deterministic 80/20 holdout split and reports accuracy, precision, recall, F1 and a confusion matrix. Because the target is generated from the same input features, the metrics validate the software pipeline only. They are **not evidence of real-world predictive validity**. Before real deployment, define an outcome label from a future assessment window, split by school/time to prevent leakage, evaluate calibration and subgroup error, and obtain independent authorised validation. Human review is mandatory.

## Data provenance and limitations

- Named public school records and UDISE identifiers: public school directory referencing UDISE+ records: https://in.knowyourschools.com/directory/uttar-pradesh/gautam-buddha-nagar
- District block labels: same public directory. Validate against the latest authorised UDISE+ school master before production.
- Learning records, attendance, baseline/midline scores, intervention records and all learner names: synthetic demonstration data.
- No live UDISE+, ASER, PARAKH or DIKSHA API connection is implemented. ASER/PARAKH aggregates are not converted into individual learner records.
- DIKSHA FLN reference: https://diksha.gov.in/fln.html. Resource links are discovery links; availability and language must be verified by teachers.
- SQLite is used for local demo runtime. PostgreSQL schema migration remains a separate deployment step.

## Key APIs

- `GET /api/health`
- `POST /api/auth/login`
- `GET /api/dashboard`
- `GET /api/learners?grade=&risk=` (empty grade is valid)
- `GET /api/schools`
- `GET /api/maps/administrative`
- `GET /api/analytics/predictions`
- `GET /api/analytics/ml-validation` (school-held-out future-gain evaluation)
- `GET /api/analytics/competency-outcomes`
- `GET /api/analytics/intervention-effectiveness`
- `GET /api/import/template`
- `POST /api/import/state-assessment`
- `GET /api/import/batches`
- `GET /api/analytics/cohorts`
- `GET /api/analytics/impact`
- `GET /api/resources?domain=&language=&grade=`
- `POST /api/reassessments`

## Security note

Demo credentials and local SQLite are for hackathon demonstration only. Use a managed identity provider, secrets manager, TLS, encrypted managed database, consent/purpose controls, retention policies, security review and authorised data-sharing agreements before any real learner data is processed.


## v3.3 assessment ingestion and model validation

See `docs/data-import-and-ml-validation.md` for the CSV contract, validation design, limitations and new endpoints. A synthetic sample import is available at `docs/samples/state_assessment_demo.csv`. Only upload real records when an authorised data-sharing basis exists.

## v3.3.1 hotfix

Fixed the Risk Analytics frontend crash: the page requested five analytics endpoints but only destructured four results from `Promise.all`, leaving `effectiveness` undefined when rendering intervention-linked reassessment outcomes. The request/result mapping now includes all five responses. FastAPI validation errors are also rendered as readable messages instead of `[object Object]`.

### Quick verification

After starting the backend, open `http://localhost:8000/docs`. The Risk Analytics view uses these endpoints:

- `/api/analytics/predictions`
- `/api/analytics/impact`
- `/api/analytics/cohorts`
- `/api/analytics/ml-validation`
- `/api/analytics/competency-outcomes`
- `/api/analytics/intervention-effectiveness`

The last endpoint may correctly return an empty `items` array until intervention-linked reassessments exist. An empty result is not an API failure.

## Real-data onboarding and longitudinal validation (v3.4)

- Import school directory metadata from the Data Exchange workspace using an 11-digit UDISE+ code.
- Import a pseudonymous learner roster with an approval/reference ID. Learners are created as **Not assessed** until valid assessment observations arrive; they are not assigned fake zero scores.
- Import repeated state assessment observations using the canonical competency-level CSV and a data-sharing approval/reference ID.
- Use **Check readiness** in Data Exchange or `GET /api/validation/readiness` to inspect coverage, provenance labels, number of schools and assessment dates.
- Risk Analytics uses a strict prospective validation protocol: train on earlier outcomes from non-held-out schools and test only on later outcomes from held-out schools. If sample size or class balance is inadequate, it reports `insufficient_*` rather than weakening the split.

The approval-reference field is an auditable workflow gate, not proof of lawful access. Verify the actual agreement with the data controller. PARAKH and ASER public outputs are aggregate/survey sources and must never be reverse-engineered into individual learner records. See `docs/real-data-validation-playbook.md` before importing any real data.


## v3.4 authorised data onboarding + leakage-aware validation

See `docs/real-data-validation-playbook.md`. Added school master CSV upsert, minimal pseudonymous roster import with approval-reference gate, assessment import approval-reference gate, source-batch provenance tracking, validation readiness endpoint, and a dual holdout model evaluation (future outcomes from unseen schools only). The model excludes synthetic/legacy batches and returns insufficient-data statuses instead of weakening validation. This workflow does not itself grant data access or prove that an approval reference is valid.

## v3.5 — Public evidence layer

A new **Public benchmarks** workspace now separates published public evidence from school/learner records.

### Included source-attributed data

- ASER 2024 rural India indicators with 2018/2022/2024 trend points for Std III reading/subtraction and Std V reading/division, plus the published Uttar Pradesh Std III government-school reading estimate.
- PARAKH Rashtriya Sarvekshan 2024 Grade 3 national competency percentages (language and mathematics) and survey coverage facts (children, schools, districts, teacher/school-leader respondents).
- Official source registry and data-boundary notes for ASER, PARAKH, UDISE+ and DIKSHA.
- Public aggregate CSV template and validated aggregate import endpoint.

### New endpoints

- `GET /api/public-data/overview`
- `GET /api/public-data/template`
- `POST /api/public-data/import-aggregate`

The aggregate importer accepts only official HTTPS source URLs from ASER Centre, PARAKH/NCERT, UDISE+ or data.gov.in. It preserves geography, year, grade, indicator, unit, definition and source-page provenance. It writes to `public_benchmarks` and never creates learner records.

### Run and verify

```powershell
.venv\\Scripts\\activate
pip install -r backend/requirements.txt
python backend/run.py
```

Second terminal:

```powershell
python -m http.server 8080 --directory frontend
```

Open `http://localhost:8080`, sign in as `block@demo.in` / `block123`, then select **Public benchmarks**.

Download the aggregate template, populate published state/district values with the exact source page/table, and upload. The API reports inserted, duplicate and rejected rows.

### Critical interpretation rules

- ASER is a rural household survey. Its aggregates are not school-census values.
- PARAKH is a sampled assessment. Its aggregates are not a complete learner roster.
- ASER task-level percentages and PARAKH percent-correct competency scores are different measures and must not be merged into a common score without a linking study.
- UDISE+ school metadata is not FLN outcome data.
- No private API access, government credentials, or learner-level data have been fabricated. State/district reports can be added through the aggregate adapter; protected data requires the relevant access approval.

See `docs/public-data-benchmarking.md` and `docs/samples/public_benchmarks_seed.csv` for source lineage.

## v3.6 — Comparability-aware benchmark engine

The Public Benchmarks workspace now includes a school/grade/domain comparison panel. It shows local learner aggregates separately from public ASER/PARAKH references and labels seeded public figures as **context only** where the underlying measure, population, mode or sampling design is not aligned.

For protocol-aligned comparisons, administrators can import two CSVs: an authorised local school observation and a published reference row. A direct descriptive difference is generated only when grade, domain, indicator, unit, population, assessment mode, instrument and sampling design match exactly. The imports require provenance/source references and are audit logged. This is not a causal impact estimate or a substitute for survey-weighted statistical analysis.

See `docs/benchmark-comparison-methodology.md` for the methodology and CSV/API contracts.
