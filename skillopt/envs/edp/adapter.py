"""EDPAgent environment adapter for ReflACT.

将 SkillOpt 训练循环连接到 EDPAgent。
实现 :class:`~skillopt.envs.base.EnvAdapter` 的 4 个抽象方法。
"""

from __future__ import annotations

import os

from skillopt.datasets.base import BatchSpec
from skillopt.envs.base import EnvAdapter
from skillopt.envs.edp.dataloader import EDPDataLoader
from skillopt.gradient.reflect import run_minibatch_reflect

TASK_TYPES: list[str] = [
    "fund_recommendation",
    "asset_allocation",
    "retirement_planning",
    "beginner_planning",
    "risk_management",
]


class EDPAdapter(EnvAdapter):
    """EDPAgent 环境适配器。

    参数说明
    --------
    split_dir : str
        预切分好的数据目录（含 train/val/test 子目录）。
    data_path : str
        原始数据集路径（JSON/JSONL），当 split_mode="ratio" 时使用。
    split_mode : str
        ``"ratio"`` 按比例自动切分，``"split_dir"`` 使用预切分数据。
    split_ratio : str
        train:val:test 比例，如 ``"2:1:7"``。
    split_seed : int
        切分随机种子。
    split_output_dir : str
        自动切分结果的输出目录。
    max_turns : int
        每个任务的最大 agent 交互轮数。
    exec_timeout : int
        每个任务的超时时间（秒）。
    workers : int
        rollout 阶段的并发 worker 数。
    analyst_workers : int
        Reflect 阶段的并发 analyst 数。
    failure_only : bool
        是否只分析失败轨迹（跳过成功轨迹）。
    minibatch_size : int
        每个 Reflect minibatch 的轨迹数（M）。
    edit_budget : int
        每次 Reflect 的最大编辑数（L，类似学习率）。
    seed : int
        全局随机种子。
    limit : int
        限制数据集大小（0=不限制，用于快速测试）。
    max_completion_tokens : int
        每次 LLM 调用的最大 completion token 数。
    """

    def __init__(
        self,
        # ── 数据配置 ──
        split_dir: str = "",
        data_path: str = "",
        split_mode: str = "ratio",
        split_ratio: str = "2:1:7",
        split_seed: int = 42,
        split_output_dir: str = "",
        # ── 执行配置 ──
        max_turns: int = 10,
        exec_timeout: int = 300,
        workers: int = 32,
        max_completion_tokens: int = 16384,
        # ── Reflect 配置 ──
        analyst_workers: int = 16,
        failure_only: bool = False,
        minibatch_size: int = 8,
        edit_budget: int = 4,
        # ── 其他 ──
        seed: int = 42,
        limit: int = 0,
    ) -> None:
        self.max_turns = max_turns
        self.exec_timeout = exec_timeout
        self.workers = workers
        self.max_completion_tokens = int(max_completion_tokens)
        self.analyst_workers = analyst_workers
        self.failure_only = failure_only
        self.minibatch_size = minibatch_size
        self.edit_budget = edit_budget

        self.dataloader = EDPDataLoader(
            split_dir=split_dir,
            data_path=data_path,
            split_mode=split_mode,
            split_ratio=split_ratio,
            split_seed=split_seed,
            split_output_dir=split_output_dir,
            seed=seed,
            limit=limit,
        )

    # ── Lifecycle ──────────────────────────────────────────────────────────

    def setup(self, cfg: dict) -> None:
        """Trainer 启动时调用一次，用于初始化 dataloader 等。"""
        super().setup(cfg)
        self.dataloader.setup(cfg)

    def get_dataloader(self):
        """返回 DataLoader 实例。"""
        return self.dataloader

    # ── 必须实现的 4 个抽象方法 ───────────────────────────────────────────

    def build_train_env(self, batch_size: int, seed: int, **kwargs):
        """构建训练环境 — 返回一个 batch 的 task items。

        Returns
        -------
        list[dict]
            采样的 task item 列表，每个 dict 至少包含 ``"id"`` 字段。
        """
        batch = self.dataloader.build_train_batch(batch_size=batch_size, seed=seed, **kwargs)
        return self.build_env_from_batch(batch, **kwargs)

    def build_eval_env(self, env_num: int, split: str, seed: int, **kwargs):
        """构建评估环境 — 返回评估集的 task items。

        Parameters
        ----------
        env_num : int
            要评估的任务数量。
        split : str
            数据集分片名（``"val"`` 或 ``"test"``）。
        seed : int
            随机种子。

        Returns
        -------
        list[dict]
        """
        batch = self.dataloader.build_eval_batch(env_num=env_num, split=split, seed=seed, **kwargs)
        return self.build_env_from_batch(batch, **kwargs)

    def build_env_from_batch(self, batch: BatchSpec, **kwargs):
        """从 BatchSpec 构建 items 列表（静态数据集场景）。"""
        return list(batch.payload or [])

    def rollout(
        self,
        env_manager,
        skill_content: str,
        out_dir: str,
        **kwargs,
    ) -> list[dict]:
        """对 env_manager 中的所有 task items 运行 EDPAgent，返回结果。

        env_manager 就是 list[dict]（来自 build_train_env / build_eval_env 的返回值）。

        每个返回的 dict 必须包含：
        - ``"id"`` (str)
        - ``"hard"`` (0/1)
        - ``"soft"`` (0.0 ~ 1.0)

        推荐包含（给 Reflect 分析师使用）：
        - ``"fail_reason"`` — 失败原因
        - ``"task_description"`` — 任务描述
        - ``"task_type"``  — 任务类别
        - ``"n_turns"`` — 执行步数
        - ``"target_system_prompt"`` — agent 使用的 system prompt
        - ``"target_user_prompt"`` — agent 使用的 user prompt

        Returns
        -------
        list[dict]
        """
        # items = env_manager
        # results = run_batch(
        #     items=items,
        #     skill_content=skill_content,
        #     out_root=out_dir,
        #     max_turns=self.max_turns,
        #     exec_timeout=self.exec_timeout,
        #     max_api_workers=self.workers,
        #     max_completion_tokens=self.max_completion_tokens,
        # )
        # return results
        raise NotImplementedError

    def reflect(
        self,
        results: list[dict],
        skill_content: str,
        out_dir: str,
        **kwargs,
    ) -> list[dict | None]:
        """分析 rollout 结果，产出补丁列表。

        委托给通用的 ``run_minibatch_reflect()``。
        框架会根据 ``_env_name`` 自动加载 ``prompts/analyst_error.md``
        和 ``prompts/analyst_success.md``。

        Returns
        -------
        list[dict | None]
            RawPatch dict 列表，每个含 ``"patch"`` + ``"source_type"``。
        """
        prediction_dir = kwargs.get("prediction_dir", os.path.join(out_dir, "predictions"))
        patches_dir = kwargs.get("patches_dir", os.path.join(out_dir, "patches"))
        random_seed = kwargs.get("random_seed")
        step_buffer_context = kwargs.get("step_buffer_context", "")
        meta_skill_context = kwargs.get("meta_skill_context", "")

        return run_minibatch_reflect(
            results=results,
            skill_content=skill_content,
            prediction_dir=prediction_dir,
            patches_dir=patches_dir,
            workers=self.analyst_workers,
            failure_only=self.failure_only,
            minibatch_size=self.minibatch_size,
            edit_budget=self.edit_budget,
            random_seed=random_seed,
            error_system=self.get_error_minibatch_prompt(),
            success_system=self.get_success_minibatch_prompt(),
            step_buffer_context=step_buffer_context,
            meta_skill_context=meta_skill_context,
            update_mode=getattr(self, "_cfg", {}).get("skill_update_mode", "patch"),
        )

    def get_task_types(self) -> list[str]:
        """返回任务类型列表，用于 per-category 指标分解。"""
        return list(TASK_TYPES)
