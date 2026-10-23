import random
from collections import deque
import numpy as np
import matplotlib.pyplot as plt
import nbtlib
from nbtlib import File, Compound, List, String, Int, Long, LongArray
import gzip
import datetime
import os
from math import ceil, log2
import argparse
import random


# 定义各状态标志位索引
WALL, PASSAGE, SOLUTION, START, END, MASK, LIGHT = range(7)
FLAG_NAMES = ['WALL', 'PASSAGE', 'SOLUTION', 'START', 'END', 'MASK', 'LIGHT']

MAX_LIGHT_LEVEL = 15
LIGHT_THRESHOLD = 5


def make_flag_array(height, width):
    return np.zeros((height, width, 7), dtype=bool)

def generate_maze_with_mask(width, height, mask, start, end):
    print(f"[✔] 生成迷宫: 高度 {height}, 宽度 {width}, 起点 {start}, 终点 {end}")
    maze = make_flag_array(height, width)
    maze[:, :, WALL] = True  # 初始化为全墙

    def legal(y, x):
        return 0 <= y < height and 0 <= x < width and not mask[y, x, MASK]

    def neighbors(y, x):
        dirs = [(-2, 0), (2, 0), (0, -2), (0, 2)]
        for dy, dx in dirs:
            ny, nx = y + dy, x + dx
            if legal(ny, nx) and maze[ny, nx, WALL]:
                yield ny, nx, dy // 2, dx // 2

    # 候选点（奇数格）
    candidates = [(y, x) for y in range(1, height, 2) for x in range(1, width, 2) if legal(y, x)]
    if not candidates:
        raise ValueError("无可用起点，mask区域覆盖了所有空间")

    # 起点终点设置
    if start is None:
        start_y, start_x = random.choice(candidates)
    else:
        start_y, start_x = start
        if not legal(start_y, start_x):
            raise ValueError("起点不合法或被mask覆盖")

    if end is None:
        end_y, end_x = random.choice(candidates)
    else:
        end_y, end_x = end
        if not legal(end_y, end_x):
            raise ValueError("终点不合法或被mask覆盖")

    # ---------- Growing Tree Algorithm ----------
    maze[start_y, start_x, WALL] = False
    maze[start_y, start_x, PASSAGE] = True
    frontier = [(start_y, start_x)]

    while frontier:
        idx = random.randint(0, len(frontier) - 1)  # idx = -1 for DFS-like
        y, x = frontier[idx]

        nbs = list(neighbors(y, x))
        if nbs:
            ny, nx, dy, dx = random.choice(nbs)
            my, mx = y + dy, x + dx
            maze[my, mx, WALL] = False
            maze[my, mx, PASSAGE] = True
            maze[ny, nx, WALL] = False
            maze[ny, nx, PASSAGE] = True
            frontier.append((ny, nx))
        else:
            frontier.pop(idx)

    # ---------- 求解路径 ----------
    prev = {}
    visited = np.zeros((height, width), dtype=bool)
    queue = deque([(start_y, start_x)])
    visited[start_y, start_x] = True
    found = False

    while queue:
        y, x = queue.popleft()
        if (y, x) == (end_y, end_x):
            found = True
            break
        for dy, dx in [(-2,0),(2,0),(0,-2),(0,2)]:
            ny, nx = y + dy, x + dx
            my, mx = y + dy // 2, x + dx // 2
            if legal(ny, nx) and maze[ny, nx, PASSAGE] and maze[my, mx, PASSAGE] and not visited[ny, nx]:
                visited[ny, nx] = True
                prev[(ny, nx)] = (y, x)
                queue.append((ny, nx))

    if not found:
        raise ValueError("起点与终点不可达，可能被mask包围")

    # ---------- 标记路径 ----------
    path = []
    cur = (end_y, end_x)
    while cur != (start_y, start_x):
        path.append(cur)
        cur = prev[cur]
    path.append((start_y, start_x))
    path.reverse()

    for i in range(len(path) - 1):
        y1, x1 = path[i]
        y2, x2 = path[i + 1]
        my, mx = (y1 + y2) // 2, (x1 + x2) // 2
        for yx in [(y1, x1), (y2, x2), (my, mx)]:
            y, x = yx
            maze[y, x, WALL] = False
            maze[y, x, PASSAGE] = True
            maze[y, x, SOLUTION] = True
    maze[end_y, end_x, SOLUTION] = True

    # ---------- 设置起点终点 ----------
    maze[start_y, start_x, START] = True
    maze[end_y, end_x, END] = True

    # ---------- 应用mask ----------
    maze[mask[:, :, MASK]] = False
    maze[:, :, MASK] = mask[:, :, MASK]

    # 设置mask区域的墙壁 (如果mask与周围有非mask区域相邻或者是边界)
    for y in range(height):
        for x in range(width):
            if mask[y, x, MASK]:
                # 检查四周是否有非mask区域
                for dy, dx in [(-1,0),(1,0),(0,-1),(0,1), (-1,-1), (-1,1), (1,-1), (1,1)]:
                # for dy, dx in [(-1,0),(1,0),(0,-1),(0,1)]:
                    ny, nx = y + dy, x + dx
                    if ny < 0 or ny >= height or nx < 0 or nx >= width or not mask[ny, nx, MASK]:
                        maze[y, x, WALL] = True
                        break

    return maze, (start_y, start_x), (end_y, end_x)

