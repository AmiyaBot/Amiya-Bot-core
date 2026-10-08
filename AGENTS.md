# AGENTS.md

`amiyabot` —— Python 异步渐进式聊天机器人框架（QQ 频道/QQ 群/KOOK/Mirai/OneBot 等适配器 + 消息链 + 关键字路由 + 插件系统）。分发名与导入名均为 `amiyabot`。

> **先读 [docs/project-map/README.md](docs/project-map/README.md)，再按任务读相关分册。**
>
> ⚠️ **改公共 API / 适配器 / Chain / 生命周期后，必须同步 SDK 用户文档**（`docs/Amiya-Bot-docs/`，独立 git 子模块）——见下方「代码改动 → SDK 文档同步」。

## 两套文档的分工（别搞混）

| 目录 | 是什么 | 面向谁 | 是否子模块 |
|---|---|---|---|
| `docs/project-map/` | **项目地图**：架构、打包、风险、模块分册 | 维护者 / AI | 否（本仓库内） |
| `docs/Amiya-Bot-docs/` | **SDK 用户文档**：VitePress 站点（`npm run docs:dev`），发布到 amiyabot.com | 插件开发者 / 使用者 | **是**（独立仓库，需单独提交） |

`[事实]` 两者职责不同，**改代码时通常两份都要看**：project-map 判断影响面，SDK docs 决定要不要同步用户可见说明。

## 命令速查

```bash
pip install -e .                       # 源码安装（勿直接跑 setup.py，见「禁区」）
python -c "import amiyabot; print('ok')"   # 冒烟：验证导入与依赖

pylint amiyabot --rcfile=pylint.conf   # Lint —— 与 CI 完全一致
black amiyabot --skip-string-normalization --line-length 120   # 格式化（CI 不跑）

pip show amiyabot                      # 查版本（amiyabot.__version__ 不存在！）
pip check                              # 依赖完整性
```

**没有测试命令。** 项目零测试，无 pytest/tox/nox/pre-commit 配置——不要试图跑它们。

## 目录速查

| 路径 | 作用 |
|---|---|
| `amiyabot/__init__.py` | 门面：`AmiyaBot`、`MultipleAccounts`、全局重导出 |
| `amiyabot/factory/` | 注册表 + 生命周期钩子 + 插件装卸 |
| `amiyabot/handler/messageHandler.py` | **唯一分发中心**，改路由看这里 |
| `amiyabot/adapters/` | 11 个平台适配器（约 3,400 行，最大子系统） |
| `amiyabot/builtin/message/` | 入站模型 `Message`/`Event` + 等待事件 |
| `amiyabot/builtin/messageChain/` | 出站 `Chain` DSL |
| `amiyabot/builtin/lib/` | 事件总线 / 定时任务 / 浏览器 / 图片生成 |
| `amiyabot/database/` | peewee ORM + 自动迁移 |
| `amiyabot/_assets/` | 打包资源（字体、markdown 模板，8.2 MB） |

## 代码风格与约定

- `.editorconfig`：4 空格、LF、文件末尾换行、去尾随空格。
- 行宽上限 **120**（`pylint.conf:339`、`scripts/black.sh:1`）。
- 字符串**不**做规范化（`--skip-string-normalization`），保持既有引号风格。
- 私有成员用 `__name`；容器访问统一走 `get_container(key)`（`factory/factoryCore.py:35`）。
- 新增「属性 ↔ 容器键」必须**同名**：`get_with_plugins()` 靠调用者函数名推断键名（`factoryCore.py:40`）。
- 注释/文档字符串以中文为主，保持一致。

## 禁区与常见坑

| 坑 | 说明 |
|---|---|
| 🚫 **不要 push 到 `master`** | `.github/workflows/pypi.yml:3-6` 在 push 到 master 时**自动发布正式 PyPI**，版本由 PyPI 最新版自增决定，PyPI 版本不可删改。 |
| 🚫 **不要直接跑 `setup.py`** | `setup.py:6` 硬依赖 `wheel`；`:68` 有交互式 `input()`（不带 `--auto-increment-version` 会挂起）；构建期还需联网到 PyPI（`:18`）。（原 `:91-92` 写回 `requirements.txt` 的副作用已移除。） |
| ⚠️ **改 peewee 模型字段名 = 丢数据** | `database/__init__.py:84-85` 对「表有模型无」的列执行 `drop_column`，启动时静默执行，无确认无日志。改 schema 前务必备份。 |
| ⚠️ **`amiyabot.__version__` 不存在** | 源码无 `__version__`，版本只在构建期由 `setup.py:61-65` 计算。用 `pip show amiyabot`。 |
| ⚠️ **`import amiyabot` 需要 playwright 库** | `browserService/__init__.py:1` 顶层导入，无延迟/降级（`amiyabot/__init__.py:30`）。浏览器**二进制**才是可选（仅渲染 HTML 时需要）。 |
| ⚠️ **改动会波及公共 API** | 无 `__all__`、无 `py.typed`、无语义化版本承诺。**弃用类已移除**：`adapters/tencent/__init__.py` 的 `TencentBotInstance` / `TencentSandboxBotInstance` 已删除（旧提示曾被注释、静默失效），文件现仅剩 re-export。 |
| ⚠️ **`implemented.py:89` 的关键字收窄是**有意**的** | `verify()` 在「前缀未通过」时把 `self.keywords` 收窄为 `Equal` 子集，供 `:113` 的 `__check` 消费。**不要**当成副作用删掉。原判「状态污染」已撤回。 |
| ⚠️ **`test` 适配器随包发布** | `adapters/test/` 进 wheel；其端点无鉴权，**不要**把 host 设为 `0.0.0.0`（`test/server.py:40-44,109`）。 |

