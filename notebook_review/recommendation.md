# AuditAI notebook review and recommended flow

## Recommendation

Use Untitled10 as the experimental foundation, with variant C's stable behavioral features and no raw entity IDs as the default candidate. Compare it against the simpler A feature set using identical OCR-free inputs and evaluation periods. Do not automatically ship the notebook's selected D variant merely because it has the largest validation score. OCR availability is not a criterion in this recommendation.

Untitled8 and Untitled9 contain exactly the same main code cell. Untitled9 has saved execution results; Untitled8 does not. These are not two distinct model architectures.

## Evidence from saved notebook outputs

| Pipeline | Average precision (called PR-AUC in notebooks) | Precision | Recall | F1 |
|---|---:|---:|---:|---:|
| Untitled9 | .822 | .801 | .799 | .800 |
| Untitled10 A, combined mean, no OCR | .913 | .786 | .852 | .818 |
| Untitled10 C, combined mean, includes receipt features | .954 | .970 | .857 | .910 |
| Untitled10 D, C plus IDs, includes receipt features | .976 | .982 | .874 | .925 |

Untitled10 figures are means across three seeds. The C and D figures are context, not a fair OCR-free comparison against Untitled9. Local OCR-free experiment results are saved separately in no_ocr_results.csv when the comparison completes. Original Colab outputs and local runs can differ because of dependency versions and runtime behavior. The local dataset has not been cryptographically matched to the original uploaded CSV.

The supervised gradient boosting reference reports AP 1.000 and F1 .990. That makes it worth testing when trustworthy labels exist; it is not proof of production accuracy or a theoretical performance ceiling. All these labels describe a synthetic benchmark.

## Fresh local comparison: OCR excluded from both candidates

Completed six CPU training runs (seeds 42, 43, 44), using the local 10,000-row dataset, identical 70/15/15 chronological partitions, 300-tree Isolation Forests and the notebook's AE training settings. The test set contains 1,500 rows, including 308 anomalies. Both candidates exclude raw IDs and all OCR/receipt inputs. Thresholds maximize validation F1. Means across seeds:

| Candidate | Validation AP | Test AP | Precision | Recall | F1 | Normal val/train error | Normal test/val error |
|---|---:|---:|---:|---:|---:|---:|---:|
| A, combined mean | .8522 | .9080 | .8560 | .7825 | .8168 | 8.6619 | 1.6088 |
| C without OCR, combined mean | .9465 | .9465 | .9391 | .8593 | .8972 | .8942 | 1.0028 |
| C without OCR, AE only | .9334 | .9284 | .9909 | .8063 | .8890 | .8942 | 1.0028 |
| C without OCR, IF only | .7942 | .7964 | .8525 | .5639 | .6736 | .8942 | 1.0028 |

The error ratios characterize the associated AE, not IF itself. This supports C-style features without relying on OCR. Combined mean provides a useful precision/recall balance, while AE-only is a strong high-precision challenger. In this local run the legacy clipped C score has slightly higher validation AP (.9501) and test AP (.9486), but lower F1 (.8931). Therefore continuous combination is a ranking/design preference and a candidate to validate, not the winner of every metric. IF alone actually deteriorates with C features; the feature improvement is model-dependent.

The executable comparison is compare_without_ocr.py and the full 24-row result table is no_ocr_results.csv. This is a focused rerun, not a full rerun of every original notebook. Multiple seeds measure training variability; they do not establish generalization to a new dataset. The existing final period is now a development benchmark; confirm the proposed flow on a new holdout.

## What improves in Untitled10

- Historical features are computed from earlier transactions, with a test that changes future rows and checks earlier features remain unchanged. This is useful evidence, not a proof against every leakage mechanism.
- C uses log-scale amount comparisons, capped lifetime counts, a rolling vendor frequency, and explicit new/missing entity flags. These address unbounded history growth and extreme numeric values.
- Both models receive preprocessed input independently. Isolation Forest does not depend on autoencoder reconstructions.
- Scores retain a continuous range instead of forcing many unusual records to the same maximum score. A's saved AP is .913 with the revised combination versus .822 with the legacy clipped score. The change also uses normal validation references, so this is not an isolated test of clipping alone.
- It compares models and seeds and reports anomaly-type recall, alert workload, and drift.

## Overfitting and limitations

For seed 42, saved normal-validation / normal-training reconstruction-error ratios are A 7.684, B 6.686, C .911 and D .988. Test-normal / validation-normal ratios are A 1.608, B 1.590, C .995 and D .993. C and D look more stable on this split. Ratios near one do not prove absence of overfitting; a high gap can reflect drift, memorization, or both. Reconstruction losses from different feature representations are not directly comparable as detection-quality measures.

