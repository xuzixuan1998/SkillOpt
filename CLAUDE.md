# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Key Commands

```bash
# Install (editable)
pip install -e .
pip install -e ".[dev]"        # with ruff + pytest
pip install -e ".[claude]"     # with Claude backend

# Lint
ruff check skillopt/ scripts/
ruff format skillopt/ scripts/

# Train
python scripts/train.py --config configs/searchqa/default.yaml \
    --split_dir /path/to/split --azure_openai_endpoint https://your-resource.openai.azure.com/

# Evaluate a trained skill
python scripts/eval_only.py --config configs/searchqa/default.yaml \
    --skill outputs/my_run/best_skill.md --split valid_unseen --split_dir /path/to/split
```

## Architecture: The ReflACT 6-Stage Pipeline

Every training step runs the same 6-stage loop, orchestrated by `skillopt/engine/trainer.py`. The trainer is **environment-agnostic** — all benchmark-specific logic lives in `EnvAdapter` subclasses under `skillopt/envs/<benchmark>/`.

| Stage | Module | What happens |
|-------|--------|--------------|
| ① **Rollout** | adapter.`rollout()` | Run agent on a batch of tasks with the current skill prompt. Produces `results.jsonl` + per-task `conversation.json`. |
| ② **Reflect** | `gradient/reflect.py` | Group trajectories into minibatches (size M), send each to an Optimizer LLM that identifies common failure/success patterns and produces edit patches. |
| ③ **Aggregate** | `gradient/aggregate.py` | Hierarchically merge patches from all minibatches into one coherent patch. Failure-driven patches take priority over success-driven ones. |
| ④ **Select** | `optimizer/clip.py` | Rank edits by quality/support, truncate to a budget L (the "learning rate"). Supports scheduler-based LR decay and autonomous LR decision. |
| ⑤ **Update** | `optimizer/skill.py` | Apply edits (append/insert_after/replace/delete) to the skill document. Produces `candidate_skill.md`. |
| ⑥ **Gate** | `evaluation/gate.py` | Evaluate candidate skill vs current best on the validation split. Accept (use as new current), accept-as-new-best, or reject. |

Additionally, at epoch boundaries: **Slow Update** (`optimizer/slow_update.py`) maintains an EMA-style long-term memory section in the skill, and **Meta Skill** (`optimizer/meta_skill.py`) evolves the optimizer's own strategy.

## Environment Adapter Pattern

Every benchmark implements `skillopt/envs/base.py:EnvAdapter` with 4 abstract methods:

- `build_train_env(batch_size, seed)` / `build_eval_env(env_num, split, seed)` → return task items
- `rollout(env_manager, skill_content, out_dir)` → execute agent, return results with `id`/`hard`/`soft` fields
- `reflect(results, skill_content, out_dir)` → call `run_minibatch_reflect()` (provided by the framework; most adapters just delegate)
- `get_task_types()` → list of task category names

The new-benchmark scaffold lives at `skillopt/envs/_template/`. See the `edp/` env for a complete skeleton with roadmap.

## Model Backend Routing

`skillopt/model/router.py` selects backends via the `REFLACT_MODEL_BACKEND` env var (`azure_openai` | `codex` | `claude`). Each backend wraps a CLI or HTTP API:

- **Azure OpenAI** (`azure_openai.py`) — direct HTTP to Azure-hosted models
- **Codex** (`codex_backend.py`) — subprocess `codex exec --json`, messages serialized to text prompt
- **Claude** (`claude_backend.py`) — subprocess `claude -p --output-format json --schema ...`, same text-prompt pattern

All backends normalize their output into `common.CompatAssistantMessage` via their respective `_compat_message_from_payload()` functions. The rollout code (`react_agent.py`, `codegen_agent.py`) then converts this into the conversation trajectory format independent of the backend used.

## Trajectory Format

Rollout trajectories are saved as `conversation.json` — a list of dicts. Three formats coexist across benchmarks, all normalized by `gradient/reflect.py:fmt_trajectory()` for the Reflect stage:

- Tool-call: `{"type": "tool_call", "cmd": "...", "obs": "..."}`
- Environment step: `{"step": N, "action": "...", "env_feedback": "...", "reasoning": "..."}`
- Plain message: `{"type": "message", "content": "..."}`

## Data Pipeline

`skillopt/datasets/base.py` provides `SplitDataLoader` which expects a `split_dir/` with `train/`, `val/`, `test/` subdirectories. Mode `split_mode="ratio"` auto-generates this from a raw dataset file by train:val:test ratio.

## Config System

YAML configs live under `configs/<env>/default.yaml`. They inherit from `configs/_base_/default.yaml` via `_base_: ...`. CLI args (e.g. `--num_epochs`) override config values. The trainer flattens all config into `out_root/config.json`.

## Key Types (`skillopt/types.py`)

- `RolloutResult` — per-task result: `id`, `hard` (0/1), `soft` (0.0-1.0), `fail_reason`, plus env-specific extras
- `Edit` — a single skill edit: `op` (append/insert_after/replace/delete), `content`, `target`, `source_type`
- `Patch` — collection of edits with reasoning
- `RawPatch` — analyst output wrapping a Patch with provenance (`source_type`, `failure_summary`)
- `SlowUpdateResult` — epoch-level slow update outcome
