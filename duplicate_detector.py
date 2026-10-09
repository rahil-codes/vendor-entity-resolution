"""
Duplicate / Entity Resolution Tool
----------------------------------
Identifies likely duplicate vendor records using normalization,
Levenshtein distance, token similarity, weighted scores, and clustering.
"""

import json
import re
from collections import defaultdict
from difflib import SequenceMatcher
from itertools import combinations
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATASET_FILE = BASE_DIR / "vendor_dataset.json"
GROUND_TRUTH_FILE = BASE_DIR / "ground_truth.json"
RESULTS_FILE = BASE_DIR / "results.json"

# Tune these using validation data, not just the final test set.
MIN_NAME_SIMILARITY = 0.76
MIN_COMBINED_SCORE = 0.72
MIN_NAME_WITH_ADDRESS = 0.55
MIN_ADDRESS_SUPPORT = 0.35

NAME_WEIGHT = 0.70
ADDRESS_WEIGHT = 0.30

TOKEN_ALIASES = {
    "corp": "corporation",
    "inc": "incorporated",
    "llc": "llc",
    "ltd": "limited",
    "co": "company",
    "grp": "group",
    "log": "logistics",
    "logist": "logistics",
    "pharma": "pharmaceuticals",
    "pharmaceutical": "pharmaceuticals",
    "tech": "technology",
    "techs": "technologies",
    "mfg": "manufacturing",
    "svcs": "services",
    "svc": "services",
    "intl": "international",
}

ADDRESS_ALIASES = {
    "street": "st",
    "road": "rd",
    "avenue": "ave",
    "boulevard": "blvd",
    "drive": "dr",
    "parkway": "pkwy",
    "suite": "ste",
    "floor": "fl",
    "highway": "hwy",
    "apartment": "apt",
    "north": "n",
    "south": "s",
    "east": "e",
    "west": "w",
}


def normalize_text(value):
    """Lowercase text, remove punctuation, and normalize whitespace."""
    if value is None:
        return ""
    value = str(value).lower()
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    return " ".join(value.split())


def normalize_name(name):
    """Normalize company names and expand common abbreviations."""
    tokens = normalize_text(name).split()
    return " ".join(TOKEN_ALIASES.get(token, token) for token in tokens)


def normalize_address(address):
    """Normalize common address abbreviations."""
    tokens = normalize_text(address).split()
    return " ".join(ADDRESS_ALIASES.get(token, token) for token in tokens)
def levenshtein_distance(a, b):
    """Calculate edit distance using O(min(len(a), len(b))) memory."""
    if len(a) < len(b):
        a, b = b, a
    if not b:
        return len(a)

    previous = list(range(len(b) + 1))
    for i, char_a in enumerate(a, start=1):
        current = [i]
        for j, char_b in enumerate(b, start=1):
            insertion = current[j - 1] + 1
            deletion = previous[j] + 1
            substitution = previous[j - 1] + (char_a != char_b)
            current.append(min(insertion, deletion, substitution))
        previous = current
    return previous[-1]


