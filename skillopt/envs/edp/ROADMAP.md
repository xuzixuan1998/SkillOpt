# EDPAgent Integration Roadmap

将 SkillOpt 接入 EDPAgent 的开发步骤。
> 每个任务的负责人填在 `👤` 后面，完成后打 `[x]`。

---

## 第一阶段：数据集准备

### 1.1 确定数据集格式
- [ ] 确定每个 task item 的字段结构（必须含 `id`，其余按需）
- [ ] 准备原始数据集文件（JSON/JSONL 格式）
- 👤 ___

### 1.2 数据切分
- [ ] 决定切分方式：手工切分 或 让 SkillOpt 按比例自动切分
  - 手工：准备 `train/items.json`、`val/items.json`、`test/items.json`
  - 自动：提供 `data_path` + `split_ratio`（如 `2:1:7`）
- [ ] 验证切分后的数据可以正确加载
- 👤 ___

### 1.3 评估标准定义
- [ ] 确定 EDPAgent 任务的评判标准（hard score: 完全正确=1 否则=0，soft score: 部分正确 0.0~1.0）
- [ ] 特殊情况：如果原评估逻辑较复杂或依赖外部 API，建议提前考虑
- 👤 ___

---

## 第二阶段：核心接口实现

> 文件位置：`skillopt/envs/edp/`

### 2.1 `dataloader.py` — 数据加载器
- [ ] 继承 `SplitDataLoader`（如果数据格式为标准 JSON）
- [ ] 如果数据有特殊加载逻辑，覆写 `load_raw_items()` 或 `load_split_items()`
- 👤 ___

### 2.2 `agent.py` — Agent 调用封装
- [ ] 实现 `run_agent(item, skill_content, **kwargs) -> dict`
  - 输入：单个 task item + 当前 skill prompt
  - 输出：`{"conversation": [...], "n_turns": N, ...}`
- [ ] conversation 格式选择（三选一，见下方说明）
- [ ] 处理超时、异常、重试
- [ ] 将 EDPAgent 产生的输出文件保存到 `out_dir/predictions/<task_id>/`
- 👤 ___

#### conversation 格式说明

| 格式 | 适用场景 | 示例 |
|------|---------|------|
| `{"type": "tool_call", "cmd": ..., "obs": ...}` | 有工具调用的 agent | bash、web search、API 调用等 |
| `{"step": N, "action": ..., "env_feedback": ..., "reasoning": ...}` | 有环境交互的 agent | 游戏、模拟器等 |
| `{"type": "message", "content": ...}` | 纯文本对话 agent | QA、代码生成（无工具） |

> 这三种格式在 Reflect 阶段会被 `fmt_trajectory()` 统一归一化，选最接近 EDPAgent 原始输出的一种即可。

### 2.3 `rollout.py` — 批量执行
- [ ] 实现 `process_one(item, ...) -> dict`：单个任务执行+评估，返回 RolloutResult 兼容 dict
- [ ] 实现 `run_batch(items, ...) -> list[dict]`：批量执行，支持并发
- [ ] 每完成一个 task，将 conversation 保存到 `predictions/<task_id>/conversation.json`
- [ ] 将汇总结果写入 `results.jsonl`
- [ ] 支持断点续跑（resume）
- 👤 ___

### 2.4 `evaluator.py` — 评估逻辑
- [ ] 实现 `evaluate(prediction, ground_truth, ...) -> {"ok": bool, "reason": str}`
- [ ] hard score 归约：所有测试用例通过 → 1，否则 → 0
- [ ] soft score 归约：通过用例数 / 总用例数（或其他自定义比例）
- 👤 ___

