# Evaluation results

| Set | Accuracy | Recall | False positive rate | Note |
|---|---|---|---|---|
| Main set (45), rules v1 | 75.6% | 56.5% | 4.5% | baseline |
| Main set (45), rules v3 | 93.3% | 87.0% | 0.0% | tuned on this set |
| Fresh set 1 (10), before tuning | 50.0% | 0.0% | 0.0% | unseen |
| Fresh set 1 (10), after tuning | 90.0% | 80.0% | 0.0% | tuned on this set |
| Fresh set 2 (10), rules v3 | 60.0% | 20.0% | 0.0% | unseen, fair number |

Notes:
- Rules were tuned after looking at failures on the main set and fresh set 1.
- Fresh set 2 was not used for tuning, so it is the fair estimate.
