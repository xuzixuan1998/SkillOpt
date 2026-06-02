"""EDP DataLoader smoke tests."""

from __future__ import annotations

import json
import os
import tempfile

import pytest

from skillopt.envs.edp.dataloader import EDPDataLoader

# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def fixture_data_path() -> str:
    """Path to the EDP sample fixture."""
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        "fixtures",
        "edp_sample",
        "data.json",
    )


@pytest.fixture
def tmp_split_dir(fixture_data_path: str) -> str:
    """Create a temporary split_dir from the fixture data."""
    import random

    tmp = tempfile.mkdtemp(prefix="edp_test_")

    with open(fixture_data_path, encoding="utf-8") as f:
        items = json.load(f)

    rng = random.Random(42)
    rng.shuffle(items)

    n_train = max(1, len(items) * 2 // 5)
    n_val = max(1, len(items) * 1 // 5)

    for name, subset in [
        ("train", items[:n_train]),
        ("val", items[n_train : n_train + n_val]),
        ("test", items[n_train + n_val :]),
    ]:
        os.makedirs(os.path.join(tmp, name))
        with open(os.path.join(tmp, name, "items.json"), "w", encoding="utf-8") as f:
            json.dump(subset, f, ensure_ascii=False, indent=2)

    return tmp


# ── DataLoader tests ────────────────────────────────────────────────────────


class TestEDPDataLoaderInit:
    """Test EDPDataLoader initialization."""

    def test_default_init(self):
        """EDPDataLoader can be instantiated with defaults."""
        loader = EDPDataLoader()
        assert loader.split_mode == "ratio"
        assert loader.split_dir == ""
        assert loader.data_path == ""

    def test_init_with_params(self):
        """EDPDataLoader accepts constructor parameters."""
        loader = EDPDataLoader(
            split_dir="/tmp/test_split",
            data_path="/tmp/test_data.json",
            split_mode="split_dir",
            split_ratio="3:2:5",
            split_seed=123,
            seed=99,
            limit=10,
        )
        assert loader.split_dir == "/tmp/test_split"
        assert loader.data_path == "/tmp/test_data.json"
        assert loader.split_mode == "split_dir"
        assert loader.split_ratio == "3:2:5"
        assert loader.split_seed == 123
        assert loader.seed == 99
        assert loader.limit == 10


class TestEDPDataLoaderLoadRawItems:
    """Test load_raw_items method."""

    def test_load_json_array(self, fixture_data_path):
        """load_raw_items loads a JSON array file."""
        loader = EDPDataLoader(data_path=fixture_data_path)
        items = loader.load_raw_items(fixture_data_path)
        assert isinstance(items, list)
        assert len(items) == 5
        for item in items:
            assert "id" in item
            assert "query" in item
            assert "task_type" in item

    def test_load_jsonl_format(self):
        """load_raw_items handles JSONL format (one JSON object per line)."""
        import tempfile

        items_data = [
            {"id": "jl_001", "query": "test query 1", "task_type": "test"},
            {"id": "jl_002", "query": "test query 2", "task_type": "test"},
            {"id": "jl_003", "query": "test query 3", "task_type": "test"},
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
            for item in items_data:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
            jsonl_path = f.name

        try:
            loader = EDPDataLoader(data_path=jsonl_path)
            items = loader.load_raw_items(jsonl_path)
            assert isinstance(items, list)
            assert len(items) == 3
            assert [it["id"] for it in items] == ["jl_001", "jl_002", "jl_003"]
        finally:
            os.unlink(jsonl_path)

    def test_load_nested_dict_with_data_key(self):
        """load_raw_items extracts items from dict with 'data' key."""
        import tempfile

        nested = {
            "metadata": {"source": "edp_test"},
            "data": [
                {"id": "nd_001", "query": "nested query 1", "task_type": "test"},
                {"id": "nd_002", "query": "nested query 2", "task_type": "test"},
            ],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(nested, f, ensure_ascii=False)
            nested_path = f.name

        try:
            loader = EDPDataLoader(data_path=nested_path)
            items = loader.load_raw_items(nested_path)
            assert isinstance(items, list)
            assert len(items) == 2
            assert [it["id"] for it in items] == ["nd_001", "nd_002"]
        finally:
            os.unlink(nested_path)

    def test_load_dict_without_data_key_uses_values(self):
        """load_raw_items falls back to dict values when no 'data' key exists."""
        import tempfile

        nested = {
            "item1": {"id": "dv_001", "query": "dict value 1", "task_type": "test"},
            "item2": {"id": "dv_002", "query": "dict value 2", "task_type": "test"},
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(nested, f, ensure_ascii=False)
            nested_path = f.name

        try:
            loader = EDPDataLoader(data_path=nested_path)
            items = loader.load_raw_items(nested_path)
            assert isinstance(items, list)
            assert len(items) == 2
            ids = sorted(it["id"] for it in items)
            assert ids == ["dv_001", "dv_002"]
        finally:
            os.unlink(nested_path)

    def test_load_nonexistent_file(self):
        """load_raw_items raises FileNotFoundError for missing files."""
        loader = EDPDataLoader()
        with pytest.raises(FileNotFoundError):
            loader.load_raw_items("/nonexistent/path/data.json")


class TestEDPDataLoaderSetup:
    """Test split_dir mode setup."""

    def test_setup_split_dir_mode(self, tmp_split_dir):
        """setup() loads all splits when split_mode=split_dir."""
        loader = EDPDataLoader(split_dir=tmp_split_dir, split_mode="split_dir", seed=42)
        loader.setup({"out_root": tmp_split_dir})

        assert len(loader.train_items) > 0
        assert len(loader.val_items) > 0
        assert len(loader.test_items) > 0

        total = len(loader.train_items) + len(loader.val_items) + len(loader.test_items)
        assert total == 5  # fixture has 5 items

    def test_setup_ratio_mode(self, fixture_data_path):
        """setup() generates splits when split_mode=ratio."""
        import shutil

        tmp = tempfile.mkdtemp(prefix="edp_ratio_")
        try:
            loader = EDPDataLoader(
                data_path=fixture_data_path,
                split_mode="ratio",
                split_ratio="3:1:1",
                split_seed=42,
            )
            loader.setup({"out_root": tmp})

            total = len(loader.train_items) + len(loader.val_items) + len(loader.test_items)
            assert total == 5  # all items preserved
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestEDPDataLoaderBatchConstruction:
    """Test batch construction methods."""

    def test_build_train_batch(self, tmp_split_dir):
        """build_train_batch returns a BatchSpec with payload."""
        loader = EDPDataLoader(split_dir=tmp_split_dir, split_mode="split_dir", seed=42)
        loader.setup({"out_root": tmp_split_dir})

        batch = loader.build_train_batch(batch_size=2, seed=42)
        from skillopt.datasets.base import BatchSpec

        assert isinstance(batch, BatchSpec)
        assert batch.phase == "train"
        assert batch.split == "train"
        assert batch.batch_size <= 2
        assert isinstance(batch.payload, list)
        for item in batch.payload:
            assert "id" in item

    def test_build_eval_batch(self, tmp_split_dir):
        """build_eval_batch returns a BatchSpec for the requested split."""
        loader = EDPDataLoader(split_dir=tmp_split_dir, split_mode="split_dir", seed=42)
        loader.setup({"out_root": tmp_split_dir})

        batch = loader.build_eval_batch(env_num=2, split="val", seed=42)
        from skillopt.datasets.base import BatchSpec

        assert isinstance(batch, BatchSpec)
        assert batch.phase == "eval"
        assert batch.split == "val"
        assert isinstance(batch.payload, list)

    def test_build_train_batch_deterministic(self, tmp_split_dir):
        """build_train_batch with same seed returns same batch."""
        loader = EDPDataLoader(split_dir=tmp_split_dir, split_mode="split_dir", seed=42)
        loader.setup({"out_root": tmp_split_dir})

        batch1 = loader.build_train_batch(batch_size=2, seed=42)
        batch2 = loader.build_train_batch(batch_size=2, seed=42)

        ids1 = [item["id"] for item in batch1.payload]
        ids2 = [item["id"] for item in batch2.payload]
        assert ids1 == ids2
