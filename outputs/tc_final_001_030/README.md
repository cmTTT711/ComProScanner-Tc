# Tc Paper 001-030 final artifacts

This directory is the single retained result set for the accepted 30-paper Tc
review. Files in `work`, `db`, `logs`, `results`, and `tmp` are regenerable and
are not part of the result set.

- `predictions_001_030.json`: final model predictions from the context-window run.
- `gold_facts_001_030.json`: user-accepted Gold facts, including strict-scoring metadata.
- `gold_review_001_030.xlsx`: review-friendly form of the accepted Gold data.
- `strict_metrics_001_030.json`: frozen comparison summary.

The strict comparison contains 46 Gold facts and 40 deduplicated predictions:
TP = 40, FP = 0, FN = 6, Precision = 1.000000, Recall = 0.869565, and
F1 = 0.930233. One Paper 30 range fact is retained as non-strict Gold.

The files preserve the latest accepted state; this cleanup does not rerun the
model, alter the Tc scientific prompt, or recalculate the benchmark.
