#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""自行车齿比计算器。

齿比 = 牙盘齿数 ÷ 飞轮齿数，含义是"牙盘转一圈，后轮转几圈"。
同一个齿比在爬坡和冲刺时的意义完全不同，所以这里既算数值，也给出档位判定。

用法：
    python gear_ratio.py                          # 用默认的 53-39 牙盘 + 8 速飞轮
    python gear_ratio.py -c 50-34 -r 11-32        # 自定义
    python gear_ratio.py -c 53 -r 11-13-15 --csv  # 只看单盘，结果输出成 CSV

依赖：仅标准库，Python 3.9+。
"""

from __future__ import annotations

import argparse
import csv
import sys
import unicodedata
from typing import Iterable, Sequence

# (齿比上限, 档位名, 适用场景)。判定规则为 ratio < 上限，取第一个满足的区间。
GEAR_BANDS: tuple[tuple[float, str, str], ...] = (
    (1.0, "超轻档", "极省力、踏频高、速度慢，陡坡 / 重载 / 起步"),
    (1.5, "轻档", "省力、高踏频、慢速，缓坡 / 逆风 / 休闲骑"),
    (2.5, "中档", "均衡、巡航踏频，平路日常 / 团骑"),
    (3.5, "重档", "费力、低踏频、速度快，提速 / 顺风 / 下坡"),
    (float("inf"), "超重档", "很费力、需摇车、速度极快，冲刺 / 极速下坡"),
)

# 表格列宽与对齐方式，按"显示宽度"计算，保证中文和数字能对齐。
COLUMNS = ((4, ">"), (4, ">"), (6, ">"), (6, "<"))


def classify(ratio: float) -> tuple[str, str]:
    """把齿比映射成 (档位名, 适用场景)。"""
    if ratio <= 0:
        raise ValueError(f"齿比必须为正数，收到 {ratio}")
    for upper, name, hint in GEAR_BANDS:
        if ratio < upper:
            return name, hint
    raise AssertionError("GEAR_BANDS 未覆盖该齿比")  # 理论上到不了这里


def parse_teeth(text: str) -> list[int]:
    """把 '53-39'、'11,13,15' 或 '11 13 15' 解析成齿数列表。"""
    cleaned = text.replace("，", ",").replace("、", ",")
    for sep in ("-", "/", "|", " ", "\t"):
        cleaned = cleaned.replace(sep, ",")
    parts = cleaned.split(",")
    if not parts or any(p == "" for p in parts):
        raise ValueError(f"分隔符位置不对，检查是否有连续或多余的符号：{text!r}")
    try:
        teeth = [int(p) for p in parts]
    except ValueError:
        raise ValueError(f"只能填数字，收到：{text!r}") from None
    if any(t <= 0 for t in teeth):
        raise ValueError(f"齿数必须是正整数：{text!r}")
    return teeth


def ratios(chainrings: Sequence[int], cogs: Sequence[int]) -> list[tuple[int, int, float]]:
    """牙盘 × 飞轮 的所有组合，返回 [(牙盘齿数, 飞轮齿数, 齿比)]。"""
    return [(c, f, c / f) for c in chainrings for f in cogs]


def summarize(rows: Iterable[tuple[int, int, float]]) -> dict[str, object]:
    """统计组合数、最轻 / 最重齿比和跨度。"""
    data = list(rows)
    if not data:
        raise ValueError("没有可统计的齿比")
    low = min(data, key=lambda r: r[2])
    high = max(data, key=lambda r: r[2])
    return {"min": low, "max": high, "span": high[2] / low[2], "count": len(data)}


def _width(text: str) -> int:
    """按终端显示宽度算长度：全角字符占 2 列。"""
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in text)


def _pad(text: str, width: int, align: str = ">") -> str:
    gap = width - _width(text)
    if gap <= 0:
        return text
    return " " * gap + text if align == ">" else text + " " * gap


def _row(cells: Sequence[str]) -> str:
    return "  ".join(_pad(c, w, a) for c, (w, a) in zip(cells, COLUMNS))


def format_table(rows: Sequence[tuple[int, int, float]]) -> str:
    """输出对齐的文本表格。"""
    lines = [_row(("牙盘", "飞轮", "齿比", "档位")), "-" * 26]
    for chainring, cog, ratio in rows:
        name, _ = classify(ratio)
        lines.append(_row((str(chainring), str(cog), f"{ratio:.2f}", name)))
    return "\n".join(lines)


def format_legend() -> str:
    """档位说明，附在表格后面。"""
    lines = ["档位说明："]
    lower = 0.0
    for upper, name, hint in GEAR_BANDS:
        top = "∞" if upper == float("inf") else f"{upper:.2f}"
        lines.append(f"  {_pad(name, 6, '<')} {lower:>5.2f} ~ {_pad(top, 5, '<')} {hint}")
        lower = upper
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="计算自行车齿比并判断档位",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例：python gear_ratio.py -c 53-39 -r 11-13-15-18-21-24-28-32",
    )
    parser.add_argument(
        "-c", "--chainring", default="53-39",
        help="牙盘齿数，用 - 或 , 分隔（默认 53-39）",
    )
    parser.add_argument(
        "-r", "--cassette", default="11-13-15-18-21-24-28-32",
        help="飞轮齿数，用 - 或 , 分隔（默认 8 速 11-32）",
    )
    parser.add_argument("--csv", action="store_true", help="以 CSV 格式输出，便于导入表格")
    parser.add_argument("--no-summary", action="store_true", help="不打印统计信息")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        chainrings = parse_teeth(args.chainring)
        cogs = parse_teeth(args.cassette)
    except ValueError as exc:
        print(f"参数错误：{exc}", file=sys.stderr)
        return 2

    rows = ratios(chainrings, cogs)

    if args.csv:
        writer = csv.writer(sys.stdout)
        writer.writerow(["牙盘", "飞轮", "齿比", "档位"])
        for chainring, cog, ratio in rows:
            name, _ = classify(ratio)
            writer.writerow([chainring, cog, f"{ratio:.2f}", name])
        return 0

    print(format_table(rows))

    if not args.no_summary:
        stats = summarize(rows)
        low = stats["min"]
        high = stats["max"]
        print("-" * 60)
        print(f"组合数 {stats['count']} 组，齿比跨度 {stats['span']:.2f} 倍")
        print(f"最轻 {low[0]} × {low[1]} = {low[2]:.2f}（{classify(low[2])[0]}）")
        print(f"最重 {high[0]} × {high[1]} = {high[2]:.2f}（{classify(high[2])[0]}）")
        print()
        print(format_legend())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