def generate_perfect_maze_with_mask(width, height, mask):
    print(f"[✔] 生成 perfect 迷宫: 高度 {height}, 宽度 {width}")
    maze = make_flag_array(height, width)
    maze[:, :, WALL] = True  # 初始化为全墙

    visited = np.zeros((height, width), dtype=bool)
    frontier = []

    def in_bounds(y, x):
        return 0 <= y < height and 0 <= x < width

    def legal(y, x):
        return in_bounds(y, x) and not mask[y, x, MASK]

    def is_passable(y, x):
        return legal(y, x) and not visited[y, x]

    def neighbors(y, x):
        for dy, dx in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
            ny, nx = y + dy, x + dx
            if is_passable(ny, nx):
                yield (ny, nx, y + dy // 2, x + dx // 2)

    # 从所有合法奇数点中随机选择起点
    candidates = [(y, x) for y in range(1, height, 2) for x in range(1, width, 2) if legal(y, x)]
    if not candidates:
        raise ValueError("无可用起点，mask区域覆盖了所有空间")
    sy, sx = random.choice(candidates)

    visited[sy, sx] = True
    maze[sy, sx, WALL] = False
    maze[sy, sx, PASSAGE] = True
    for ny, nx, wy, wx in neighbors(sy, sx):
        frontier.append((ny, nx, wy, wx))

    random.shuffle(frontier)

    while frontier:
        idx = random.randint(0, len(frontier) - 1)
        y, x, wy, wx = frontier.pop(idx)
        if visited[y, x]:
            continue
        visited[y, x] = True
        maze[y, x, WALL] = False
        maze[y, x, PASSAGE] = True
        maze[wy, wx, WALL] = False
        maze[wy, wx, PASSAGE] = True
        for ny, nx, wny, wnx in neighbors(y, x):
            if not visited[ny, nx]:
                frontier.append((ny, nx, wny, wnx))

    # 应用 mask 区域（将所有 MASK 区域设为墙）
    maze[mask[:, :, MASK]] = False
    maze[:, :, MASK] = mask[:, :, MASK]

    for y in range(height):
        for x in range(width):
            if mask[y, x, MASK]:
                for dy, dx in [(-1,0),(1,0),(0,-1),(0,1), (-1,-1), (-1,1), (1,-1), (1,1)]:
                    ny, nx = y + dy, x + dx
                    if ny < 0 or ny >= height or nx < 0 or nx >= width or not mask[ny, nx, MASK]:
                        maze[y, x, WALL] = True
                        break

    return maze


def solve_maze(maze, start, end):
    print(f"[✔] 开始寻路: 起点 {start}, 终点 {end}")
    h, w = maze.shape[:2]
    visited = np.full((h, w), False)
    prev = dict()

    queue = deque([start])
    visited[start] = True

    while queue:
        y, x = queue.popleft()
        if (y, x) == end:
            break
        for dy, dx in [(-1,0),(1,0),(0,-1),(0,1)]:
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx] and maze[ny, nx, PASSAGE]:
                visited[ny, nx] = True
                prev[(ny, nx)] = (y, x)
                queue.append((ny, nx))

    path = []
    cur = end
    while cur in prev:
        path.append(cur)
        cur = prev[cur]
    path.append(start)
    path.reverse()

    for y, x in path:
        maze[y, x, SOLUTION] = True

    maze[start[0], start[1], START] = True
    maze[end[0], end[1], END] = True
    return maze, path

