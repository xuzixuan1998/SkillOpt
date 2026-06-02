"""EDPAgent 的 DataLoader。

继承 ``SplitDataLoader`` 提供了开箱即用的 train/val/test 分片加载。
基类的 ``_load_json_or_jsonl()`` 已支持 JSON array / JSONL / 嵌套 dict 三种格式。
"""

from __future__ import annotations

from skillopt.datasets.base import SplitDataLoader


class EDPDataLoader(SplitDataLoader):
    """EDPAgent 数据加载器。

    默认行为：
    - ``split_mode="ratio"``: 从 ``data_path`` 加载原始数据，按比例切分
    - ``split_mode="split_dir"``: 直接从 ``split_dir/train|val|test/items.json`` 加载

    如果有特殊格式需要覆写的方法：

    1. 数据在 JSON 中嵌套了 → 覆写 ``load_raw_items()``
    2. 数据是多文件目录结构 → 覆写 ``load_split_items()``
    3. 需要动态过滤/采样 → 覆写 ``build_train_batch()`` / ``build_eval_batch()``
    """