### 2.5 `adapter.py` — 环境适配器
- [ ] 继承 `EnvAdapter`，实现 4 个抽象方法：
  - `build_train_env(batch_size, seed)` → 返回 task item 列表
  - `build_eval_env(env_num, split, seed)` → 返回 task item 列表
  - `rollout(env_manager, skill_content, out_dir)` → 批量执行并返回结果
  - `reflect(results, skill_content, out_dir)` → 调用 `run_minibatch_reflect()`
  - `get_task_types()` → 返回任务类型列表
- 👤 ___

### 2.6 `reflect.py` — 分析 prompt 配置（可选）
- [ ] 如果需要自定义 Reflect 阶段的 prompt 加载逻辑，在此实现
- [ ] 大多数情况下不需要修改此文件，靠 `prompts/analyst_error.md` 和 `prompts/analyst_success.md` 即可
- 👤 ___

---

## 第三阶段：Prompt 模板

> 文件位置：`skillopt/envs/edp/prompts/`

### 3.1 `analyst_error.md` — 失败分析 prompt
- [ ] 告诉 Optimizer LLM 如何从 EDPAgent 失败轨迹中提取共性模式
- [ ] 包含输出 JSON schema（patch 格式）
- [ ] 如果任务有领域特定概念，在这里解释
- 👤 ___

### 3.2 `analyst_success.md` — 成功分析 prompt
- [ ] 告诉 Optimizer LLM 如何从 EDPAgent 成功轨迹中提取强化策略
- [ ] 包含输出 JSON schema
- 👤 ___

### 3.3 `skills/initial.md` — 初始 skill prompt
- [ ] 写一个初始的 skill prompt 模板（EDPAgent 的 system prompt）
- [ ] 这是优化的起点，写清楚 agent 应该遵循的规则和策略
- 👤 ___

---

## 第四阶段：训练配置与测试

### 4.1 训练配置文件
- [ ] 写一个 `configs/edp.yaml` 或 `configs/edp.json`
  - 指定 `env: edp`、`data_path`、`out_root` 等关键参数
  - 指定模型后端（`REFLACT_MODEL_BACKEND=codex` 或 `claude`）
- 👤 ___

### 4.2 冒烟测试
- [ ] 单 task rollout 测试：确保 EDPAgent 调用正常，conversation.json 正确生成
- [ ] 小批量（5-10 task）训练测试：确保 Reflect → Aggregate → Select → Update 完整链路跑通
- [ ] 对照 `outputs/` 目录检查所有中间产物是否正确保存
- 👤 ___

### 4.3 正式训练
- [ ] 全量数据训练
- [ ] 监控训练曲线（hard/soft score 变化）
- [ ] 调参（edit_budget、minibatch_size、learning rate 等）
- 👤 ___

---

## 附录：文件结构总览

```
skillopt/envs/edp/
├── __init__.py              # 包入口，导出 EDPAdapter
├── adapter.py               # ★ EnvAdapter 实现（4 个抽象方法）
├── dataloader.py            # ★ 数据加载器（继承 SplitDataLoader）
├── agent.py                 # ★ EDPAgent 的调用封装
├── rollout.py               # ★ 批量执行 + 结果保存
├── evaluator.py             # ★ 评估逻辑
├── reflect.py               # Reflect prompt 配置（可选）
├── ROADMAP.md               # 本文档
├── prompts/
│   ├── analyst_error.md     # 失败分析 prompt
│   └── analyst_success.md   # 成功分析 prompt
└── skills/
    └── initial.md           # 初始 skill prompt 模板
```

> ★ = 核心文件，必须实现

## 附录：与 SkillOpt 框架的交互点

```
EDPAdapter.rollout()
    │
    │  agent.py 执行 EDPAgent
    │  + evaluator.py 评分
    │  = results.jsonl + conversation.json
    ▼
EDPAdapter.reflect()
    │
    │  调用 run_minibatch_reflect()（框架提供）
    │  + prompts/analyst_error.md
    │  + prompts/analyst_success.md
    │  = patches/*.json
    ▼
框架自动：Aggregate → Select → Update → Gate
    （不需要你实现）
```
