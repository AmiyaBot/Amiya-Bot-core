# 项目地图（project map）

**`amiyabot`** —— Python 异步渐进式聊天机器人框架。分发名与导入名均为 `amiyabot`，当前 PyPI 最新版 `2.1.0`。

> 本文档面向**人和 AI 共用**。约定：`[事实]` 有证据 / `[推断]` 由证据推导 / `[建议]` 改进意见 / `[不确定]` 待验证。
> 所有结论附 `文件:行` 或命令输出。**本套文档是只读探索的产物，未改动任何源代码/配置/CI。**

## 快速命令

| 目的 | 命令 | 证据 |
|---|---|---|
| 安装 | `pip install amiyabot` | `README.md:23` |
| 源码安装 | `pip install -e .`（**勿直接跑 `setup.py`**，见坑 1） | — |
| 冒烟检查 | `python -c "import amiyabot; print('ok')"` | — |
| Lint（与 CI 一致） | `pylint amiyabot --rcfile=pylint.conf` | `scripts/pylint.sh:1`、`pylint.yml:24` |
| 格式化 | `black amiyabot --skip-string-normalization --line-length 120` | `scripts/black.sh:1` |
| 查看版本 | `pip show amiyabot`（**`amiyabot.__version__` 不存在**） | `grep -rn "__version__"` 无输出 |
| 查依赖完整性 | `pip check` | — |
| **不要跑** | `pytest` / `tox` / `nox` / `pre-commit`（**未配置**）；`twine upload`（会真发版） | `ls pytest.ini tox.ini noxfile.py` 均不存在 |

## 文档地图

| 文件 | 一句话 |
|---|---|
| [overview.md](overview.md) | 项目身份、分发名/导入名、版本来源、构建后端、包布局、发布状态 |
| [architecture.md](architecture.md) | 五层架构、核心调用链、消息选择算法、等待事件、生命周期钩子、插件 |
| [packaging-release.md](packaging-release.md) | setup.py 机制、版本自增、`_assets` 打包、CI 发布链路、发布注意事项 |
| [packaging-release-wheel.md](packaging-release-wheel.md) | **正式 wheel 实测**：`namelist()`/`RECORD`/METADATA 证据链 |
| [public-api.md](public-api.md) | 公开导入路径、`__all__`/`py.typed` 缺失、`Chain`/`Message` API、弃用策略 |
| [dependencies.md](dependencies.md) | 13 个运行时依赖、6 个隐式依赖、无 extras/无锁定、风险依赖 |
| [testing-quality.md](testing-quality.md) | **零测试**、CI 只跑 pylint、无类型检查、建议的最小验证闭环 |
| [runbook.md](runbook.md) | 安装、最小示例、调试命令、运行时参数、常见错误表、排障清单 |
| [risks.md](risks.md) | **高风险总表**：3 条 🔴 + 6 条 🟠，含证据与建议 |
| [risks-packaging.md](risks-packaging.md) | 🟡 打包与依赖类：R-4 / R-12 / R-14 / R-17 |
| [risks-api.md](risks-api.md) | 🟡 API 与质量类：R-7 / R-9 / R-10 / R-16 |
| [risks-low.md](risks-low.md) | 🟢 低severity：R-8 / R-11 / R-13 / R-18 / R-19 / R-21 / R-22 + 「已否定推断」附录 |

### 模块分册

| 文件 | 一句话 |
|---|---|
| [modules/factory-and-plugins.md](modules/factory-and-plugins.md) | 注册表、7 个生命周期钩子、分发算法、插件装卸（`factory/` + `handler/`） |
| [modules/factory-and-plugins-impl.md](modules/factory-and-plugins-impl.md) | 上者续篇：依赖、数据流、补测建议、风险清单 |
| [modules/message-and-waiter.md](modules/message-and-waiter.md) | `Message`/`Event` 入站模型、关键字匹配、等待事件机制 |
| [modules/adapters.md](modules/adapters.md) | 适配器契约、11 个平台实现对照表、重复代码、平台风险 |
| [modules/builtin-lib-and-database.md](modules/builtin-lib-and-database.md) | `Chain` DSL、事件总线、定时任务、浏览器服务、图片生成、ORM |

> ℹ️ `[事实]` 全部 19 个文档**均 ≤300 行**（按任务约束拆分）。

## 模块列表（代码侧）

`[事实]` 共 75 个 `.py`、7,277 行（`find amiyabot -name "*.py" | xargs wc -l`）。