D includes vendor, employee and approver identities. IDs are not automatically leakage, and their benefit is not automatically memorization. However, the experiment does not establish performance on unseen organizations or entities. Its seed rank correlations are .771 and .805 even though the top 100 alerts overlap strongly. Keep D as a challenger until unseen-entity tests show that its advantage transfers. The notebook's arbitrary .03 AP-gap rule does not certify safety.

The selected D model misses all 8 split-invoice cases and all 11 Benford cases in this test period at its displayed F1 threshold. Overall metrics therefore conceal coverage gaps. Counts are small and need uncertainty estimates. Add sequence/group-based duplicate and split-payment features; assess Benford patterns at an appropriate aggregate level rather than assuming every individual transaction can be classified this way.

The code uses known-normal labels to select training and reference rows. It is label-assisted anomaly detection even though the AE/IF losses do not directly fit anomaly labels. The so-called label-free threshold also selects normal validation rows using labels. This assumption must be stated clearly for real data.

One validation period serves early stopping, reference calibration, feature/model selection and threshold tuning. Test metrics are printed for every candidate, encouraging repeated reuse of the test set during development. Selection is explicitly by validation AP in code, but future revisions should keep a genuinely new final test period hidden until decisions are frozen.

Other concrete code issues:

- In 8/9, MASTER_DATA_AS_OF_SAFE=False does not actually exclude shared_phone_count/shared_address_count/shared_bank_account_count when present in the raw CSV: the frame retains them and the feature list selects them. Explicitly remove them unless provenance is verified. The saved run did not use these columns.
- In 8/9, the saved artifacts omit the score-normalization reference quantiles needed to reproduce the combined score on new data.
- In 10, top_drivers are AE reconstruction errors even if the winning family is IF or a combination. Label them as AE drivers; they do not fully explain the final score.
- Current features assume event-time ordering and update history from all earlier transactions, including anomalies. That is appropriate only when it matches production availability. Backdated entries, equal timestamps and delayed data need explicit handling.
- Dropping invalid dates or amounts silently removes potentially relevant audit cases. Route these to data-quality review and record counts.

## Recommended new flow

1. Validate raw transactions; retain invalid records for review. Define posting/availability time and effective-dated master data. Keep labels and generated risk explanations out of model inputs.
2. Reserve a final future test period. Within earlier data, use expanding chronological training/validation folds. Reserve a separate later calibration segment where data volume permits. Keep related copies of the same underlying event from contaminating evaluation; preserve genuine repeat-payment events.
3. Build history sequentially before scoring each transaction. Use C-style stable features without receipt/OCR columns initially. Keep identity values as lookup keys, not raw model inputs. Include log absolute amount and a sign flag, rolling frequencies, historical amount deviations, new/missing entity indicators, duplicate/split-window signals, and compact transaction categories.
4. Fit imputers, encoders and scalers on training data only. Use reviewed normal training rows when available. Validate the assumed cleanliness of that normal pool.
5. Train IF-only, a small regularized AE, and their combination as competing candidates. Start from the existing dropout, weight decay and early stopping; select complexity on chronological validation performance. Add supervised boosting as a separate candidate only when label quality supports it.
6. Calibrate comparable continuous AE/IF scores using held-out normal references, with a minimum scale safeguard. Select the simplest candidate that meets precision/recall and review-capacity requirements consistently across folds and seeds. Do not assume an ensemble always wins.
7. Freeze a threshold using a separate calibration period, targeting the audit team's review capacity or precision requirement. Save the threshold, score references, feature schema, preprocessing and model configuration together.
8. Evaluate once on a fresh future holdout: AP, precision, recall, F1, false-positive rate, precision/recall at review budgets, category coverage, unseen entities and uncertainty by time block. Add independent synthetic-generation seeds and eventually reviewed real cases.
9. Deploy the identical feature builder and persisted history state. Score before updating state. Explain rule findings separately from model-specific evidence; monitor alert rate, feature drift and reviewer outcomes.
10. Add OCR later as an optional feature block with confidence and missingness handling, then repeat the same validation protocol.

Flow: raw transactions -> validation and chronological partitioning -> prior-only behavioral features -> training-fitted preprocessing -> parallel AE / IF candidates -> calibrated continuous score -> frozen review threshold -> explanations and auditor feedback.

This is a proposed flow, not a claim that the production backend has been replaced or that its accuracy has been established.

## Method references

- scikit-learn: fit preprocessing on training data and avoid using test data for selection: https://scikit-learn.org/stable/common_pitfalls.html
- scikit-learn: precision-recall and average precision for imbalanced detection: https://scikit-learn.org/stable/auto_examples/model_selection/plot_precision_recall.html
