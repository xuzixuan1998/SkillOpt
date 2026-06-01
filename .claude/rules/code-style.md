# Code Style

## Ruff compliance

New code must pass `ruff check` and `ruff format`. The project config is in `pyproject.toml`:

- line-length = 120
- target-version = py310
- Enabled rules: E (pycodestyle errors), F (pyflakes), I (isort), W (pycodestyle warnings)
- E501 (line-too-long) is suppressed; 120-char lines are fine

```bash
ruff check skillopt/ scripts/    # lint
ruff format skillopt/ scripts/   # format in-place
```

## Type Hints

Always annotate function signatures in `skillopt/`. Use `from __future__ import annotations` at the top of every module (all existing modules do this). For optional types, use `str | None` not `Optional[str]`.

## Docstrings

Use triple-quoted docstrings on all public functions and classes. The project uses a consistent Sphinx-style format:

```python
def my_function(param1: str, param2: int = 0) -> dict:
    """One-line summary.

    Parameters
    ----------
    param1 : str
        Description.
    param2 : int
        Description.

    Returns
    -------
    dict
        Description of return value.
    """
```

Keep summaries under one line when possible. Multi-line summaries should have a blank line after the first sentence.

## Import Order

Follow isort (I001 rule): stdlib → third-party → skillopt internal. Within each group, alphabetize. For `skillopt` internal imports, use full paths:

```python
# good
from skillopt.envs.base import EnvAdapter
from skillopt.model import chat_target_messages

# avoid
from ..base import EnvAdapter
```

## `__future__` annotations

Every module under `skillopt/` must start with `from __future__ import annotations` as the first import. This enables PEP 604 union syntax and makes type hints lazy.
