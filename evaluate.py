import sys
import pandas as pd
from pipeline import analyze_rules_only

path = sys.argv[1] if len(sys.argv) > 1 else "data/test_set.csv"
df = pd.read_csv(path)

rows = []
for _, r in df.iterrows():
    verdict, score, reasons = analyze_rules_only(r["text"])
    predicted = "scam" if verdict in ("LIKELY_SCAM", "SUSPICIOUS") else "genuine"
    rows.append({"text": r["text"], "actual": r["label"],
                 "predicted": predicted, "verdict": verdict, "score": score})

res = pd.DataFrame(rows)
tp = ((res.actual == "scam") & (res.predicted == "scam")).sum()
tn = ((res.actual == "genuine") & (res.predicted == "genuine")).sum()
fp = ((res.actual == "genuine") & (res.predicted == "scam")).sum()
fn = ((res.actual == "scam") & (res.predicted == "genuine")).sum()

total = len(res)
print(f"File: {path}")
print(f"Samples: {total}")
print(f"Accuracy: {(tp + tn) / total:.1%}")
print(f"Precision (scam): {tp / (tp + fp) if (tp + fp) else 0:.1%}")
print(f"Recall (scam): {tp / (tp + fn) if (tp + fn) else 0:.1%}")
print(f"False positive rate: {fp / (fp + tn) if (fp + tn) else 0:.1%}")
print(f"Confusion: TP={tp} TN={tn} FP={fp} FN={fn}")

print("\n--- Wrongly classified ---")
for _, w in res[res.actual != res.predicted].iterrows():
    print(f"[actual={w.actual}, got={w.verdict}, score={w.score}] {w.text[:120]}")