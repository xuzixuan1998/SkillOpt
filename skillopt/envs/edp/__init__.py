"""EDPAgent environment adapter for ReflACT.

将 SkillOpt 接入 EDPAgent，实现 skill prompt 自动优化。
"""

from skillopt.envs.edp.adapter import EDPAdapter

__all__ = ["EDPAdapter"]
