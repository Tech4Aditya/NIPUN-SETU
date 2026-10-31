# NIPUNSetu 🇮🇳

### Foundational Learning Intelligence & Policy Decision-Support Platform

**Turning India's school data into actionable learning interventions.**

NIPUNSetu is an education intelligence platform designed to bridge the gap between India's existing school data ecosystem and actual foundational learning outcomes.

Built around the objectives of **NEP 2020** and the **NIPUN Bharat Mission**, the platform transforms school-level assessment data into actionable insights for teachers, block administrators and state education authorities.

Instead of treating attendance and assessment records as compliance requirements, NIPUNSetu turns them into a continuous cycle of learning diagnosis, targeted remediation, reassessment and policy feedback.

> **Evidence → Intelligence → Intervention → Reassessment → Policy Feedback**

---

## 🎯 The Problem

India has achieved near-universal school enrolment, but foundational literacy and numeracy remain significant challenges.

Despite the availability of large-scale education datasets through UDISE+, ASER, PARAKH and state assessment systems, important gaps remain:

* Assessment data is fragmented across different platforms.
* Learning gaps are not always translated into classroom-level interventions.
* Teachers lack accessible tools for identifying specific competency weaknesses.
* Administrative dashboards often prioritise reporting over actionable decisions.
* There is limited integration between learner progress and resource allocation.

**NIPUNSetu addresses the implementation gap between collecting educational data and improving actual learning outcomes.**

---

## 💡 Our Solution

NIPUNSetu provides a unified decision-support layer that connects educational data with classroom and administrative workflows.

The platform enables:

1. Standardised ingestion of school and assessment data.
2. Competency-level foundational learning diagnostics.
3. Explainable early-warning and learning-risk analytics.
4. Teacher-oriented remediation recommendations.
5. Longitudinal learner progress tracking.
6. School, block and district-level intelligence.
7. Public benchmark comparisons using published ASER and PARAKH evidence.
8. Data governance, provenance and auditability.

---

## ✨ Key Features

### 1. District Intelligence Dashboard

* Foundational literacy and numeracy indicators.
* Reading and numeracy performance.
* Attendance monitoring.
* School-level learning summaries.
* Administrative performance insights.

### 2. Learner Intelligence

* Learner directory and search.
* Grade and school filtering.
* Individual learning profiles.
* Reading and numeracy gap identification.
* Learner-level assessment history.
* Risk categorisation.

### 3. FLN Diagnostic Engine

Identifies foundational learning weaknesses across reading and numeracy.

The diagnostic workflow maps assessment observations to specific competency gaps and recommends targeted classroom activities.

### 4. Intervention Management

A structured intervention workflow:

* Identify struggling learners.
* Recommend remediation activities.
* Assign interventions.
* Track intervention status.
* Record reassessment results.
* Monitor subsequent learning progress.

### 5. School & Block Intelligence

Provides administrative visibility across the education delivery network.

* School-wise performance.
* Block-level aggregation.
* Attendance and learning indicators.
* Administrative prioritisation.
* Comparative performance summaries.

### 6. Explainable Risk Analytics

An early-warning engine designed to identify learners requiring additional attention.

The current heuristic uses weighted indicators:

* Reading gap: 35%
* Numeracy gap: 35%
* Attendance gap: 30%

The platform also includes an experimental machine-learning validation pipeline.

**Important:** The heuristic is not a clinically or educationally validated predictive model. ML performance must be established using authorised longitudinal assessment data and independent holdout evaluation.

### 7. Public Education Benchmarks

Connects local education intelligence with published national evidence.

Supported evidence sources:

| Source            | Application                                    |
| ----------------- | ---------------------------------------------- |
| ASER              | Foundational reading and arithmetic benchmarks |
| PARAKH            | National competency-level assessment evidence  |
| UDISE+            | School master and institutional information    |
| DIKSHA            | Teaching and learning resource discovery       |
| State assessments | Local competency-level observations            |

Includes:

* Public benchmark dashboards.
* Historical learning trends.
* Benchmark metadata.
* Source attribution.
* Local-to-public comparison.
* Measurement comparability checks.

