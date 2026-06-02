"""EDP config smoke tests."""

from __future__ import annotations

import os

import yaml

_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))),
    "configs",
    "edp",
    "default.yaml",
)


class TestEDPConfig:
    """Test the EDP training config file."""

    def test_config_exists(self):
        """The config file exists."""
        assert os.path.isfile(_CONFIG_PATH), f"Missing config file: {_CONFIG_PATH}"

    def test_config_parsable(self):
        """The config file is valid YAML."""
        with open(_CONFIG_PATH, encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        assert isinstance(cfg, dict)

    def test_env_name_is_edp(self):
        """env.name is 'edp'."""
        with open(_CONFIG_PATH, encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        assert cfg["env"]["name"] == "edp"

    def test_skill_init_path(self):
        """env.skill_init points to a real file."""
        with open(_CONFIG_PATH, encoding="utf-8") as f:
            cfg = yaml.safe_load(f)

        skill_path = cfg["env"]["skill_init"]
        assert os.path.isfile(skill_path), f"skill_init path does not exist: {skill_path}"
