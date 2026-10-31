# 3-minute hackathon pitch

**Opening:** India has built large school data systems and has clear FLN policy goals. The missing link is not another app that asks teachers to enter the same data again. It is the conversion of existing records into a useful next action for a child who is falling behind.

**Problem:** Assessment, attendance and school information live across different systems, formats and reporting levels. A compliance dashboard may tell an administrator that outcomes are weak, but it often does not tell a teacher which learner needs support, which competency is weak, what activity to try, and whether the child improved afterwards.

**Solution:** NIPUNSetu is an FLN decision-support and policy feedback layer. It standardises authorised data into a common contract, surfaces explainable learner-level signals where learner-level data is legitimately available, creates a teacher intervention workflow, and rolls up recurring gaps for block/state planning.

**Demo:** Sign in as a teacher. Open priority learners. Inspect one learner's reading/numeracy/attendance signal. Create a targeted intervention with a due date. Move it from Planned to In progress to Completed. Switch to the block/state role and show how aggregated patterns can inform teacher support and resource allocation. Open Data Exchange to show the CSV contract and Governance to show source boundaries and auditability.

**What is technically different:** We distinguish data types and governance boundaries. ASER and PARAKH aggregate evidence is not falsely joined to named learners. UDISE+ school identifiers are used as a registry mapping only through authorised sources. State assessment exports are the plausible route for learner-level diagnostics. Every import has provenance; every recommendation is reviewable; every action can be tracked to reassessment.

**Impact hypothesis:** Shorter time from assessment to targeted support, improved visibility of unaddressed learning gaps, more evidence-based block-level teacher support, and a feedback loop that measures learner progress rather than counting app activity.

**Close:** NIPUNSetu does not replace the systems India already has. It helps those systems change what happens next in the classroom.

## Demo caveat to state clearly

All records shown are synthetic. This prototype does not have live government integrations. Risk thresholds are illustrative and must be calibrated with state authorities and validated assessment instruments.
