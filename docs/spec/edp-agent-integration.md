# Spec: EDPAgent × SkillOpt Integration

**Date:** 2026-06-01
**Status:** Draft
**Author:** Zixuan Xu (optimizer + integration verification) + TBD (evaluator)

---

## 1. Objective

将 EDPAgent（金融推荐场景的 ReAct agent）接入 SkillOpt 的 ReflACT 训练管道，通过自动优化 agent 的 skill prompt 来提升任务成功率。

### 1.1 Target Users

- 内部研发团队：使用 SkillOpt 自动改进 EDPAgent 的手搓 skill
- 评估同事：基于 rubrics + LLM-as-judge 评估 EDPAgent 输出质量

### 1.2 Success Criteria

- [ ] 6 阶段管道（Rollout → Reflect → Aggregate → Select → Update → Gate）全链路跑通
- [ ] 至少一个 epoch 完成，skill 被优化器修改，Gate 给出 ACCEPT/REJECT 判定
- [ ] 中间产物正确保存：`results.jsonl`、`conversation.json`、`patches/*.json`、`candidate_skill.md`

---

## 2. Architecture Overview

### 2.1 EDPAgent 交互模型

```
┌──────────┐     user query      ┌───────────────┐
│ SkillOpt │ ──────────────────▶ │  EDP Server   │
│ (trainer)│                     │  (HTTP API)   │
│          │ ◀────────────────── │               │
│          │   trajectory +      │  EDPAgent     │
│          │   final answer      │  (ReAct loop) │
└──────────┘                     └───────────────┘
     │                                  │
     │  skill upload API (TBD)          │
     └──────────────────────────────────┘
```

关键约束：
- **只能传 user query**，不能传 system prompt
- EDPAgent **内部自动调用多个 skill**（手搓的），用户不可控
- SkillOpt 优化的 skill 内容通过 **独立的 skill upload API**（待开发）注入
- 返回**完整执行轨迹**（格式待定）

### 2.2 优化目标

SkillOpt 优化的是 **EDPAgent 使用的 skill 文档内容**（初始值 = 手搓 skill），不是 user query 构造策略。

```
skills/initial.md               EDP Server
  (手搓 skill) ──▶ ReflACT ──▶ 优化后的 skill ──▶ skill upload API
```

### 2.3 ReflACT 6 阶段管道（EDP 视角）

| 阶段 | 模块 | EDP 适配状态 |
|------|------|-------------|
| ① Rollout | `adapter.rollout()` → `rollout.py` → `agent.py` → EDP HTTP | **阻塞**（等 EDP server） |
| ② Reflect | `reflect.py` → `run_minibatch_reflect()` | ✅ 已实现 |
| ③ Aggregate | `gradient/aggregate.py` | 框架自动，无需适配 |
| ④ Select | `optimizer/clip.py` | 框架自动，无需适配 |
| ⑤ Update | `optimizer/skill.py` | 框架自动，无需适配 |
| ⑥ Gate | `evaluation/gate.py` | 框架自动，无需适配 |

---

## 3. Current State

### 3.1 已完成（骨架）

```
skillopt/envs/edp/
├── __init__.py              ✅ 导出 EDPAdapter
├── adapter.py               ✅ 骨架（4 抽象方法 + reflect 已完成）
├── dataloader.py            🟡 骨架（继承 SplitDataLoader，加载逻辑待实现）
├── agent.py                 🔴 骨架（run_agent 函数签名 + TODO）
├── rollout.py               🟡 process_one + run_batch 逻辑完整，
│                              只差 agent 调用 + evaluator 调用两段
├── evaluator.py             🔴 骨架（同事负责）
├── reflect.py               ✅ 仅说明文档（不需要修改）
├── ROADMAP.md               🟡 需更新进度
├── prompts/
│   ├── analyst_error.md     🔴 模板（缺 EDP 领域知识）
│   └── analyst_success.md   🔴 模板（同上）
└── skills/
    └── initial.md           🔴 模板（缺 EDP 实际 skill 内容）
```

