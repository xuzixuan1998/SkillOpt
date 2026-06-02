# Development Plan: EDPAgent × SkillOpt Integration

**Date:** 2026-06-01
**Source Spec:** `docs/spec/edp-agent-integration.md`
**Status:** Ready for review

---

## Phase 0: Prerequisites Check (Checkpoint)

> 在开始任何编码工作前，确认以下前置条件已满足。

- [ ] **P0.1** — 开发环境可用：`pip install -e ".[dev]"` 通过，`ruff --version` 正常
- [ ] **P0.2** — 参考实现可运行：SearchQA adapter 的 `configs/searchqa/default.yaml` 能被 YAML parser 正确加载
- [ ] **P0.3** — 理解 ReflACT 6 阶段管道：已阅读 `CLAUDE.md` 和 `skillopt/engine/trainer.py` 核心流程

**校验方式：**
```bash
pip install -e ".[dev]"
ruff check skillopt/envs/edp/
python -c "from skillopt.envs.edp import EDPAdapter; print('OK')"
```

---

## Phase 1: Unblocked Foundation (可立即推进)

> 以下任务 **不依赖 EDP 服务端**，全部可以立即执行。

### Task 1.1: `dataloader.py` — 数据加载器实现

| 字段 | 内容 |
|------|------|
| **依赖** | 无（`SplitDataLoader` 基类已完备） |
| **估时** | 30min |
| **负责人** | Zixuan |

**当前状态：** `EDPDataLoader(SplitDataLoader)` 已定义，`pass` 即可用。但需要覆写 `load_raw_items()` 以处理 EDP 特定的数据格式。

**工作内容：**

1. 参考 `SearchQADataLoader.load_raw_items()` 实现 `EDPDataLoader.load_raw_items()`
2. 数据格式与 `SplitDataLoader._load_json_or_jsonl()` 兼容 → 大概率无需覆写，直接复用基类
3. 如果原始数据集是自定义格式（非标准 JSON/JSONL），实现自定义解析逻辑

**验收标准：**
- [ ] `load_raw_items(data_path)` 能正确加载 JSON/JSONL 文件
- [ ] `load_split_items(split_path)` 能正确加载单个 split 的 items
- [ ] `build_train_batch(batch_size, seed)` 返回正确的 `BatchSpec`
- [ ] `build_eval_batch(env_num, split, seed)` 返回正确的 `BatchSpec`
- [ ] `ruff check` 通过

**验证步骤：**
```python
from skillopt.envs.edp.dataloader import EDPDataLoader

# 测试 JSON 加载
loader = EDPDataLoader(data_path="tests/fixtures/edp_sample.json", split_mode="ratio")
loader.setup({"split_mode": "ratio", "data_path": "tests/fixtures/edp_sample.json"})

# 测试 batch 构建
batch = loader.build_train_batch(batch_size=4, seed=42)
assert len(batch.payload) > 0
```

---

### Task 1.2: `adapter.py` — 环境适配器解注释

| 字段 | 内容 |
|------|------|
| **依赖** | Task 1.1 (dataloader) |
| **估时** | 20min |
| **负责人** | Zixuan |

**当前状态：** `EDPAdapter` 骨架完整，核心逻辑被 TODO 注释包裹。结构与 `SearchQAAdapter` 高度一致。

**工作内容：**

1. 取消 `__init__()` 中 dataloader 初始化的注释（`self.dataloader = EDPDataLoader(...)`）
2. 取消 `setup()` 中 `self.dataloader.setup(cfg)` 的注释
3. 取消 `get_dataloader()` 的注释（`return self.dataloader`）
4. 取消 `build_train_env()` 的注释（委托给 dataloader）
5. 取消 `build_eval_env()` 的注释（委托给 dataloader）
6. 取消 `build_env_from_batch()` 的注释
7. **保持** `rollout()` 为注释状态（依赖 agent.py + EDP server）

