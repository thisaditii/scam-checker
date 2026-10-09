# Evaluation results

All numbers come from `evaluate.py` (rules only) or `evaluate_hybrid.py` (rules + LLM chains).
"Tuned on" means I changed rules or prompts after seeing that set's failures, so the number is optimistic.
"Unseen" means nothing was tuned on it before measuring.

| Set | Version | Accuracy | Recall | False positive rate | Confusion (TP/TN/FP/FN) | Status |
|---|---|---|---|---|---|---|
| Main set (45) | Rules v1 | 75.6% | 56.5% | 4.5% | 13/21/1/10 | baseline |
| Main set (45) | Rules v2 | 88.9% | 78.3% | 0.0% | 18/22/0/5 | tuned on |
| Main set (45) | Rules v3 | 93.3% | 87.0% | 0.0% | 20/22/0/3 | tuned on |
| Main set (45) | Hybrid v2, before fix | 93.3% | 95.7% | 9.1% | 22/20/2/1 | tuned on |
| Main set (45) | Hybrid v2, after fix | 97.8% | 95.7% | 0.0% | 22/22/0/1 | tuned on |
| Fresh set 1 (10) | Rules, before tuning | 50.0% | 0.0% | 0.0% | 0/5/0/5 | unseen |
| Fresh set 1 (10) | Rules, after tuning | 90.0% | 80.0% | 0.0% | 4/5/0/1 | tuned on |
| Fresh set 2 (10) | Rules only | 60.0% | 20.0% | 0.0% | 1/5/0/4 | unseen |
| Fresh set 2 (10) | Hybrid v1 (rules + LLM second opinion) | 90.0% | 80.0% | 0.0% | 4/5/0/1 | prompt written after seeing this set |
| Fresh set 2 (10) | Hybrid v2 | 90.0% | 80.0% | 0.0% | 4/5/0/1 | prompt written after seeing this set |
| Final set (16) | Rules only | 68.8% | 22.2% | 0.0% | 2/7/0/7 | unseen |
| Final set (16) | Hybrid v2, before fixes | 68.8% | 77.8% | 42.9% | 7/4/3/2 | unseen |
| Final set (16) | Hybrid v2, after prompt + platform fixes | 87.5% | 77.8% | 0.0% | 7/7/0/2 | tuned on |
| **Clean set (14)** | **Hybrid v2** | **78.6%** | **71.4%** | **14.3%** | **5/6/1/2** | **unseen, headline** |

## Headline result

On the clean set of 14 unseen messages, the hybrid caught 5 of 7 scams and wrongly flagged 1 of 7 genuine messages.
With 14 messages, one message moves accuracy by about 7 points, so treat this as indicative, not precise.

## What each component contributes (same unseen set, final set of 16)

| Version | Recall | False positive rate |
|---|---|---|
| Rules only | 22.2% | 0.0% |
| Rules + LLM chains (before fixes) | 77.8% | 42.9% |

Rules never falsely accuse a company but miss polished scams. The LLM catches most of them but needs a carefully worded prompt to avoid flagging routine platform emails.

## Error analysis (final clean set)

| Message | Result | Cause |
|---|---|---|
| Beacon Hill Search (scam) | Missed | Polished recruiter outreach, no rule fired, LLM treats it as normal |
| Pacifica Companies (scam) | Missed | Polished text, only a weak signal (score 20) |
| Minfy Technologies (genuine) | False positive (score 35) | Sent via Keka (`kekamail.com`), which is not in my platform allowlist, so the company-vs-domain rule (+20) and the website-unreachable rule (+15) fired |

## Notes

- Rules were tuned after looking at failures on the main set, fresh set 1 and the final set (16).
- Fresh set 2 was used to shape the LLM prompt, so its hybrid numbers are slightly optimistic.
- The clean set (14) was not tuned on. Do not change rules or prompts and then quote its number as unseen.
- Datasets are a mix of real messages (personal details removed) and synthetic ones. See the README for counts.
