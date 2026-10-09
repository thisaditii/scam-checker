# check_minfy.py
from pipeline import assess
import pandas as pd

df = pd.read_csv("data/final_set2.csv")
row = df[df.text.str.contains("Minfy")].iloc[0]
findings, score, reasons = assess(row.text)
print(score, [(r["source_tool"], r["signal"][:100]) for r in reasons])
print(findings.get("llm_extract"))