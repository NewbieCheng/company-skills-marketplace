#!/usr/bin/env python3
"""Validate a v2.1 product selling-point analysis report and AI handoff."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

import yaml


REQUIRED_QUESTIONS = [
    "## 一、这款产品现在最应该卖什么？",
    "## 二、谁最可能为它买单，为什么？",
    "## 三、产品凭什么让用户相信？",
    "## 四、不同 SKU 分别适合谁，应该怎么选？",
    "## 五、用户最可能犹豫什么，我们现在能回答到哪？",
    "## 六、销售和内容现在能说什么、不能说什么？",
    "## 七、现在还缺哪些证据，应该先补哪一项？",
    "## 八、这轮卖点打完后，下一步应该继续、调整还是换方向？",
]

EVIDENCE_STATUSES = {"confirmed", "inferred", "unknown", "conflict"}
AVAILABILITY_STATUSES = {"existing", "planned", "absent", "unknown"}
USAGE_LEVELS = {"direct", "test_only", "prohibited"}
CARD_STATUSES = {"pending_validation", "limited_use", "validated"}
CORE_STATUSES = {"formal", "hypothesis", "unavailable"}
SUPPORT_STATUSES = {"formal", "hypothesis"}
SKU_STATUSES = {"confirmed", "inferred", "unknown"}
FAQ_STATUSES = {"confirmed", "limited", "unavailable"}
ITERATION_STAGES = {"evidence_collection", "small_test", "scale_validation", "validated"}
GAP_TYPES = {
    "product_proof",
    "user_evidence",
    "behavior_evidence",
    "capability_delivery",
    "compliance",
}
GAP_STATUSES = {"open", "in_progress", "complete", "blocked"}
GAP_PRIORITIES = {"blocking", "decision", "optimization"}
ROUND_STATUSES = {"not_started", "in_progress", "completed"}
ROUND_DECISIONS = {"pending", "continue", "adjust", "switch", "stop"}
CLAIM_ID_RE = re.compile(r"^C\d{3}$")
GAP_ID_RE = re.compile(r"^G\d{3}$")
YAML_BLOCK_RE = re.compile(r"```ya?ml\s*\n(.*?)\n```", re.DOTALL | re.IGNORECASE)
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)

# These terms require an independent compliance decision and must not be auto-released.
BLOCKED_DIRECT_PATTERNS = [
    r"治疗",
    r"治愈",
    r"预防疾病",
    r"保健功效",
    r"改善身体",
    r"不伤身",
    r"无负担",
    r"百分之百",
    r"100%",
    r"行业唯一",
    r"行业第一",
    r"最好",
    r"无硫熏",
    r"年份保真",
    r"原产保证",
    r"古法九制",
    r"九蒸九晒",
    r"保证(?:有效|治愈|改善)",
]

UNVERIFIED_PROMISE_PATTERNS = [
    r"可提供.{0,20}(?:待补|待制作|尚未|计划)",
    r"配(?:套|完整)?.{0,20}教程.{0,10}(?:待制作|尚未|计划)",
    r"标清.{0,20}(?:产地|年份|工艺).{0,20}(?:待证|待补|无证明)",
    r"品质可追溯.{0,20}(?:待证|待补|无证明)",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="校验九江双蒸产品卖点分析报告 v2.1 的结构与 AI 交接契约。"
    )
    parser.add_argument("card", type=Path, help="待校验的 Markdown 产品卖点分析报告")
    return parser.parse_args()


def add_error(errors: list[str], message: str) -> None:
    errors.append(message)


def require_dict(value: Any, path: str, errors: list[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        add_error(errors, f"{path} 必须是映射对象")
        return {}
    return value


def require_list(value: Any, path: str, errors: list[str]) -> list[Any]:
    if not isinstance(value, list):
        add_error(errors, f"{path} 必须是列表")
        return []
    return value


def validate_question_structure(text: str, errors: list[str]) -> None:
    usage_pos = text.find("## 这份报告怎么用？")
    first_question_pos = text.find(REQUIRED_QUESTIONS[0])
    if usage_pos < 0:
        add_error(errors, "缺少面向新手的“## 这份报告怎么用？”")
    elif first_question_pos >= 0 and usage_pos > first_question_pos:
        add_error(errors, "报告使用说明必须位于八个人类决策问题之前")

    positions: list[int] = []
    for heading in REQUIRED_QUESTIONS:
        pos = text.find(heading)
        if pos < 0:
            add_error(errors, f"缺少问题式一级标题：{heading}")
        positions.append(pos)

    present_positions = [pos for pos in positions if pos >= 0]
    if present_positions != sorted(present_positions):
        add_error(errors, "八个人类决策问题的顺序不正确")

    appendix_pos = text.find("# 证据与判断附录")
    handoff_pos = text.find("# AI 交接区")
    if appendix_pos < 0:
        add_error(errors, "缺少“# 证据与判断附录”")
    if handoff_pos < 0:
        add_error(errors, "缺少“# AI 交接区”")
    if present_positions and appendix_pos >= 0 and appendix_pos < max(present_positions):
        add_error(errors, "证据附录必须位于八个人类决策问题之后")

    required_action_headings = [
        "### 证据补充行动板",
        "### 不要把这些证据混为一谈",
        "### 本轮只做什么",
        "### 这一轮到底在验证什么",
        "### 打完以后要记录什么",
        "### 看到什么结果以后怎么决定",
        "### 什么情况下生成下一版报告",
    ]
    for heading in required_action_headings:
        if heading not in text:
            add_error(errors, f"缺少运营闭环子标题：{heading}")
    if appendix_pos >= 0 and handoff_pos >= 0 and handoff_pos < appendix_pos:
        add_error(errors, "AI 交接区必须位于证据附录之后")


def validate_candidate_count(text: str, errors: list[str]) -> None:
    start = text.find("### 候选资格闸门")
    end = text.find("### 五维比较", start + 1) if start >= 0 else -1
    if start < 0 or end < 0:
        add_error(errors, "证据附录必须包含“候选资格闸门”和“五维比较”")
        return
    table_lines = [line.strip() for line in text[start:end].splitlines() if line.strip().startswith("|")]
    body_rows = [
        line
        for line in table_lines
        if not re.fullmatch(r"\|?[\s:|-]+\|?", line)
        and "候选方向" not in line
    ]
    candidate_names = [split_markdown_row(line)[0] for line in body_rows]
    unique_candidates = set(candidate_names)
    if len(candidate_names) != len(unique_candidates):
        duplicates = sorted(
            {name for name in candidate_names if candidate_names.count(name) > 1}
        )
        add_error(errors, f"候选资格闸门含重复候选：{', '.join(duplicates)}")
    if len(unique_candidates) < 5:
        add_error(errors, f"候选资格闸门至少需要 5 个真实候选，当前识别到 {len(unique_candidates)} 个")


def expand_claim_ids(text: str) -> set[str]:
    result: set[str] = set()
    pattern = re.compile(r"C(\d{3})(?:\s*[-—–~至]\s*C?(\d{3}))?")
    for match in pattern.finditer(text):
        start = int(match.group(1))
        end_text = match.group(2)
        if end_text is None:
            result.add(f"C{start:03d}")
            continue
        end = int(end_text)
        if start <= end and end - start <= 100:
            result.update(f"C{number:03d}" for number in range(start, end + 1))
        else:
            result.add(f"C{start:03d}")
            result.add(f"C{end:03d}")
    return result


def expand_gap_ids(text: str) -> set[str]:
    return set(re.findall(r"\bG\d{3}\b", text))


def split_markdown_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def extract_table_rows(section: str, required_header: str) -> tuple[list[str], list[list[str]]]:
    lines = section.splitlines()
    for index, line in enumerate(lines):
        if line.strip().startswith("|") and required_header in line:
            headers = split_markdown_row(line)
            rows: list[list[str]] = []
            for candidate in lines[index + 1 :]:
                stripped = candidate.strip()
                if not stripped.startswith("|"):
                    if rows:
                        break
                    continue
                if re.fullmatch(r"\|?[\s:|-]+\|?", stripped):
                    continue
                cells = split_markdown_row(stripped)
                if len(cells) == len(headers):
                    rows.append(cells)
            return headers, rows
    return [], []


def validate_human_faq(text: str, direct_ids: set[str], errors: list[str]) -> None:
    start = text.find(REQUIRED_QUESTIONS[4])
    end = text.find(REQUIRED_QUESTIONS[5], start + 1) if start >= 0 else -1
    if start < 0 or end < 0:
        return
    headers, rows = extract_table_rows(text[start:end], "回答状态")
    required_headers = {
        "回答状态",
        "现在可以确认的回答",
        "可引用的 direct 声明",
        "还不能回答什么",
    }
    if not headers or not required_headers.issubset(set(headers)):
        add_error(errors, "第五问 FAQ 表必须包含回答状态、当前回答、direct 声明和未解决缺口")
        return
    indexes = {header: headers.index(header) for header in required_headers}
    for row_index, row in enumerate(rows, start=1):
        status = row[indexes["回答状态"]].strip("`")
        answer = row[indexes["现在可以确认的回答"]]
        ids_text = row[indexes["可引用的 direct 声明"]]
        claim_ids = expand_claim_ids(ids_text)
        if status not in FAQ_STATUSES:
            add_error(errors, f"第五问 FAQ 第 {row_index} 行回答状态非法：{status!r}")
        if status == "confirmed":
            if not claim_ids:
                add_error(errors, f"第五问 FAQ 第 {row_index} 行 confirmed 回答必须引用 direct 声明")
            if claim_ids - direct_ids:
                add_error(
                    errors,
                    f"第五问 FAQ 第 {row_index} 行 confirmed 回答引用了非 direct 声明：{', '.join(sorted(claim_ids - direct_ids))}",
                )
        if status in {"limited", "unavailable"} and not re.search(
            r"当前|目前|只能|不能|尚未|未提供|没有", answer
        ):
            add_error(errors, f"第五问 FAQ 第 {row_index} 行必须明确当前回答限制")
        for pattern in UNVERIFIED_PROMISE_PATTERNS:
            if re.search(pattern, answer):
                add_error(errors, f"第五问 FAQ 第 {row_index} 行承诺了待补证明或计划能力")
                break
        if status == "confirmed":
            for pattern in BLOCKED_DIRECT_PATTERNS:
                if re.search(pattern, answer, re.IGNORECASE):
                    add_error(errors, f"第五问 FAQ 第 {row_index} 行 confirmed 回答含高风险表达")
                    break


def validate_human_sku_table(text: str, errors: list[str]) -> None:
    start = text.find(REQUIRED_QUESTIONS[3])
    end = text.find(REQUIRED_QUESTIONS[4], start + 1) if start >= 0 else -1
    if start < 0 or end < 0:
        return
    headers, _ = extract_table_rows(text[start:end], "SKU 标称")
    required = {"SKU 标称（不等于属性已证明）", "已确认的规格与价格", "已确认属性", "角色状态"}
    if not headers or not required.issubset(set(headers)):
        add_error(errors, "第四问必须把 SKU 标称、已确认规格价格、已确认属性和角色状态分开")


def find_usage_section_text(section: str, heading: str, row_markers: tuple[str, ...]) -> str:
    heading_pos = section.find(heading)
    if heading_pos >= 0:
        content_start = heading_pos + len(heading)
        next_heading = section.find("\n### ", content_start)
        return section[content_start:] if next_heading < 0 else section[content_start:next_heading]
    matching_lines = [
        line for line in section.splitlines() if all(marker in line for marker in row_markers)
    ]
    return "\n".join(matching_lines)


def validate_human_usage_sections(
    text: str,
    direct_ids: set[str],
    test_ids: set[str],
    prohibited_ids: set[str],
    errors: list[str],
) -> None:
    start = text.find(REQUIRED_QUESTIONS[5])
    end = text.find(REQUIRED_QUESTIONS[6], start + 1) if start >= 0 else -1
    if start < 0 or end < 0:
        return
    section = text[start:end]
    direct_text = find_usage_section_text(section, "### 现在可以直接说", ("✅", "直接"))
    test_text = find_usage_section_text(
        section, "### 只能拿去测试，不能当事实说", ("🟡", "测试")
    )
    prohibited_text = find_usage_section_text(
        section, "### 当前禁止或必须人工审核", ("🔴",)
    )
    human_direct = expand_claim_ids(direct_text)
    human_test = expand_claim_ids(test_text)
    human_prohibited = expand_claim_ids(prohibited_text)

    if direct_ids and not human_direct:
        add_error(errors, "第六问必须通过声明 ID 列出现在可以直接说的内容")
    if human_direct - direct_ids:
        add_error(errors, f"第六问的直接使用区含非 direct 声明：{', '.join(sorted(human_direct - direct_ids))}")
    if human_test - test_ids:
        add_error(errors, f"第六问的测试区含非 test_only 声明：{', '.join(sorted(human_test - test_ids))}")
    if human_prohibited - prohibited_ids:
        add_error(
            errors,
            f"第六问的禁止区含非 prohibited 声明：{', '.join(sorted(human_prohibited - prohibited_ids))}",
        )
    for pattern in BLOCKED_DIRECT_PATTERNS:
        if re.search(pattern, direct_text, re.IGNORECASE):
            add_error(errors, "第六问的直接使用区含需要独立合规审核的高风险表达")
            break


def extract_handoff(text: str, errors: list[str]) -> dict[str, Any]:
    matching_blocks = [
        block for block in YAML_BLOCK_RE.findall(text) if re.search(r"^ai_handoff:\s*$", block, re.MULTILINE)
    ]
    if not matching_blocks:
        add_error(errors, "未找到包含顶层 ai_handoff 的 YAML 代码块")
        return {}
    if len(matching_blocks) > 1:
        add_error(errors, "只能有一个包含 ai_handoff 的 YAML 代码块")
        return {}

    try:
        parsed = yaml.safe_load(matching_blocks[0])
    except yaml.YAMLError as exc:
        add_error(errors, f"AI 交接 YAML 无法解析：{exc}")
        return {}

    root = require_dict(parsed, "YAML 顶层", errors)
    return require_dict(root.get("ai_handoff"), "ai_handoff", errors)


def extract_frontmatter(text: str, errors: list[str]) -> dict[str, Any]:
    match = FRONTMATTER_RE.search(text)
    if not match:
        add_error(errors, "文件开头缺少 YAML frontmatter")
        return {}
    try:
        parsed = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        add_error(errors, f"YAML frontmatter 无法解析：{exc}")
        return {}
    return require_dict(parsed, "YAML frontmatter", errors)


def validate_id_list(
    handoff: dict[str, Any], key: str, registry: dict[str, Any], errors: list[str]
) -> list[str]:
    values = require_list(handoff.get(key), f"ai_handoff.{key}", errors)
    valid_values: list[str] = []
    for value in values:
        if not isinstance(value, str) or not CLAIM_ID_RE.fullmatch(value):
            add_error(errors, f"ai_handoff.{key} 含非法声明 ID：{value!r}")
            continue
        if value not in registry:
            add_error(errors, f"ai_handoff.{key} 引用了不存在的声明：{value}")
        valid_values.append(value)
    if len(valid_values) != len(set(valid_values)):
        add_error(errors, f"ai_handoff.{key} 含重复声明 ID")
    return valid_values


def validate_reference_ids(
    values: Any, path: str, registry: dict[str, Any], errors: list[str]
) -> list[str]:
    ids = require_list(values, path, errors)
    result: list[str] = []
    for claim_id in ids:
        if not isinstance(claim_id, str) or not CLAIM_ID_RE.fullmatch(claim_id):
            add_error(errors, f"{path} 含非法声明 ID：{claim_id!r}")
            continue
        if claim_id not in registry:
            add_error(errors, f"{path} 引用了不存在的声明：{claim_id}")
        result.append(claim_id)
    return result


def validate_registry(handoff: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    registry = require_dict(handoff.get("claim_registry"), "ai_handoff.claim_registry", errors)
    if not registry:
        add_error(errors, "ai_handoff.claim_registry 至少需要一条声明")
        return registry

    required_fields = {
        "text",
        "evidence_status",
        "availability_status",
        "usage_level",
        "source",
        "evidence",
        "limits",
    }
    for claim_id, raw_claim in registry.items():
        if not isinstance(claim_id, str) or not CLAIM_ID_RE.fullmatch(claim_id):
            add_error(errors, f"claim_registry 含非法声明 ID：{claim_id!r}")
            continue
        claim = require_dict(raw_claim, f"claim_registry.{claim_id}", errors)
        missing = sorted(required_fields - set(claim))
        if missing:
            add_error(errors, f"claim_registry.{claim_id} 缺少字段：{', '.join(missing)}")
        if claim.get("evidence_status") not in EVIDENCE_STATUSES:
            add_error(errors, f"{claim_id}.evidence_status 非法：{claim.get('evidence_status')!r}")
        if claim.get("availability_status") not in AVAILABILITY_STATUSES:
            add_error(errors, f"{claim_id}.availability_status 非法：{claim.get('availability_status')!r}")
        if claim.get("usage_level") not in USAGE_LEVELS:
            add_error(errors, f"{claim_id}.usage_level 非法：{claim.get('usage_level')!r}")
        for text_key in ("text", "source", "evidence", "limits"):
            if not isinstance(claim.get(text_key), str) or not claim.get(text_key, "").strip():
                add_error(errors, f"claim_registry.{claim_id}.{text_key} 必须是非空字符串")
    return registry


def validate_claim_lists(
    handoff: dict[str, Any], registry: dict[str, Any], errors: list[str]
) -> tuple[set[str], set[str], set[str]]:
    direct_ids = validate_id_list(handoff, "direct_claim_ids", registry, errors)
    test_ids = validate_id_list(handoff, "test_only_claim_ids", registry, errors)
    prohibited_ids = validate_id_list(handoff, "prohibited_claim_ids", registry, errors)

    list_sets = [set(direct_ids), set(test_ids), set(prohibited_ids)]
    if list_sets[0] & list_sets[1] or list_sets[0] & list_sets[2] or list_sets[1] & list_sets[2]:
        add_error(errors, "同一声明 ID 不得同时出现在两个使用清单中")

    expected_usage = {
        **{claim_id: "direct" for claim_id in direct_ids},
        **{claim_id: "test_only" for claim_id in test_ids},
        **{claim_id: "prohibited" for claim_id in prohibited_ids},
    }
    for claim_id, raw_claim in registry.items():
        if not isinstance(raw_claim, dict):
            continue
        usage = raw_claim.get("usage_level")
        if claim_id not in expected_usage:
            add_error(errors, f"{claim_id} 未进入与 usage_level 对应的使用清单")
            continue
        if expected_usage[claim_id] != usage:
            add_error(errors, f"{claim_id} 的 usage_level 与所在使用清单不一致")

    for claim_id in direct_ids:
        claim = registry.get(claim_id, {})
        if not isinstance(claim, dict):
            continue
        actual = (
            claim.get("evidence_status"),
            claim.get("availability_status"),
            claim.get("usage_level"),
        )
        if actual != ("confirmed", "existing", "direct"):
            add_error(errors, f"{claim_id} 不满足 confirmed + existing + direct，不能直接使用")
        if str(claim.get("source", "")).strip().lower() in {"unknown", "未知", "无"}:
            add_error(errors, f"{claim_id} 是直接声明，但 source 未提供可追溯来源")
        if str(claim.get("evidence", "")).strip().lower() in {"unknown", "未知", "无"}:
            add_error(errors, f"{claim_id} 是直接声明，但 evidence 未提供具体依据")
        claim_text = str(claim.get("text", ""))
        for pattern in BLOCKED_DIRECT_PATTERNS:
            if re.search(pattern, claim_text, re.IGNORECASE):
                add_error(errors, f"{claim_id} 含需要独立合规审核的高风险直接声明：{claim_text}")
                break
    return set(direct_ids), set(test_ids), set(prohibited_ids)


def validate_selling_points(
    handoff: dict[str, Any], registry: dict[str, Any], direct_ids: set[str], errors: list[str]
) -> None:
    core = require_dict(handoff.get("core_selling_point"), "ai_handoff.core_selling_point", errors)
    core_status = core.get("status")
    if core_status not in CORE_STATUSES:
        add_error(errors, f"core_selling_point.status 非法：{core_status!r}")
    core_ids = validate_reference_ids(core.get("claim_ids"), "core_selling_point.claim_ids", registry, errors)
    if core_status == "formal" and not core_ids:
        add_error(errors, "formal 核心卖点至少需要一个声明 ID")
    if core_status == "formal" and not set(core_ids).issubset(direct_ids):
        add_error(errors, "formal 核心卖点只能引用 direct_claim_ids")
    if not isinstance(core.get("text"), str) or not core.get("text", "").strip():
        add_error(errors, "core_selling_point.text 必须是非空字符串")
    required_evidence = core.get("required_evidence")
    if not isinstance(required_evidence, list):
        add_error(errors, "core_selling_point.required_evidence 必须是列表")

    supports = require_list(handoff.get("supporting_points"), "ai_handoff.supporting_points", errors)
    if len(supports) > 3:
        add_error(errors, "supporting_points 最多三条")
    for index, item in enumerate(supports):
        point = require_dict(item, f"supporting_points[{index}]", errors)
        if point.get("status") not in SUPPORT_STATUSES:
            add_error(errors, f"supporting_points[{index}].status 非法：{point.get('status')!r}")
        point_ids = validate_reference_ids(
            point.get("claim_ids"), f"supporting_points[{index}].claim_ids", registry, errors
        )
        if point.get("status") == "formal" and not set(point_ids).issubset(direct_ids):
            add_error(errors, f"supporting_points[{index}] 为 formal 时只能引用 direct_claim_ids")


def validate_consumers(
    handoff: dict[str, Any],
    registry: dict[str, Any],
    direct_ids: set[str],
    errors: list[str],
) -> None:
    sku_roles = require_list(handoff.get("sku_roles"), "ai_handoff.sku_roles", errors)
    for index, item in enumerate(sku_roles):
        role = require_dict(item, f"sku_roles[{index}]", errors)
        if role.get("status") not in SKU_STATUSES:
            add_error(errors, f"sku_roles[{index}].status 非法：{role.get('status')!r}")
        validate_reference_ids(role.get("claim_ids"), f"sku_roles[{index}].claim_ids", registry, errors)

    faq_inputs = require_list(handoff.get("faq_inputs"), "ai_handoff.faq_inputs", errors)
    for index, item in enumerate(faq_inputs):
        faq = require_dict(item, f"faq_inputs[{index}]", errors)
        faq_ids = validate_reference_ids(
            faq.get("claim_ids"), f"faq_inputs[{index}].claim_ids", registry, errors
        )
        answer_status = faq.get("answer_status")
        if answer_status not in FAQ_STATUSES:
            add_error(errors, f"faq_inputs[{index}].answer_status 非法：{answer_status!r}")
        if answer_status == "confirmed" and not set(faq_ids).issubset(direct_ids):
            add_error(errors, f"faq_inputs[{index}] 为 confirmed 时只能引用 direct_claim_ids")
        for key in ("question", "answer_scope", "unresolved"):
            if not isinstance(faq.get(key), str) or not faq.get(key, "").strip():
                add_error(errors, f"faq_inputs[{index}].{key} 必须是非空字符串")
        answer_scope = str(faq.get("answer_scope", ""))
        if answer_status in {"limited", "unavailable"} and not re.search(
            r"当前|目前|只能|不能|尚未|未提供|没有", answer_scope
        ):
            add_error(errors, f"faq_inputs[{index}].answer_scope 必须明确当前限制")
        for pattern in UNVERIFIED_PROMISE_PATTERNS:
            if re.search(pattern, answer_scope):
                add_error(errors, f"faq_inputs[{index}] 承诺了待补证明或计划能力")
                break


def require_nonempty_string(
    mapping: dict[str, Any], key: str, path: str, errors: list[str]
) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        add_error(errors, f"{path}.{key} 必须是非空字符串")
        return ""
    return value


def validate_iteration(
    handoff: dict[str, Any], registry: dict[str, Any], text: str, errors: list[str]
) -> int:
    iteration = require_dict(handoff.get("iteration"), "ai_handoff.iteration", errors)
    if not iteration:
        return 0

    if iteration.get("current_stage") not in ITERATION_STAGES:
        add_error(errors, f"iteration.current_stage 非法：{iteration.get('current_stage')!r}")
    require_nonempty_string(iteration, "current_round_goal", "iteration", errors)

    current_test = require_dict(
        iteration.get("current_round_test"), "iteration.current_round_test", errors
    )
    for key in ("selling_point", "audience", "scene", "expected_action"):
        require_nonempty_string(current_test, key, "iteration.current_round_test", errors)
    controlled = require_list(
        current_test.get("controlled_variables"),
        "iteration.current_round_test.controlled_variables",
        errors,
    )
    if not [item for item in controlled if isinstance(item, str) and item.strip()]:
        add_error(errors, "iteration.current_round_test.controlled_variables 不得为空")

    gaps = require_list(iteration.get("evidence_gaps"), "iteration.evidence_gaps", errors)
    seen_gap_ids: set[str] = set()
    required_gap_strings = {
        "question",
        "minimum_evidence",
        "collection_action",
        "responsible_role",
        "completion_rule",
        "updates",
    }
    for index, item in enumerate(gaps):
        gap = require_dict(item, f"iteration.evidence_gaps[{index}]", errors)
        gap_id = gap.get("gap_id")
        if not isinstance(gap_id, str) or not GAP_ID_RE.fullmatch(gap_id):
            add_error(errors, f"iteration.evidence_gaps[{index}].gap_id 非法：{gap_id!r}")
        elif gap_id in seen_gap_ids:
            add_error(errors, f"iteration.evidence_gaps 含重复 gap_id：{gap_id}")
        else:
            seen_gap_ids.add(gap_id)
        if gap.get("evidence_type") not in GAP_TYPES:
            add_error(errors, f"{gap_id or index}.evidence_type 非法：{gap.get('evidence_type')!r}")
        if gap.get("status") not in GAP_STATUSES:
            add_error(errors, f"{gap_id or index}.status 非法：{gap.get('status')!r}")
        if gap.get("priority") not in GAP_PRIORITIES:
            add_error(errors, f"{gap_id or index}.priority 非法：{gap.get('priority')!r}")
        validate_reference_ids(
            gap.get("claim_ids"), f"iteration.evidence_gaps[{index}].claim_ids", registry, errors
        )
        for key in required_gap_strings:
            require_nonempty_string(gap, key, f"iteration.evidence_gaps[{index}]", errors)

    if iteration.get("current_stage") != "validated" and not gaps:
        add_error(errors, "尚未 validated 的报告至少需要一个 evidence_gap")

    seventh_start = text.find(REQUIRED_QUESTIONS[6])
    eighth_start = text.find(REQUIRED_QUESTIONS[7], seventh_start + 1) if seventh_start >= 0 else -1
    if seventh_start >= 0 and eighth_start >= 0:
        human_gap_ids = expand_gap_ids(text[seventh_start:eighth_start])
        missing_in_yaml = human_gap_ids - seen_gap_ids
        missing_in_human = seen_gap_ids - human_gap_ids
        if missing_in_yaml:
            add_error(errors, f"第七问引用了 iteration 中不存在的缺口：{', '.join(sorted(missing_in_yaml))}")
        if missing_in_human:
            add_error(errors, f"iteration 缺口未出现在第七问行动板：{', '.join(sorted(missing_in_human))}")

    result = require_dict(
        iteration.get("last_round_result"), "iteration.last_round_result", errors
    )
    round_status = result.get("status")
    round_decision = result.get("decision")
    if round_status not in ROUND_STATUSES:
        add_error(errors, f"iteration.last_round_result.status 非法：{round_status!r}")
    if round_decision not in ROUND_DECISIONS:
        add_error(errors, f"iteration.last_round_result.decision 非法：{round_decision!r}")
    if round_status == "not_started" and round_decision != "pending":
        add_error(errors, "last_round_result 为 not_started 时 decision 必须为 pending")
    require_nonempty_string(result, "evidence_summary", "iteration.last_round_result", errors)

    for key in ("next_version_triggers", "next_version_inputs"):
        values = require_list(iteration.get(key), f"iteration.{key}", errors)
        if not [value for value in values if isinstance(value, str) and value.strip()]:
            add_error(errors, f"iteration.{key} 不得为空")
    return len(gaps)


def validate_metadata(handoff: dict[str, Any], errors: list[str]) -> None:
    if handoff.get("schema_version") != "2.1":
        add_error(errors, "ai_handoff.schema_version 必须为字符串 \"2.1\"")
    if handoff.get("card_status") not in CARD_STATUSES:
        add_error(errors, f"ai_handoff.card_status 非法：{handoff.get('card_status')!r}")
    if not isinstance(handoff.get("product"), str) or not handoff.get("product", "").strip():
        add_error(errors, "ai_handoff.product 必须是非空字符串")
    sources = require_list(handoff.get("source_files"), "ai_handoff.source_files", errors)
    valid_sources = [source for source in sources if isinstance(source, str) and source.strip()]
    if len(valid_sources) < 2:
        add_error(errors, "ai_handoff.source_files 至少需要上游用户假设和产品事实两个来源")


def validate_frontmatter(
    frontmatter: dict[str, Any], handoff: dict[str, Any], errors: list[str]
) -> None:
    if not frontmatter:
        return
    if frontmatter.get("card_type") != "产品卖点分析报告":
        add_error(errors, "frontmatter.card_type 必须为“产品卖点分析报告”")
    title = frontmatter.get("title")
    if not isinstance(title, str) or not title.endswith("产品卖点分析报告"):
        add_error(errors, "frontmatter.title 必须以“产品卖点分析报告”结尾")
    if str(frontmatter.get("template_version")) != "2.1":
        add_error(errors, "frontmatter.template_version 必须为字符串 \"2.1\"")
    if frontmatter.get("status") not in CARD_STATUSES:
        add_error(errors, f"frontmatter.status 非法：{frontmatter.get('status')!r}")
    if handoff and frontmatter.get("status") != handoff.get("card_status"):
        add_error(errors, "frontmatter.status 必须与 ai_handoff.card_status 一致")
    version = frontmatter.get("version")
    if not isinstance(version, str) or not re.fullmatch(r"v[1-9]\d*", version):
        add_error(errors, "frontmatter.version 必须使用 v1、v2 等格式")
    if frontmatter.get("evidence_level") not in {"low", "medium", "high"}:
        add_error(errors, f"frontmatter.evidence_level 非法：{frontmatter.get('evidence_level')!r}")


def validate_status_consistency(handoff: dict[str, Any], errors: list[str]) -> None:
    core = handoff.get("core_selling_point")
    if not isinstance(core, dict):
        return
    if handoff.get("card_status") == "validated" and core.get("status") != "formal":
        add_error(errors, "validated 卡片必须具有 formal 核心卖点")
    iteration = handoff.get("iteration")
    if (
        handoff.get("card_status") == "validated"
        and isinstance(iteration, dict)
        and iteration.get("current_stage") != "validated"
    ):
        add_error(errors, "validated 报告的 iteration.current_stage 必须为 validated")


def validate_all_markdown_ids(text: str, registry: dict[str, Any], errors: list[str]) -> None:
    markdown_ids = set(re.findall(r"\bC\d{3}\b", text))
    missing = sorted(markdown_ids - set(registry))
    if missing:
        add_error(errors, f"正文或附录引用了 claim_registry 中不存在的声明：{', '.join(missing)}")


def validate_claim_appendix(text: str, registry: dict[str, Any], errors: list[str]) -> None:
    start = text.find("## B、每条产品声明的依据在哪里？")
    end = text.find("## C、哪些候选被放弃了，为什么？", start + 1) if start >= 0 else -1
    if start < 0 or end < 0:
        add_error(errors, "证据附录必须包含完整的 B、C 两个问题模块")
        return

    appendix_ids = expand_claim_ids(text[start:end])
    registry_ids = set(registry)
    missing = sorted(registry_ids - appendix_ids)
    extra = sorted(appendix_ids - registry_ids)
    if missing:
        add_error(errors, f"附录 B 未呈现 claim_registry 中的声明：{', '.join(missing)}")
    if extra:
        add_error(errors, f"附录 B 含 claim_registry 中不存在的声明：{', '.join(extra)}")


def main() -> int:
    args = parse_args()
    errors: list[str] = []
    gaps_count = 0

    if not args.card.is_file():
        print(f"ERROR: 文件不存在：{args.card}", file=sys.stderr)
        return 2
    try:
        text = args.card.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        print(f"ERROR: 无法读取文件：{exc}", file=sys.stderr)
        return 2

    validate_question_structure(text, errors)
    validate_candidate_count(text, errors)
    frontmatter = extract_frontmatter(text, errors)
    handoff = extract_handoff(text, errors)
    if handoff:
        validate_metadata(handoff, errors)
        validate_frontmatter(frontmatter, handoff, errors)
        registry = validate_registry(handoff, errors)
        direct_ids, test_ids, prohibited_ids = validate_claim_lists(handoff, registry, errors)
        validate_selling_points(handoff, registry, direct_ids, errors)
        validate_consumers(handoff, registry, direct_ids, errors)
        gaps_count = validate_iteration(handoff, registry, text, errors)
        validate_status_consistency(handoff, errors)
        validate_all_markdown_ids(text, registry, errors)
        validate_claim_appendix(text, registry, errors)
        validate_human_usage_sections(text, direct_ids, test_ids, prohibited_ids, errors)
        validate_human_faq(text, direct_ids, errors)
        validate_human_sku_table(text, errors)

    if errors:
        print(f"FAIL: {args.card}")
        for index, error in enumerate(errors, start=1):
            print(f"{index}. {error}")
        return 1

    registry = handoff.get("claim_registry", {})
    print(
        f"OK: {args.card} | schema=2.1 | claims={len(registry)} | gaps={gaps_count} "
        f"| direct={len(handoff.get('direct_claim_ids', []))} "
        f"| test_only={len(handoff.get('test_only_claim_ids', []))} "
        f"| prohibited={len(handoff.get('prohibited_claim_ids', []))}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
