import hashlib
import json
import os
import sys
import time

sys.path.insert(0, os.getcwd())          # run from the project root
import pandas as pd

from pipeline import run_tools, rule_score, call, extract_chain, opinion_chain
from guardrails import sanitize

RAW_DIR = "experiments/raw"
os.makedirs(RAW_DIR, exist_ok=True)


def key(text):
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


for path in sys.argv[1:]:
    df = pd.read_csv(path)
    for text in df["text"]:
        out = f"{RAW_DIR}/{key(text)}.json"
        if os.path.exists(out):
            continue
        msg = sanitize(text)
        findings = run_tools(msg)
        info = call(extract_chain, {"message": msg[:2000]})
        opinion = call(opinion_chain, {"message": msg[:2000]})
        if info is None or opinion is None:
            print("LLM call failed, will retry on next run:", text[:60])
            continue
        findings["llm_extract"] = info.model_dump()
        score, reasons = rule_score(findings)
        hand = 30 if (score < 30 and opinion.is_suspicious) else score
        with open(out, "w", encoding="utf-8") as f:
            json.dump({"findings": findings, "reasons": reasons,
                       "extract": info.model_dump(), "opinion": opinion.model_dump(),
                       "hand_score": hand}, f, default=str)
        print("saved", key(text))
        time.sleep(12)                    