### 3.2 项目基础设施（已完成）

- `CLAUDE.md` — 架构概览 + 关键命令
- `.claude/rules/` — code-style.md, git.md, testing.md, new-env.md
- SearchQA 首次跑通验证（SiliconFlow + DeepSeek V4 Pro）

---

## 4. Work Plan: Unblocked Tasks

以下工作**不依赖 EDP 服务端**，可以立即推进。

### 4.1 `dataloader.py` — 数据加载器

**目标：** 实现 `EDPDataLoader.load_raw_items()`，支持标准 JSON/JSONL 格式。

**数据格式（建议）：**
```json
{
  "id": "fund_001",
  "query": "我月收入2万，风险偏好中等，想定投3只基金，帮我推荐",
  "task_type": "fund_recommendation",
  "ground_truth": "...",
  "rubrics": "..."
}
```

每个 item 必须含 `"id"`，其余字段按需。数据切分支持两种模式：
- `split_mode="split_dir"`: 手工准备 `train/val/test/items.json`
- `split_mode="ratio"`: 提供原始 JSON/JSONL，自动按比例切分

**验收标准：**
- [ ] 从 JSON/JSONL 文件正确加载 items
- [ ] `build_train_batch()` / `build_eval_batch()` 返回正确 `BatchSpec`
- [ ] `ruff check` 通过

**估时：** 30min（大部分逻辑在 `SplitDataLoader` 基类中已实现）

### 4.2 `adapter.py` — 环境适配器解注释

**目标：** 取消注释 dataloader 初始化、`setup()`、`build_train_env()`、`build_eval_env()`、`build_env_from_batch()`。

**不动的部分：**
- `rollout()` — 保持注释，依赖 `agent.py` + EDP server
- `reflect()` — 已完成，不需要改
- `get_task_types()` — 等任务类型确定后填入

**验收标准：**
- [ ] `EDPAdapter.__init__()` 初始化 `self.dataloader`
- [ ] `setup()` 调用 `self.dataloader.setup(cfg)`
- [ ] `build_train_env()` / `build_eval_env()` 委托给 dataloader
- [ ] `ruff check` 通过
- [ ] 结构与 SearchQA adapter 一致

**估时：** 20min

### 4.3 `configs/edp.yaml` — 训练配置

**目标：** 创建 EDPAgent 训练配置，继承 `_base_/default.yaml`。

**关键参数：**
```yaml
_base_: ../_base_/default.yaml

train:
  train_size: 0          # 自动推导
  batch_size: 40

gradient:
  minibatch_size: 8

optimizer:
  learning_rate: 4

env:
  name: edp
  skill_init: skillopt/envs/edp/skills/initial.md
  split_mode: split_dir
  max_turns: 10           # 待 EDP 确定后调整
  exec_timeout: 300       # 同上
```

**验收标准：**
- [ ] 配置文件可以被 YAML parser 正确加载
- [ ] 继承链正确（base → edp）

**估时：** 15min

### 4.4 `skills/initial.md` — 初始 Skill Prompt

**目标：** 从 EDP 团队获取现成手搓 skill，填入模板。如果暂时拿不到，写一个占位版本。

**内容方向（金融推荐场景）：**
- 基金筛选规则
- 风险评估方法
- 推荐输出格式
- 常见陷阱和注意事项

**验收标准：**
- [ ] 包含结构化的 markdown 内容（## 分节）
- [ ] 不硬编码具体任务答案
- [ ] 包含 `<!-- SLOW_UPDATE_START -->` / `<!-- SLOW_UPDATE_END -->` 标记

**估时：** 取决于能否拿到手搓 skill（拿到→10min，自己写→1h+）

---

## 5. Work Plan: Blocked Tasks

以下工作**依赖 EDP 服务端**，需要 EDP 团队提供 API 契约后才能推进。

