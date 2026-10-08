# check_fp.py
from pipeline import assess
import pandas as pd

df = pd.read_csv("data/test_set.csv")
for key in ["Deloitte will conduct", "interview with HCLTech"]:
    row = df[df.text.str.contains(key)].iloc[0]
    findings, score, reasons = assess(row.text)
    print(score, [r["signal"] for r in reasons])
    print(findings.get("llm_extract"), "\n")