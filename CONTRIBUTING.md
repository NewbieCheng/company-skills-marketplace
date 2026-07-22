# 上传和贡献 Skills

## 最简单：把文件夹交给 Codex

准备好包含 `SKILL.md` 的完整 Skill 文件夹，然后把下面这句话交给已经获得仓库写权限的 Codex：

> 请把 `<我的Skill文件夹完整路径>` 加入 https://github.com/NewbieCheng/company-skills-marketplace，归类到 `<项目名>`。按仓库 AGENTS.md 创建 Plugin、更新 catalog 和 Marketplace、运行全部校验，然后直接推送 main。不要上传密钥、Cookie、账号数据、构建缓存或 node_modules。

Codex 应完成命名、目录整理、依赖登记、校验、提交和推送。不要把 ZIP 上传到仓库；上传展开后的源文件。

## 通过 GitHub 网页上传

1. 先确认项目 ID，例如 `jiujiang`。
2. 创建目录 `plugins/<project>-<capability>`。
3. 上传 `.codex-plugin/plugin.json` 和完整 `skills/<skill-name>/`。
4. 更新 `catalog.json`。
5. 更新 `.agents/plugins/marketplace.json`。
6. 等待 GitHub Actions 校验结果。

网页上传适合小包。包含大量脚本或资源时，优先让 Codex处理。

## 必须遵守

- 插件、Skill、项目 ID 只使用小写英文、数字和连字符。
- 插件目录必须以项目 ID 开头，例如 `jiujiang-report-builder`。
- `SKILL.md` frontmatter 只能包含 `name` 和 `description`。
- 使用 UTF-8，不能留下 TODO、占位内容或无用说明文件。
- 不上传密码、Token、Cookie、私钥、客户数据或内部访问地址。
- 不上传 `node_modules`、构建产物、日志或无关项目源码。
- 脚本必须支持声明的系统并实际运行验证。
- 系统依赖必须在 `catalog.json` 明确声明检测、安装和验证命令。
- 插件版本必须与 `catalog.json` 相同。

## 直接推送责任

本仓库允许受邀成员直接推送 `main`，CI 在推送后才运行。推送者必须先在本地执行：

```text
python scripts/validate_repository.py
python -m unittest discover -s tests -v
```

直接推送表示团队信任你的 Skill 指令和安装命令。发现错误后立即通知管理员并创建 revert 提交。
