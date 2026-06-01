"""EDPAgent 批量 rollout 执行 + 结果保存。

提供：
- ``process_one()``:  单任务执行 + 评估
- ``run_batch()``:    批量执行 + 并发 + 断点续跑
"""
from __future__ import annotations

import json
import os
import time
import traceback
from concurrent.futures import (
    FIRST_COMPLETED,
    ThreadPoolExecutor,
    wait,
)


# ── 单任务执行 ──────────────────────────────────────────────────────────────

def process_one(
    item: dict,
    out_root: str,
    skill_content: str,
    max_turns: int = 10,
    max_completion_tokens: int = 16384,
    exec_timeout: int = 300,
    **kwargs,
) -> dict:
    """对单个 task 运行 EDPAgent + 评估。

    Parameters
    ----------
    item : dict
        单个 task item。
    out_root : str
        输出根目录（rollout 结果保存到 ``out_root/predictions/<task_id>/``）。
    skill_content : str
        当前 skill prompt。
    max_turns : int
        最大交互轮数。
    max_completion_tokens : int
        LLM 最大 completion token。
    exec_timeout : int
        单任务超时（秒）。

    Returns
    -------
    dict
        RolloutResult 兼容 dict，必须包含：
        - ``"id"``, ``"hard"`` (0/1), ``"soft"`` (0.0-1.0)

        推荐包含：
        - ``"fail_reason"``, ``"task_type"``, ``"task_description"``
        - ``"n_turns"``, ``"target_system_prompt"``, ``"target_user_prompt"``
    """
    task_id = str(item["id"])

    # TODO: 从 item 中提取任务信息
    # instruction = item["instruction"]
    # task_type = item.get("task_type", "default")

    # 初始化结果 dict
    result = {
        "id": task_id,
        "ok": False,
        "hard": 0,
        "soft": 0.0,
        "n_turns": 0,
        "fail_reason": "",
        "task_type": "",
        "task_description": "",
        "phase": "setup",
        "error": "",
    }

    try:
        # ── 创建输出目录 ────────────────────────────────────────────────
        task_out_dir = os.path.join(out_root, "predictions", task_id)
        os.makedirs(task_out_dir, exist_ok=True)

        # ── 构建 prompts ────────────────────────────────────────────────
        # TODO: 构建并保存 target system/user prompt
        # from skillopt.envs.edp.agent import _build_system_prompt, _build_user_prompt
        # target_system_prompt = _build_system_prompt(skill_content)
        # target_user_prompt = _build_user_prompt(item)
        # result["target_system_prompt"] = target_system_prompt
        # result["target_user_prompt"] = target_user_prompt
        # with open(os.path.join(task_out_dir, "target_system_prompt.txt"), "w") as f:
        #     f.write(target_system_prompt)
        # with open(os.path.join(task_out_dir, "target_user_prompt.txt"), "w") as f:
        #     f.write(target_user_prompt)

        # ── 运行 EDPAgent ──────────────────────────────────────────────
        result["phase"] = "agent"
        # TODO: 调用 agent
        # from skillopt.envs.edp.agent import run_agent
        # agent_result = run_agent(
        #     item=item,
        #     skill_content=skill_content,
        #     max_turns=max_turns,
        #     max_completion_tokens=max_completion_tokens,
        # )
        # result["n_turns"] = agent_result.get("n_turns", 0)

        # ── 保存 conversation.json ─────────────────────────────────────
        # with open(os.path.join(task_out_dir, "conversation.json"), "w") as f:
        #     json.dump(
        #         agent_result.get("conversation", []),
        #         f, ensure_ascii=False, indent=2,
        #     )

        # ── 评估 ────────────────────────────────────────────────────────
        result["phase"] = "eval"
        # TODO: 对 EDPAgent 输出进行评分
        # from skillopt.envs.edp.evaluator import evaluate
        # predicted = agent_result.get("predicted_answer", "")
        # ground_truth = item.get("answer", "")
        # eval_result = evaluate(predicted, ground_truth, item)
        # result["hard"] = 1 if eval_result["ok"] else 0
        # result["soft"] = 1.0 if eval_result["ok"] else 0.0
        # if not eval_result["ok"]:
        #     result["fail_reason"] = eval_result.get("reason", "eval-failed")

        result["ok"] = bool(result["hard"])
        if result["ok"]:
            result["fail_reason"] = ""
        return result

    except Exception as exc:
        result["fail_reason"] = f"unexpected: {type(exc).__name__}: {exc}"
        result["error"] = traceback.format_exc()
        return result


