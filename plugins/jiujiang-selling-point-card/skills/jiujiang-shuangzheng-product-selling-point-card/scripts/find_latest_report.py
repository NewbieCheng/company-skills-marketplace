#!/usr/bin/env python3
"""在已授权的单一目录中，为指定产品选择唯一的最新旧版报告。"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any, Optional

import yaml


REPORT_MARKERS = ("产品卖点分析报告", "产品卖点内容卡")
DATE_RE = re.compile(r"(?<!\d)(20\d{2})[-_.年](\d{1,2})[-_.月](\d{1,2})(?:日)?(?!\d)")
VERSION_RE = re.compile(r"(?:^|[^a-zA-Z0-9])v(\d+)(?=$|[^a-zA-Z0-9])", re.IGNORECASE)
NORMALIZE_RE = re.compile(r"[^0-9a-zA-Z\u4e00-\u9fff]+")


@dataclass(frozen=True)
class Candidate:
    path: Path
    report_time: Optional[datetime]
    version: Optional[int]
    mtime: float
    date_source: Optional[str]
    version_source: Optional[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="只扫描一个已授权目录的 Markdown 元数据，选择指定产品的最新旧版卖点报告。"
    )
    parser.add_argument("directory", type=Path, help="已授权的产品卖点报告目录；不会递归扫描")
    parser.add_argument("--product", required=True, help="稳定产品名称，用于筛选同一对象的旧报告")
    parser.add_argument(
        "--as-of",
        required=True,
        help="当前任务日期或时间，ISO 8601 格式；带日期的未来报告会被排除",
    )
    return parser.parse_args()


def parse_as_of(value: str) -> datetime:
    cleaned = value.strip().replace("Z", "+00:00")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", cleaned):
        try:
            return datetime.combine(date.fromisoformat(cleaned), time.max)
        except ValueError as exc:
            raise ValueError("--as-of 必须是 YYYY-MM-DD 或合法 ISO 8601 时间") from exc
    try:
        return datetime.fromisoformat(cleaned)
    except ValueError as exc:
        raise ValueError("--as-of 必须是 YYYY-MM-DD 或合法 ISO 8601 时间") from exc


def read_frontmatter(path: Path) -> dict[str, Any]:
    """只读取文件开头的 frontmatter，不读取报告正文。"""
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            first = handle.readline()
            if first.strip() != "---":
                return {}
            lines: list[str] = []
            total = 0
            for line in handle:
                total += len(line.encode("utf-8", errors="ignore"))
                if total > 65536:
                    return {}
                if line.strip() == "---":
                    parsed = yaml.safe_load("".join(lines)) or {}
                    return parsed if isinstance(parsed, dict) else {}
                lines.append(line)
    except OSError:
        return {}
    return {}


def normalize_identity(value: Any) -> str:
    text = str(value or "").lower()
    for marker in REPORT_MARKERS:
        text = text.replace(marker, "")
    text = text.replace("九江双蒸", "")
    return NORMALIZE_RE.sub("", text)


def parse_date_value(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, time.min)
    if not isinstance(value, str) or not value.strip():
        return None
    cleaned = value.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(cleaned)
    except ValueError:
        match = DATE_RE.search(value)
        if not match:
            return None
        try:
            return datetime.combine(date(*(int(part) for part in match.groups())), time.min)
        except ValueError:
            return None


def parse_filename_date(name: str) -> Optional[datetime]:
    match = DATE_RE.search(name)
    if not match:
        return None
    try:
        return datetime.combine(date(*(int(part) for part in match.groups())), time.min)
    except ValueError:
        return None


def parse_version_value(value: Any) -> Optional[int]:
    if isinstance(value, int) and value >= 0:
        return value
    if not isinstance(value, str):
        return None
    match = re.fullmatch(r"\s*v?(\d+)\s*", value, re.IGNORECASE)
    return int(match.group(1)) if match else None


def parse_filename_version(name: str) -> Optional[int]:
    matches = VERSION_RE.findall(name)
    return int(matches[-1]) if matches else None


def is_report(path: Path, frontmatter: dict[str, Any]) -> bool:
    marker_in_name = any(marker in path.stem for marker in REPORT_MARKERS)
    marker_in_type = str(frontmatter.get("card_type", "")) in REPORT_MARKERS
    return marker_in_name or marker_in_type


def matches_product(path: Path, frontmatter: dict[str, Any], product: str) -> bool:
    query = normalize_identity(product)
    if not query:
        return False
    fields = (path.stem, frontmatter.get("product"), frontmatter.get("title"))
    return any(query in normalize_identity(field) for field in fields if field)


def build_candidate(path: Path, frontmatter: dict[str, Any]) -> Candidate:
    frontmatter_date = parse_date_value(frontmatter.get("created_at"))
    filename_date = parse_filename_date(path.stem)
    frontmatter_version = parse_version_value(frontmatter.get("version"))
    filename_version = parse_filename_version(path.stem)
    return Candidate(
        path=path.resolve(),
        report_time=frontmatter_date or filename_date,
        version=frontmatter_version if frontmatter_version is not None else filename_version,
        mtime=path.stat().st_mtime,
        date_source="frontmatter.created_at" if frontmatter_date else ("filename" if filename_date else None),
        version_source=(
            "frontmatter.version"
            if frontmatter_version is not None
            else ("filename" if filename_version is not None else None)
        ),
    )


def comparison_time(value: datetime, as_of: datetime) -> datetime:
    reference_zone = as_of.tzinfo or timezone.utc
    localized = value if value.tzinfo else value.replace(tzinfo=reference_zone)
    return localized.astimezone(timezone.utc)


def choose_latest(candidates: list[Candidate], as_of: datetime) -> tuple[str, list[Candidate], str]:
    as_of_comparison = comparison_time(as_of, as_of)
    eligible = [
        candidate
        for candidate in candidates
        if not candidate.report_time
        or comparison_time(candidate.report_time, as_of) <= as_of_comparison
    ]
    if not eligible:
        return "none", [], "没有日期不晚于当前任务时间的候选报告"

    dated = [candidate for candidate in eligible if candidate.report_time]
    if dated:
        latest_date = max(
            comparison_time(candidate.report_time, as_of)
            for candidate in dated
            if candidate.report_time
        )
        pool = [
            candidate
            for candidate in dated
            if candidate.report_time and comparison_time(candidate.report_time, as_of) == latest_date
        ]
        versioned = [candidate for candidate in pool if candidate.version is not None]
        if versioned:
            latest_version = max(candidate.version for candidate in versioned if candidate.version is not None)
            pool = [candidate for candidate in versioned if candidate.version == latest_version]
            basis = "date_then_version"
        else:
            basis = "date"
        return ("selected" if len(pool) == 1 else "ambiguous"), pool, basis

    versioned = [candidate for candidate in eligible if candidate.version is not None]
    if versioned:
        latest_version = max(candidate.version for candidate in versioned if candidate.version is not None)
        pool = [candidate for candidate in versioned if candidate.version == latest_version]
        return ("selected" if len(pool) == 1 else "ambiguous"), pool, "version"

    latest_mtime = max(candidate.mtime for candidate in eligible)
    pool = [candidate for candidate in eligible if candidate.mtime == latest_mtime]
    return ("selected" if len(pool) == 1 else "ambiguous"), pool, "mtime_fallback"


def candidate_payload(candidate: Candidate) -> dict[str, Any]:
    return {
        "path": str(candidate.path),
        "date": candidate.report_time.isoformat() if candidate.report_time else None,
        "date_source": candidate.date_source,
        "version": candidate.version,
        "version_source": candidate.version_source,
    }


def main() -> int:
    args = parse_args()
    try:
        as_of = parse_as_of(args.as_of)
    except ValueError as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 2

    directory = args.directory.resolve()
    if not directory.is_dir():
        print(json.dumps({"status": "error", "message": f"目录不存在：{directory}"}, ensure_ascii=False))
        return 2

    candidates: list[Candidate] = []
    for path in sorted(directory.iterdir(), key=lambda item: item.name):
        if not path.is_file() or path.suffix.lower() != ".md":
            continue
        frontmatter = read_frontmatter(path)
        if not is_report(path, frontmatter) or not matches_product(path, frontmatter, args.product):
            continue
        try:
            candidates.append(build_candidate(path, frontmatter))
        except OSError:
            continue

    if not candidates:
        print(
            json.dumps(
                {
                    "status": "none",
                    "selected_report": None,
                    "selection_basis": None,
                    "matched_candidate_count": 0,
                    "message": "授权目录中没有匹配该产品的旧版卖点报告",
                },
                ensure_ascii=False,
            )
        )
        return 0

    status, pool, basis = choose_latest(candidates, as_of)
    if status == "none":
        print(
            json.dumps(
                {
                    "status": "none",
                    "selected_report": None,
                    "selection_basis": None,
                    "matched_candidate_count": len(candidates),
                    "message": basis,
                },
                ensure_ascii=False,
            )
        )
        return 0

    if status == "ambiguous":
        print(
            json.dumps(
                {
                    "status": "ambiguous",
                    "selected_report": None,
                    "selection_basis": basis,
                    "matched_candidate_count": len(candidates),
                    "tied_candidates": [candidate_payload(candidate) for candidate in pool],
                    "message": "最高优先级仍有并列；不得读取正文，需由用户指定一份",
                },
                ensure_ascii=False,
            )
        )
        return 3

    selected = pool[0]
    print(
        json.dumps(
            {
                "status": "selected",
                "selected_report": str(selected.path),
                "selection_basis": basis,
                "selected_date": selected.report_time.isoformat() if selected.report_time else None,
                "selected_version": selected.version,
                "matched_candidate_count": len(candidates),
                "message": "只允许把 selected_report 的正文纳入后续分析上下文",
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
