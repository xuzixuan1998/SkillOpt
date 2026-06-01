#!/usr/bin/env python3
"""Convert SearchQA zip files to SkillOpt format and create train/val/test split.

Uses cached val.zip + downloads test.zip (avoids 2.1GB train.zip).
Creates 400/200/1400 split matching paper's proportions.
"""
from __future__ import annotations

import json
import os
import random
import sys
import uuid
import zipfile
from urllib.request import urlretrieve

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)

# ── Config ────────────────────────────────────────────────────────────────────

HF_BASE = "https://huggingface.co/datasets/kyunghyuncho/search_qa/resolve/main"
CACHE_DIR = "/tmp/searchqa_cache"
OUTPUT_DIR = os.path.join(_PROJECT_ROOT, "data", "searchqa_split")
RAW_DIR = os.path.join(_PROJECT_ROOT, "data", "searchqa_raw")

_SEARCHQA_NS = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef0123456789")
_MAX_SNIPPETS = 20
TRAIN_SIZE = 400
VAL_SIZE = 200
TEST_SIZE = 1400
SPLIT_SEED = 42


def _build_context(search_results: list[dict]) -> str:
    snippets = []
    if isinstance(search_results, dict):
        search_results = [search_results]
    for sr in search_results:
        snippet = sr.get("snippet", "")
        if snippet:
            snippets.append(snippet)
        if len(snippets) >= _MAX_SNIPPETS:
            break
    return "[DOC] " + " [DOC] ".join(snippets)


def _convert_zip(zip_path: str) -> list[dict]:
    items = []
    skipped = 0
    with zipfile.ZipFile(zip_path) as zf:
        names = [n for n in zf.namelist() if n.endswith(".json")]
        total = len(names)
        for i, name in enumerate(names):
            with zf.open(name) as f:
                try:
                    raw = json.load(f)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    skipped += 1
                    continue

            question = raw.get("question", "")
            answer = raw.get("answer", "")
            search_results = raw.get("search_results", [])

            if not question or not answer:
                skipped += 1
                continue

            if isinstance(search_results, dict):
                search_results = [search_results]

            context = _build_context(search_results)
            item_id = str(uuid.uuid5(_SEARCHQA_NS, question + "|||" + answer))

            items.append({
                "id": item_id,
                "question": question.strip(),
                "context": context,
                "answers": [answer.strip()],
            })

            if (i + 1) % 5000 == 0:
                print(f"    {i+1}/{total} items...", flush=True)

    print(f"    Converted {len(items)}, skipped {skipped}")
    return items


def _download(url: str, dest: str) -> None:
    if os.path.exists(dest):
        print(f"  Already cached: {dest}")
        return
    print(f"  Downloading from {url} ...")
    tmp = dest + ".tmp"

    def _report(block_num, block_size, total_size):
        if total_size > 0:
            pct = min(100, int(block_num * block_size * 100 / total_size))
            mb = block_num * block_size / (1024 * 1024)
            print(f"\r    {mb:.1f}/{total_size/(1024*1024):.1f} MB ({pct}%)", end="", flush=True)

    urlretrieve(url, tmp, reporthook=_report)
    print()
    os.rename(tmp, dest)


def main() -> None:
    os.makedirs(CACHE_DIR, exist_ok=True)
    os.makedirs(RAW_DIR, exist_ok=True)

    # ── Step 1: Convert cached val.zip ────────────────────────────────────────
    val_zip = os.path.join(CACHE_DIR, "val.zip")
    assert os.path.exists(val_zip), f"val.zip not found at {val_zip}"

    val_json = os.path.join(RAW_DIR, "val_full.json")
    if not os.path.exists(val_json):
        print("Converting val.zip...")
        val_items = _convert_zip(val_zip)
        with open(val_json, "w") as f:
            json.dump(val_items, f, ensure_ascii=False)
        print(f"Saved {len(val_items)} items to {val_json}")
    else:
        with open(val_json) as f:
            val_items = json.load(f)
        print(f"Loaded {len(val_items)} val items from cache")

    # ── Step 2: Download & convert test.zip ───────────────────────────────────
    test_zip = os.path.join(CACHE_DIR, "test.zip")
    if not os.path.exists(test_zip):
        _download(f"{HF_BASE}/data/train_test_val/test.zip", test_zip)

    test_json = os.path.join(RAW_DIR, "test_full.json")
    if not os.path.exists(test_json):
        print("Converting test.zip...")
        test_items = _convert_zip(test_zip)
        with open(test_json, "w") as f:
            json.dump(test_items, f, ensure_ascii=False)
        print(f"Saved {len(test_items)} items to {test_json}")
    else:
        with open(test_json) as f:
            test_items = json.load(f)
        print(f"Loaded {len(test_items)} test items from cache")

    # ── Step 3: Combine and split ─────────────────────────────────────────────
    all_items = val_items + test_items
    print(f"\nCombined: {len(all_items)} items ({len(val_items)} from val, {len(test_items)} from test)")

    # Shuffle deterministically
    rng = random.Random(SPLIT_SEED)
    rng.shuffle(all_items)

    total_needed = TRAIN_SIZE + VAL_SIZE + TEST_SIZE
    assert len(all_items) >= total_needed, f"Need {total_needed}, only have {len(all_items)}"

    train_items = all_items[:TRAIN_SIZE]
    val_split_items = all_items[TRAIN_SIZE:TRAIN_SIZE + VAL_SIZE]
    test_split_items = all_items[TRAIN_SIZE + VAL_SIZE:TRAIN_SIZE + VAL_SIZE + TEST_SIZE]

    # ── Step 4: Save split ────────────────────────────────────────────────────
    for split_name, items in [
        ("train", train_items),
        ("val", val_split_items),
        ("test", test_split_items),
    ]:
        split_dir = os.path.join(OUTPUT_DIR, split_name)
        os.makedirs(split_dir, exist_ok=True)
        out_path = os.path.join(split_dir, "items.json")
        with open(out_path, "w") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        print(f"  {split_name}: {len(items)} items → {out_path}")

    # Verify format
    print("\nVerification:")
    for split_name in ["train", "val", "test"]:
        with open(os.path.join(OUTPUT_DIR, split_name, "items.json")) as f:
            data = json.load(f)
        item = data[0]
        assert all(k in item for k in ["id", "question", "context", "answers"]), \
            f"Missing keys in {split_name} item: {list(item.keys())}"
        print(f"  {split_name}: {len(data)} items, first id={item['id'][:16]}..., "
              f"question='{item['question'][:50]}...', "
              f"answer='{item['answers'][0]}'")


if __name__ == "__main__":
    main()