**验收标准：**
- [ ] `EDPAdapter.__init__()` 初始化 `self.dataloader`
- [ ] `setup()` 调用 `self.dataloader.setup(cfg)`
- [ ] `get_dataloader()` 返回 dataloader 实例
- [ ] `build_train_env()` / `build_eval_env()` / `build_env_from_batch()` 委托给 dataloader
- [ ] `reflect()` 保持不变（已正确实现）
- [ ] 结构与 `SearchQAAdapter` 一致
- [ ] `ruff check` 通过

**参考文件：**
- `skillopt/envs/searchqa/adapter.py:18-130` — 完整参考实现

---

### Task 1.3: `configs/edp/default.yaml` — 训练配置

| 字段 | 内容 |
|------|------|
| **依赖** | 无 |
| **估时** | 15min |
| **负责人** | Zixuan |

**工作内容：**

创建 `configs/edp/default.yaml`，继承 `_base_/default.yaml`：

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
- [ ] 配置文件可被 Python YAML parser 正确加载
- [ ] 继承链正确（base → edp），override 值生效
- [ ] `env.name == "edp"`

**验证步骤：**
```python
import yaml
with open("configs/edp/default.yaml") as f:
    cfg = yaml.safe_load(f)
print(cfg["env"]["name"])  # "edp"
```

---

### Task 1.4: `skills/initial.md` — 初始 Skill Prompt

| 字段 | 内容 |
|------|------|
| **依赖** | 需要 EDP 团队提供手搓 skill 文本（非技术依赖，可并行询问） |
| **估时** | 拿到手搓 skill → 10min；自己写 → 1h+ |
| **负责人** | Zixuan |

**工作内容：**

1. 联系 EDP 团队获取现有手搓 skill 内容
2. 填入 `skillopt/envs/edp/skills/initial.md` 模板
3. 保持模板结构（`## Core Rules`, `## Workflow`, `## Common Pitfalls`, `## Examples`）
4. 确保 `<!-- SLOW_UPDATE_START -->` / `<!-- SLOW_UPDATE_END -->` 标记存在

**如果暂时拿不到手搓 skill：**

写一个占位版本，包含金融推荐场景的基础规则：
- 基金筛选规则（风险匹配、历史业绩、费率）
- 风险评估方法
- 推荐输出格式
- 常见陷阱和注意事项

**验收标准：**
- [ ] 包含结构化的 markdown 内容（`##` 分节）
- [ ] 不硬编码具体任务答案
- [ ] 包含 `<!-- SLOW_UPDATE_START -->` / `<!-- SLOW_UPDATE_END -->` 标记
- [ ] 内容与金融推荐场景相关

---

### Phase 1 Checkpoint

完成 Phase 1 后，验证：

```bash
# 1. 代码质量
ruff check skillopt/envs/edp/ && ruff format skillopt/envs/edp/

# 2. 导入验证
python -c "
from skillopt.envs.edp import EDPAdapter
from skillopt.envs.edp.dataloader import EDPDataLoader
print('All imports OK')
"

# 3. 配置加载
python -c "
import yaml
with open('configs/edp/default.yaml') as f:
    cfg = yaml.safe_load(f)
assert cfg['env']['name'] == 'edp'
print('Config OK')
"
```

---

## Phase 2: Blocked — 等待 EDP 团队

> 以下任务 **全部依赖 EDP 服务端 API**，需要等待外部信息后才能推进。

### Blocker B1: EDP Rollout HTTP API 契约

**需要的回答（来自 spec §9）：**

1. HTTP endpoint URL 格式？
2. 请求 body schema（query 字段？额外参数？）
3. 响应 body schema（trajectory 格式？final answer 位置？）
4. 认证方式（API key？Bearer token？）
5. 超时/重试策略建议？

### Blocker B2: EDP Skill Upload API 契约

**需要的回答：**

1. HTTP endpoint URL 格式？
2. 请求 body schema？
3. 是否支持增量更新（还是必须全量替换）？

### Blocker B3: EDPAgent 轨迹格式 + 工具列表

