"""EDP Rollout smoke tests."""

from __future__ import annotations

import json
import os

import pytest

from skillopt.envs.edp.rollout import process_one, run_batch

# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def sample_item() -> dict:
    """A minimal EDP task item."""
    return {
        "id": "test_001",
        "query": "测试查询",
        "task_type": "fund_recommendation",
        "ground_truth": "推荐沪深300ETF",
    }


@pytest.fixture
def sample_items() -> list[dict]:
    """A small batch of EDP task items."""
    return [
        {"id": "batch_001", "query": "查询1", "task_type": "test", "ground_truth": "答案1"},
        {"id": "batch_002", "query": "查询2", "task_type": "test", "ground_truth": "答案2"},
        {"id": "batch_003", "query": "查询3", "task_type": "test", "ground_truth": "答案3"},
    ]


@pytest.fixture
def skill_content() -> str:
    """A minimal skill prompt."""
    return "# Test Skill\n\n## Core Rules\n1. 规则1\n"


# ── process_one tests ──────────────────────────────────────────────────────


class TestProcessOne:
    """Test process_one() basic behavior."""

    def test_returns_required_fields(self, sample_item, skill_content, tmp_path):
        """process_one returns a dict with all required fields."""
        result = process_one(sample_item, str(tmp_path), skill_content)

        assert isinstance(result, dict)
        assert result["id"] == "test_001"
        assert "hard" in result
        assert "soft" in result
        assert isinstance(result["hard"], int)
        assert isinstance(result["soft"], float)
        assert "fail_reason" in result
        assert "n_turns" in result
        assert "phase" in result

    def test_creates_prediction_directory(self, sample_item, skill_content, tmp_path):
        """process_one creates out_root/predictions/<task_id>/ directory."""
        result = process_one(sample_item, str(tmp_path), skill_content)

        pred_dir = os.path.join(str(tmp_path), "predictions", result["id"])
        assert os.path.isdir(pred_dir)

    def test_result_structure_defaults(self, sample_item, skill_content, tmp_path):
        """process_one result has correct default values before agent integration."""
        result = process_one(sample_item, str(tmp_path), skill_content)

        assert result["ok"] is False
        assert result["hard"] == 0
        assert result["soft"] == 0.0
        assert result["n_turns"] == 0
        assert result["fail_reason"] == ""
        # Phase progresses through setup→agent→eval; last non-commented assignment wins
        assert result["phase"] == "eval"

    def test_handles_item_without_task_type(self, skill_content, tmp_path):
        """process_one works when item has no task_type field."""
        item = {"id": "minimal_001"}
        result = process_one(item, str(tmp_path), skill_content)

        assert result["id"] == "minimal_001"
        assert result["hard"] == 0

    def test_id_is_always_string(self, skill_content, tmp_path):
        """process_one always converts id to string."""
        item = {"id": 12345}
        result = process_one(item, str(tmp_path), skill_content)

        assert result["id"] == "12345"
        assert isinstance(result["id"], str)

    def test_successful_run_has_empty_error(self, sample_item, skill_content, tmp_path):
        """process_one leaves error field empty on a clean run."""
        result = process_one(sample_item, str(tmp_path), skill_content)

        assert result["error"] == ""
        assert result["fail_reason"] == ""

    def test_missing_id_returns_graceful_error(self, skill_content, tmp_path):
        """process_one returns error result when item dict has no 'id' key."""
        item: dict = {"no_id": True}  # type: ignore[assignment]
        result = process_one(item, str(tmp_path), skill_content)
        assert result["id"] == "unknown"
        assert result["hard"] == 0
        assert "invalid item" in result["fail_reason"]
        assert result["phase"] == "error"


# ── run_batch tests ────────────────────────────────────────────────────────


class TestRunBatch:
    """Test run_batch() batch execution."""

    def test_runs_all_items(self, sample_items, skill_content, tmp_path):
        """run_batch processes all items and returns results."""
        results = run_batch(
            sample_items,
            str(tmp_path),
            skill_content,
            max_api_workers=2,
        )

        assert isinstance(results, list)
        assert len(results) == 3
        result_ids = sorted(r["id"] for r in results)
        assert result_ids == ["batch_001", "batch_002", "batch_003"]

    def test_writes_results_jsonl(self, sample_items, skill_content, tmp_path):
        """run_batch writes results.jsonl to out_root."""
        run_batch(sample_items, str(tmp_path), skill_content, max_api_workers=2)

        results_path = os.path.join(str(tmp_path), "results.jsonl")
        assert os.path.isfile(results_path)

        with open(results_path, encoding="utf-8") as f:
            lines = f.readlines()
        assert len(lines) == 3
        for line in lines:
            r = json.loads(line)
            assert "id" in r
            assert "hard" in r
            assert "soft" in r

    def test_resume_skips_completed_items(self, sample_items, skill_content, tmp_path):
        """run_batch skips items already present in results.jsonl."""
        # Pre-create a results.jsonl with one completed item
        results_path = os.path.join(str(tmp_path), "results.jsonl")
        os.makedirs(str(tmp_path), exist_ok=True)
        with open(results_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"id": "batch_001", "hard": 1, "soft": 1.0, "ok": True}, ensure_ascii=False) + "\n")

        results = run_batch(sample_items, str(tmp_path), skill_content, max_api_workers=2)

        # Should have 3 results total (1 resumed + 2 new)
        assert len(results) == 3
        ids = sorted(r["id"] for r in results)
        assert ids == ["batch_001", "batch_002", "batch_003"]

        # The resumed item should preserve its hard/soft values
        resumed = next(r for r in results if r["id"] == "batch_001")
        assert resumed["hard"] == 1
        assert resumed["soft"] == 1.0

    def test_empty_items_returns_existing(self, sample_items, skill_content, tmp_path):
        """run_batch returns existing results when all items are already done."""
        # Pre-create results.jsonl with ALL items completed
        results_path = os.path.join(str(tmp_path), "results.jsonl")
        os.makedirs(str(tmp_path), exist_ok=True)
        with open(results_path, "w", encoding="utf-8") as f:
            for it in sample_items:
                f.write(
                    json.dumps({"id": it["id"], "hard": 1, "soft": 1.0, "ok": True}, ensure_ascii=False) + "\n"
                )

        results = run_batch(sample_items, str(tmp_path), skill_content, max_api_workers=2)

        # Should return existing results without re-processing
        assert len(results) == 3
        for r in results:
            assert r["hard"] == 1

    def test_results_jsonl_is_overwritten_on_completion(self, sample_items, skill_content, tmp_path):
        """run_batch overwrites results.jsonl with full results on completion."""
        run_batch(sample_items, str(tmp_path), skill_content, max_api_workers=2)

        results_path = os.path.join(str(tmp_path), "results.jsonl")

        # Read back and verify integrity
        with open(results_path, encoding="utf-8") as f:
            results = [json.loads(line) for line in f if line.strip()]

        assert len(results) == 3
        for r in results:
            assert r["id"] in ("batch_001", "batch_002", "batch_003")

    def test_handles_single_item(self, skill_content, tmp_path):
        """run_batch works with a single-item list."""
        single = [{"id": "single_001", "query": "single test"}]
        results = run_batch(single, str(tmp_path), skill_content, max_api_workers=1)

        assert len(results) == 1
        assert results[0]["id"] == "single_001"