## 改动后必须跑什么

1. `python -c "import amiyabot"` —— 保证包可导入（最容易踩到急切导入与依赖问题）。
2. `pylint amiyabot --rcfile=pylint.conf` —— 与 CI 门禁一致，PR 会被它拦。
3. `black amiyabot --skip-string-normalization --line-length 120` —— 统一格式（CI 不查，但请保持）。
4. 手动验证：**没有自动化测试可依赖**，涉及适配器/浏览器/数据库的改动必须在真实环境或 `test` 适配器上人工验证。

## 代码改动 → SDK 文档同步

`[事实]` 子模块位置 `docs/Amiya-Bot-docs/`（VitePress，**独立 git 仓库**，需在其内部单独 commit）。
`[事实]` 完整映射表见 [docs/project-map/sdk-docs-sync.md](docs/project-map/sdk-docs-sync.md)。高频对照：

| 你改了什么 | 同步到 |
|---|---|
| `Chain` 及其元素（`.text/.image/.at/...`） | `docs/Amiya-Bot-docs/docs/develop/basic/chainBuild/*.md` |
| `on_message` / `on_event` / `on_exception` | `basic/messageHandler.md`、`basic/handleEvents.md`、`basic/handleException.md` |
| 适配器（新增/改工厂函数/改连接参数） | `develop/adapters/*.md`（qqChannel / qqGroup / qqGlobal / kook / onebot11 / onebot12 / gocq / mah / comwechat） |
| `ChainBuilder` 子类化 | `advanced/chainBuilder.md` |
| 7 个生命周期钩子 | `advanced/lifeCycle.md` |
| `event_bus` | `advanced/eventBus.md` |
| `timed_task` / `TasksControl` | `advanced/timedTask.md` |
| 启动参数（`--text-max-length` 等） | `advanced/startupParameter.md` |
| 插件机制（`PluginInstance` 等） | `develop/plugin/*.md` |
| 数据库 API | `develop/tools/databaseSupport.md` |
| 等待事件 / `Message.wait` | `basic/continuityMessage.md` |

**规则**

1. **新增/修改公共 API → 必须同步**相应 SDK 文档；仅内部重构（不改签名与行为）可不同步。
2. **破坏性变更**（如移除类、改参数）→ 除更新文档外，须在文档显式标注迁移方式。
3. `[事实]` 当前 `docs/develop/adapters/qqChannel.md` 等已使用 `amiyabot.adapters.tencent.qqGuild` 这类**新路径**——改动时保持文档与代码的导入路径一致。
4. `[建议]` 提交顺序：先提 SDK 文档仓库（`cd docs/Amiya-Bot-docs && git commit`），再提本仓库的子模块指针更新。
5. `[事实]` 本仓库的 `docs/project-map/` **不是**用户文档，不要往里写面向使用者的教程；教程一律进 SDK 文档。

## 发布注意事项

- 触发：push 到 `master`（`.github/workflows/pypi.yml:3-6`）→ 自动构建 + 发布**正式 PyPI**。
- 版本：**不是手填的**，由 PyPI 最新版自增（`setup.py:61-63`，规则 `1.0.9→1.1.0`、`1.9.9→2.0.0`）。
- 认证：OIDC Trusted Publishing（`pypi.yml:13-14`，无 `secrets.`）——无 token 泄漏面。
- 无 TestPyPI 预发布环节；`scripts/publish.sh` 是手动 `twine upload dist/*` 的旧路径。
- 手动构建务必带 `--auto-increment-version`。

## 深入阅读

| 分册 | 内容 |
|---|---|
| [project-map/README.md](docs/project-map/README.md) | 索引、模块列表、阅读顺序 |
| [overview.md](docs/project-map/overview.md) | 身份、版本来源、包布局、发布状态 |
| [architecture.md](docs/project-map/architecture.md) | 分层、调用链、分发算法、等待事件 |
| [packaging-release.md](docs/project-map/packaging-release.md) | 打包机制、版本自增、CI、发布注意事项 |
| [packaging-release-wheel.md](docs/project-map/packaging-release-wheel.md) | 正式 wheel 实测证据链 |
| [public-api.md](docs/project-map/public-api.md) | 公开 API 与兼容性 |
| [dependencies.md](docs/project-map/dependencies.md) | 依赖与隐式依赖 |
| [testing-quality.md](docs/project-map/testing-quality.md) | 质量现状与验证闭环 |
| [runbook.md](docs/project-map/runbook.md) | 安装、调试、常见错误 |
| [risks.md](docs/project-map/risks.md) | 风险总表（🔴🟠） |
| [risks-packaging.md](docs/project-map/risks-packaging.md) / [risks-api.md](docs/project-map/risks-api.md) / [risks-low.md](docs/project-map/risks-low.md) | 风险分册（🟡🟢）+ 已否定推断附录 |
| [modules/](docs/project-map/README.md#模块分册) | 模块分册：factory/handler、message/waiter、adapters、builtin/database |
