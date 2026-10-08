# 项目概览（overview）

> 证据约定：`[事实]` = 有文件/命令证据；`[推断]` = 由证据推导但未直接验证；`[建议]` = 改进意见；`[不确定]` = 未能确认。

## 一句话

`amiyabot` 是一个 **Python 异步渐进式 QQ/聊天平台机器人框架**：对外暴露适配器抽象（QQ频道、QQ群、KOOK、Mirai、OneBot 11/12 等），对内提供消息链、关键字路由、等待事件、定时任务、插件加载、数据库等能力。

## 身份标识

| 项 | 值 | 证据 |
|---|---|---|
| 分发名（PyPI） | `amiyabot` | `setup.py:100` `name='amiyabot'` |
| 导入名 | `amiyabot` | `amiyabot/__init__.py`（flat-layout 包目录同名） |
| 项目描述 | `Python 异步渐进式机器人框架` | `setup.py:106` |
| 作者 / 邮箱 | `vivien8261` / `826197021@qq.com` | `setup.py:102-103` |
| 主页 | `https://www.amiyabot.com` | `setup.py:104` |
| 许可证 | MIT | `setup.py:105` `license='MIT Licence'`；`LICENSE:1` `MIT License` |

`[事实]` 仓库名（Amiya-Bot-core）与分发名（amiyabot）**不同**：git remote 目录为 `Amiya-Bot-core`，但打包名与导入名都是 `amiyabot`。

## 版本与版本来源（重要）

`[事实]` **源码中没有任何 `__version__` 定义**。

```
$ grep -rn "__version__" --include="*.py" amiyabot/
（无输出）
```

版本号有两套，且互不同步：

| 来源 | 值 | 证据 |
|---|---|---|
| `setup.py` 里静态声明 | `0.1.0` | `setup.py:101` `version='0.1.0'` |
| 构建时被覆盖为 PyPI 最新版的新值 | 构建期动态计算 | `setup.py:61-73` |
| PyPI 实际最新发布 | `2.1.0` | `curl https://pypi.org/pypi/amiyabot/json` → `info.version = 2.1.0` |

机制（`[事实]`，`setup.py:17-25, 30-44, 60-73`）：

1. `get_new_version()` 联网请求 `https://pypi.python.org/pypi/amiyabot/json`，取出 `releases` 全部版本号。
2. 用 `ver_num()` 把 `'x.y.z'` 变成整数（`2.1.0` → `210`；`<1000` 时 ×10）后排序取最大 → `latest`。
3. `incr_version()` 按 `1.0.9 → 1.1.0`、`1.9.9 → 2.0.0` 规则自增。
4. `CustomBdistWheelCommand.finalize_options()` 把自增结果写进 `self.distribution.metadata.version`，**覆盖 `setup.py:101` 的 `0.1.0`**。

`[事实]` 版本只在 `bdist_wheel` 这一步产生，源码树里的 `0.1.0` 从不生效。因此：

- `import amiyabot; amiyabot.__version__` → **`AttributeError`**（属性不存在）。`[推断]` 由「grep 无 `__version__`」直接推出。
- 运行时无法感知自身版本；`pip show amiyabot` 才拿得到。`[推断]`

`[建议]` 见 [risks.md](risks.md) R-1 / R-2：这套机制把「构建」与「联网查 PyPI + 自增」耦合，且不产生 git tag。

## 构建后端与 Python 要求

| 项 | 值 | 证据 |
|---|---|---|
| 构建后端 | **setuptools（legacy `setup.py`）**，无 `pyproject.toml` | `setup.py:4` `import setuptools`；`ls pyproject.toml` → 不存在 |
| `[事实]` 无 `pyproject.toml` / `setup.cfg` / `tox.ini` / `noxfile.py` | 全部不存在 | `ls` 各文件均 `No such file or directory` |
| `python_requires` | `>=3.10` | `setup.py:112` |
| PyPI 声明 requires_python | `>=3.10` | PyPI JSON `info.requires_python` |
| 构建期 Python（CI） | `3.10` | `.github/workflows/pypi.yml:22` |
| `classifiers` | **完全没有** | `setup.py:99-117` 无 `classifiers=` 参数 |
| `[事实]` 本机 Python | `3.13.3` | `python3 -c "import sys; print(sys.version)"` |

`[事实]` CI 的构建/lint 只用 3.10，但 `requires-python` 允许 3.10+，且依赖里含 3.13 专属的 `audioop-lts`（`requirements.txt:9`）。`[推断]` 3.11/3.12/3.13 在 CI 中从未被验证。

`[事实]` 无 `classifiers` 意味着 PyPI 上拿不到「Programming Language :: Python :: 3.x」分类，也声明不了 license classifier。

## 包布局

`[事实]` **flat-layout**（非 src-layout）：包目录 `amiyabot/` 直接位于仓库根。