### 8. Teaching Resource Discovery

Competency-oriented teaching activities for foundational literacy and numeracy.

Resources include:

* Reading fluency.
* Phonemic awareness.
* Vocabulary development.
* Reading comprehension.
* Number recognition.
* Addition and subtraction.
* Multiplication and division.
* Pattern recognition.

Includes curated discovery links to DIKSHA.

### 9. Data Exchange & Governance

Designed to support interoperability between different educational data systems.

Features include:

* CSV-based data ingestion.
* School master imports.
* Pseudonymous learner onboarding.
* Assessment imports.
* Canonical data mapping.
* Duplicate detection.
* Row-level validation.
* Data provenance.
* Import history.
* Approval-reference requirements.

### 10. Multilingual & Offline Capabilities

* English/Hindi interface support.
* Progressive Web App foundations.
* Service worker caching.
* Offline event queue foundations.
* Synchronisation workflow foundations.

Full conflict-safe offline data synchronisation remains a deployment-level requirement.

---

## 🏗️ System Architecture

```text
                DATA SOURCES
                      |
       +--------------+--------------+
       |              |              |
     UDISE+          ASER          PARAKH
       |              |              |
       +--------------+--------------+
                      |
              STATE ASSESSMENTS
                      |
                      v
              DATA INGESTION
                      |
                      v
              VALIDATION ENGINE
                      |
                      v
             CANONICAL DATA MODEL
                      |
          +-----------+-----------+
          |           |           |
          v           v           v
      LEARNER      SCHOOL      BENCHMARK
      RECORDS      RECORDS     REFERENCES
          |           |           |
          +-----------+-----------+
                      |
                      v
             ANALYTICS ENGINE
                      |
          +-----------+-----------+
          |           |           |
          v           v           v
       FLN GAP      RISK       PROGRESS
       DETECTION   ANALYTICS   TRACKING
          |           |           |
          +-----------+-----------+
                      |
                      v
             RECOMMENDATION ENGINE
                      |
                      v
             TEACHER INTERVENTIONS
                      |
                      v
                 REASSESSMENT
                      |
                      v
             ADMINISTRATIVE FEEDBACK
                      |
          +-----------+-----------+
          |           |           |
          v           v           v
       TEACHER      BLOCK       STATE
      DASHBOARD   DASHBOARD   DASHBOARD
```

---

## 🧠 Machine Learning Pipeline

NIPUNSetu includes an experimental learning-risk prediction pipeline.

### Pipeline

```text
Assessment History
        |
        v
Data Quality Validation
        |
        v
Longitudinal Pair Generation
        |
        v
Feature Engineering
        |
        v
School / Temporal Holdout
        |
        v
Logistic Regression
        |
        v
Independent Evaluation
        |
        v
Model Performance Report
```

### Evaluation Metrics

The validation framework supports:

* Accuracy
* Precision
* Recall
* F1 Score
* ROC-AUC
* Brier Score
* Confusion Matrix
* Majority-class baseline comparison

The objective is to determine whether historical learning observations can help identify learners at risk of future learning stagnation.

**Model integrity:** Synthetic demonstration records must not be presented as evidence of real-world predictive performance. Validation on authorised, independently held-out school data is required before operational use.

---

## 🔄 End-to-End Workflow

Consider a learner struggling with basic subtraction.

**Step 1 — Identification**

The diagnostic engine identifies a numeracy competency gap.

**Step 2 — Analysis**

The platform examines available assessment and attendance information.

**Step 3 — Recommendation**

The system recommends targeted activities involving number lines, counters and guided subtraction exercises.

**Step 4 — Intervention**

The teacher assigns and records the intervention.

**Step 5 — Reassessment**

The teacher conducts another assessment and records the updated score.

**Step 6 — Progress Monitoring**

NIPUNSetu compares the learner's previous and latest assessment observations.

**Step 7 — Administrative Feedback**

Aggregated learning gaps help block and district administrators identify schools requiring additional academic support.

---

## 🛠️ Technology Stack

