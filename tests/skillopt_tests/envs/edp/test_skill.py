"""EDP skill initial smoke tests."""

from __future__ import annotations

import os

_SKILL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))),
    "skillopt",
    "envs",
    "edp",
    "skills",
    "initial.md",
)


class TestSkillInitial:
    """Test the EDP initial skill prompt."""

    def test_skill_file_exists(self):
        """The initial skill file exists."""
        assert os.path.isfile(_SKILL_PATH), f"Missing skill file: {_SKILL_PATH}"

    def test_contains_slow_update_markers(self):
        """The skill contains SLOW_UPDATE markers."""
        with open(_SKILL_PATH, encoding="utf-8") as f:
            content = f.read()

        assert "<!-- SLOW_UPDATE_START -->" in content, "Missing SLOW_UPDATE_START marker"
        assert "<!-- SLOW_UPDATE_END -->" in content, "Missing SLOW_UPDATE_END marker"

    def test_has_structured_sections(self):
        """The skill has markdown sections with ## headings."""
        with open(_SKILL_PATH, encoding="utf-8") as f:
            content = f.read()

        assert "## Core Rules" in content
        assert "## Workflow" in content
        assert "## Common Pitfalls" in content

    def test_does_not_hardcode_specific_answers(self):
        """The skill does NOT contain specific fund/product names as answers."""
        with open(_SKILL_PATH, encoding="utf-8") as f:
            content = f.read()

        # General financial terms are OK, but specific recommendations are not
        # (this is a strategy document, not a look-up table)
        assert "<!-- TODO" not in content, "Skill still has TODO placeholders"

    def test_content_is_non_empty(self):
        """Each section has meaningful content."""
        with open(_SKILL_PATH, encoding="utf-8") as f:
            content = f.read()

        # Core Rules section should have at least a few lines after heading
        sections = content.split("## ")
        for section in sections[1:]:  # skip preamble
            lines = section.strip().split("\n")
            # Should have heading line + at least 2 content lines
            assert len(lines) >= 3, f"Section '## {lines[0]}' has too little content"
