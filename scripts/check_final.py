from pipeline import assess
import pandas as pd

df = pd.read_csv("data/final_set.csv")
for _, r in df[df.label == "genuine"].iterrows():
    findings, score, reasons = assess(r.text)
    print(score, [(x["source_tool"], x["signal"][:90]) for x in reasons], "\n")