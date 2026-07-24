#!/usr/bin/env python3
"""Inspect a product material folder or zip without modifying source files."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from material_common import (
    CATEGORY_DIRS,
    extension,
    file_id,
    infer_category_from_path,
    infer_product,
    list_materials,
    material_type_from_extension,
    media_kind,
    write_json,
)


def build_manifest(input_path: Path) -> dict:
    materials = list_materials(input_path)
    records = []
    for item in materials:
        product, product_confidence, product_source = infer_product(item.display_path)
        material_type_key, material_type_dir, material_type_confidence = material_type_from_extension(item.display_path)
        category_key, category_confidence, category_source = infer_category_from_path(item.display_path)
        if material_type_key != "image":
            category_key = "pending"
            category_confidence = 1.0
            category_source = "not_applicable"
        records.append(
            {
                "id": file_id(item.display_path, item.size),
                "source_kind": item.source_kind,
                "input_path": item.input_path,
                "member_path": item.member_path,
                "display_path": item.display_path,
                "filename": Path(item.display_path).name,
                "extension": extension(item.display_path),
                "media_kind": media_kind(item.display_path),
                "material_type_key": material_type_key,
                "material_type_dir": material_type_dir,
                "material_type_confidence": material_type_confidence,
                "size": item.size,
                "path_suggested_product": product,
                "path_product_confidence": product_confidence,
                "path_product_source": product_source,
                "path_suggested_category": CATEGORY_DIRS[category_key],
                "path_category_key": category_key,
                "path_category_confidence": category_confidence,
                "path_category_source": category_source,
            }
        )
    return {
        "schema": "jiujiang-material-manifest.v1",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "input": str(input_path),
        "records": records,
    }


def write_summary(manifest: dict, output_path: Path) -> None:
    records = manifest["records"]
    ext_counts = Counter(r["extension"] or "[no extension]" for r in records)
    material_type_counts = Counter(r["material_type_dir"] for r in records)
    product_counts = Counter(r["path_suggested_product"] or "未识别产品" for r in records)
    image_records = [r for r in records if r["material_type_key"] == "image"]
    category_counts = Counter(r["path_suggested_category"] for r in image_records)
    by_type_product = defaultdict(Counter)
    by_product_category = defaultdict(Counter)
    for record in records:
        by_type_product[record["material_type_dir"]][record["path_suggested_product"] or "未识别产品"] += 1
    for record in image_records:
        by_product_category[record["path_suggested_product"] or "未识别产品"][
            record["path_suggested_category"]
        ] += 1

    lines = [
        "# 产品素材盘点摘要",
        "",
        f"- 输入：`{manifest['input']}`",
        f"- 生成时间：{manifest['created_at']}",
        f"- 素材总数：{len(records)}",
        "",
        "## 文件类型",
        "",
    ]
    for ext, count in ext_counts.most_common():
        lines.append(f"- {ext}: {count}")

    lines.extend(["", "## 文件类型分类", ""])
    for material_type, count in material_type_counts.most_common():
        lines.append(f"- {material_type}: {count}")

    lines.extend(["", "## 路径识别产品", ""])
    for product, count in product_counts.most_common():
        lines.append(f"- {product}: {count}")

    lines.extend(["", "## 文件类型 x 产品", ""])
    for material_type in sorted(by_type_product):
        lines.append(f"### {material_type}")
        for product, count in by_type_product[material_type].most_common():
            lines.append(f"- {product}: {count}")
        lines.append("")

    lines.extend(["## 图片路径建议分类", ""])
    if category_counts:
        for category, count in category_counts.most_common():
            lines.append(f"- {category}: {count}")
    else:
        lines.append("- 无图片类素材")

    lines.extend(["", "## 产品 x 图片路径建议分类", ""])
    if by_product_category:
        for product in sorted(by_product_category):
            lines.append(f"### {product}")
            for category, count in by_product_category[product].most_common():
                lines.append(f"- {category}: {count}")
            lines.append("")
    else:
        lines.append("- 无图片类素材")

    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Folder or .zip file to inspect")
    parser.add_argument("--output-dir", required=True, help="Directory for manifest and summary")
    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = build_manifest(input_path)
    write_json(output_dir / "manifest.json", manifest)
    write_summary(manifest, output_dir / "summary.md")
    print(output_dir / "manifest.json")
    print(output_dir / "summary.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
