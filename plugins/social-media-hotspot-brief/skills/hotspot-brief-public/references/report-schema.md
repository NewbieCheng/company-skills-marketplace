# 热点报告结构

## 输入摘要

记录业务 Profile、允许来源、地域、关键词、排除词、时间范围、数量、排序方式和失败回退。未提供但不会阻塞研究的字段写为 `null`；会实质改变结果的缺口应先询问用户。

## Markdown 顺序

1. 配置摘要
2. 来源执行状态
3. Top 热点
4. 热门关键词与共性规律
5. 内容机会
6. 待持续关注
7. 明日或下周期预测
8. 待审核说明

每条热点至少包含：标题、来源、URL、发布时间、采集时间、公开指标、摘要、排序依据、引用和 `pending_review` 状态。

## JSON 结构

顶层字段：

- `reportMeta`: 配置、生成时间、实际时间范围和回退说明。
- `sourceRuns`: 每个来源的状态、结果数和失败原因。
- `hotspots`: 入选热点。
- `excludedHotspots`: 被排除项目及原因。

每条 `hotspots` 至少包含：

- `id`
- `title`
- `sourceId`
- `url`
- `publishedAt`
- `collectedAt`
- `publicMetrics`
- `rankingBasis`
- `summary`
- `pendingReview`

无法证实的互动指标填 `null`。`pendingReview` 固定为 `true`，除非用户在当前任务中明确完成了人工审核。

## 质量规则

- 先过滤，再评分。
- 使用绝对时间，避免只写“今天”“昨天”。
- 不得捏造或补齐缺失证据。
- 预测和建议必须与事实分区展示。
- 来源失败或结果不足必须如实呈现。
