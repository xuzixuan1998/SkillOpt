# EDPAgent Integration Roadmap

将 SkillOpt 接入 EDPAgent 的开发步骤。
> 每个任务的负责人填在 `👤` 后面，完成后打 `[x]`。

---

## 第一阶段：数据集准备

### 1.1 确定数据集格式
- [x] 确定每个 task item 的字段结构：`id`, `query`, `task_type`, `ground_truth`, `rubrics`
- [x] 准备原始数据集文件（JSON 格式，5 条 sample items 已就绪）
- 👤 Zixuan Xu (2026-06-01)

### 1.2 数据切分
- [x] 支持两种切分方式：`split_mode="split_dir"`（手工）和 `split_mode="ratio"`（自动）
- [x] 验证切分后的数据可以正确加载（14 dataloader tests pass）
- 👤 Zixuan Xu (2026-06-01)

### 1.3 评估标准定义
- [x] 确定评判接口：`evaluate(predicted, ground_truth, item) -> {"ok": bool, "reason": str, "score": float}`
  - `ok` → hard score (0/1)，`score` → soft score (0.0-1.0)
- [ ] 实现具体评估逻辑（阻塞项 B1/B3：需要 EDP agent 实际输出格式）
- 👤 同事负责 evaluator 实现

---

## 第二阶段：核心接口实现

> 文件位置：`skillopt/envs/edp/`

### 2.1 `dataloader.py` — 数据加载器 ✅
- [x] 继承 `SplitDataLoader`，基类 `_load_json_or_jsonl()` 已支持 JSON array / JSONL / 嵌套 dict 三种格式
- [x] **无需覆写 `load_raw_items()`** — 基类行为完全满足 EDP 数据格式需求
- 👤 Zixuan Xu (2026-06-01, 简化于 2026-06-02)

### 2.2 `agent.py` — Agent 调用封装
- [ ] 实现 `run_agent(item, skill_content, **kwargs) -> dict`
  - 输入：单个 task item + 当前 skill prompt
  - 输出：`{"conversation": [...], "n_turns": N, ...}`
- [ ] conversation 格式选择（三选一，见下方说明）
- [ ] 处理超时、异常、重试
- [ ] 将 EDPAgent 产生的输出文件保存到 `out_dir/predictions/<task_id>/`
- 🔒 **阻塞项 B1**: EDP Rollout HTTP API (endpoint / schema / 认证 / 超时)
- 🔒 **阻塞项 B3**: EDPAgent 轨迹格式 + 工具列表
- 👤 ___

#### conversation 格式说明

| 格式 | 适用场景 | 示例 |
|------|---------|------|
| `{"type": "tool_call", "cmd": ..., "obs": ...}` | 有工具调用的 agent | bash、web search、API 调用等 |
| `{"step": N, "action": ..., "env_feedback": ..., "reasoning": ...}` | 有环境交互的 agent | 游戏、模拟器等 |
| `{"type": "message", "content": ...}` | 纯文本对话 agent | QA、代码生成（无工具） |

> 这三种格式在 Reflect 阶段会被 `fmt_trajectory()` 统一归一化，选最接近 EDPAgent 原始输出的一种即可。

### 2.3 `rollout.py` — 批量执行
- [x] 实现 `process_one(item, ...) -> dict`：单任务执行框架已就绪（目录创建、结果结构、异常处理）
- [x] 实现 `run_batch(items, ...) -> list[dict]`：并发 + 断点续跑 + 超时处理已完整实现
- [x] 每完成一个 task，将 conversation 保存到 `predictions/<task_id>/conversation.json`（路径逻辑就绪，保存代码注释中）
- [x] 将汇总结果写入 `results.jsonl`（已实现）
- [x] 支持断点续跑（resume，已实现）
- [x] `task_id` 异常安全：缺失 id 时返回 `{"id": "unknown", ...}` 而非崩溃
- [ ] 取消 agent + evaluator 调用注释，串联全流程
- 🔒 **阻塞项 B1/B3**: 等 agent.py 和 evaluator.py 就绪
- 👤 Zixuan Xu (2026-06-01/02)

