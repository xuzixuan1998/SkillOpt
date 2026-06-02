"""EDP Adapter smoke tests."""

from __future__ import annotations

import json
import os
import tempfile

import pytest

from skillopt.envs.edp.adapter import EDPAdapter

# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def tmp_split_dir():
    """Create a temporary split_dir with sample EDP data."""
    import random

    # Same fixture data as the dataloader test
    fixture_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        "fixtures",
        "edp_sample",
        "data.json",
    )

    with open(fixture_path, encoding="utf-8") as f:
        items = json.load(f)

    rng = random.Random(42)
    rng.shuffle(items)

    n_train = max(1, len(items) * 2 // 5)
    n_val = max(1, len(items) * 1 // 5)

    tmp = tempfile.mkdtemp(prefix="edp_adapter_")
    for name, subset in [
        ("train", items[:n_train]),
        ("val", items[n_train : n_train + n_val]),
        ("test", items[n_train + n_val :]),
    ]:
        os.makedirs(os.path.join(tmp, name))
        with open(os.path.join(tmp, name, "items.json"), "w", encoding="utf-8") as f:
            json.dump(subset, f, ensure_ascii=False, indent=2)

    return tmp


# ── Adapter tests ───────────────────────────────────────────────────────────


class TestEDPAdapterInit:
    """Test EDPAdapter initialization."""

    def test_init_creates_dataloader(self):
        """EDPAdapter.__init__ creates an EDPDataLoader instance."""
        adapter = EDPAdapter(
            split_dir="/tmp/test",
            split_mode="split_dir",
            seed=42,
        )
        assert adapter.dataloader is not None
        from skillopt.envs.edp.dataloader import EDPDataLoader

        assert isinstance(adapter.dataloader, EDPDataLoader)

    def test_init_preserves_params(self):
        """EDPAdapter stores configuration parameters."""
        adapter = EDPAdapter(
            max_turns=15,
            exec_timeout=600,
            workers=8,
            minibatch_size=4,
            edit_budget=6,
        )
        assert adapter.max_turns == 15
        assert adapter.exec_timeout == 600
        assert adapter.workers == 8
        assert adapter.minibatch_size == 4
        assert adapter.edit_budget == 6


class TestEDPAdapterSetup:
    """Test EDPAdapter.setup()."""

    def test_setup_configures_dataloader(self, tmp_split_dir):
        """setup() delegates to self.dataloader.setup(cfg)."""
        adapter = EDPAdapter(split_dir=tmp_split_dir, split_mode="split_dir", seed=42)
        adapter.setup({"out_root": tmp_split_dir})

        # After setup, dataloader should have loaded splits
        dl = adapter.dataloader
        assert len(dl.train_items) > 0
        assert len(dl.val_items) > 0
        assert len(dl.test_items) > 0


class TestEDPAdapterGetDataloader:
    """Test get_dataloader()."""

    def test_returns_dataloader_instance(self):
        """get_dataloader() returns the dataloader."""
        adapter = EDPAdapter()
        dl = adapter.get_dataloader()
        assert dl is not None
        assert dl is adapter.dataloader


class TestEDPAdapterBuildEnv:
    """Test build_train_env / build_eval_env / build_env_from_batch."""

    def test_build_train_env(self, tmp_split_dir):
        """build_train_env returns a list of task items."""
        adapter = EDPAdapter(split_dir=tmp_split_dir, split_mode="split_dir", seed=42)
        adapter.setup({"out_root": tmp_split_dir})

        items = adapter.build_train_env(batch_size=2, seed=42)
        assert isinstance(items, list)
        assert len(items) <= 2
        for item in items:
            assert "id" in item

    def test_build_eval_env(self, tmp_split_dir):
        """build_eval_env returns a list of eval task items."""
        adapter = EDPAdapter(split_dir=tmp_split_dir, split_mode="split_dir", seed=42)
        adapter.setup({"out_root": tmp_split_dir})

        items = adapter.build_eval_env(env_num=2, split="val", seed=42)
        assert isinstance(items, list)
        assert len(items) > 0
        for item in items:
            assert "id" in item

    def test_build_env_from_batch(self, tmp_split_dir):
        """build_env_from_batch extracts items from BatchSpec."""
        adapter = EDPAdapter(split_dir=tmp_split_dir, split_mode="split_dir", seed=42)
        adapter.setup({"out_root": tmp_split_dir})

        batch = adapter.dataloader.build_train_batch(batch_size=2, seed=42)
        items = adapter.build_env_from_batch(batch)
        assert isinstance(items, list)
        assert items == batch.payload


class TestEDPAdapterReflect:
    """Test reflect() method (already implemented)."""

    def test_reflect_requires_results(self, tmp_split_dir):
        """reflect() calls run_minibatch_reflect with empty results."""
        adapter = EDPAdapter(split_dir=tmp_split_dir, split_mode="split_dir", seed=42)
        adapter.setup({"out_root": tmp_split_dir})

        # With empty results, reflect should return empty list
        patches = adapter.reflect(
            results=[],
            skill_content="# Test skill",
            out_dir=tmp_split_dir,
            prediction_dir=os.path.join(tmp_split_dir, "predictions"),
            patches_dir=os.path.join(tmp_split_dir, "patches"),
        )
        assert isinstance(patches, list)
        # Empty results → no minibatches → empty list
        assert len(patches) == 0


class TestEDPAdapterTaskTypes:
    """Test get_task_types()."""

    def test_get_task_types_returns_list(self):
        """get_task_types returns a list of strings."""
        adapter = EDPAdapter()
        types = adapter.get_task_types()
        assert isinstance(types, list)
