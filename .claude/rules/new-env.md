# New Environment Integration

When adding a new benchmark/agent to SkillOpt, follow this checklist.

## File structure

```
skillopt/envs/<name>/
├── __init__.py              # exports <Name>Adapter
├── adapter.py               # EnvAdapter subclass with 4 abstract methods
├── dataloader.py            # SplitDataLoader subclass
├── agent.py                 # call-your-agent wrapper
├── rollout.py               # process_one() + run_batch()
├── evaluator.py             # evaluate(predicted, ground_truth, item) -> dict
├── reflect.py               # optional prompt override (usually just a docstring)
├── prompts/
│   ├── analyst_error.md     # Optimizer LLM failure analysis prompt
│   └── analyst_success.md   # Optimizer LLM success analysis prompt
└── skills/
    └── initial.md           # starting skill prompt template
```

## Interface contract

1. **rollout results** (`results.jsonl`): each line must have `id`, `hard` (0/1), `soft` (0.0-1.0). Recommend adding `fail_reason`, `task_type`, `task_description`, `n_turns`.

2. **trajectories** (`conversation.json`): list of dicts that `fmt_trajectory()` can render. Three supported formats (pick one):
   - `{"type": "tool_call", "cmd": "...", "obs": "..."}` (agents with tool calls)
   - `{"step": N, "action": "...", "env_feedback": "...", "reasoning": "..."}` (env-interaction agents)
   - `{"type": "message", "content": "..."}` (plain text agents)

3. **prompts**: `analyst_error.md` and `analyst_success.md` must output the JSON patch schema (see existing templates in `skillopt/prompts/`). They should explain domain-specific concepts the Optimizer LLM needs to understand.

4. **data split**: must have `train/`, `val/`, `test/` subdirectories, each with an `items.json` array.

## Use the scaffold

There is a template at `skillopt/envs/_template/`. The `skillopt/envs/edp/` dir is a complete skeleton with TODOs and a `ROADMAP.md`.