### 2.4 `evaluator.py` — 评估逻辑
- [x] 接口定义：`evaluate(predicted, ground_truth, item) -> {"ok": bool, "reason": str, "score": float}`
- [ ] 实现具体评估逻辑（硬/软评分规则）
- 👤 同事负责
- 🔒 **阻塞项 B1/B3**: 需了解 EDP agent 的实际输出格式

### 2.5 `adapter.py` — 环境适配器
- [x] 继承 `EnvAdapter`，实现 4 个抽象方法：
  - [x] `build_train_env(batch_size, seed)` ✅
  - [x] `build_eval_env(env_num, split, seed)` ✅
  - [ ] `rollout(env_manager, skill_content, out_dir)` — 代码骨架就绪，注释中，等 agent/evaluator
  - [x] `reflect(results, skill_content, out_dir)` ✅ (委托 `run_minibatch_reflect()`)
  - [x] `get_task_types()` ✅ (5 个金融推荐子类型)
- 👤 Zixuan Xu (2026-06-01/02)

### 2.6 `reflect.py` — 分析 prompt 配置（可选）
- [x] 无需修改 — 直接委托 `run_minibatch_reflect()`，靠 prompts/ 目录下的 analyst 模板
- 👤 Zixuan Xu (2026-06-01)

---

## 第三阶段：Prompt 模板

> 文件位置：`skillopt/envs/edp/prompts/`

### 3.1 `analyst_error.md` — 失败分析 prompt
- [ ] 告诉 Optimizer LLM 如何从 EDPAgent 失败轨迹中提取共性模式
- [ ] 包含输出 JSON schema（patch 格式）
- [ ] 如果任务有领域特定概念，在这里解释
- 🔒 **阻塞项 B3**: 需要 EDPAgent 轨迹格式 + 工具列表后才能写
- 👤 ___

### 3.2 `analyst_success.md` — 成功分析 prompt
- [ ] 告诉 Optimizer LLM 如何从 EDPAgent 成功轨迹中提取强化策略
- [ ] 包含输出 JSON schema
- 🔒 **阻塞项 B3**: 同上
- 👤 ___

### 3.3 `skills/initial.md` — 初始 skill prompt ✅
- [x] 金融推荐场景的初始 skill prompt，含 Core Rules / Workflow / Common Pitfalls / Examples 四节
- [x] 已包含 `<!-- SLOW_UPDATE_START -->` / `<!-- SLOW_UPDATE_END -->` 标记
- 👤 Zixuan Xu (2026-06-01)

---

## 第四阶段：训练配置与测试

### 4.1 训练配置文件 ✅
- [x] `configs/edp/default.yaml` — 继承 `_base_/default.yaml`，`env.name=edp`
- 👤 Zixuan Xu (2026-06-01)

### 4.2 冒烟测试
- [x] 单元测试：43 tests pass，覆盖 dataloader / adapter / rollout / config / skill
- [ ] 单 task rollout 测试：需等 agent/evaluator 就绪
- [ ] 小批量（5-10 task）训练测试：确保 Reflect → Aggregate → Select → Update 完整链路跑通
- [ ] 对照 `outputs/` 目录检查所有中间产物是否正确保存
- 🔒 **阻塞项 B1/B2/B3**: 全链路测试需 EDP API 就绪
- 👤 Zixuan Xu (部分完成于 2026-06-01/02)

### 4.3 正式训练
- [ ] 全量数据训练
- [ ] 监控训练曲线（hard/soft score 变化）
- [ ] 调参（edit_budget、minibatch_size、learning rate 等）
- 🔒 等待 Phase 2 + Phase 3 全部解除阻塞
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
