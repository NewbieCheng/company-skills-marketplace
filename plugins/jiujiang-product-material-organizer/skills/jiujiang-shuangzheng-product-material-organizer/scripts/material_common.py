#!/usr/bin/env python3
"""Shared helpers for the Jiujiang material organizer scripts."""

from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import posixpath
import re
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".gif", ".bmp", ".tif", ".tiff"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm", ".wmv"}
DOCUMENT_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".csv",
    ".ppt",
    ".pptx",
    ".pages",
    ".numbers",
    ".key",
    ".txt",
    ".md",
}

MATERIAL_TYPE_DIRS = {
    "image": "图片类素材",
    "video": "视频类素材",
    "document": "文档类素材",
    "unknown": "00_待人工确认",
}

CATEGORY_DIRS = {
    "pending": "00_待人工确认",
    "product_photo": "01_产品实拍",
    "positive_review": "02_好评截图",
    "user_showcase": "03_用户晒单",
    "user_inquiry": "04_用户咨询",
}

PRODUCT_PATTERNS = [
    ("青梅酒_南高梅", ("青梅酒", "云南青梅", "南高梅")),
    ("青梅酒_福建青梅", ("青梅酒", "福建青梅")),
    ("青梅酒_云南青梅", ("青梅酒", "云南青梅")),
    ("药材酒_仙人健脾", ("药材酒", "仙人健脾")),
    ("菠萝酒", ("菠萝酒",)),
    ("黄皮酒", ("黄皮酒",)),
    ("三华李酒", ("三华李酒",)),
    ("杨梅酒", ("杨梅酒",)),
    ("玫瑰酒", ("玫瑰酒",)),
    ("桑葚酒", ("桑葚酒",)),
    ("荔枝酒", ("荔枝酒",)),
    ("基酒", ("基酒",)),
    ("青梅酒", ("青梅酒",)),
    ("药材酒", ("药材酒",)),
]

PATH_CATEGORY_PATTERNS = [
    ("positive_review", 0.92, ("好评", "评价", "商品好评")),
    ("user_inquiry", 0.92, ("咨询", "用户咨询", "问", "询价")),
    ("user_showcase", 0.88, ("晒单", "用户分享", "成品分享", "收货反馈", "开箱")),
    ("product_photo", 0.82, ("产品实拍", "原料素材", "产品", "原料")),
]


@dataclass
class MaterialSource:
    source_kind: str
    input_path: str
    member_path: str
    display_path: str
    size: int


def decode_zip_name(name: str) -> str:
    """Repair common macOS/Windows Chinese zip names when Python exposes mojibake."""
    try:
        repaired = name.encode("cp437").decode("gb18030")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return name
    if "\ufffd" in name or repaired != name:
        return repaired
    return name


def normalize_posix(path: str) -> str:
    return posixpath.normpath(path.replace("\\", "/")).lstrip("/")


def safe_rel_path(path: str) -> str:
    path = normalize_posix(path)
    parts = [p for p in path.split("/") if p not in ("", ".", "..")]
    return "/".join(parts)


def file_id(display_path: str, size: int) -> str:
    payload = f"{display_path}\0{size}".encode("utf-8", errors="replace")
    return hashlib.sha1(payload).hexdigest()[:16]


def short_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", errors="replace")).hexdigest()[:8]


def ensure_unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    digest = short_hash(str(path))
    candidate = path.with_name(f"{stem}_{digest}{suffix}")
    counter = 2
    while candidate.exists():
        candidate = path.with_name(f"{stem}_{digest}_{counter}{suffix}")
        counter += 1
    return candidate


def infer_product(path: str) -> tuple[str | None, float, str]:
    compact = path.replace("\\", "/")
    for product, needles in PRODUCT_PATTERNS:
        if all(needle in compact for needle in needles):
            return product, 0.95, "path"
    return None, 0.0, "unknown"


def infer_category_from_path(path: str) -> tuple[str, float, str]:
    compact = path.replace("\\", "/")
    for key, confidence, needles in PATH_CATEGORY_PATTERNS:
        if any(needle in compact for needle in needles):
            return key, confidence, "path"
    return "pending", 0.0, "unknown"


def list_materials(input_path: Path) -> list[MaterialSource]:
    if input_path.is_dir():
        return list_folder_materials(input_path)
    if input_path.is_file() and input_path.suffix.lower() == ".zip":
        return list_zip_materials(input_path)
    raise ValueError(f"Input must be a folder or .zip file: {input_path}")


def list_folder_materials(input_path: Path) -> list[MaterialSource]:
    records: list[MaterialSource] = []
    for root, _, files in os.walk(input_path):
        for filename in files:
            path = Path(root) / filename
            if filename == ".DS_Store":
                continue
            rel = safe_rel_path(str(path.relative_to(input_path)))
            records.append(
                MaterialSource(
                    source_kind="folder",
                    input_path=str(input_path),
                    member_path=rel,
                    display_path=rel,
                    size=path.stat().st_size,
                )
            )
    return records


def list_zip_materials(input_path: Path) -> list[MaterialSource]:
    records: list[MaterialSource] = []
    with zipfile.ZipFile(input_path) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            display = safe_rel_path(decode_zip_name(info.filename))
            if posixpath.basename(display) == ".DS_Store":
                continue
            records.append(
                MaterialSource(
                    source_kind="zip",
                    input_path=str(input_path),
                    member_path=info.filename,
                    display_path=display,
                    size=info.file_size,
                )
            )
    return records


def extension(path: str) -> str:
    return Path(path).suffix.lower()


def material_type_from_extension(path: str) -> tuple[str, str, float]:
    ext = extension(path)
    if ext in IMAGE_EXTENSIONS:
        return "image", MATERIAL_TYPE_DIRS["image"], 0.98
    if ext in VIDEO_EXTENSIONS:
        return "video", MATERIAL_TYPE_DIRS["video"], 0.98
    if ext in DOCUMENT_EXTENSIONS:
        return "document", MATERIAL_TYPE_DIRS["document"], 0.98
    return "unknown", MATERIAL_TYPE_DIRS["unknown"], 0.0


def media_kind(path: str) -> str:
    material_key, _, _ = material_type_from_extension(path)
    if material_key != "unknown":
        return material_key
    mime, _ = mimetypes.guess_type(path)
    if mime:
        return mime
    return "unknown"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def copy_material(record: dict[str, Any], destination: Path) -> None:
    input_path = Path(record["input_path"])
    if record["source_kind"] == "folder":
        source = input_path / record["member_path"]
        shutil.copy2(source, destination)
        return
    if record["source_kind"] == "zip":
        with zipfile.ZipFile(input_path) as archive:
            with archive.open(record["member_path"]) as source, destination.open("wb") as target:
                shutil.copyfileobj(source, target)
        return
    raise ValueError(f"Unknown source kind: {record['source_kind']}")


def sanitize_filename(name: str) -> str:
    name = posixpath.basename(name)
    name = re.sub(r"[\r\n\t]", "_", name)
    return name or "unnamed"
