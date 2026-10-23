# maze_to_litematic_nbtlib.py
import nbtlib
from nbtlib import File, Compound, List, String, Int, Long, LongArray
import gzip
import datetime
import os

PATH = 0
WALL = 1
SOLUTION = 2
START = 3
END = 4

from math import ceil, log2

def read_maze_file(filename):
    with open(filename, 'r') as f:
        return [[int(c) for c in line.strip()] for line in f if line.strip()]

def encode_blockstates(block_ids, bits_per_block):
    longs = []
    value = 0
    bits_filled = 0

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


def print_maze(maze: List[List[int]]):
    for row in maze:
        print("".join({WALL: "██", PATH: "  ", SOLUTION: "..", START: "##", END: "**"}[cell] for cell in row))

def export_litematic_from_maze(maze_txt_path, output_file="maze.litematic", block_map=None):
    maze = read_maze_file(maze_txt_path)
    height = 4
    size_z = len(maze)
    size_x = len(maze[0])
    FLOOR_BLOCKS = {SOLUTION}

    print_maze(maze)

    if block_map is None:
        block_map = {
            PATH: ("minecraft:air", {}),
            WALL: ("minecraft:stone_bricks", {}),
            SOLUTION: ("minecraft:green_carpet", {}),
            START: ("minecraft:gold_block", {}),
            END: ("minecraft:diamond_block", {}),
        }

    palette = []
    palette_map = {}
    
    for block_name, props in block_map.values():
        key = (block_name, frozenset(props.items()))
        if key not in palette_map:
            palette_map[key] = len(palette)
            palette.append(Compound({"Name": String(block_name)}))

    block_ids = []
    for y in range(height):  # height=1，但保留结构
        for x in (range(size_x)):  # Minecraft 中 z 和 x 顺序相反
            for z in reversed(range(size_z)):
                cell = maze[z][x]  # 注意 z 和 x 顺序
                if y != 0 and cell in FLOOR_BLOCKS:
                    cell = PATH
                block_ids.append(cell)
    bits_per_block = max(2, ceil(log2(len(palette))))
    longs = encode_blockstates(block_ids, bits_per_block)

    sizeEnclosing = Compound({
        "x": Int(size_x),
        "y": Int(height),
        "z": Int(size_z)
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

    timeCreated = Long(datetime.datetime.now().timestamp() * 1000)

    schematic = File({
        "Version": Int(6),
        "SubVersion": Int(1),
        "MinecraftDataVersion": Int(3218),
        "Metadata": Compound({
            "Name": String("Maze"),
            "Author": String("ohtoai002"),
            "Description": String("Maze supported by ohtoai002"),
            "EnclosingSize": sizeEnclosing,
            "RegionCount": Int(1),
            "TimeCreated": timeCreated,
            "TimeModified": timeCreated,
            "TotalBlocks": Int(len(block_ids)),
            "TotalVolume": Int(size_x * height * size_z),
        }),
        "Regions": Compound({String("Maze"): region})
    })

    schematic.save(output_file, gzipped=True)

    print(f"[✔] 导出完成: {output_file}")

if __name__ == "__main__":
    export_litematic_from_maze("maze_21x21.txt", "maze_21x21.litematic")
