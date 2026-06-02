"""EDPAgent 的评估逻辑。

评估 agent 输出与 ground truth 的匹配程度。
"""

from __future__ import annotations


def evaluate(
    predicted: str,
    ground_truth: str,
    item: dict | None = None,
    **kwargs,
) -> dict:
    """评估单个 agent 输出的正确性。

    Parameters
    ----------
    predicted : str
        Agent 的预测输出/答案。
    ground_truth : str
        标准答案。
    item : dict, optional
        完整的 task item（可用于更复杂的评估逻辑，如多条件判断）。

    Returns
    -------
    dict
        {
          "ok": bool,        # 是否完全正确（决定 hard score）
          "reason": str,     # 简短说明（如 fail_reason）
          "score": float,    # 部分正确分数 0.0-1.0（决定 soft score），可选
        }

    示例：简单字符串匹配
    --------------------
    .. code-block:: python

        def evaluate(predicted, ground_truth, item=None):
            if predicted.strip().lower() == ground_truth.strip().lower():
                return {"ok": True, "reason": "", "score": 1.0}
            return {"ok": False, "reason": f"mismatch: got {predicted!r}, expected {ground_truth!r}", "score": 0.0}

    示例：F1 / 模糊匹配
    --------------------
    .. code-block:: python

        def evaluate(predicted, ground_truth, item=None):
            # 使用 BLEU / ROUGE / 自定义指标
            score = compute_similarity(predicted, ground_truth)
            ok = score >= 0.9
            return {"ok": ok, "reason": f"similarity={score:.2f}", "score": score}
    """
    # TODO: 实现 EDPAgent 的评估逻辑
    #
    # 评估结果直接影响 SkillOpt 的训练：
    # - hard=1 → 轨迹进入 success analyst → 强化成功模式
    # - hard=0 → 轨迹进入 error analyst → 诊断失败模式
    # - soft score → 用于 Gate 阶段的细粒度比较
    raise NotImplementedError