| Layer                | Technology                    |
| -------------------- | ----------------------------- |
| Frontend             | HTML5, CSS3, JavaScript       |
| Backend              | Python, FastAPI               |
| API                  | REST API, OpenAPI             |
| Validation           | Pydantic                      |
| Database             | SQLite runtime                |
| Data Processing      | Python, Pandas                |
| Machine Learning     | Scikit-learn                  |
| Authentication       | JWT-based authentication      |
| Data Exchange        | CSV, JSON                     |
| Offline Foundations  | Service Workers, LocalStorage |
| Resource Integration | DIKSHA discovery links        |
| Development          | VS Code, Git, GitHub          |

---

## 📂 Project Structure

```text
NIPUNSetu-Product/
│
├── backend/
│   ├── app/
│   │   ├── API modules
│   │   ├── authentication
│   │   ├── analytics
│   │   ├── data processing
│   │   └── application services
│   │
│   ├── data/
│   ├── requirements.txt
│   └── run.py
│
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── app.js
│
├── scripts/
│   └── smoke-test.py
│
├── docs/
│   ├── data governance
│   ├── ML validation
│   ├── data integration
│   └── architecture documentation
│
├── .gitignore
└── README.md
```

---

## 🚀 Installation & Setup

### Prerequisites

* Python 3.10+
* pip
* Git
* Visual Studio Code (recommended)

### 1. Clone the repository

```bash
git clone https://github.com/Tech4Aditya/NIPUNSetu.git

cd NIPUNSetu
```

Replace the repository URL if the project is hosted under a different GitHub repository.

### 2. Create a virtual environment

**Windows PowerShell**

```powershell
python -m venv .venv

.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r backend/requirements.txt
```

### 4. Configure environment variables

Create a `.env` file based on the provided `.env.example`, if available.

Configure a persistent, randomly generated JWT secret before running the application.

Never commit production secrets or real learner information.

### 5. Start the backend

From the project root:

```bash
python backend/run.py
```

Backend:

```text
http://localhost:8000
```

Interactive API documentation:

```text
http://localhost:8000/docs
```

### 6. Start the frontend

Open another terminal:

```bash
python -m http.server 8080 --directory frontend
```

Open:

```text
http://localhost:8080
```

---

## 🔐 Demo Authentication

The demonstration environment provides role-based accounts.

| Role                | Email                                     | Password   |
| ------------------- | ----------------------------------------- | ---------- |
| Teacher             | [teacher@demo.in](mailto:teacher@demo.in) | teacher123 |
| Block Officer       | [block@demo.in](mailto:block@demo.in)     | block123   |
| State Administrator | [state@demo.in](mailto:state@demo.in)     | state123   |
| Admin               | [admin@demo.in](mailto:admin@demo.in)     | admin123   |

These credentials are for local demonstration only.

Replace demo authentication with managed identity and secure credential provisioning before deployment.

---

## 📡 API Overview

The backend exposes REST endpoints for the platform's core workflows.

| Endpoint                                    | Purpose                      |
| ------------------------------------------- | ---------------------------- |
| `/api/dashboard`                            | Dashboard intelligence       |
| `/api/learners`                             | Learner directory            |
| `/api/interventions`                        | Intervention management      |
| `/api/maps/administrative`                  | Administrative intelligence  |
| `/api/analytics/predictions`                | Learning-risk analytics      |
| `/api/analytics/ml-validation`              | ML validation results        |
| `/api/analytics/competency-outcomes`        | Competency analytics         |
| `/api/analytics/intervention-effectiveness` | Intervention outcomes        |
| `/api/public-data/overview`                 | Public benchmark information |
| `/api/comparison/overview`                  | Local-to-public comparisons  |
| `/api/resources`                            | Teaching resource discovery  |
| `/api/governance`                           | Data governance information  |

Explore the complete interactive API documentation at `/docs`.

---

## 📊 Data Strategy & Governance

NIPUNSetu follows a source-aware data architecture.

### Data classification

**1. Public Aggregate Data**

Published national and state-level education statistics.

Examples:

