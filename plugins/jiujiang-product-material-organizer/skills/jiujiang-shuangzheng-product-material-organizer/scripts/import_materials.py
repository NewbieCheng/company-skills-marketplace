#!/usr/bin/env python3
"""Copy approved product materials into the Obsidian product material library."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from material_common import copy_material, ensure_unique_path, read_json


def append_markdown(path: Path, title: str, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else f"# {title}\n"
    addition = "\n" + "\n".join(lines).rstrip() + "\n"
    path.write_text(existing.rstrip() + "\n" + addition, encoding="utf-8")


def execute_plan(plan: dict, dry_run: bool) -> dict:
    target_root = Path(plan["target_root"])
    copied = []
    pending = []
    errors = []
    for record in plan["records"]:
        if record["action"] != "import":
            pending.append(record)
            continue
        destination = ensure_unique_path(target_root / record["target_rel"])
        if not dry_run:
            destination.parent.mkdir(parents=True, exist_ok=True)
            try:
                copy_material(record, destination)
            except Exception as exc:  # noqa: BLE001
                errors.append({**record, "error": str(exc)})
                continue
        copied.append({**record, "actual_target_path": str(destination)})
    return {"copied": copied, "pending": pending, "errors": errors}


def write_indexes(plan: dict, result: dict, dry_run: bool) -> None:
    if dry_run:
        return
    target_root = Path(plan["target_root"])
    index_dir = target_root / "99_入库索引"
    now = datetime.now().isoformat(timespec="seconds")

    total_lines = [
        f"## {now}",
        "",
        f"- 本次自动入库：{len(result['copied'])}",
        f"- 待人工确认：{len(result['pending'])}",
        f"- 异常：{len(result['errors'])}",
        "",
        "| 文件类型 | 产品 | 图片分类 | 置信度 | 原始路径 | 入库路径 |",
        "|---|---|---|---:|---|---|",
    ]
    for record in result["copied"]:
        total_lines.append(
            f"| {record['final_material_type']} | {record['final_product']} | {record['final_category'] or '无图片细分'} | "
            f"{record['final_confidence']} | `{record['display_path']}` | `{record['actual_target_path']}` |"
        )
    append_markdown(index_dir / "素材入库总表.md", "素材入库总表", total_lines)

    pending_lines = [
        f"## {now}",
        "",
        "| 文件类型 | 产品 | 建议图片分类 | 置信度 | 原始路径 | 待确认路径 |",
        "|---|---|---|---:|---|---|",
    ]
    for record in result["pending"]:
        pending_lines.append(
            f"| {record.get('final_material_type') or '文件类型待确认'} | {record.get('final_product') or '产品待确认'} | "
            f"{record.get('suggested_category') or '无图片细分'} | "
            f"{record['final_confidence']} | `{record['display_path']}` | `{record['target_path']}` |"
        )
    append_markdown(index_dir / "待人工确认清单.md", "待人工确认清单", pending_lines)

    error_lines = [
        f"## {now}",
        "",
        "| 原始路径 | 目标路径 | 错误 |",
        "|---|---|---|",
    ]
    for record in result["errors"]:
        error_lines.append(f"| `{record['display_path']}` | `{record['target_path']}` | {record['error']} |")
    append_markdown(index_dir / "异常清单.md", "异常清单", error_lines)


def print_summary(result: dict, dry_run: bool) -> None:
    by_product_category = defaultdict(Counter)
    for record in result["copied"]:
        group = f"{record['final_material_type']}/{record['final_product']}"
        by_product_category[group][record["final_category"] or "无图片细分"] += 1
    copied_label = "would_copy" if dry_run else "copied"
    print(f"{copied_label}={len(result['copied'])}")
    print(f"pending={len(result['pending'])}")
    print(f"errors={len(result['errors'])}")
    for product in sorted(by_product_category):
        for category, count in by_product_category[product].most_common():
            print(f"{product}\t{category}\t{count}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", help="import_plan.json from plan_import.py")
    parser.add_argument("--execute", action="store_true", help="Actually copy files. Omit for dry run.")
    args = parser.parse_args()

    plan = read_json(Path(args.plan).expanduser().resolve())
    result = execute_plan(plan, dry_run=not args.execute)
    write_indexes(plan, result, dry_run=not args.execute)
    print_summary(result, dry_run=not args.execute)
    if result["errors"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
