# 完全小白使用教程

你不需要学 Git、不需要找 ZIP，也不需要知道 Skill 应该放在哪个文件夹。只要电脑上已经能使用 Codex，就把仓库链接和包名交给它。

## 安装

1. 打开 Codex，新建任务。
2. 复制下面整句话并发送：

   > 请从 https://github.com/NewbieCheng/company-skills-marketplace 安装 `social-media-hotspot-brief`，按 catalog.json 检查我的系统和依赖；缺少组件时汇总让我确认一次，然后自动安装并验证。不要让我安装 Git 或手工解压。

3. 如果 Codex 列出缺失组件和安装命令，确认来源无误后只需同意一次。
4. 看到“安装完成”后，新建一个 Codex 任务，再说：

   > 使用 `$hotspot-brief-public` 研究今天与我的业务相关的热点，先问我需要的业务范围。

公开仓库会被直接下载。GitHub 内部可能使用压缩传输，但下载、展开和放置目录都由 Codex 完成，用户不需要操作压缩包。

## Windows 和 macOS

- Windows 默认安装位置通常是 `%USERPROFILE%\.codex\skills\<skill-name>`。
- macOS 默认安装位置通常是 `~/.codex/skills/<skill-name>`。
- 不要手工创建这些目录；让 `$skill-installer` 处理。
- 包如果只支持某个系统，Codex 会根据 `catalog.json` 停止不兼容安装。

## 更新

把下面这句话交给 Codex：

> 请从 https://github.com/NewbieCheng/company-skills-marketplace 更新 `social-media-hotspot-brief`。先备份我本地同名 Skill，再安装最新版并验证；完成后告诉我是否需要新开任务。

官方安装器遇到已存在目录时会中止，以防覆盖个人修改。更新时应先让 Codex备份或在用户确认后移走旧目录，再重新安装。

## 卸载

把下面这句话交给 Codex：

> 请卸载 `hotspot-brief-public`。先确认实际安装目录，只删除这个 Skill，不要删除整个 `.codex` 目录；完成后告诉我如何恢复。

如果是 Marketplace Plugin，则使用：

```text
codex plugin remove social-media-hotspot-brief@newbiecheng-team
```

## 常见问题

### 安装后找不到

新安装的 Skill 通常在下一轮任务中出现。先新开任务；仍未出现再重启 Codex，并让 Codex检查 Skill 目录和 `SKILL.md`。

### 提示同名目录已经存在

不要强制覆盖。让 Codex 比较现有版本，备份后再更新，或者保留现有版本。

### 下载超时或打不开 GitHub

让 Codex重试公开下载并检查 `github.com`、`codeload.github.com` 是否可访问。网络仍不可用时停止，不要改用来源不明的网盘包。

### 缺少 Python、Node 或其他组件

Codex 会根据 `catalog.json` 运行检测命令，汇总需要安装的组件、来源和系统改动。你确认一次后，它才执行安装和验证。不要同意无法识别来源的命令。

### 公司私有包

本仓库是公开仓库，不需要 GitHub 登录。未来如果某个包迁移到私有仓库，用户必须先完成 GitHub 身份认证，否则无法下载。