```
amiyabot/              75 个 .py 文件，共 7277 行
$ find amiyabot -name "*.py" | wc -l   → 75
$ find amiyabot -name "*.py" | xargs wc -l | tail -1  → 7277 total
```

| 目录 | 职责 | 证据 |
|---|---|---|
| `amiyabot/adapters/` | 各平台适配器 + 适配器抽象 | `adapters/__init__.py:19` `BotAdapterProtocol` |
| `amiyabot/factory/` | 工厂核心：注册表、生命周期、插件 | `factory/factoryCore.py:7` `FactoryCore` |
| `amiyabot/handler/` | 消息/事件分发 | `handler/messageHandler.py:14` `message_handler` |
| `amiyabot/builtin/message/` | `Message` / `Event` / `Waiter` 数据结构 | `builtin/message/__init__.py`（220 行） |
| `amiyabot/builtin/messageChain/` | `Chain` 回复消息链 DSL | `builtin/messageChain/__init__.py:21` `Chain` |
| `amiyabot/builtin/lib/` | 事件总线、定时任务、浏览器服务、图片生成 | `builtin/lib/eventBus.py`、`timedTask/`、`browserService/` |
| `amiyabot/database/` | peewee ORM 封装 + 自动建表/迁移 | `database/__init__.py:63` `table()` |
| `amiyabot/network/` | 网络层（大量为兼容旧插件的转发 shim） | `network/httpRequests.py:2`、`httpServer.py:2` |
| `amiyabot/_assets/` | 打包数据：字体、markdown 渲染模板 | `du -sh` → `8.2M`，10 个文件 |

`[事实]` 包体积几乎全部来自 `_assets`（8.2 MB）。这是 wheel 体积的主因。`[推断]`

### 项目类型

`[事实]` **框架 / 库**，不是 CLI、不是终端应用：

- `setup.py:99-117` **没有 `entry_points=`**，因此没有 `console_scripts` / `gui_scripts`。
- `[事实]` 无插件 entry points 机制；插件通过 `BotInstance.load_plugin()` 以文件路径/zip 方式动态加载（`factory/__init__.py:230-268`）。
- `[事实]` 使用方式是在用户自己的脚本里 `from amiyabot import AmiyaBot` 然后 `asyncio.run(bot.start())`（`README.md:27-41`）。

## 发布状态

`[事实]` **已发布到 PyPI，且是正式 PyPI（非 TestPyPI）**。

| 项 | 值 | 证据 |
|---|---|---|
| 最新版本 | `2.1.0` | PyPI JSON `info.version` |
| 历史版本数 | 51 | PyPI JSON `len(releases)` |
| 首次发布 | `2022-05-31` | PyPI JSON 最早 release 的 `upload_time` |
| 最新构建时间 | `2026-02-25T08:01:29` | PyPI JSON `amiyabot-2.1.0-535-py3-none-any.whl` |
| 最新 wheel 文件名 | `amiyabot-2.1.0-**535**-py3-none-any.whl` | 同上 |

`[事实]` wheel 文件名里的 `535` **不是版本号**，而是 `setup.py:76` `random.randint(0, 1000)` 生成的随机 build number：`self.build_number = f'{build_number}'`。注释自称目的是「保证 Action 可以重复执行」（`setup.py:75`）。

`[事实]` 发布方式为 **Trusted Publishing（OIDC）**，无 token secret：`.github/workflows/pypi.yml:13-14` 声明 `permissions: id-token: write`，`:12` 使用 `environment: release`，`:34` 使用 `pypa/gh-action-pypi-publish@release/v1`，全文件**没有任何 `secrets.` 引用**。

`[事实]` 发布会触发于 **push 到 `master`**（`.github/workflows/pypi.yml:3-6`）。`[事实]` 当前分支正是 `master`（`git rev-parse --abbrev-ref HEAD` → `master`）。`[推断]` 即：**任何一次向 master 的 push 都会自动构建并发布一个新版本到正式 PyPI**，且版本号由 PyPI 最新版自增决定 —— 这会在 merge PR 时意外发版。详见 [risks.md](risks.md) R-3。

## 证据汇总（本文件用到的只读命令）

```
git rev-parse --abbrev-ref HEAD
grep -rn "__version__" --include="*.py" amiyabot/
find amiyabot -name "*.py" | wc -l
find amiyabot -name "*.py" | xargs wc -l | tail -1
du -sh amiyabot/_assets
python3 -c "import sys; print(sys.version)"
curl -s https://pypi.org/pypi/amiyabot/json
ls pyproject.toml setup.cfg tox.ini noxfile.py
```

## 相关文档

- 架构与调用链 → [architecture.md](architecture.md)
- 打包、版本、发布 → [packaging-release.md](packaging-release.md)
- 风险与雷区 → [risks.md](risks.md)
