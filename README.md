# NewbieCheng Team Skills Marketplace

这是一个给普通用户和公司同事使用的 Codex Skills 仓库。仓库保存的是已经展开的文件夹；最终用户不需要安装 Git，也不需要下载或解压 ZIP。

## 30 秒安装

把下面整句话复制给 Codex：

> 请从 https://github.com/NewbieCheng/company-skills-marketplace 安装 `social-media-hotspot-brief`，按 catalog.json 检查我的系统和依赖；缺少组件时汇总让我确认一次，然后自动安装并验证。不要让我安装 Git 或手工解压。

Codex 会读取 [`catalog.json`](catalog.json)，找到对应 Skill 路径，并使用内置 `$skill-installer` 从公开 GitHub 仓库直接下载。安装完成后请新开一个任务；新 Skill 会在下一轮可用。

## 当前可安装包

| 包名 | 项目 | 功能 | 系统依赖 |
| --- | --- | --- | --- |
| `social-media-hotspot-brief` | 社媒 | 研究当前公开热点并生成带来源的 Markdown 与 JSON 简报 | 无 |

“九江”已经注册为项目分类。以后九江项目的包使用 `jiujiang-能力名`，例如 `jiujiang-report-builder`，界面显示“九江 · 报告生成”。插件目录保持扁平，不创建 `plugins/九江/...` 多层结构。

## 两种分发方式

### 无 Git 安装单个 Skill（推荐给小白）

只需把仓库链接和包名交给 Codex。公开仓库由 `$skill-installer` 直接下载；用户无需 GitHub 登录、Git 或压缩软件。

### 安装 Plugin Marketplace（进阶）

```text
codex plugin marketplace add NewbieCheng/company-skills-marketplace
codex plugin add social-media-hotspot-brief@newbiecheng-team
```

Marketplace 适合在 Codex 插件目录里浏览和整包安装。如果机器没有 Git 或该命令失败，改用上面的“一句话安装”。

## 教程

- [完全小白安装、更新和卸载](docs/USER_GUIDE.md)
- [管理员建包、邀请成员和回滚](docs/ADMIN_GUIDE.md)
- [公司同事上传 Skill](CONTRIBUTING.md)
- [安全与信任说明](SECURITY.md)

## 目录规则

```text
.agents/plugins/marketplace.json       Codex Marketplace 目录
catalog.json                           给 Codex 读取的包、项目、系统和依赖清单
plugins/<项目>-<能力>/                 可安装 Plugin
  .codex-plugin/plugin.json            Plugin 清单
  skills/<skill-name>/SKILL.md         实际 Skill
schemas/catalog.schema.json            catalog.json 结构定义
scripts/validate_repository.py         本地和 CI 校验器
```

## 信任模式

本仓库按团队决定允许受邀协作者直接推送 `main`，不强制 PR 审核，也不限制依赖安装命令。安装任何会修改系统的依赖前，Codex 必须展示全部命令并只向用户请求一次确认。请只邀请可信任的公司成员。

## License

[MIT](LICENSE) © 2026 NewbieCheng Team
