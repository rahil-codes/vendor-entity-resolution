# Duplicate / Entity Resolution Tool

Finds likely duplicate vendor records using name/address normalization,
Levenshtein distance, token similarity, weighted scoring, and clustering
(connected components). Includes a synthetic dataset generator with known
ground truth so precision, recall, and F1 can be measured.

## Requirements

Python 3.8+ (standard library only, no packages to install).

## Usage

```bash
# 1. (Optional) regenerate the synthetic dataset and ground truth
python generate_dataset.py

# 2. Run the detector and evaluate against ground truth
python duplicate_detector.py
```

## Files

| File | Purpose |
|------|---------|
| `generate_dataset.py` | Builds `vendor_dataset.json` and `ground_truth.json` (seeded, reproducible) |
| `duplicate_detector.py` | Compares all record pairs, clusters matches, writes `results.json` |
| `vendor_dataset.json` | Generated vendor records (67 records, 20 companies) |
| `ground_truth.json` | Known duplicate groups |
| `results.json` | Detector output: matched pairs, predicted groups, metrics |

## Tuning

Thresholds are constants at the top of `duplicate_detector.py`
(`MIN_NAME_SIMILARITY`, `MIN_COMBINED_SCORE`, etc.). Tune on validation data,
not just the final test set.

## Note

The dataset is synthetic, so the perfect score (precision/recall/F1 = 1.0)
reflects how clean the generated typos are, not real-world performance.
