# mc_maze

Minecraft 迷宫生成器：生成带遮罩、带照明规划的迷宫，并导出为 Litematica 投影（`.litematic`）、文本网格和光照预览图。

## 功能

- **迷宫生成**：随机完美迷宫（任意两点间唯一路径），支持指定入口/出口并求解路径
- **遮罩（Mask）**：限制迷宫生成的区域形状——内置圆形 / 圆环 / 空心等类型，也可从现有 `.litematic` 投影加载遮罩（按投影占格生成迷宫）
- **照明规划**：按最低亮度层级自动在迷宫内布光（防止刷怪），可预览亮度图（`--preview-light`）
- **多格式导出**：
  - `.litematic` —— Litematica 投影，直接投影到世界里摆放（含墙、路面、光照方块）
  - `.txt` —— 0/1 文本网格
  - `.npz` —— 完整状态数组（墙/通路/解/起终点/遮罩/亮度 7 层），供二次处理
  - `.png` —— 地图与亮度预览

## 使用

```bash
# 生成 21×21 迷宫并导出 litematic，光照最低 7 级
python maze_generator.py -g -W 21 --light-level 7 -L maze_21x21.litematic

# 预览地图与亮度图
python maze_generator.py -m -l

# 从现有投影加载遮罩（按投影形状生成迷宫）
python maze_generator.py -g --load-mask MASK.litematic -W 129 -H 129

# 圆形遮罩 + 指定起终点
python maze_generator.py -g --mask-type circular -s 2,2 -e 127,127
```

也可以用 `maze_to_litematic.py` 把已有的文本网格（首行为 `宽 高` 的 0/1 矩阵）转换为 `.litematic`。

## 依赖

```bash
pip install numpy matplotlib nbtlib
```

## 文件说明

| 文件 | 说明 |
|---|---|
| `maze_generator.py` | 主程序：生成 / 预览 / 导出 |
| `maze_to_litematic.py` | 文本网格 → litematic 转换器 |
| `MASK.litematic` | 遮罩加载示例投影 |
| `maze_21x21.txt` / `.litematic` | 21×21 迷宫导出示例 |
| `light_map1.png` / `light_map2.png` | 亮度预览示例 |

## License

MIT
