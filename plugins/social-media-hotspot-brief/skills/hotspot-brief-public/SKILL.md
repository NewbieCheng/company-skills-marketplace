---
name: hotspot-brief-public
description: Research current public web and social-media trends, preserve traceable sources and public metrics, and produce Markdown and structured JSON briefs with content ideas. Use for daily or weekly hotspot reports, keyword trend research, public-source monitoring, content planning, and evidence-based topic selection when private services are unavailable or unnecessary.
---

# 公开热点简报与选题

## 工作流

1. 收集业务 Profile、允许来源、地域、关键词、排除词、时间范围、结果数量和排序偏好。缺少会改变结果的字段时，先列出缺口并询问；不要自行扩大范围。
2. 使用当前可用的公开网页搜索或浏览工具进行实时研究。优先使用原始发布页、平台公开榜单、官方公告和可信媒体；不要绕过登录、验证码、付费墙或访问限制。
3. 先按来源、地域、关键词、排除词和时间过滤，再根据用户指定规则排序。没有指定排序时，综合相关性、时效性和可核验公开热度。
4. 为每个候选保存标题、来源、公开链接、发布时间、采集时间、可见互动指标、排序依据和失败或回退说明。
5. 按 [references/report-schema.md](references/report-schema.md) 同时输出 Markdown 和 JSON。所有内容建议默认标记为 `pending_review`，不得自动发布或修改排期。

## 证据边界

- 不得根据旧知识补写“今日热点”，也不得捏造链接、作者、时间、指标或引用。
- 没有公开指标时填 `null` 或“暂无公开数据”，不要用估算值伪装真实数据。
- 来源失败时记录具体原因；结果不足时展示实际数量，只有用户明确允许时才扩大时间窗口或来源范围。
- 区分事实、来源观点和基于证据的推断。推断必须明确标注。
- 涉及人物隐私、敏感事件或未经证实指控时，降低传播性表述并优先引用权威来源。

## 完成检查

- 每个入选热点都有可访问的公开链接或明确的失败说明。
- 时间范围、地域、来源范围和排序回退在报告开头可见。
- Markdown 与 JSON 的核心项目数量和标识一致。
- 内容机会与预测不冒充已发生事实。