# ── 批量执行 ────────────────────────────────────────────────────────────────

def run_batch(
    items: list[dict],
    out_root: str,
    skill_content: str,
    max_turns: int = 10,
    max_completion_tokens: int = 16384,
    max_api_workers: int = 32,
    exec_timeout: int = 300,
    task_timeout: int = 600,
    **kwargs,
) -> list[dict]:
    """对一批 task items 运行 EDPAgent，支持并发 + 断点续跑。

    Parameters
    ----------
    items : list[dict]
        Task item 列表。
    out_root : str
        输出根目录。
    skill_content : str
        当前 skill prompt。
    max_turns : int
        每个任务的最大交互轮数。
    max_completion_tokens : int
        LLM 最大 completion token。
    max_api_workers : int
        并发数。
    exec_timeout : int
        单任务超时（秒）。
    task_timeout : int
        ThreadPool future 级别的硬超时（秒）。

    Returns
    -------
    list[dict]
        所有任务的执行结果。
    """
    os.makedirs(out_root, exist_ok=True)

    # ── Resume 支持 ──────────────────────────────────────────────────────
    results_path = os.path.join(out_root, "results.jsonl")
    done_ids: set[str] = set()
    existing: list[dict] = []
    if os.path.exists(results_path):
        with open(results_path) as f:
            for line in f:
                try:
                    r = json.loads(line)
                    done_ids.add(str(r["id"]))
                    existing.append(r)
                except Exception:
                    pass

    pending = [it for it in items if str(it["id"]) not in done_ids]
    print(
        f"  [edp rollout] total={len(items)} done={len(done_ids)} "
        f"pending={len(pending)} workers={max_api_workers}"
    )

    if not pending:
        return existing

    t0 = time.time()
    results = list(existing)
    started_at: dict[str, float] = {}

    def _run_one(it: dict) -> dict:
        started_at[str(it["id"])] = time.time()
        return process_one(
            it,
            out_root,
            skill_content,
            max_turns,
            max_completion_tokens,
            exec_timeout,
        )

    def _timeout_result(it: dict) -> dict:
        return {
            "id": str(it["id"]),
            "ok": False,
            "phase": "timeout",
            "fail_reason": f"task-timeout-{task_timeout}s",
            "hard": 0,
            "soft": 0.0,
            "n_turns": 0,
            "error": "timeout",
        }

    def _error_result(it: dict, exc: Exception) -> dict:
        return {
            "id": str(it["id"]),
            "ok": False,
            "phase": "error",
            "fail_reason": f"unexpected: {type(exc).__name__}: {exc}",
            "hard": 0,
            "soft": 0.0,
            "n_turns": 0,
            "error": str(exc),
        }

    ex = ThreadPoolExecutor(max_workers=max_api_workers)
    try:
        futs = {ex.submit(_run_one, it): it for it in pending}
        pending_futs = set(futs)
        finished = 0

        while pending_futs:
            done, _ = wait(pending_futs, timeout=5, return_when=FIRST_COMPLETED)
            now = time.time()

            # 处理超时的 future（在 ThreadPool 级别）
            timed_out = [
                fut for fut in pending_futs - done
                if str(futs[fut]["id"]) in started_at
                and now - started_at[str(futs[fut]["id"])] >= task_timeout
            ]

            for fut in done:
                pending_futs.remove(fut)
                item = futs[fut]
                try:
                    res = fut.result()
                except Exception as exc:
                    res = _error_result(item, exc)
                results.append(res)
                finished += 1
                status = "PASS" if res.get("hard") else "FAIL"
                dt = time.time() - t0
                print(
                    f"    {finished}/{len(pending)} id={res['id']:<10} {status}  "
                    f"turns={res.get('n_turns', 0):<3}  dt={dt:.0f}s"
                )

            for fut in timed_out:
                pending_futs.remove(fut)
                fut.cancel()
                res = _timeout_result(futs[fut])
                results.append(res)
                finished += 1
                print(
                    f"    {finished}/{len(pending)} id={res['id']:<10} TIMEOUT  dt={time.time()-t0:.0f}s"
                )

        # ── 写入 results.jsonl ────────────────────────────────────────────
        with open(results_path, "w") as f:
            for r in results:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

        return results

    finally:
        ex.shutdown(wait=False, cancel_futures=True)
