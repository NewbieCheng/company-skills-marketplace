# 航哥朋友圈运行配置

所有路径均相对于当前项目根目录。不得把 Mac 或 Windows 的外层绝对路径写进 Skill。

```yaml
knowledgeBaseRoot: 九江双蒸知识库v1.0

output:
  directory: 一、私域库/07_朋友圈分发库
  allowDirectWrite: true
  showBodyInChat: false
  allowOverwrite: false

history:
  directory: 一、私域库/07_朋友圈分发库
  recentDays: 30
  recentWeeklyFiles: 4
  keywordSearchAllHistory: true

cadence:
  defaultPostsPerDay: 3
  defaultDays: 7
  defaultTotalPosts: 21
  allowCustomCadence: true

sources:
  productLibrary: 一、私域库/01_产品库
  userHypothesisLibrary: 一、私域库/01_产品库/01.1_用户假设卡
  sellingPointLibrary: 一、私域库/01_产品库/01.2_产品卖点卡
  caseLibrary: 一、私域库/03_用户案例库
  faqLibrary: 一、私域库/04_用户 FAQ
  activityLibrary: 一、私域库/05_活动方案库
  weeklyReports: 三、经营管理/02_经营数据库/02.1_经营周报
  complianceLibrary: 三、经营管理/01_内容合规库
```

## 路径解析

1. 以当前项目根目录为起点解析 `knowledgeBaseRoot`；
2. 只读取配置列出的知识库目录和用户在当前任务额外授权的文件；
3. 不扫描整个 Obsidian；
4. 路径不存在时列出失效的相对路径，不猜测新位置；
5. 输出目录不存在时停止，不自行改到其他目录。

## 文件命名

周成果：

```text
YYYY-MM-DD至YYYY-MM-DD_航哥一周朋友圈内容.md
```

单条成果：

```text
YYYY-MM-DD_航哥朋友圈_主题.md
```

同名文件存在时：

```text
原文件名_v2.md
原文件名_v3.md
```

禁止覆盖或修改历史文件。用户明确要求修订某份历史成果时，也创建下一版本。

## 直接写入

运行配置已经授权在成功完成检查后直接新建成果文件，无需在对话中预览正文。

成功后对话只返回：

- 保存路径；
- 规划周期；
- 总条数；
- 可直接发布条数；
- 待确认或待补素材条数。

信息不足或冲突时不写文件，只返回最小缺口。

## 来源优先级

1. 用户在当前任务中的明确确认；
2. 当前周期最新经营周报；
3. 最新正式产品、活动、价格、库存和会员资料；
4. 最新产品卖点报告；
5. 原始图片、反馈、订单、FAQ 和现场记录；
6. Skill 内置 Profile、Style 和 Business；
7. Skill 内置表达样本；
8. 历史朋友圈；
9. 模型常识只能帮助表达，不能补客户事实。

冲突处理：

- 产品正式资料优先于卖点报告；
- 当前用户确认优先于历史周报；
- Profile 决定身份，Style 和样本决定表达；
- 样本不能覆盖当前事实；
- 未确认的用户假设不得写成客户事实；
- 价格、活动、库存和会员权益冲突时停止相关成果写入。