def circular_mask(height, width, ratio=0.9):
    center_y, center_x = height // 2, width // 2
    max_r = min(center_y, center_x) * ratio
    y, x = np.ogrid[:height, :width]
    dist = np.sqrt((y - center_y)**2 + (x - center_x)**2)
    mask = make_flag_array(height, width)
    mask[dist > max_r, MASK] = True
    return mask

def ring_mask(height, width, inner_ratio=0.4, outer_ratio=0.9):
    center_y, center_x = height // 2, width // 2
    y, x = np.ogrid[:height, :width]
    dist = np.sqrt((y - center_y)**2 + (x - center_x)**2)
    inner = min(center_y, center_x) * inner_ratio
    outer = min(center_y, center_x) * outer_ratio
    mask = make_flag_array(height, width)
    mask[(dist < inner) | (dist > outer), MASK] = True
    return mask

# 掏空一个圆的mask
def hollow_circular_mask(height, width, ratio=0.9):
    center_y, center_x = height // 2, width // 2
    hollow_r = min(center_y, center_x) * ratio
    y, x = np.ogrid[:height, :width]
    dist = np.sqrt((y - center_y)**2 + (x - center_x)**2)
    mask = make_flag_array(height, width)
    mask[(dist < hollow_r), MASK] = True  # 掏空内圈
    return mask


def compute_light_map(maze, light_positions, max_light=MAX_LIGHT_LEVEL):
    h, w = maze.shape[:2]
    light_map = np.zeros((h, w), dtype=int)
    queue = deque()

    # 初始化所有光源
    for y, x in light_positions:
        light_map[y, x] = max_light
        queue.append((y, x, max_light))

    # BFS传播
    while queue:
        y, x, light = queue.popleft()
        if light <= 1:
            continue
        for dy, dx in [(-1,0),(1,0),(0,-1),(0,1)]:
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w:
                if maze[ny, nx, WALL] or maze[ny, nx, MASK]:
                    continue
                # 只有当新光强比已有光强强时才更新
                if light_map[ny, nx] < light - 1:
                    light_map[ny, nx] = light - 1
                    queue.append((ny, nx, light - 1))
    return light_map


def place_lights(maze, threshold=LIGHT_THRESHOLD):
    """
    按照网格间距放置灯光，允许放在墙上，分布整齐。
    """
    h, w = maze.shape[:2]
    light_positions = []
    for y in range(0, h, threshold):
        for x in range(0, w, threshold):
            if not maze[y, x, LIGHT] and not maze[y, x, MASK]:
                maze[y, x, LIGHT] = True
                light_positions.append((y, x))
    return maze, light_positions

# def place_lights(maze, threshold=LIGHT_THRESHOLD):
#     light_positions = []
#     for _ in range(1000):
#         light_map = compute_light_map(maze, light_positions)
#         dark = [(y, x) for y in range(maze.shape[0]) for x in range(maze.shape[1])
#                 if (maze[y, x, PASSAGE]) and light_map[y, x] < threshold]
#         if not dark:
#             break
#         y, x = min(dark, key=lambda pos: light_map[pos])
#         maze[y, x, LIGHT] = True
#         light_positions.append((y, x))
#     return maze, light_positions