**需要的回答：**

1. 轨迹格式是什么？（tool_call / env_step / plain message？）
2. 能否看到内部 skill 调用链？
3. EDPAgent 有哪些工具？每个工具的作用是什么？
4. 常见失败模式有哪些？
5. 现有手搓 skill 的文本在哪？

### Blocker B4: 任务数据集

**需要的回答：**

1. 数据集由谁提供？（EDP 团队 vs 自己构建）
2. 数据集规模和格式？

---

## Phase 3: Agent + Evaluator Integration (解除阻塞后)

> 执行条件：Phase 1 完成 + B1/B2/B3 获得回答。

### Task 3.1: `agent.py` — Agent 调用封装

| 字段 | 内容 |
|------|------|
| **依赖** | B1 (EDP rollout HTTP API 契约) |
| **估时** | 2-3h |
| **负责人** | Zixuan |

**工作内容：**

1. 实现 `_build_system_prompt(skill_content)` — 将 skill 嵌入 EDP system prompt 模板
2. 实现 `_build_user_prompt(item)` — 根据 task item 构建 user prompt
3. 实现 `run_agent()` — 核心执行循环：
   - POST 到 EDP HTTP endpoint
   - 等待 agent 执行完成（支持超时/重试）
   - 解析 trajectory + final answer
   - 返回标准 dict：`{"conversation": [...], "n_turns": N, "predicted_answer": "..."}`

**关键决策点：**

- conversation 格式选择（三选一），取决于 EDPAgent 的实际交互模式
- 重试策略：网络错误自动重试，逻辑错误不重试
- 超时处理：`exec_timeout` 硬超时 + TCP 层面的 connect/read timeout

**验收标准：**
- [ ] `run_agent()` 能成功调用 EDP HTTP endpoint
- [ ] 返回 dict 包含 `conversation` (list), `n_turns` (int), `predicted_answer` (str)
- [ ] conversation 格式与 Reflect 阶段的 `fmt_trajectory()` 兼容
- [ ] 超时场景返回错误标记而非崩溃
- [ ] HTTP 错误有合理的异常处理
- [ ] `ruff check` 通过

---

### Task 3.2: `rollout.py` — 串联 Agent + Evaluator

| 字段 | 内容 |
|------|------|
| **依赖** | Task 3.1 (agent.py), Task 3.3 (evaluator.py) |
| **估时** | 1h |
| **负责人** | Zixuan |

**当前状态：** `run_batch()` 完整（并发、超时、断点续跑），`process_one()` 骨架完整。只需取消 agent 调用 + evaluator 调用的 TODO 注释。

**工作内容：**

1. 取消 `process_one()` 中 agent 调用的注释（`from skillopt.envs.edp.agent import run_agent`）
2. 取消 evaluator 调用的注释（`from skillopt.envs.edp.evaluator import evaluate`）
3. 确保 results 字段与 `RolloutResult` 类型兼容

**验收标准：**
- [ ] `process_one(item)` 完整执行 agent + evaluator 流程
- [ ] `conversation.json` 保存到 `predictions/<task_id>/`
- [ ] `results.jsonl` 正确追加
- [ ] 断点续跑：已完成的 task 被跳过
- [ ] `ruff check` 通过

---

### Task 3.3: `evaluator.py` — 评估逻辑

| 字段 | 内容 |
|------|------|
| **依赖** | B3 (EDPAgent 输出格式 + rubrics 结构) |
| **估时** | 待同事确定 |
| **负责人** | 同事 |

**接口契约（与 spec §6.3 对齐）：**
```python
def evaluate(predicted: str, ground_truth: str, item: dict | None = None) -> dict:
    """返回 {"ok": bool, "reason": str, "score": float}"""
```

**验收标准：**
- [ ] 函数签名符合契约
- [ ] hard score 逻辑正确（完全正确 → 1，否则 → 0）
- [ ] soft score 逻辑合理（部分正确 0.0~1.0）
- [ ] `ruff check` 通过

---

