import sys
import time
import pandas as pd
from pipeline import analyze_hybrid

path = sys.argv[1] if len(sys.argv) > 1 else "data/test_set.csv"
df = pd.read_csv(path)

rows, llm_calls = [], 0
for _, r in df.iterrows():
    verdict, score, reasons, used = analyze_hybrid(r["text"])
    if used:
        llm_calls += 1
        time.sleep(6)   
    predicted = "scam" if verdict in ("LIKELY_SCAM", "SUSPICIOUS") else "genuine"
    rows.append({"text": r["text"], "actual": r["label"],
                 "predicted": predicted, "verdict": verdict, "score": score})

res = pd.DataFrame(rows)
tp = ((res.actual == "scam") & (res.predicted == "scam")).sum()
tn = ((res.actual == "genuine") & (res.predicted == "genuine")).sum()
fp = ((res.actual == "genuine") & (res.predicted == "scam")).sum()
fn = ((res.actual == "scam") & (res.predicted == "genuine")).sum()
total = len(res)

print(f"File: {path} | Samples: {total} | LLM calls: {llm_calls}")
print(f"Accuracy: {(tp + tn) / total:.1%}")
print(f"Precision (scam): {tp / (tp + fp) if (tp + fp) else 0:.1%}")
print(f"Recall (scam): {tp / (tp + fn) if (tp + fn) else 0:.1%}")
print(f"False positive rate: {fp / (fp + tn) if (fp + tn) else 0:.1%}")
print(f"Confusion: TP={tp} TN={tn} FP={fp} FN={fn}")
for _, w in res[res.actual != res.predicted].iterrows():
    print(f"[actual={w.actual}, got={w.verdict}, score={w.score}] {w.text[:120]}")