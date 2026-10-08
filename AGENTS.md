# AGENTS.md

`amiyabot` —— Python 异步渐进式聊天机器人框架（QQ 频道/QQ 群/KOOK/Mirai/OneBot 等适配器 + 消息链 + 关键字路由 + 插件系统）。分发名与导入名均为 `amiyabot`。

> **先读 [docs/project-map/README.md](docs/project-map/README.md)，再按任务读相关分册。**

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
| 🚫 **不要直接跑 `setup.py`** | `setup.py:6` 硬依赖 `wheel`；`:68` 有交互式 `input()`（不带 `--auto-increment-version` 会挂起）；`:91-92` 会**写回** `requirements.txt` 污染 git status。构建期还需联网到 PyPI（`:18`）。 |
| ⚠️ **改 peewee 模型字段名 = 丢数据** | `database/__init__.py:84-85` 对「表有模型无」的列执行 `drop_column`，启动时静默执行，无确认无日志。改 schema 前务必备份。 |
| ⚠️ **`amiyabot.__version__` 不存在** | 源码无 `__version__`，版本只在构建期由 `setup.py:61-65` 计算。用 `pip show amiyabot`。 |
| ⚠️ **`import amiyabot` 需要 playwright 库** | `browserService/__init__.py:1` 顶层导入，无延迟/降级（`amiyabot/__init__.py:30`）。浏览器**二进制**才是可选（仅渲染 HTML 时需要）。 |
| ⚠️ **改动会波及公共 API** | 无 `__all__`、无 `py.typed`、无语义化版本承诺、无弃用机制（旧名弃用提示在 `adapters/tencent/__init__.py:10-17` 被注释掉，静默失效）。 |
| ⚠️ **`implemented.py:89` 的关键字收窄是**有意**的** | `verify()` 在「前缀未通过」时把 `self.keywords` 收窄为 `Equal` 子集，供 `:113` 的 `__check` 消费。**不要**当成副作用删掉。原判「状态污染」已撤回。 |
| ⚠️ **`test` 适配器随包发布** | `adapters/test/` 进 wheel；其端点无鉴权，**不要**把 host 设为 `0.0.0.0`（`test/server.py:40-44,109`）。 |

## 改动后必须跑什么

1. `python -c "import amiyabot"` —— 保证包可导入（最容易踩到急切导入与依赖问题）。
2. `pylint amiyabot --rcfile=pylint.conf` —— 与 CI 门禁一致，PR 会被它拦。
3. `black amiyabot --skip-string-normalization --line-length 120` —— 统一格式（CI 不查，但请保持）。
4. 手动验证：**没有自动化测试可依赖**，涉及适配器/浏览器/数据库的改动必须在真实环境或 `test` 适配器上人工验证。

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