def edit_similarity(a, b):
    """Convert Levenshtein distance into a similarity score from 0 to 1."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return 1.0 - levenshtein_distance(a, b) / max(len(a), len(b))


def token_similarity(a, b):
    """Compare token sets while ignoring word order."""
    tokens_a = set(a.split())
    tokens_b = set(b.split())
    if not tokens_a and not tokens_b:
        return 1.0
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)


def similarity(a, b):
    """Combine character-level, token-level, and sorted-token similarity."""
    if not a or not b:
        return 1.0 if a == b else 0.0

    character_score = edit_similarity(a, b)
    token_score = token_similarity(a, b)
    sorted_a = " ".join(sorted(a.split()))
    sorted_b = " ".join(sorted(b.split()))
    sorted_score = SequenceMatcher(None, sorted_a, sorted_b).ratio()

    return max(
        0.50 * character_score + 0.50 * token_score,
        sorted_score,
    )


def compare_records(record_a, record_b):
    """Compare two records and return component scores and a match decision."""
    name_a = normalize_name(record_a.get("name", ""))
    name_b = normalize_name(record_b.get("name", ""))
    address_a = normalize_address(record_a.get("address", ""))
    address_b = normalize_address(record_b.get("address", ""))

    name_score = similarity(name_a, name_b)
    address_score = similarity(address_a, address_b)
    combined_score = NAME_WEIGHT * name_score + ADDRESS_WEIGHT * address_score

    likely_duplicate = (
        name_score >= MIN_NAME_SIMILARITY
        and combined_score >= MIN_COMBINED_SCORE
    ) or (
        name_score >= MIN_NAME_WITH_ADDRESS
        and address_score >= MIN_ADDRESS_SUPPORT
        and combined_score >= MIN_COMBINED_SCORE
    )

    if likely_duplicate and name_score >= 0.90:
        confidence = "high"
    elif likely_duplicate and name_score >= 0.75:
        confidence = "medium"
    elif likely_duplicate:
        confidence = "low"
    else:
        confidence = "not_matched"

    return {
        "record_a": record_a["id"],
        "record_b": record_b["id"],
        "name_a": record_a.get("name", ""),
        "name_b": record_b.get("name", ""),
        "address_a": record_a.get("address", ""),
        "address_b": record_b.get("address", ""),
        "name_similarity": round(name_score, 4),
        "address_similarity": round(address_score, 4),
        "combined_score": round(combined_score, 4),
        "confidence": confidence,
        "is_duplicate": likely_duplicate,
    }


def build_groups(records, matched_pairs):
    """Build duplicate clusters using connected components."""
    parent = {record["id"]: record["id"] for record in records}

    def find(item):
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    def union(a, b):
        root_a = find(a)
        root_b = find(b)
        if root_a != root_b:
            parent[root_b] = root_a

    for pair in matched_pairs:
        union(pair["record_a"], pair["record_b"])

    clusters = defaultdict(list)
    for record in records:
        clusters[find(record["id"])].append(record["id"])

    return sorted(
        [sorted(ids) for ids in clusters.values() if len(ids) > 1],
        key=lambda group: group[0],
    )


def pairs_from_groups(groups):
    """Expand groups into a set of unique record-ID pairs."""
    pairs = set()
    for group in groups:
        for a, b in combinations(sorted(group), 2):
            pairs.add((a, b))
    return pairs


def evaluate(ground_truth_groups, predicted_groups):
    """Calculate pairwise precision, recall, and F1."""
    actual_pairs = pairs_from_groups(ground_truth_groups)
    predicted_pairs = pairs_from_groups(predicted_groups)

    true_positives = len(actual_pairs & predicted_pairs)
    false_positives = len(predicted_pairs - actual_pairs)
    false_negatives = len(actual_pairs - predicted_pairs)

    precision = (
        true_positives / (true_positives + false_positives)
        if true_positives + false_positives else 0.0
    )
    recall = (
        true_positives / (true_positives + false_negatives)
        if true_positives + false_negatives else 0.0
    )
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall else 0.0
    )

    return {
        "true_duplicate_pairs": len(actual_pairs),
        "predicted_duplicate_pairs": len(predicted_pairs),
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "missed_pairs": sorted(actual_pairs - predicted_pairs),
        "incorrect_pairs": sorted(predicted_pairs - actual_pairs),
    }


def main():
    with DATASET_FILE.open(encoding="utf-8") as file:
        records = json.load(file)
    with GROUND_TRUTH_FILE.open(encoding="utf-8") as file:
        ground_truth_groups = json.load(file)

    matched_pairs = []
    all_comparisons = []

    for record_a, record_b in combinations(records, 2):
        result = compare_records(record_a, record_b)
        all_comparisons.append(result)
        if result["is_duplicate"]:
            matched_pairs.append(result)
    predicted_groups = build_groups(records, matched_pairs)
    metrics = evaluate(ground_truth_groups, predicted_groups)
    record_by_id = {record["id"]: record for record in records}

    output = {
        "total_records": len(records),
        "candidate_pairs_compared": len(all_comparisons),
        "direct_matches": len(matched_pairs),
        "predicted_groups": predicted_groups,
        "matched_pairs": matched_pairs,
        "evaluation": metrics,
        "thresholds": {
            "min_name_similarity": MIN_NAME_SIMILARITY,
            "min_combined_score": MIN_COMBINED_SCORE,
            "min_name_with_address": MIN_NAME_WITH_ADDRESS,
            "min_address_support": MIN_ADDRESS_SUPPORT,
        },
    }

    with RESULTS_FILE.open("w", encoding="utf-8") as file:
        json.dump(output, file, indent=2)

    print(f"Total records: {len(records)}")
    print(f"Candidate pairs compared: {len(all_comparisons)}")
    print(f"Direct matches: {len(matched_pairs)}")
    print(f"Predicted duplicate groups: {len(predicted_groups)}")
    print("\n=== Evaluation against ground truth ===")
    for key, value in metrics.items():
        if key not in ("missed_pairs", "incorrect_pairs"):
            print(f"{key}: {value}")

    print("\n=== Missed duplicate pairs ===")
    for a, b in metrics["missed_pairs"]:
        print(f'{record_by_id[a]["name"]!r} <-> {record_by_id[b]["name"]!r}')

    print("\n=== Incorrectly matched pairs ===")
    for a, b in metrics["incorrect_pairs"]:
        print(f'{record_by_id[a]["name"]!r} <-> {record_by_id[b]["name"]!r}')

    print(f"\nFull results saved to: {RESULTS_FILE}")


if __name__ == "__main__":
    main()
