"""EDPAgent 的 DataLoader。

继承 ``SplitDataLoader`` 提供了开箱即用的 train/val/test 分片加载。
如果数据就是标准 JSON/JSONL 格式，不需要额外代码。
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

    示例：覆写 load_raw_items 处理自定义格式
    --------------------------------------------
    .. code-block:: python

        def load_raw_items(self, data_path: str) -> list[dict]:
            # 如果是自定义文件格式
            items = []
            with open(data_path) as f:
                for line in f:
                    item = parse_my_format(line)
                    items.append({"id": item["uid"], **item})
            return items
    """

    # TODO: 如果数据集是标准 JSON/JSONL，此文件不需要任何修改。
    # TODO: 如果有自定义加载逻辑，覆写 load_raw_items() 或 load_split_items()。
    pass
