# 管理员教程

## 仓库信息

- 所有者：`NewbieCheng`
- 仓库：`company-skills-marketplace`
- Marketplace：`newbiecheng-team`
- 发布者：`NewbieCheng Team`
- 主分支：`main`
- 权限模式：受邀协作者可直接推送，不启用强制 PR 审核

## 项目和包如何区分

项目在 `catalog.json` 的 `projects` 中注册，项目 ID 只能使用小写英文、数字和连字符。插件必须放在扁平目录 `plugins/<project>-<capability>`。

九江示例：

```text
项目 ID：jiujiang
插件 ID：jiujiang-report-builder
显示名称：九江 · 报告生成
插件目录：plugins/jiujiang-report-builder
Skill 目录：plugins/jiujiang-report-builder/skills/report-builder
```

## 创建新包

1. 使用官方 `plugin-creator` 在 `plugins/` 下生成插件骨架。
2. 使用官方 `skill-creator` 在插件的 `skills/` 下初始化 Skill。
3. 完成 `SKILL.md`、`agents/openai.yaml` 和必要的 `references/`、`scripts/`、`assets/`。
4. 在 `catalog.json` 添加包信息、支持系统和依赖。
5. 在 `.agents/plugins/marketplace.json` 追加同名插件条目。
6. 运行：

   ```text
   python scripts/validate_repository.py
   python -m unittest discover -s tests -v
   ```

7. 用官方 Skill 安装器安装到临时目录，确认公开下载和目录结构正常。
8. 提交并推送 `main`。

详细命名和质量规则位于根目录 `AGENTS.md`。

## 声明系统依赖

在 `catalog.json` 的包条目中填写 `dependencies`。每个依赖包含：

- `name`：组件名称。
- `purpose`：为什么需要。
- `required`：是否必需。
- `modifiesSystem`：安装是否修改系统。
- `detect`：各系统检测命令。
- `install`：各系统安装命令。
- `verify`：各系统安装后验证命令。

依赖涉及的每个支持系统都必须有完整命令。最终用户执行前，Codex 必须汇总展示并请求一次确认。

## 邀请公司成员

GitHub 没有“任何人点开都成为协作者”的通用邀请链接。管理员需要知道成员的 GitHub 用户名或账号邮箱，然后逐个邀请。

网页操作：

1. 打开仓库。
2. 进入 **Settings → Collaborators**。
3. 选择 **Add people**。
4. 输入 GitHub 用户名或邮箱。
5. 授予 `Write` 权限。

GitHub 会为该账号生成专属邀请，并通过站内通知或邮件发送。对方接受后才能直接推送。

管理员也可以把用户名交给 Codex：

> 请邀请 GitHub 用户 `<用户名>` 成为 `NewbieCheng/company-skills-marketplace` 的协作者，授予 write/push 权限；不要授予 admin 权限。

## 权限调整和移除

在 **Settings → Collaborators** 调整成员权限或移除成员。普通上传者使用 `Write`；只有负责仓库设置、权限和删除操作的人才需要更高权限。

## 版本更新

- 插件和 `catalog.json` 必须使用相同的语义版本，例如 `1.1.0`。
- 修正文案或小错误增加补丁版本。
- 增加向后兼容能力增加次版本。
- 不兼容变化增加主版本。
- 更新后运行全部校验，并从公开 GitHub 地址重新安装测试。

## 回滚错误推送

不要使用强制重置覆盖团队历史。优先在 GitHub 查看错误提交，然后创建一个反向提交：

```text
git revert <错误提交ID>
git push origin main
```

不熟悉 Git 时，把错误提交链接交给 Codex，并明确要求“创建 revert 提交，不要 reset 或 force push”。
