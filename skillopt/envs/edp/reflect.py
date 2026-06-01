"""Reflect 阶段的 prompt 配置（可选）。

大多数情况下此文件不需要修改。
框架会自动从 ``prompts/`` 目录加载 prompt 模板：

1. 优先加载 ``skillopt/envs/edp/prompts/<name>.md``（env-specific）
2. 回退到 ``skillopt/prompts/<name>.md``（通用默认）

如果需要做额外处理（如动态注入上下文），覆写
``EDPAdapter.get_error_minibatch_prompt()`` 和
``EDPAdapter.get_success_minibatch_prompt()``。
"""
