"""EDPAgent 的调用封装。

实现单个任务的 Agent 执行逻辑。被 ``rollout.py`` 中的批量函数调用。

核心约定
--------
返回的 ``conversation`` 是 SkillOpt Reflect 阶段的输入，用于诊断失败模式。
格式选择取决于 EDPAgent 的交互方式，三种都支持（最终由 ``fmt_trajectory()`` 归一化）。
"""

from __future__ import annotations

from typing import Any

# ── System / User prompt 构建 ──────────────────────────────────────────────


def _build_system_prompt(skill_content: str) -> str:
    """构建 EDPAgent 的 system prompt。

    将当前的 skill prompt 嵌入 system prompt 模板中。
    这是 SkillOpt 优化的核心 — 每次 Update 阶段修改 skill_content，
    下一次 rollout 时 system prompt 也随之改变。

    Parameters
    ----------
    skill_content : str
        当前 skill prompt 内容（由 SkillOpt 训练循环维护）。

    Returns
    -------
    str
        完整的 system prompt。
    """
    # TODO: 将 skill_content 嵌入 EDPAgent 的 system prompt 模板
    # 示例:
    #   template = load_prompt("your_system_template", env="edp")
    #   return template.format(skill=skill_content)
    raise NotImplementedError


def _build_user_prompt(item: dict, **kwargs) -> str:
    """根据 task item 构建 user prompt。

    Parameters
    ----------
    item : dict
        单个 task item，字段结构由你的数据集定义。

    Returns
    -------
    str
        agent 的 user prompt / 任务输入。
    """
    # TODO: 从 item 中提取信息，构建 user prompt
    # 典型结构:
    #   instruction = item["instruction"]
    #   context = item.get("context", "")
    #   return f"# Task\n{instruction}\n\n# Context\n{context}"
    raise NotImplementedError


# ── Agent 执行 ──────────────────────────────────────────────────────────────


def run_agent(
    item: dict,
    skill_content: str,
    *,
    max_turns: int = 10,
    max_completion_tokens: int = 16384,
    **kwargs,
) -> dict[str, Any]:
    """对单个 task 运行 EDPAgent。

    这是你需要实现的核心函数。

    Parameters
    ----------
    item : dict
        单个 task item。
    skill_content : str
        当前 skill prompt 文本。
    max_turns : int
        最大交互轮数。
    max_completion_tokens : int
        LLM 调用最大 completion token 数。

    Returns
    -------
    dict
        {
          "conversation": list[dict],   # ★ 执行轨迹
          "n_turns": int,               # 实际交互轮数
          "predicted_answer": str,      # Agent 的最终答案
          "target_system_prompt": str,  # 实际使用的 system prompt
          "target_user_prompt": str,    # 实际使用的 user prompt
          # ... 其他需要的字段
        }

    conversation 格式
    ------------------
    三种格式任选一种，对应不同的 agent 交互模式：

    **格式 A：工具调用型**（推荐，如果有工具调用）
    [
        {"type": "tool_call", "cmd": "...", "obs": "..."},
        {"type": "tool_call", "cmd": "...", "obs": "..."},
        {"type": "message", "content": "final answer..."},
    ]

    **格式 B：环境交互型**（适合有环境反馈的游戏/模拟器）
    [
        {"step": 1, "action": "...", "env_feedback": "...", "reasoning": "...", "reward": 0.0, "done": False},
        {"step": 2, "action": "...", "env_feedback": "...", "reasoning": "...", "reward": 1.0, "done": True},
    ]

    **格式 C：纯文本对话型**（适合简单 QA / 代码生成）
    [
        {"type": "message", "turn": 1, "content": "..."},
        {"type": "message", "turn": 2, "content": "..."},
    ]
    """
    # TODO: 实现 EDPAgent 的调用逻辑
    #
    # 典型流程：
    # 1. 构建 system/user prompt
    #    system = _build_system_prompt(skill_content)
    #    user = _build_user_prompt(item)
    #
    # 2. 调用 EDPAgent（多轮交互循环）
    #    conversation = []
    #    for turn in range(max_turns):
    #        response = call_edp_agent(system, user, messages_history)
    #        # 记录工具调用或文本回复
    #        # 如果 agent 给出了最终答案，break
    #
    # 3. 返回结果
    #    return {
    #        "conversation": conversation,
    #        "n_turns": len(conversation),
    #        "predicted_answer": final_answer,
    #        "target_system_prompt": system,
    #        "target_user_prompt": user,
    #    }
    raise NotImplementedError