| 模块 | 一句话 | 分册 |
|---|---|---|
| `amiyabot/__init__.py` | 顶层门面：`AmiyaBot`、`MultipleAccounts`，急切导入几乎整个包 | [architecture](architecture.md) |
| `factory/` | 注册表 + 生命周期容器 + 插件装卸（364+117+116+84 行） | [✅](modules/factory-and-plugins.md) |
| `handler/` | 唯一分发中心 `message_handler`（189 行） | [✅](modules/factory-and-plugins.md) |
| `adapters/` | 11 个平台适配器 + 契约（约 3,400 行，最大子系统） | [✅](modules/adapters.md) |
| `builtin/message/` | 入站模型 + 等待事件（220+167+168 行） | [✅](modules/message-and-waiter.md) |
| `builtin/messageChain/` | 出站 `Chain` DSL + 14 种元素（570 行） | [✅](modules/builtin-lib-and-database.md) |
| `builtin/lib/` | 事件总线、定时任务、浏览器服务、图片生成 | [✅](modules/builtin-lib-and-database.md) |
| `database/` | peewee 双后端 + `@table` 自动迁移（131 行） | [✅](modules/builtin-lib-and-database.md) |
| `network/` | HTTP/下载；**多数为兼容旧插件的转发 shim** | [⬜ TODO](#未完成-todo) |
| `log/`、`util/`、`typeIndexes.py`、`signalHandler.py` | 2 行 shim / 类型索引 / SIGINT 处理 | [⬜ TODO](#未完成-todo) |

图例：✅ = 已有分册；⬜ = 待补。

## 阅读顺序

| 你的目的 | 读什么 |
|---|---|
| **新人上手** | [overview.md](overview.md) → [architecture.md](architecture.md) §1-4 → [runbook.md](runbook.md) §2 |
| **改消息处理/路由** | [architecture.md](architecture.md) §5-6 → [modules/factory-and-plugins.md](modules/factory-and-plugins.md) → [modules/message-and-waiter.md](modules/message-and-waiter.md) |
| **加/改适配器** | [modules/adapters.md](modules/adapters.md) §2（契约）→ §3（对照表）→ §5（重复代码） |
| **改打包/发版** | [packaging-release.md](packaging-release.md) 全文 → [risks.md](risks.md) R-1/R-3 |
| **排障** | [runbook.md](runbook.md) §7（错误表）→ §8（检查清单）→ [risks.md](risks.md) |
| **评估技术债** | [risks.md](risks.md) 全文 → [testing-quality.md](testing-quality.md) |
| **AI 改代码前** | [AGENTS.md](../../AGENTS.md) → 本文件 → 对应分册 |

## 核心速记（最该记住的 6 件事）

1. `[事实]` **默认适配器是 QQ 频道**（`amiyabot/__init__.py:53`）——不传 `adapter` 会连腾讯 API。
2. `[事实]` **版本号源码里没有**，只在 `bdist_wheel` 时联网从 PyPI 自增产生（`setup.py:61-65`）；`amiyabot.__version__` 会 `AttributeError`。
3. `[事实]` **push 到 `master` 会自动发布正式 PyPI**（`.github/workflows/pypi.yml:3-6`），不要随手推。
4. `[事实]` **`@table` 会按模型字段自动 `drop_column`**（`database/__init__.py:84-85`）——改字段名 = 丢数据。
5. `[事实]` **项目零测试**，CI 只有 pylint 且仅在 PR 触发。
6. `[事实]` **`import amiyabot` 会急切导入 playwright**（`browserService/__init__.py:1`），必须先装 playwright 库。

## 未完成 TODO

`[事实]` 本套文档按「先索引 + 全局分册 + 核心模块」策略完成，以下为**有意留下的待补项**：

### 文档待补

- ⬜ `modules/network.md` —— `network/` 是兼容 shim，但被 6 处适配器引用（`kook/api.py:5`、`mirai/api.py:8`、`qqGuild/api.py:6`、`onebot/v11/api.py:3`、`onebot/v12/api.py:3`），值得单独说明「旧插件兼容层」的边界与移除路径。
- ⬜ `modules/tencent-deep-dive.md` —— `adapters/tencent/` 约 1,500 行、含 `qqGuild/api.py`（525 行，全仓库最大文件）、三层继承、`PortSingleton`、双路由 `qqGlobal`，本套仅在 [adapters.md](modules/adapters.md) §4.4 做了概要。
- ⬜ `glossary.md` —— 领域术语（`Chain`/`Waiter`/`GroupConfig`/`prefix_keywords`/`factory_name`/`Intents` 等）尚未汇总。**本次判断：核心概念已在各分册就地解释，故未新建。**
- ⬜ 逐文件级 API 参考 —— 有意不做（避免生成百科，见任务约束）。

### 代码侧 TODO（本次**未处理**，仅记录）

`[事实]` 以下均来自源码注释或本次审计，**属代码改动，超出本次授权范围**：

- ⬜ `[事实]` 7 处 `# todo 生命周期 - xxx` 标注（`factory/__init__.py:63,69`；`handler/messageHandler.py:29,45,60,77,97,104`）——生命周期设计未完成。
- ⬜ `[事实]` `waitEvent.py:43-44` 超时分支被注释掉。
- ⬜ `[建议]` 补文档说明 `data.verify.keypoint`（命中的关键字 / 正则分组列表）——这是**文档缺口，非代码缺陷**。原 R-20 判为「状态污染」，经复核已撤回（见 [risks.md](risks.md) R-20）。
- ⬜ `[建议]` 修 R-4（`setup.py:94-97,110` 重复落盘 + `MANIFEST.in:1` 目录名错）+ 减 wheel 体积。
- ⬜ `[建议]` 加 `py.typed`（R-7）；加 `__version__`（R-2）；扩 CI matrix（R-10）。
- ⬜ `[建议]` 补最小测试集（见 [testing-quality.md](testing-quality.md) §7）。

### 待验证（`[不确定]`）

- ⬜ **sdist** 中 `_assets` 是否完整——本次只解包校验了 **wheel**（已在 [packaging-release.md](packaging-release.md) §8 实测确认资源存在并被重复落盘）。
- ⬜ `setup.py:10` `ver_num()` 的版本换算在边界（如 `10.0.0`、`99.9.9`）上的单调性未穷举验证。
- ⬜ KOOK 心跳 `create_task`（`kook/__init__.py:122`）是否堆积任务——需运行时验证。
- ⬜ `test` 适配器在 `0.0.0.0` 下的实际可利用性——需运行时验证。
- ⬜ `timedTask` 重复 job id 是否触发 apscheduler `ConflictingIdError`。
- ⬜ `choice_handlers` 深拷贝开销未做基准测试。

## 导航

- AI/人通用速查 → [AGENTS.md](../../AGENTS.md)
- 风险总表 → [risks.md](risks.md)
