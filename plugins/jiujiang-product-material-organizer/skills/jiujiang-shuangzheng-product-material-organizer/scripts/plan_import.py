#!/usr/bin/env python3
"""Create an Obsidian import plan from a material manifest."""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path

from material_common import CATEGORY_DIRS, read_json, sanitize_filename, short_hash, write_json


REVERSE_CATEGORY = {value: key for key, value in CATEGORY_DIRS.items()}
VALID_DIRS = set(CATEGORY_DIRS.values())


def read_decisions(path: Path | None) -> dict[str, dict]:
    if not path:
        return {}
    decisions: dict[str, dict] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            item_id = (row.get("id") or "").strip()
            if not item_id:
                continue
            decisions[item_id] = {
                "product": (row.get("product") or "").strip(),
                "category": (row.get("category") or "").strip(),
                "confidence": float(row.get("confidence") or 0),
                "note": (row.get("note") or "").strip(),
            }
    return decisions


def choose_product(record: dict, decision: dict | None) -> tuple[str | None, float, str]:
    if decision and decision.get("product"):
        return decision["product"], float(decision.get("confidence") or 0), "decision"
    return record.get("path_suggested_product"), float(record.get("path_product_confidence") or 0), "path"


def choose_category(record: dict, decision: dict | None) -> tuple[str, float, str]:
    if record.get("material_type_key") != "image":
        return "", 1.0, "not_applicable"
    if decision and decision.get("category"):
        category = decision["category"]
        if category in REVERSE_CATEGORY:
            return category, float(decision.get("confidence") or 0), "decision"
        if category in CATEGORY_DIRS:
            return CATEGORY_DIRS[category], float(decision.get("confidence") or 0), "decision"
        return CATEGORY_DIRS["pending"], 0.0, "invalid_decision_category"
    return (
        record.get("path_suggested_category") or CATEGORY_DIRS["pending"],
        float(record.get("path_category_confidence") or 0),
        "path",
    )


def planned_target(material_type: str, product: str | None, category: str, filename: str) -> str:
    product_dir = product or "00_产品待确认"
    if material_type == "图片类素材":
        if category not in VALID_DIRS:
            category = CATEGORY_DIRS["pending"]
        return f"{material_type}/{product_dir}/{category}/{sanitize_filename(filename)}"
    return f"{material_type}/{product_dir}/{sanitize_filename(filename)}"


def build_plan(manifest: dict, target_root: Path, decisions: dict[str, dict]) -> dict:
    plan_records = []
    for record in manifest["records"]:
        decision = decisions.get(record["id"])
        product, product_confidence, product_source = choose_product(record, decision)
        category, category_confidence, category_source = choose_category(record, decision)
        material_type = record.get("material_type_dir") or "00_待人工确认"
        material_type_confidence = float(record.get("material_type_confidence") or 0)
        confidence = min(product_confidence, category_confidence)
        if material_type == "00_待人工确认":
            confidence = 0.0
        if record.get("material_type_key") != "image":
            category = ""
            suggested_category = ""
            confidence = min(product_confidence, material_type_confidence)
        elif not product:
            category = CATEGORY_DIRS["pending"]
            suggested_category = category
        else:
            suggested_category = category
        if confidence < 0.90:
            if record.get("material_type_key") == "image":
                suggested_category = category
                category = CATEGORY_DIRS["pending"]
            category = CATEGORY_DIRS["pending"]
            action = "needs_review"
        else:
            action = "import"

        target_rel = planned_target(material_type, product, category, record["filename"])
        plan_records.append(
            {
                **record,
                "final_material_type": material_type,
                "final_product": product,
                "final_category": category,
                "suggested_category": suggested_category,
                "final_confidence": round(confidence, 3),
                "product_source": product_source,
                "category_source": category_source,
                "action": action,
                "target_root": str(target_root),
                "target_rel": target_rel,
                "target_path": str(target_root / Path(target_rel)),
                "note": (decision or {}).get("note", ""),
            }
        )
    return {
        "schema": "jiujiang-material-import-plan.v1",
        "source_manifest": manifest.get("input"),
        "target_root": str(target_root),
        "records": plan_records,
    }


def write_preview(plan: dict, output_path: Path) -> None:
    records = plan["records"]
    action_counts = Counter(r["action"] for r in records)
    by_material_type = Counter(r["final_material_type"] for r in records)
    by_product = Counter(r["final_product"] or "00_产品待确认" for r in records)
    by_type_product = defaultdict(Counter)
    by_type_product_category = defaultdict(Counter)
    for record in records:
        material_type = record["final_material_type"]
        product = record["final_product"] or "00_产品待确认"
        by_type_product[material_type][product] += 1
        category = record["final_category"] or "无图片细分"
        by_type_product_category[f"{material_type}/{product}"][category] += 1

    lines = [
        "# 产品素材入库预案",
        "",
        f"- 目标根路径：`{plan['target_root']}`",
        f"- 总素材数：{len(records)}",
        f"- 可自动入库：{action_counts.get('import', 0)}",
        f"- 待人工确认：{action_counts.get('needs_review', 0)}",
        "",
        "## 按文件类型统计",
        "",
    ]
    for material_type, count in by_material_type.most_common():
        lines.append(f"- {material_type}: {count}")

    lines.extend([
        "",
        "## 按产品统计",
        "",
    ])
    for product, count in by_product.most_common():
        lines.append(f"- {product}: {count}")

    lines.extend(["", "## 文件类型 x 产品", ""])
    for material_type in sorted(by_type_product):
        lines.append(f"### {material_type}")
        for product, count in by_type_product[material_type].most_common():
            lines.append(f"- {product}: {count}")
        lines.append("")

    lines.extend(["## 文件类型 x 产品 x 图片分类", ""])
    for group in sorted(by_type_product_category):
        lines.append(f"### {group}")
        for category, count in by_type_product_category[group].most_common():
            lines.append(f"- {category}: {count}")
        lines.append("")

    lines.extend(["## 待人工确认样例", ""])
    pending = [r for r in records if r["action"] == "needs_review"]
    for record in pending[:50]:
        lines.append(
            f"- `{record['display_path']}` -> `{record['target_rel']}` "
            f"(建议：{record['final_material_type']} / {record['final_product'] or '产品待确认'}"
            f"{(' / ' + record['suggested_category']) if record['suggested_category'] else ''}"
            f" / {record['final_confidence']})"
        )
    if len(pending) > 50:
        lines.append(f"- 另有 {len(pending) - 50} 个待确认素材未展开。")

    lines.extend(
        [
            "",
            "## 执行闸门",
            "",
            "未得到用户明确确认前，不要执行 `import_materials.py --execute`。",
        ]
    )
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", help="manifest.json from inspect_materials.py")
    parser.add_argument("--target-root", required=True, help="Obsidian product material root")
    parser.add_argument("--decisions", help="Optional CSV: id,product,category,confidence,note")
    parser.add_argument("--output-dir", required=True, help="Directory for import_plan.json and preview")
    args = parser.parse_args()

    manifest_path = Path(args.manifest).expanduser().resolve()
    target_root = Path(args.target_root).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    decisions = read_decisions(Path(args.decisions).expanduser().resolve() if args.decisions else None)
    manifest = read_json(manifest_path)
    plan = build_plan(manifest, target_root, decisions)
    write_json(output_dir / "import_plan.json", plan)
    write_preview(plan, output_dir / "import_preview.md")
    print(output_dir / "import_plan.json")
    print(output_dir / "import_preview.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