def place_lights_optimized(maze, threshold=LIGHT_THRESHOLD, max_lights=1000):
    h, w = maze.shape[:2]
    light_positions = []

    # 预计算所有可能放灯的候选点：所有PASSAGE和SOLUTION点
    candidates = [(y, x) for y in range(h) for x in range(w) if maze[y, x, PASSAGE] or maze[y, x, SOLUTION]]

    light_map = np.zeros((h, w), dtype=int)

    for _ in range(max_lights):
        # 计算当前光照覆盖
        light_map = compute_light_map(maze, light_positions)

        # 找暗区格子
        dark_points = [(y, x) for y, x in candidates if light_map[y, x] < threshold]

        if not dark_points:
            break  # 已全部覆盖

        best_pos = None
        best_coverage = -1

        # 对每个候选点，估计放灯后新增覆盖的暗点数量
        for y, x in candidates:
            if (y, x) in light_positions:
                continue  # 已放灯

            # 计算此灯光覆盖范围
            coverage = 0
            # BFS光照传播的简单模拟（半径max_light）
            queue = deque()
            visited = set()
            queue.append((y, x, MAX_LIGHT_LEVEL))
            while queue:
                cy, cx, light = queue.popleft()
                if light < threshold:
                    continue
                if (cy, cx) in visited:
                    continue
                visited.add((cy, cx))
                if (cy, cx) in dark_points:
                    coverage +=1
                if light > 1:
                    for dy, dx in [(-1,0),(1,0),(0,-1),(0,1)]:
                        ny, nx = cy + dy, cx + dx
                        if 0 <= ny < h and 0 <= nx < w:
                            if maze[ny, nx, WALL] or maze[ny, nx, MASK]:
                                continue
                            queue.append((ny, nx, light -1))

            if coverage > best_coverage:
                best_coverage = coverage
                best_pos = (y, x)

        if best_pos is None or best_coverage == 0:
            # 没有找到能提升覆盖的点，提前结束
            break

        y, x = best_pos
        maze[y, x, LIGHT] = True
        light_positions.append((y, x))

    return maze, light_positions


def check_light_coverage(maze, light_map, threshold=LIGHT_THRESHOLD):
    h, w = maze.shape[:2]
    uncovered = []
    for y in range(h):
        for x in range(w):
            if maze[y, x, PASSAGE]:
                if light_map[y, x] < threshold:
                    uncovered.append((y, x, light_map[y, x]))
    if uncovered:
        print(f"未达到阈值({threshold})的PASSAGE格子共{len(uncovered)}个，部分示例：")
        for i, (y, x, val) in enumerate(uncovered[:10]):
            print(f"  坐标 ({y}, {x}), 光强: {val}")
        return False
    else:
        print("所有PASSAGE格子光强均满足阈值要求。")
        return True


def render_maze(maze, return_img=False):
    h, w = maze.shape[:2]
    img = np.ones((h, w, 3))  # 背景为白色

    # 定义每个标记的颜色（RGB），以及叠加的优先级或权重
    colors = {
        WALL: (0, 0, 0),
        MASK: (0.9, 0.1, 0.1),
        PASSAGE: (1, 1, 1),
        SOLUTION: (0, 1, 0),
        LIGHT: (1, 1, 0),
        START: (0, 1, 1),
        END: (0, 0, 1),
    }

    for y in range(h):
        for x in range(w):
            color_sum = np.zeros(3)
            count = 0

            for flag, color in colors.items():
                if maze[y, x, flag]:
                    color_sum += np.array(color)
                    count += 1

            if count > 0:
                img[y, x] = np.clip(color_sum / count, 0, 1)  # 平均颜色叠加
            else:
                img[y, x] = (1, 1, 1)  # 默认为白色

    plt.figure(figsize=(8, 8))
    plt.imshow(img)
    plt.axis('off')
    if return_img:
        return img
    else:
        plt.show()


def render_light_map(light_map):
    plt.figure(figsize=(8, 8))
    plt.imshow(light_map, cmap='plasma', vmin=0, vmax=MAX_LIGHT_LEVEL)
    plt.colorbar(label='Light Level')
    plt.title('Light Level Map')
    plt.axis('off')
    plt.show()

def save_maze(maze, filename):
    np.savez(filename, maze=maze)

def load_maze(filename):
    data = np.load(filename)
    return data['maze']

