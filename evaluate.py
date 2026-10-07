import pandas as pd
from pipeline import analyze_rules_only

df = pd.read_csv("data/test_set.csv")

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
accuracy = (tp + tn) / total
precision = tp / (tp + fp) if (tp + fp) else 0
recall = tp / (tp + fn) if (tp + fn) else 0
fpr = fp / (fp + tn) if (fp + tn) else 0

print(f"Samples: {total}")
print(f"Accuracy: {accuracy:.1%}")
print(f"Precision (scam): {precision:.1%}")
print(f"Recall (scam): {recall:.1%}")
print(f"False positive rate: {fpr:.1%}  (genuine offers wrongly flagged)")
print(f"Confusion: TP={tp} TN={tn} FP={fp} FN={fn}")

wrong = res[res.actual != res.predicted]
print("\n--- Wrongly classified ---")
for _, w in wrong.iterrows():
    print(f"[actual={w.actual}, got={w.verdict}, score={w.score}] {w.text[:120]}")

res.to_csv("data/results.csv", index=False)