### Task 3.4: `prompts/analyst_error.md` + `analyst_success.md`

| 字段 | 内容 |
|------|------|
| **依赖** | B3 (轨迹格式 + 领域知识) |
| **估时** | 1-2h |
| **负责人** | Zixuan |

**工作内容：**

1. 在 `analyst_error.md` 的 `<!-- TODO -->` 区域添加 EDPAgent 领域知识：
   - 可用工具列表及作用
   - 常见失败模式分类
   - 领域术语解释
2. 在 `analyst_success.md` 的 `<!-- TODO -->` 区域添加 EDPAgent 领域知识：
   - 关键成功因素
   - 高质量 reasoning 的特征
   - Best practice 行为描述
3. **不修改** JSON schema 部分（已正确）

**参考：** `skillopt/envs/searchqa/prompts/analyst_error.md` 和 `analyst_success.md`（如果存在）

**验收标准：**
- [ ] 两个 prompt 文件的 TODO 区域已替换为具体领域知识
- [ ] JSON schema 部分保持不变
- [ ] 不包含具体的任务答案或硬编码值
- [ ] 没有 markdown fence 包裹（prompt 是 raw markdown）

---

### Phase 3 Checkpoint

完成 Phase 3 后，验证端到端数据流：

```bash
# 单 task rollout（需要 EDP server 可用）
python -c "
from skillopt.envs.edp.agent import run_agent
result = run_agent(
    item={'id': 'test_001', 'query': '帮我推荐3只基金'},
    skill_content='# Test Skill\n\n## Rules\n- Always check risk level first.',
    max_turns=5,
)
assert 'conversation' in result
assert 'predicted_answer' in result
print('Agent OK')
"
```

---

## Phase 4: Prompts + Skill Polish (可部分并行)

> 执行条件：Phase 1 完成即可开始，但完整版本需要 B3 的信息。

### Task 4.1: `prompts/analyst_error.md` 完善

| 字段 | 内容 |
|------|------|
| **依赖** | B3 (轨迹格式 + 领域知识) |
| **估时** | 40min |
| **负责人** | Zixuan |

已在 Phase 3 Task 3.4 中合并处理。

---

### Task 4.2: `prompts/analyst_success.md` 完善

| 字段 | 内容 |
|------|------|
| **依赖** | B3 (轨迹格式 + 领域知识) |
| **估时** | 40min |
| **负责人** | Zixuan |

已在 Phase 3 Task 3.4 中合并处理。

---

## Phase 5: Integration Verification (冒烟测试)

> 执行条件：Phase 1-4 全部完成 + EDP server 可用。

### Task 5.1: 单 Task Rollout 测试

**目标：** 验证 EDPAgent 调用正常、产物正确。

- [ ] EDPAgent HTTP 调用成功（无网络错误）
- [ ] `conversation.json` 正确生成（格式与 `fmt_trajectory()` 兼容）
- [ ] `target_system_prompt.txt` 和 `target_user_prompt.txt` 保存
- [ ] `results.jsonl` 行包含所有必须字段（id, hard, soft）

### Task 5.2: 小批量训练（5-10 tasks）

**目标：** 验证 Reflect → Aggregate → Select → Update 全链路。

- [ ] Reflect 阶段产出 `patches/*.json` 文件
- [ ] Aggregate 阶段正确合并 minibatch patches
- [ ] Select 阶段正确截断 edit 数量
- [ ] Update 阶段产出 `candidate_skill.md`
- [ ] candidate skill 与原始 skill 有实际差异

### Task 5.3: 中间产物检查

- [ ] `results.jsonl` — 所有 task 的评估结果
- [ ] `predictions/<task_id>/conversation.json` — 每个 task 的执行轨迹
- [ ] `patches/*.json` — 每个 minibatch 的分析结果
- [ ] `aggregated_patch.json` — 合并后的 patch
- [ ] `candidate_skill.md` — 更新后的 skill
- [ ] `gate_result.json` — Gate 阶段的 ACCEPT/REJECT 判定