### 5.1 `agent.py` — Agent 调用封装

**阻塞原因：** 需要 EDP HTTP API 的 endpoint、请求格式、响应格式。

**预期实现：**
```python
def run_agent(item, skill_content, *, max_turns, max_completion_tokens, **kwargs) -> dict:
    # 1. 构建 user query（将 task instruction + skill 上下文嵌入）
    # 2. POST 到 EDP HTTP endpoint
    # 3. 等待 agent 执行完成
    # 4. 解析 trajectory + final answer
    # 5. 返回 {"conversation": [...], "n_turns": N, "predicted_answer": "..."}
```

**依赖信息（需要 EDP 团队提供）：**
- [ ] HTTP endpoint URL 格式
- [ ] 请求 body schema（query 字段？额外参数？）
- [ ] 响应 body schema（trajectory 格式？final answer 位置？）
- [ ] 认证方式（API key？Bearer token？）
- [ ] 超时/重试策略建议
- [ ] skill upload API 的 endpoint + schema

### 5.2 `rollout.py` — 串联 Agent + Evaluator

**阻塞原因：** 依赖 `agent.py` 和 `evaluator.py`。

**已完成部分：**
- `run_batch()` — 并发、超时、断点续跑逻辑完整
- `process_one()` — 骨架完整，只差 agent 调用 + evaluator 调用两段

### 5.3 `prompts/analyst_error.md` + `analyst_success.md`

**阻塞原因：** 需要知道 EDPAgent 的：
- 轨迹格式（Optimizer LLM 需要读懂轨迹）
- 常见失败模式（error analyst 需要领域知识才能诊断）
- 成功行为特征（success analyst 需要知道什么算"好的行为"）
- 可用工具列表、领域术语

### 5.4 `evaluator.py`

**负责：** 同事
**阻塞原因：** 需要知道 EDPAgent 的输出格式和 rubrics 结构。

### 5.5 集成验证 / 冒烟测试

**阻塞原因：** 需要全链路（EDP server + agent + evaluator）就绪。

**测试 checklist（就绪后执行）：**
- [ ] 单 task rollout：EDPAgent 调用正常，`conversation.json` 正确生成
- [ ] 小批量训练（5-10 tasks）：Reflect → Aggregate → Select → Update 全链路跑通
- [ ] 中间产物检查：`results.jsonl`、`patches/*.json`、`candidate_skill.md`
- [ ] EDP skill upload API：优化后的 skill 能成功上传

---

## 6. Interface Contracts

### 6.1 Adapter ↔ Trainer

```python
# 已由 EnvAdapter 基类定义，EDPAdapter 必须实现：

build_train_env(batch_size, seed) → list[dict]          # 返回 task items
build_eval_env(env_num, split, seed) → list[dict]       # 同上
rollout(env_manager, skill_content, out_dir) → list[dict]  # 执行 + 返回结果
reflect(results, skill_content, out_dir) → list[dict|None]  # 分析 + 返回补丁
get_task_types() → list[str]                            # 任务类型列表
```

### 6.2 Rollout Result Schema

每个 `results.jsonl` 行必须包含：
```json
{
  "id": "fund_001",
  "hard": 0,
  "soft": 0.0,
  "fail_reason": "...",
  "task_type": "fund_recommendation",
  "task_description": "...",
  "n_turns": 5,
  "target_system_prompt": "",
  "target_user_prompt": "..."
}
```

### 6.3 Evaluator Contract（与同事对齐）

```python
def evaluate(predicted: str, ground_truth: str, item: dict | None = None) -> dict:
    """返回 {"ok": bool, "reason": str, "score": float}"""
```

---

## 7. Boundaries & Responsibilities

