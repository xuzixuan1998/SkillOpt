#!/usr/bin/env python3
"""Download SearchQA dataset from HuggingFace and convert to SkillOpt format.

Output structure::

    data/searchqa_raw/train.json    # 151K items
    data/searchqa_raw/test.json     # 43K items
    data/searchqa_raw/val.json      # 21K items

Each item::

    {
        "id": "<uuid5-from-question>",
        "question": "...",
        "context": "[DOC] snippet1 [DOC] snippet2 ...",
        "answers": ["answer text"]
    }
"""
from __future__ import annotations

import io
import json
import os
import sys
import uuid
import zipfile
from urllib.request import urlretrieve

# Ensure project root on path
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)

# ── Config ────────────────────────────────────────────────────────────────────

HF_REPO = "https://huggingface.co/datasets/kyunghyuncho/search_qa/resolve/main"
SPLITS = {
    "train": f"{HF_REPO}/data/train_test_val/train.zip",
    "test": f"{HF_REPO}/data/train_test_val/test.zip",
    "val": f"{HF_REPO}/data/train_test_val/val.zip",
}
OUTPUT_DIR = os.path.join(_PROJECT_ROOT, "data", "searchqa_raw")

# We use a fixed namespace so IDs are deterministic across runs
_SEARCHQA_NAMESPACE = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef0123456789")
_MAX_SNIPPETS = 20  # limit context snippets per item


def _build_context(search_results: list[dict]) -> str:
    """Join search snippets into a single context string with [DOC] separators."""
    snippets = []
    for sr in search_results:
        snippet = sr.get("snippet", "")
        if snippet:
            snippets.append(snippet)
        if len(snippets) >= _MAX_SNIPPETS:
            break
    return "[DOC] " + " [DOC] ".join(snippets)


def _make_id(question: str, answer: str) -> str:
    """Generate a deterministic UUID from question + answer."""
    return str(uuid.uuid5(_SEARCHQA_NAMESPACE, question + "|||" + answer))


def _convert_items(zip_path: str) -> list[dict]:
    """Extract zip, convert each JSON file to SkillOpt format."""
    items = []
    skipped = 0
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        total = len(names)
        for i, name in enumerate(names):
            if not name.endswith(".json"):
                continue
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

            # search_results can be a list (normal) or dict (rare edge case)
            if isinstance(search_results, dict):
                search_results = [search_results]

            context = _build_context(search_results)
            item_id = _make_id(question, answer)

            items.append({
                "id": item_id,
                "question": question.strip(),
                "context": context,
                "answers": [answer.strip()],
            })

            if (i + 1) % 5000 == 0:
                print(f"    {i+1}/{total} items processed...", flush=True)

    print(f"    Converted {len(items)} items ({skipped} skipped)")
    return items


def _download(url: str, dest: str) -> None:
    """Download with progress reporting."""
    if os.path.exists(dest):
        print(f"  Already cached: {dest}")
        return

    print(f"  Downloading {os.path.basename(dest)} from {url} ...")
    tmp = dest + ".tmp"

    def _report(block_num: int, block_size: int, total_size: int):
        if total_size > 0:
            downloaded = block_num * block_size
            pct = min(100, int(downloaded * 100 / total_size))
            mb = downloaded / (1024 * 1024)
            total_mb = total_size / (1024 * 1024)
            print(f"\r    {mb:.1f}/{total_mb:.1f} MB ({pct}%)", end="", flush=True)

    urlretrieve(url, tmp, reporthook=_report)
    print()  # newline after progress
    os.rename(tmp, dest)
    print(f"  Saved: {dest}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for split_name, url in SPLITS.items():
        print(f"\n{'='*60}")
        print(f"  Processing split: {split_name}")
        print(f"{'='*60}")

        zip_path = os.path.join(OUTPUT_DIR, f"{split_name}.zip")
        json_path = os.path.join(OUTPUT_DIR, f"{split_name}.json")

        if os.path.exists(json_path):
            print(f"  Already converted: {json_path}")
            continue

        _download(url, zip_path)
        print(f"  Converting to SkillOpt format...")
        items = _convert_items(zip_path)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False)
        print(f"  Saved {len(items)} items to {json_path}")

        # Free up disk space
        os.remove(zip_path)
        print(f"  Removed {zip_path}")

    # Summary
    print(f"\n{'='*60}")
    print(f"  Summary")
    print(f"{'='*60}")
    for split_name in SPLITS:
        json_path = os.path.join(OUTPUT_DIR, f"{split_name}.json")
        if os.path.exists(json_path):
            with open(json_path) as f:
                data = json.load(f)
            print(f"  {split_name}: {len(data)} items")


if __name__ == "__main__":
    main()
