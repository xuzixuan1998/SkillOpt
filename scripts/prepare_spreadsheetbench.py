#!/usr/bin/env python3
"""Prepare SpreadsheetBench data for SkillOpt ReAct mode.

1. Extracts verified_400 xlsx files to data/spreadsheetbench_verified_400/
2. Creates train/val/test split from the 400 items
3. Saves to data/spreadsheetbench_split/
"""
from __future__ import annotations

import json
import os
import random
import sys
import tarfile

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)

# ── Config ────────────────────────────────────────────────────────────────────

TARBALL = "/tmp/spreadsheetbench/spreadsheetbench_verified_400.tar.gz"
DATA_ROOT = os.path.join(_PROJECT_ROOT, "data", "spreadsheetbench_verified_400")
SPLIT_DIR = os.path.join(_PROJECT_ROOT, "data", "spreadsheetbench_split")
SPLIT_RATIO = (280, 40, 80)  # train/val/test (match paper proportions)
SPLIT_SEED = 42


def main() -> None:
    # ── Step 1: Extract verified_400 xlsx data ─────────────────────────────
    if not os.path.exists(DATA_ROOT):
        print(f"Extracting verified_400 to {DATA_ROOT}...")
        os.makedirs(DATA_ROOT, exist_ok=True)
        with tarfile.open(TARBALL) as tf:
            for member in tf.getmembers():
                # Skip the top-level container dir entry
                if member.isdir():
                    continue
                # Strip "spreadsheetbench_verified_400/" prefix
                rel = member.name
                prefix = "spreadsheetbench_verified_400/"
                if rel.startswith(prefix):
                    rel = rel[len(prefix):]
                dest = os.path.join(DATA_ROOT, rel)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                tf.extract(member, path=DATA_ROOT)
                # Move if needed
                full_dest = os.path.join(DATA_ROOT, member.name)
                if full_dest != dest and os.path.exists(full_dest):
                    import shutil
                    shutil.move(full_dest, dest)
        print(f"  Extracted to {DATA_ROOT}")
    else:
        print(f"Already extracted: {DATA_ROOT}")

    # ── Step 2: Load dataset.json ─────────────────────────────────────────
    dataset_path = os.path.join(DATA_ROOT, "dataset.json")
    with open(dataset_path) as f:
        items = json.load(f)
    print(f"\nLoaded {len(items)} items from dataset.json")

    # Normalize: some IDs are ints, convert to string
    for item in items:
        item["id"] = str(item["id"])
        # Ensure answer_sheet exists (some items may lack it)
        if "answer_sheet" not in item:
            item["answer_sheet"] = ""

    # ── Step 3: Create split ──────────────────────────────────────────────
    rng = random.Random(SPLIT_SEED)
    rng.shuffle(items)

    train_n, val_n, test_n = SPLIT_RATIO
    assert train_n + val_n + test_n <= len(items), \
        f"Need {train_n+val_n+test_n} items, only have {len(items)}"

    splits = {
        "train": items[:train_n],
        "val": items[train_n:train_n + val_n],
        "test": items[train_n + val_n:train_n + val_n + test_n],
    }

    # ── Step 4: Save split ────────────────────────────────────────────────
    for split_name, split_items in splits.items():
        split_path = os.path.join(SPLIT_DIR, split_name)
        os.makedirs(split_path, exist_ok=True)
        out_file = os.path.join(split_path, "items.json")
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(split_items, f, ensure_ascii=False, indent=2)
        print(f"  {split_name}: {len(split_items)} items → {out_file}")

    # ── Step 5: Verify ────────────────────────────────────────────────────
    print("\nVerification:")
    for split_name in ["train", "val", "test"]:
        path = os.path.join(SPLIT_DIR, split_name, "items.json")
        with open(path) as f:
            data = json.load(f)
        item = data[0]
        assert all(k in item for k in ["id", "instruction", "spreadsheet_path",
                                        "instruction_type", "answer_position"]), \
            f"Missing keys in {split_name}: {list(item.keys())}"
        # Check xlsx files exist
        sp = item["spreadsheet_path"]
        task_dir = os.path.join(DATA_ROOT, sp)
        assert os.path.isdir(task_dir), f"Missing directory: {task_dir}"
        xlsx_files = [f for f in os.listdir(task_dir) if f.endswith('.xlsx')]
        print(f"  {split_name}: {len(data)} items, first={item['id']}, "
              f"xlsx_files={len(xlsx_files)}, type={item['instruction_type']}")

    # Instruction type distribution
    types = {}
    for item in items[:train_n + val_n + test_n]:
        t = item.get("instruction_type", "unknown")
        types[t] = types.get(t, 0) + 1
    print(f"\nInstruction types: {types}")
    print(f"Total in split: {sum(types.values())}")
    print("\n✅ Done! Ready for training.")


if __name__ == "__main__":
    main()