def get_light_positions(maze):
    return [(y, x) for y in range(maze.shape[0]) for x in range(maze.shape[1]) if maze[y, x, LIGHT]]

def save_maze_image(maze, filename="maze.png"):
    plt.imsave(filename, render_maze(maze, return_img=True))

def save_light_map_image(light_map, filename="light_map.png"):
    plt.imsave(filename, light_map, cmap='plasma', vmin=0, vmax=MAX_LIGHT_LEVEL)



def encode_blockstates(block_ids, bits_per_block):
    longs = []
    value = 0
    bits_filled = 0
    # 打印前三块的id以便角度长度
    print(f"[✔] 编码开始: 每个块 {bits_per_block} 位")
    print(f"[✔] 前3个块ID: {block_ids[:3]}")

    for state in block_ids:
        value |= (state & ((1 << bits_per_block) - 1)) << bits_filled
        bits_filled += bits_per_block

        while bits_filled >= 64:
            part = value & 0xFFFFFFFFFFFFFFFF
            # 如果大于最大有符号64位，转成负数
            if part >= 0x8000000000000000:
                part -= 0x10000000000000000
            longs.append(part)
            value >>= 64
            bits_filled -= 64

    if bits_filled > 0:
        # 最后剩余部分也处理为有符号64位
        if value >= 0x8000000000000000:
            value -= 0x10000000000000000
        longs.append(value)

    print(f"[✔] 编码完成: {len(longs)} longs, 每个块 {bits_per_block} 位")
    print(f"[✔] 总块数: {len(block_ids)}")

    return longs


def export_litematic_from_numpy_maze(maze, output_file="maze.litematic"):
    from math import ceil, log2
    import datetime
    import nbtlib
    from nbtlib import File, Compound, List, String, Int, Long, LongArray

    BLOCK_AIR, BLOCK_WALL, BLOCK_SOLUTION, BLOCK_START, BLOCK_END, BLOCK_MASK, BLOCK_LIGHT, BLOCK_CARPET, BLOCK_CEIL = range(9)
    BlockMap = {
        BLOCK_AIR: ("minecraft:air", {}),
        BLOCK_WALL: ("minecraft:stone_bricks", {}),
        BLOCK_SOLUTION: ("minecraft:black_wool", {}),
        BLOCK_START: ("minecraft:gold_block", {}),
        BLOCK_END: ("minecraft:diamond_block", {}),
        BLOCK_MASK: ("minecraft:air", {}),  # MASK
        BLOCK_LIGHT: ("minecraft:sea_lantern", {}),  # LIGHT
        BLOCK_CARPET: ("minecraft:black_wool", {}),  # 解决方案路径用绿色地毯
        BLOCK_CEIL: ("minecraft:white_stained_glass", {}),  # 顶部用白色玻璃
    }
    HEIGHT = 5  # 默认高度层

    def maze_state_to_block_index(maze, x, y, z):
        # 0层数 优先放置light和solution， 其他层优先mask和wall
        if y == HEIGHT - 1:
            if maze[z, x, LIGHT]:
                return BLOCK_LIGHT
            elif maze[z, x, MASK]:
                pass
            else:
                return BLOCK_CEIL
        if y == 0:
            if maze[z, x, START]:
                return BLOCK_START
            elif maze[z, x, END]:
                return BLOCK_END
            elif maze[z, x, SOLUTION]:
                return BLOCK_SOLUTION
            elif maze[z, x, PASSAGE]:
                return BLOCK_CARPET
        if maze[z, x, WALL]:
            return BLOCK_WALL
        elif maze[z, x, MASK]:
            return BLOCK_MASK
        # elif maze[z, x, START]:
        #     return BLOCK_START
        # elif maze[z, x, END]:
        #     return BLOCK_END
        # solution 只在0层放置
        # elif maze[z, x, SOLUTION]:
        #     return BLOCK_SOLUTION
        elif maze[z, x, PASSAGE]:
            return BLOCK_AIR
        return BLOCK_AIR

    h, w = maze.shape[:2]

    # 生成 block palette
    palette = []
    for block_name, props in BlockMap.values():
        palette.append(Compound({"Name": String(block_name)}))

    # 展平 block ids（y轴遍历 0~3，每个平面 z->x）
    block_ids = []
    for y in range(HEIGHT):
        for x in range(w):
            for z in reversed(range(h)):
                cell = maze_state_to_block_index(maze, x, y, z)
                block_ids.append(cell)

    # 编码 blockstates
    bits_per_block = max(2, ceil(log2(len(palette))))
    longs = encode_blockstates(block_ids, bits_per_block)

    sizeEnclosing = Compound({
        "x": Int(w),
        "y": Int(HEIGHT),
        "z": Int(h)
    })

    region = Compound({
        "Position": Compound({
            "x": Int(0),
            "y": Int(0),
            "z": Int(0)
        }),
        "Size": sizeEnclosing,
        "BlockStates": LongArray(longs),
        "BlockStatePalette": List(palette),
        "Entities": List([]),
        "PendingBlockTicks": List([]),
        "PendingFluidTicks": List([]),
        "TileEntities": List([]),
    })

    timeCreated = Long(int(datetime.datetime.now().timestamp() * 1000))

    schematic = File({
        "Version": Int(6),
        "SubVersion": Int(1),
        "MinecraftDataVersion": Int(3218),
        "Metadata": Compound({
            "Name": String("Maze"),
            "Author": String("ohtoai002"),
            "Description": String("Generated by ChatGPT-ohtoai002"),
            "EnclosingSize": sizeEnclosing,
            "RegionCount": Int(1),
            "TimeCreated": timeCreated,
            "TimeModified": timeCreated,
            "TotalBlocks": Int(len(block_ids)),
            "TotalVolume": Int(w * HEIGHT * h),
        }),
        "Regions": Compound({String("Maze"): region})
    })

    schematic.save(output_file, gzipped=True)
    print(f"[✔] Litematic 导出完成: {output_file}")