| 范围 | 负责人 | 状态 |
|------|--------|------|
| `dataloader.py` | Zixuan | 🟢 可推进 |
| `adapter.py`（结构） | Zixuan | 🟢 可推进 |
| `configs/edp.yaml` | Zixuan | 🟢 可推进 |
| `skills/initial.md` | Zixuan | 🟡 需拿手搓 skill |
| `agent.py` | Zixuan | 🔴 等 EDP API |
| `rollout.py`（agent+evaluator 串联） | Zixuan | 🔴 等 agent.py + evaluator.py |
| `prompts/analyst_*.md` | Zixuan | 🔴 等轨迹格式 + 领域知识 |
| `evaluator.py` | 同事 | 🔴 等输出格式 + rubrics |
| 集成验证 / 冒烟测试 | Zixuan | 🔴 等全链路就绪 |
| EDP rollout HTTP API | EDP 团队 | 🔴 外部依赖 |
| EDP skill upload API | EDP 团队 | 🔴 外部依赖 |

### 7.1 Always Do

- `ruff check` + `ruff format` 在每次修改后运行
- 遵循项目 code style（type hints, docstrings, `from __future__ import annotations`）
- commit 前 `git diff --staged | grep -i "api_key\|password\|secret\|token"`
- 参考 SearchQA adapter 的实现模式

### 7.2 Ask First

- 修改框架层代码（`skillopt/engine/`, `skillopt/gradient/`, `skillopt/optimizer/`）
- 引入新的第三方依赖
- 修改已有环境适配器（searchqa, spreadsheetbench, alfworld 等）

### 7.3 Never Do

- 提交 `.env`、`.secrets/`、API keys
- 在 skill 中硬编码具体任务答案
- 修改 `<!-- SLOW_UPDATE_START -->` / `<!-- SLOW_UPDATE_END -->` 之间的内容

---

## 8. File Index

| 想看什么 | 路径 |
|---------|------|
| 本 spec | `docs/spec/edp-agent-integration.md` |
| 开发路线图 | `skillopt/envs/edp/ROADMAP.md` |
| EDP adapter（骨架） | `skillopt/envs/edp/adapter.py` |
| EDP rollout（骨架） | `skillopt/envs/edp/rollout.py` |
| EDP agent 封装（骨架） | `skillopt/envs/edp/agent.py` |
| EDP dataloader（骨架） | `skillopt/envs/edp/dataloader.py` |
| EDP evaluator（骨架） | `skillopt/envs/edp/evaluator.py` |
| EDP 初始 skill | `skillopt/envs/edp/skills/initial.md` |
| EDP 失败分析 prompt | `skillopt/envs/edp/prompts/analyst_error.md` |
| EDP 成功分析 prompt | `skillopt/envs/edp/prompts/analyst_success.md` |
| EnvAdapter 基类 | `skillopt/envs/base.py` |
| ReflACT 类型定义 | `skillopt/types.py` |
| SearchQA adapter（参考） | `skillopt/envs/searchqa/adapter.py` |
| SearchQA dataloader（参考） | `skillopt/envs/searchqa/dataloader.py` |
| 基础配置 | `configs/_base_/default.yaml` |
| SearchQA 配置（参考） | `configs/searchqa/default.yaml` |
| 首次跑通手记 | `docs/handoff/skillopt-first-run.md` |
| EDP 集成 handoff | `docs/handoff/2026-06-01-edp-agent-integration.md` |

---

## 9. Open Questions

这些是需要 EDP 团队回答的阻塞性问题：

1. **Rollout HTTP API 的契约是什么？**（endpoint, request schema, response schema, auth）
2. **Skill upload API 的契约是什么？**（endpoint, request schema, 是否支持增量更新）
3. **轨迹格式是什么？**（tool_call / env_step / plain message？能看到内部 skill 调用链吗？）
4. **EDPAgent 有哪些工具？每个工具的作用是什么？**（影响 analyst prompt 的领域知识）
5. **现有手搓 skill 的文本在哪？**（用于填充 `skills/initial.md`）
6. **任务数据集由谁提供？**（EDP 团队提供还是自己构建？）
