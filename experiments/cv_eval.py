import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import (RepeatedStratifiedKFold, StratifiedKFold,
                                     cross_val_predict)

from build_features import FEATURES


def wilson(k, n, z=1.96):
    if n == 0:
        return 0.0, 0.0
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return centre - half, centre + half


def pick_threshold(X, y, max_fpr=0.05):
    """Chosen on the TRAINING part only: best recall while keeping false positives <= max_fpr."""
    inner = StratifiedKFold(5, shuffle=True, random_state=0)
    p = cross_val_predict(LogisticRegression(C=1.0, max_iter=1000), X, y,
                          cv=inner, method="predict_proba")[:, 1]
    best_t, best_rec = 0.5, -1.0
    for t in np.linspace(0.1, 0.9, 33):
        pred = p >= t
        neg = (y == 0).sum()
        pos = (y == 1).sum()
        fpr = (pred & (y == 0)).sum() / max(neg, 1)
        rec = (pred & (y == 1)).sum() / max(pos, 1)
        if fpr <= max_fpr and rec > best_rec:
            best_t, best_rec = t, rec
    return best_t


def report(name, c, repeats):
    tp, fp, tn, fn = [v / repeats for v in c]
    n = tp + fp + tn + fn
    rec_lo, rec_hi = wilson(tp, tp + fn)
    fpr_lo, fpr_hi = wilson(fp, fp + tn)
    print(f"{name:34s} acc {(tp + tn) / n:5.1%} | recall {tp / (tp + fn):5.1%} "
          f"[{rec_lo:.0%}-{rec_hi:.0%}] | FPR {fp / (fp + tn):5.1%} [{fpr_lo:.0%}-{fpr_hi:.0%}]")


def main():
    df = pd.read_csv("experiments/features_dev.csv")
    X = df[FEATURES].values
    y = (df["label"] == "scam").astype(int).values
    hand = (df["hand_score"] >= 30).astype(int).values
    repeats = 5
    cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=repeats, random_state=42)

    tot = {"hand-tuned rules (not trained)": [0, 0, 0, 0],
           "logistic regression, thr 0.5": [0, 0, 0, 0],
           "logistic regression, tuned thr": [0, 0, 0, 0]}

    def add(name, pred, truth):
        t = tot[name]
        t[0] += int(((pred == 1) & (truth == 1)).sum())
        t[1] += int(((pred == 1) & (truth == 0)).sum())
        t[2] += int(((pred == 0) & (truth == 0)).sum())
        t[3] += int(((pred == 0) & (truth == 1)).sum())

    for tr, te in cv.split(X, y):
        model = LogisticRegression(C=1.0, max_iter=1000).fit(X[tr], y[tr])   # 0/1 features: no scaler needed
        p = model.predict_proba(X[te])[:, 1]
        thr = pick_threshold(X[tr], y[tr])
        add("hand-tuned rules (not trained)", hand[te], y[te])
        add("logistic regression, thr 0.5", (p >= 0.5).astype(int), y[te])
        add("logistic regression, tuned thr", (p >= thr).astype(int), y[te])

    print(f"{len(df)} dev messages, 5-fold x {repeats} repeats (development estimate)\n")
    for name, c in tot.items():
        report(name, c, repeats)

    model = LogisticRegression(C=1.0, max_iter=1000).fit(X, y)
    print("\nLearned weights (fit on all dev data, for interpretation only):")
    for name, w in sorted(zip(FEATURES, model.coef_[0]), key=lambda t: -abs(t[1])):
        print(f"  {name:22s} {w:+.2f}")


if __name__ == "__main__":
    main()