### Task 5.4: Skill Upload API 测试

- [ ] 优化后的 skill 能成功上传到 EDP server
- [ ] 上传后 EDPAgent 实际使用新 skill

---

## Phase 6: Full Training Run

> 执行条件：Phase 5 全部通过。

- [ ] 全量数据训练至少 1 epoch
- [ ] 训练曲线监控（hard/soft score 变化）
- [ ] 调参（`edit_budget`, `minibatch_size`, `learning_rate`）
- [ ] 产出最终优化 skill

---

## Dependency Graph

```
Phase 0 (Prerequisites)
  │
  ├── Task 1.1 (dataloader) ────┐
  ├── Task 1.3 (config)         │
  └── Task 1.4 (skill init)     │
        │                       │
        ▼                       ▼
      Task 1.2 (adapter 解注释)
        │
        ▼
  [Phase 1 Checkpoint] ─── 可独立验证，不需要 EDP server
        │
        ▼
  ╔══════════════════════════════════════╗
  ║  BLOCKED: 等待 EDP 团队回答 B1-B4   ║
  ╚══════════════════════════════════════╝
        │
        ▼
  Task 3.1 (agent.py) ─────────┐
  Task 3.3 (evaluator.py) ─────┤  (可并行)
  Task 3.4 (prompts) ──────────┘
        │
        ▼
  Task 3.2 (rollout 串联)
        │
        ▼
  [Phase 3 Checkpoint] ─── 端到端单 task 验证
        │
        ▼
  Phase 5 (集成冒烟测试)
        │
        ▼
  Phase 6 (全量训练)
```

---

## Risk Register

| Risk | 影响 | 缓解措施 |
|------|------|---------|
| EDP server API 迟迟不确定 | Phase 3-6 全部阻塞 | Phase 1 先行推进；mock server 可用于基本测试 |
| EDPAgent 轨迹格式复杂 | analyst prompt 需要大量重写 | 先用模板，拿到 real trajectory 后再精调 |
| 同事的 evaluator 延迟 | rollout 无法产出 hard/soft score | 先用占位 evaluator（总是返回 ok=True）；并行不阻塞 |
| 手搓 skill 拿不到 | `skills/initial.md` 内容质量低 | 先用通用金融推荐规则，后续迭代 |
| 数据集格式不标准 | dataloader 需要额外定制 | `SplitDataLoader` 已支持多种格式，大概率兼容 |

---

## Time Estimates Summary

| Phase | Tasks | 估时 (unblocked) | 估时 (blocked) |
|-------|-------|-----------------|----------------|
| Phase 1 | 1.1 + 1.2 + 1.3 + 1.4 | ~1.5h | - |
| Phase 3 | 3.1 + 3.2 + 3.3 + 3.4 | - | ~4-6h (含同事) |
| Phase 4 | prompt polish | - | ~1.5h |
| Phase 5 | integration tests | - | ~2h |
| Phase 6 | full training | - | 取决于数据规模 |
| **Total (Zixuan)** | | **~1.5h** | **~8-10h** |

---

## File Index (与 spec §8 一致)

| 想看什么 | 路径 |
|---------|------|
| 本计划 | `docs/plan/edp-agent-integration.md` |
| 原始 spec | `docs/spec/edp-agent-integration.md` |
| 开发路线图 | `skillopt/envs/edp/ROADMAP.md` |
| EDP adapter | `skillopt/envs/edp/adapter.py` |
| EDP rollout | `skillopt/envs/edp/rollout.py` |
| EDP agent | `skillopt/envs/edp/agent.py` |
| EDP dataloader | `skillopt/envs/edp/dataloader.py` |
| EDP evaluator | `skillopt/envs/edp/evaluator.py` |
| SearchQA adapter (参考) | `skillopt/envs/searchqa/adapter.py` |
| EnvAdapter 基类 | `skillopt/envs/base.py` |
| SplitDataLoader 基类 | `skillopt/datasets/base.py` |
