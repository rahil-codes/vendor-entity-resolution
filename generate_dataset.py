"""
Generates a synthetic third-party/vendor dataset with realistic duplicate entries.
Known ground-truth groups are generated so precision and recall can be measured.
"""

import json
import random
from pathlib import Path

random.seed(42)

BASE_DIR = Path(__file__).resolve().parent

BASE_COMPANIES = [
    ("Acme Logistics Corporation", "100 Industrial Pkwy, Suite 200, Austin, TX"),
    ("Northwind Traders Inc", "45 Harbor Road, Seattle, WA"),
    ("Meridian Health Systems LLC", "900 Wellness Blvd, Denver, CO"),
    ("BrightPath Manufacturing Co", "12 Factory Lane, Detroit, MI"),
    ("Silverline Consulting Group", "77 Market Street, Floor 9, Boston, MA"),
    ("Unity Freight Solutions", "230 Dockside Ave, Newark, NJ"),
    ("Vantage Point Analytics", "500 Innovation Dr, Austin, TX"),
    ("Coastal Supply Chain Partners", "18 Pier Road, Miami, FL"),
    ("Granite Peak Materials", "600 Quarry Rd, Salt Lake City, UT"),
    ("Harborview Pharmaceuticals", "4 Bayfront Plaza, San Diego, CA"),
    ("Redwood Data Services", "900 Sequoia Way, San Jose, CA"),
    ("Falcon Aerospace Components", "321 Runway Blvd, Wichita, KS"),
    ("Clearwater Environmental Inc", "55 Lakeview Dr, Tampa, FL"),
    ("Pioneer Steel Works", "88 Foundry St, Pittsburgh, PA"),
    ("Blue Ridge Textiles LLC", "14 Mill Road, Charlotte, NC"),
    ("Apex Industrial Equipment", "250 Machine Ave, Cleveland, OH"),
    ("Lumen Energy Partners", "700 Power Plant Rd, Houston, TX"),
    ("Summit Financial Services", "1 Capital Plaza, New York, NY"),
    ("Oakridge Agricultural Supply", "33 Farm Route 9, Des Moines, IA"),
    ("Cascade Water Technologies", "40 River Rd, Portland, OR"),
]

SUFFIX_VARIANTS = {
    "Corporation": ["Corp", "Corp.", "Corporation"],
    "Incorporated": ["Inc", "Inc.", "Incorporated"],
    "LLC": ["LLC", "L.L.C.", "Llc"],
    "Co": ["Co", "Co.", "Company"],
    "Group": ["Group", "Grp"],
}


def typo(text, rate=0.06):
    """Randomly swap, drop, or duplicate characters to simulate data-entry typos."""
    chars = list(text)
    for i in range(len(chars)):
        if random.random() < rate and chars[i].isalpha():
            action = random.choice(["drop", "swap", "dup"])
            if action == "drop":
                chars[i] = ""
            elif action == "dup":
                chars[i] = chars[i] * 2
            elif action == "swap" and i < len(chars) - 1:
                chars[i], chars[i + 1] = chars[i + 1], chars[i]
    return "".join(chars)


def vary_suffix(name):
    for full, variants in SUFFIX_VARIANTS.items():
        if full in name:
            return name.replace(full, random.choice(variants))
    return name


def vary_address(address):
    """Abbreviate address terms, sometimes omit suite/floor details, or change case."""
    address = address.replace("Suite", random.choice(["Ste", "Suite", "Ste."]))
    address = address.replace("Floor", random.choice(["Fl", "Floor"]))
    if random.random() < 0.3:
        parts = address.split(",")
        if len(parts) > 2:
            address = parts[0] + ", " + ",".join(parts[2:]).strip()
    if random.random() < 0.2:
        address = address.upper()
    return address.strip().strip(",").strip()


def make_variant(name, address):
    variant_name = typo(vary_suffix(name))
    if random.random() < 0.3:
        variant_name = variant_name.lower()
    return variant_name, vary_address(address)
records = []
record_id = 1000
ground_truth_groups = []

for name, address in BASE_COMPANIES:
    group_ids = []

    records.append({"id": record_id, "name": name, "address": address})
    group_ids.append(record_id)
    record_id += 1

    num_duplicates = random.choice([1, 1, 2, 2, 3])
    for _ in range(num_duplicates):
        variant_name, variant_address = make_variant(name, address)
        records.append({
            "id": record_id,
            "name": variant_name,
            "address": variant_address,
        })
        group_ids.append(record_id)
        record_id += 1

    ground_truth_groups.append(group_ids)

# Similar-sounding distractors are distinct real-world entities.
DISTRACTORS = [
    ("Apex Capital Partners", "90 Finance Row, Chicago, IL"),
    ("Northwind Realty Group", "12 Commerce St, Seattle, WA"),
    ("Meridian Logistics LLC", "500 Transit Way, Denver, CO"),
    ("Summit Steel Works", "40 Foundry St, Pittsburgh, PA"),
    ("Coastal Energy Partners", "20 Pier Road, Miami, FL"),
    ("Redwood Analytics Group", "901 Sequoia Way, San Jose, CA"),
]

for name, address in DISTRACTORS:
    records.append({"id": record_id, "name": name, "address": address})
    record_id += 1

# Hard true duplicates with abbreviations and truncation.
records.append({
    "id": record_id,
    "name": "Acme Log. Corp",
    "address": "Industrial Pkwy, Austin TX",
})
ground_truth_groups[0].append(record_id)
record_id += 1

records.append({
    "id": record_id,
    "name": "Harborview Pharma",
    "address": "Bayfront Plaza, San Diego",
})
ground_truth_groups[9].append(record_id)
record_id += 1

random.shuffle(records)

with (BASE_DIR / "vendor_dataset.json").open("w", encoding="utf-8") as file:
    json.dump(records, file, indent=2)

with (BASE_DIR / "ground_truth.json").open("w", encoding="utf-8") as file:
    json.dump(ground_truth_groups, file, indent=2)

print(
    f"Generated {len(records)} vendor records representing "
    f"{len(BASE_COMPANIES)} base companies."
)
print(f"Ground-truth duplicate groups: {len(ground_truth_groups)}")