* ASER reports.
* PARAKH reports.
* Published education indicators.

**2. Institutional Data**

School-level information obtained from authorised sources.

Examples:

* UDISE+ school master exports.
* School infrastructure indicators.
* Institutional attendance summaries.

**3. Learner-Level Data**

Individual assessment and intervention observations.

Requires:

* Appropriate institutional authorisation.
* Data minimisation.
* Pseudonymous learner identifiers.
* Role-based access.
* Auditability.
* Secure storage and transmission.

### Comparability safeguards

Different assessments do not automatically measure the same thing.

Before calculating direct benchmark differences, NIPUNSetu checks relevant metadata such as:

* Grade.
* Learning domain.
* Competency.
* Assessment instrument.
* Measurement unit.
* Target population.
* Sampling methodology.

When measurements are not comparable, the platform presents them as contextual evidence rather than manufacturing a numerical comparison.

---

## ⚠️ Current Implementation Boundaries

NIPUNSetu is a working prototype and integration framework, not an officially deployed government system.

| Component                    | Current status                |
| ---------------------------- | ----------------------------- |
| Frontend dashboards          | Implemented                   |
| FastAPI backend              | Implemented                   |
| JWT authentication           | Implemented for demonstration |
| FLN diagnostics              | Implemented                   |
| Intervention workflow        | Implemented                   |
| Synthetic demonstration data | Included                      |
| Public benchmark references  | Included                      |
| CSV data ingestion           | Implemented                   |
| ML validation framework      | Experimental                  |
| UDISE+ live integration      | Not connected                 |
| PARAKH live API              | Not connected                 |
| ASER microdata access        | Requires authorised access    |
| DIKSHA live API integration  | Not connected                 |
| PostgreSQL runtime migration | Not yet completed             |
| Production deployment        | Not yet completed             |

All synthetic records must be distinguished from actual government statistics and authorised institutional data.

---

## 🎯 Alignment with National Education Policy

NIPUNSetu supports the implementation objectives of:

* **National Education Policy 2020:** Emphasis on foundational literacy and numeracy.
* **NIPUN Bharat Mission:** Foundational learning targets and competency development.
* **UDISE+:** Institutional education data.
* **PARAKH:** Assessment and learning-outcome monitoring.
* **ASER:** Independent evidence on foundational learning.
* **DIKSHA:** Digital teaching and learning resources.

The platform is designed to complement these initiatives, not replace their existing systems.

---

## 🔮 Future Roadmap

| Priority | Planned development                               |
| -------- | ------------------------------------------------- |
| P0       | PostgreSQL runtime integration                    |
| P0       | Production authentication and identity management |
| P0       | Secure, conflict-safe offline synchronisation     |
| P0       | Authorised state assessment integration           |
| P1       | Validated predictive learning analytics           |
| P1       | Multilingual classroom recommendations            |
| P1       | DIKSHA resource integration                       |
| P1       | Geographic school intelligence                    |
| P2       | District-level resource allocation optimisation   |
| P2       | Intervention effectiveness evaluation             |
| P2       | Scalable multi-state deployment                   |

---

## 👥 Built For

**IIT Bombay Hackathon — Theme 2: Foundational Learning Outcomes**

The project explores how existing education data infrastructure can be transformed into an actionable decision-support system for India's foundational learning ecosystem.

### Core Philosophy

> Data should not end in a report. It should reach the classroom, guide an intervention, and help establish whether a learner has actually improved.

---

## 👨‍💻 Team & Project

**Project:** NIPUNSetu
**Domain:** GovTech · EdTech · Data Intelligence · Machine Learning
**Focus:** Foundational Literacy & Numeracy

---

## 📜 Disclaimer

NIPUNSetu is an independent prototype developed for research, demonstration and hackathon purposes.

It is not affiliated with, endorsed by, or operated by the Ministry of Education, Government of India, NCERT, ASER Centre or any state education department.

Government datasets and published statistics remain the property of their respective owners and are subject to their respective terms of use.

No synthetic demonstration result should be interpreted as an official educational statistic or validated real-world intervention outcome.
