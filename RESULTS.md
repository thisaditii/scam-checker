# Evaluation results

All numbers come from `evaluate.py` (rules only), `evaluate_hybrid.py` (rules + LLM chains) or `experiments/final_eval.py`.
"Tuned on" means I changed rules or prompts after seeing that set's failures, so the number is optimistic.
"Unseen" means nothing was tuned on it before measuring.

## Headline: locked set (42 real messages)

Messages were collected, committed and the protocol written down before any test was run.
The system and its rules, prompts, features and threshold were frozen; each scorer was run once.

| Scorer | Scams caught | Recall (95% CI) | False alarms | Accuracy |
|---|---|---|---|---|
| **Hybrid: hand-tuned rules + LLM chains, as deployed (`evaluate_hybrid.py`, pre-registered headline)** | **15 / 21** | **71.4%** | **0 / 21** | **85.7%** |
| Hand-tuned rules on cached LLM outputs (`final_eval.py`) | 16 / 21 | 76% (55-89%) | 0 / 21 | 88% |
| L2 logistic regression on cached features (thr 0.47) | 14 / 21 | 67% (45-83%) | 0 / 21 | 83% |

- Confusion for the headline run: TP=15, TN=21, FP=0, FN=6.
- The 15 vs 16 difference between the two hand-tuned rows is LLM run-to-run variation (fresh calls vs cached outputs).
- Logistic regression showed no clear gain; the intervals overlap. Hand-tuned rules were kept, as pre-registered.
- Only 42 messages: report this as "15 of 21 scams caught, 0 false alarms", not as a precise accuracy.
- No changes were made to rules, prompts or features after this run.

### Locked-set error analysis (6 missed scams)

| Message | Why it was missed |
|---|---|
| Edvirra | Polished text on its own domain, no payment request (score 15) |
| Workable / "PUMA" | Sent via a recruiting-platform domain, which my allowlist treats as normal (score 0) |
| fresherjobsz | Fake job-portal domain with a generic "hall ticket" lure (score 15) |
| Tallymet | Polite interview invite pointing to WhatsApp (score 0) |
| naukriapply | Impersonates a known brand, but no pattern fired (score 5) |
| webboostsolutions | Free internship orientation with a stipend promise (score 20) |

Common theme: polished scams with no fee request, sensitive-data ask or odd domain. These are listed as future work, not fixed, so the locked result stays valid.

## Locked set protocol (pre-registered, 17 Oct 2026)
- 42 real messages: 21 scam / 21 genuine, all with a sender email.
- Headline system: hand-tuned rules + LLM chains, as deployed (`evaluate_hybrid.py`). Chosen before testing.
- Comparison: L2 logistic regression trained on the 95 dev messages, threshold chosen by cross-validation on dev data only.
- Rules, prompts, features and threshold frozen. Each scorer run once.

## Learned scoring experiment (development estimate)

95 dev messages, repeated stratified 5-fold cross-validation (5 repeats), L2 logistic regression with C=1.

| Scorer | Accuracy | Recall (95% CI) | False positive rate |
|---|---|---|---|
| Hand-tuned rules (in-sample, optimistic) | 90.5% | 83.7% (71-91%) | 2.2% |
| Logistic regression, threshold 0.5 | 85.5% | 73.9% (60-84%) | 2.2% |
| Logistic regression, tuned threshold | 84.2% | 74.7% (61-85%) | 5.7% |

The hand-tuned rules were written after seeing this data, so their figure is optimistic. The learned weights agreed with intuition (largest: LLM suspicion flag, young domain, unrealistic pay, company-domain mismatch). No clear gain from learning the weights, on dev data or on the locked set.

## Development and earlier unseen sets

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
| Fresh set 2 (10) | Hybrid (rules + LLM) | 90.0% | 80.0% | 0.0% | 4/5/0/1 | prompt written after seeing this set |
| Final set (16) | Rules only | 68.8% | 22.2% | 0.0% | 2/7/0/7 | unseen |
| Final set (16) | Hybrid v2, before fixes | 68.8% | 77.8% | 42.9% | 7/4/3/2 | unseen |
| Final set (16) | Hybrid v2, after prompt + platform fixes | 87.5% | 77.8% | 0.0% | 7/7/0/2 | tuned on |
| Clean set (14) | Hybrid v2 | 78.6% | 71.4% | 14.3% | 5/6/1/2 | unseen at the time, earlier headline |

### What each component contributes (final set of 16, unseen)

| Version | Recall | False positive rate |
|---|---|---|
| Rules only | 22.2% | 0.0% |
| Rules + LLM chains (before fixes) | 77.8% | 42.9% |

Rules never falsely accuse a company but miss polished scams. The LLM catches most of them but needed a carefully worded prompt to avoid flagging routine platform emails.

### Clean-set (14) error analysis

| Message | Result | Cause |
|---|---|---|
| Beacon Hill Search (scam) | Missed | Polished recruiter outreach, no rule fired |
| Pacifica Companies (scam) | Missed | Polished text, weak signal only (score 20) |
| Minfy Technologies (genuine) | False positive (score 35) | Sent via Keka (`kekamail.com`), not in my platform allowlist, so the company-vs-domain (+20) and website-unreachable (+15) rules fired |

## Security tests
`test_security.py` (12 tests, all passing) and `security_demo.py` cover the rule layer, with no LLM calls. See the README for the case table.

## Notes
- Rules were tuned after looking at failures on the main set, fresh set 1, the final set (16) and the clean set (14), so only the locked set is a fair estimate.
- Datasets mix real messages (personal details removed) and 20 synthetic ones, all in `test_set.csv`. See the README for counts.