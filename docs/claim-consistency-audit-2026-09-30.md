# Claim consistency audit — 30 September 2026

Scope: the local `audit.db` demo dataset (2,000 expense claims and their saved predictions, cases, and reports). This checks internal consistency and auditor-facing evidence; it does not establish real-world fraud accuracy.

| Check | Result |
|---|---:|
| Claims with a saved prediction | 2,000 / 2,000 |
| Scored but not flagged | 1,814 |
| Flagged | 186 |
| Score at or above the model review boundary | 49 |
| Holiday policy rule triggered | 142 |
| Both model boundary and holiday policy | 5 |
| Claim status versus prediction flag mismatches | 0 |
| Date-only claims with unsupported after-hours evidence | 0 |
| Flagged claims without an active open case | 0 |
| Unflagged claims with an active open case | 0 |
| Generated reports on flagged claims | 186 |

The flag totals reconcile: 49 model signals + 142 holiday-policy signals − 5 overlaps = 186 flagged claims. A policy-only claim can correctly be flagged even with an index below 50. Forty-nine model-flagged claims have stored SHAP attribution; the other 137 are holiday-policy-only flags and display that rule separately.

Four old system-created cases were still open after their claims became unflagged: `CLM-01913`, `CLM-01751`, `CLM-01915`, and `CLM-01919`. None had a maker or checker action. They were marked `cancelled_unflagged` with a new system audit-trail event; the case records and original trail were preserved. Future rescoring now cancels untouched cases when a flag clears and reopens them if the flag returns. The API also prevents maker/checker action on a claim that is no longer flagged.

The vendor-name warning now requires a plausible spelling variation, rather than a common suffix such as “Airlines.” Sixteen claims currently show the warning across six plausible name pairs: `Uberr Rides`/`Uber`, `Swiggi Delivery`/`Swiggy`, `Starbuks Coffee`/`Starbucks`, `Amazn Inc`/`Amazon`, `Flipkrt Online`/`Flipkart`, and `Zomto Food`/`Zomato`. These are identity checks, not model fraud findings.

The dashboard now calls the fraction of flagged claims **Flagged Claim Rate**, not “Fraud Rate,” and displays the average as an anomaly index out of 100 rather than a percentage. The database currently has no maker or checker sign-offs, so separation of duties was verified by authorization tests rather than historical review outcomes.

**Score-scale limitation:** 1,951 claims display 0–49, 49 display 50–64, and none display 65–100. The active supervised model's raw output is bounded by 0 and 1, while its current arctangent display transform is anchored at a cutoff near 0.923. This maps the possible display range to approximately 26–52, so the 65–100 filter is unreachable with this model version. A displayed 26 is near the low end of this scale, not a 26% fraud probability. The display calibration needs separate validation and versioning before changing saved scores, report text, or audit history; this audit did not silently rescale them.