def load_mask_from_litematic(filename):
    """
    从litematic文件读取单层投影，生成mask数组。
    规则：空气为0，结构为1，其它为mask。
    返回: height, width, mask
    """
    import nbtlib

    litematic = nbtlib.load(filename)
    region = list(litematic['Regions'].values())[0]
    size = region['Size']
    w, h = size['x'], size['z']  # 注意litematic的x为宽，z为高
    palette = [p['Name'] for p in region['BlockStatePalette']]
    blockstates = region['BlockStates']

    # 解码blockstates
    bits_per_block = max(2, int(np.ceil(np.log2(len(palette)))))
    total_blocks = w * h
    block_ids = []
    value = 0
    bits_read = 0
    long_idx = 0

    for i in range(total_blocks):
        if bits_read < bits_per_block:
            value |= (blockstates[long_idx] & 0xFFFFFFFFFFFFFFFF) << bits_read
            bits_read += 64
            long_idx += 1
        block_id = value & ((1 << bits_per_block) - 1)
        block_ids.append(block_id)
        value >>= bits_per_block
        bits_read -= bits_per_block

    arr = np.array([palette[i] for i in block_ids]).reshape((h, w))

    mask = make_flag_array(h, w)
    # 你可以根据实际palette内容调整结构方块的判断
    for y in range(h):
        for x in range(w):
            if arr[y, x] == "minecraft:air":
                continue  # 空气
            elif arr[y, x] == "minecraft:stone_bricks":
                continue  # 结构
            else:
                mask[y, x, MASK] = True  # 其它都设为mask
                # 外圈3x3也设置
                for dy in range(-1, 2):
                    for dx in range(-1, 2):
                        if 0 <= y + dy < h and 0 <= x + dx < w:
                            if not mask[y + dy, x + dx, MASK]:
                                mask[y + dy, x + dx, MASK] = True
    # 中心绘制一个圆圈也作为mask
    center_y, center_x = h // 2, w // 2
    max_r = min(center_y, center_x) * 0.5
    y, x = np.ogrid[:h, :w]
    dist = np.sqrt((y - center_y)**2 + (x - center_x)**2)
    mask[dist < max_r, MASK] = True  # 掏空内圈

    return h, w, mask

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="迷宫生成与导出工具")
    parser.add_argument('--preview-light', '-l', action='store_true', help='预览亮度图')
    parser.add_argument('--preview-map', '-m', action='store_true', help='预览地图')
    parser.add_argument('--generate-map', '-g', action='store_true', help='生成新地图')
    parser.add_argument('--width', '-W', type=int, default=21, help='生成迷宫宽度')
    parser.add_argument('--height', '-H', type=int, help='生成迷宫高度，默认为宽度')
    parser.add_argument('--output', '-o', type=str, help='指定输出文件名（如maze.npz）')
    parser.add_argument('--input', '-i', type=str, default='maze.npz', help='指定输入文件名')
    parser.add_argument('--litematic', '-L', type=str, help='导出litematic文件名')
    parser.add_argument('--light-level', type=int, default=0, help='指定照明最低层级，0为不生成灯光')
    parser.add_argument('--start', '-s', type=str, default=None, help='入口坐标')
    parser.add_argument('--end', '-e', type=str, default=None, help='出口坐标')
    # 设置mask类型
    parser.add_argument('--mask-type', choices=['circular', 'ring', 'hollow', 'none'], default='none', help='选择生成的mask类型')
    parser.add_argument('--load-mask', type=str, help='从litematic文件加载mask')

    args = parser.parse_args()

    if args.start:
        start = tuple(map(int, args.start.split(',')))
    else:
        start = None

    if args.end:
        end = tuple(map(int, args.end.split(',')))
    else:
        end = None

    if args.generate_map:
        if args.load_mask:
            height, width, mask = load_mask_from_litematic(args.load_mask)
            print(f"[✔] 从litematic加载mask: {args.load_mask}, 高度: {height}, 宽度: {width}")
        else:
            width = args.width
            height = args.height if args.height else width
            if args.mask_type == 'circular':
                mask = circular_mask(height, width)
            elif args.mask_type == 'ring':
                mask = ring_mask(height, width)
            elif args.mask_type == 'hollow':
                mask = hollow_circular_mask(height, width)
            else:
                mask = make_flag_array(height, width)
        # maze, start, end = generate_maze_with_mask(width, height, mask, start, end)
        maze = generate_perfect_maze_with_mask(width, height, mask)
        maze, path = solve_maze(maze, start, end)
        if args.light_level > 0:
            if not check_light_coverage(maze, compute_light_map(maze, get_light_positions(maze))):
                maze, light_positions = place_lights(maze, threshold=args.light_level)
        if args.output:
            save_maze(maze, args.output)
    else:
        maze = load_maze(args.input)
        # 如果指定了入口和出口，重新设置寻路
        if start is not None or end is not None:
            # 清除现有的入口和出口标记
            if start is not None:
                maze[start[0], start[1], START] = True
            else:
                if np.any(maze[:, :, START]):
                    start = np.argwhere(maze[:, :, START])[0]  # 默认取第一个入口作为起点
                else:
                    start = np.argwhere(maze[:, :, PASSAGE])[0]  # 默认取第一个通路作为起点
            start = tuple(start)
            if end is not None:
                maze[end[0], end[1], END] = True
            else:
                if np.any(maze[:, :, END]):
                    end = np.argwhere(maze[:, :, END])[0]
                else:
                    end = np.argwhere(maze[:, :, PASSAGE])[-1]  # 默认取最后一个通路作为终点
            end = tuple(end)
            print(f"[✔] 入口: {start}, 出口: {end}")

            # 重新寻路
            maze, path = solve_maze(maze, start, end)

        if args.light_level > 0:
            if not check_light_coverage(maze, compute_light_map(maze, get_light_positions(maze))):
                maze, light_positions = place_lights(maze, threshold=args.light_level)
        else:
            light_positions = get_light_positions(maze)

    if args.preview_map:
        render_maze(maze)
    if args.preview_light:
        light_map = compute_light_map(maze, get_light_positions(maze))
        render_light_map(light_map)
    if args.litematic:
        export_litematic_from_numpy_maze(maze, args.litematic)
