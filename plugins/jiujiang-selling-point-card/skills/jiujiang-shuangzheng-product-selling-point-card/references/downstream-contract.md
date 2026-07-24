# 产品卖点分析报告下游交接契约 v2.1

## 目的

本契约让下游 AI 稳定识别三件事：什么可以直接使用、什么只能测试、下一轮需要补什么证据以及何时生成新版本。它不替代事实核验、实际投放、数据采集或正式合规审核。

人类决策层负责理解与行动；证据附录负责追溯；文末 `ai_handoff` YAML 是唯一机器交接入口。

## 声明状态

每条声明使用唯一 ID，格式为 `C001`、`C002`……。

### `evidence_status`

- `confirmed`：有可追溯证据直接支持；
- `inferred`：由现有信息推断；
- `unknown`：缺少信息；
- `conflict`：来源相互矛盾。

### `availability_status`

- `existing`：当前已存在且可兑现；
- `planned`：已计划但尚未交付；
- `absent`：当前明确不存在；
- `unknown`：无法确认。

### `usage_level`

- `direct`：可在声明原有语境和限制内直接调用；
- `test_only`：只可内部讨论或小范围验证；
- `prohibited`：不得用于对外内容或确定性回答。

只有 `confirmed + existing + direct` 的声明才能进入 `direct_claim_ids`。`planned`、`inferred`、`unknown`、`conflict` 永远不能进入直接清单。一个声明 ID 不得同时出现在两个使用清单中。

## 卡片与迭代状态

### `card_status`

- `pending_validation`：正式核心卖点尚未成立；
- `limited_use`：部分事实可直接使用，但核心差异或用户反应仍待验证；
- `validated`：真实行为证据支持核心卖点，关键声明可追溯。

### `iteration.current_stage`

- `evidence_collection`：补产品证明、用户证据或交付能力；
- `small_test`：小范围执行一个卖点假设；
- `scale_validation`：方向初步成立，扩大验证；
- `validated`：当前主轴已有足够真实证据支持。

### `last_round_result`

- `status`：`not_started`、`in_progress`、`completed`；
- `decision`：`pending`、`continue`、`adjust`、`switch`、`stop`。

首次报告通常使用 `not_started + pending`。能力交付完成但没有行为证据时，只更新可用性，不得把卖点价值升级为已验证。

## 证据缺口

每条缺口使用唯一 ID `G001`、`G002`……。

### `evidence_type`

- `product_proof`：产品事实证明；
- `user_evidence`：用户任务、阻力或语言证据；
- `behavior_evidence`：咨询、购买、复购、退款或推荐行为；
- `capability_delivery`：教程、服务或其他交付能力；
- `compliance`：正式审核和发布边界。

### `status`

- `open`：尚未开始；
- `in_progress`：正在补充；
- `complete`：已达到本条完成标准；
- `blocked`：当前无法获得或存在外部阻塞。

### `priority`

- `blocking`：不补就不能对外说或不能继续当前主轴；
- `decision`：决定继续、调整或换方向；
- `optimization`：只影响表达、效率或放大方式。

完成 `product_proof` 不等于完成 `user_evidence`；完成 `capability_delivery` 不等于完成 `behavior_evidence`。不同类型不能互相升级。

## YAML 结构

文末只保留一个包含顶层键 `ai_handoff` 的 YAML 代码块。完整结构以 [product-card-template.md](product-card-template.md) 的示例为准，必须包含：

- `schema_version: "2.1"`；
- 三份声明使用清单和 `claim_registry`；
- `core_selling_point`、`supporting_points`、`sku_roles`、`faq_inputs`；
- `iteration.current_stage`、`current_round_goal`、`current_round_test`；
- `iteration.evidence_gaps`；
- `iteration.last_round_result`；
- `iteration.next_version_triggers` 和 `next_version_inputs`；
- `source_files`。

## 字段约束

- 文件 frontmatter 的 `card_type` 固定为 `产品卖点分析报告`；
- `template_version` 固定为字符串 `"2.1"`，`status` 与 `ai_handoff.card_status` 一致；
- 产品报告版本使用 `v1`、`v2`……，证据等级使用 `low`、`medium`、`high`；
- `schema_version` 固定为字符串 `"2.1"`；
- `claim_registry` 是机器交接的声明事实源，其他字段只引用声明 ID；
- 附录 B 必须与 `claim_registry` 完整对齐，逐条呈现全部声明；
- 候选资格闸门至少包含五个去重后的真实候选，禁止以重复行凑数；
- 直接声明的 `source` 和 `evidence` 不能写 `unknown`；
- `core_selling_point.status` 只能为 `formal`、`hypothesis`、`unavailable`；
- `formal` 核心卖点引用的所有 ID 必须位于 `direct_claim_ids`；
- `supporting_points.status` 只能为 `formal` 或 `hypothesis`；
- `sku_roles.status` 只能为 `confirmed`、`inferred`、`unknown`；
- SKU 名称中的产地、年份和工艺不能因为标称而升级为已确认属性；
- `faq_inputs.answer_status` 只能为 `confirmed`、`limited`、`unavailable`；
- FAQ 为 `confirmed` 时只能引用直接声明；为 `limited` 或 `unavailable` 时必须明确目前不能确认的部分，不得承诺待补证明和计划能力；
- 每条证据缺口必须引用存在的声明 ID，并包含问题、证据类型、状态、优先级、最低证据、行动、负责人、完成标准和更新对象；
- 正文第七问出现的所有 `G` ID 必须与 `iteration.evidence_gaps` 一致；
- `next_version_triggers` 和 `next_version_inputs` 不得为空；
- `source_files` 至少列出上游用户假设和产品事实来源；没有独立资料时明确写“暂无”，不能伪造第二来源。
- 存在旧版时，frontmatter 的 `previous_report` 和 `source_files` 只允许引用自动发现后唯一选中的最新旧版；其他候选旧报告不得进入交接上下文。

## 下游读取顺序

1. 先读 `card_status` 和 `iteration.current_stage`；
2. 只从 `direct_claim_ids` 获取可直接引用声明；
3. 对照 `claim_registry.limits` 限制使用范围；
4. `test_only_claim_ids` 只能进入内部实验方案；
5. `prohibited_claim_ids` 用于拦截风险表达；
6. 按 `evidence_gaps` 形成补证任务，但不得假装已自动执行；
7. 读取 `last_round_result.decision` 判断继续、调整、换方向或停止；
8. 满足 `next_version_triggers` 后，把 `next_version_inputs` 交回本 Skill；
9. 发布前继续经过对应内容审核和正式合规流程。

## 校验边界

`scripts/validate_card_contract.py` 检查名称、八问结构、至少五个去重候选、附录与声明登记表对齐、枚举、ID 引用、正文使用分区、FAQ 回答状态、证据行动板和版本触发条件。它只检查字段和高风险模式，不判断来源真假、证明强度、卖点是否真的有效，也不替代人工审阅或提供法律意见。
