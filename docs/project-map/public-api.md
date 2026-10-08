# 公共 API（public-api）

> 证据约定：`[事实]` / `[推断]` / `[建议]` / `[不确定]`。

## 1. 公开导入路径

`[事实]` 对外门面是 **`amiyabot/__init__.py`**，用户在 `README.md:30` 只 `from amiyabot import AmiyaBot, Message, Chain`。该文件导入并因此重导出的名字（`:11-42`）：

| 类别 | 名字 | 来源行 |
|---|---|---|
| 适配器 | `BotAdapterProtocol`, `KOOKBotInstance`, `MiraiBotInstance`, `CQHttpBotInstance`, `OneBot11Instance`, `OneBot12Instance`, `QQGuildBotInstance`, `QQGuildSandboxBotInstance`, `ComWeChatBotInstance` | `:11-18` |
| 工厂 | `BotInstance`, `PluginInstance`, `GroupConfig` | `:21` |
| 处理器 | `message_handler`, `SignalHandler` | `:24-25` |
| 内置库 | `event_bus`, `TasksControl`, `BrowserLaunchConfig`, `basic_browser_service` | `:28-30` |
| 消息链 | `Chain`, `ChainBuilder`, `InlineKeyboard`, `CQCode` | `:33` |
| 消息结构 | `Event`, `EventList`, `Message`, `Waiter`, `WaitEventCancel`, `WaitEventOutOfFocus`, `Equal` | `:34-42` |
| 主类 | `AmiyaBot`（`:47`）、`MultipleAccounts`（`:105`） | 本文件定义 |

`[事实]` 另有二级导入路径，README 中已示范：

- `from amiyabot.adapters.onebot.v11 import onebot11`（`README.md:71`）
- `from amiyabot.adapters.tencent.qqGuild import ...`

`[建议]` 用户应优先用顶层 `amiyabot` 路径；二级路径（`amiyabot.adapters.*`、`amiyabot.builtin.*`）属实现细节。

## 2. `__all__` 与类型标注

`[事实]` **全仓没有 `__all__`**：

```
$ grep -rn "__all__" --include="*.py" amiyabot/
（无输出）
```

`[推断]` 因此「公共 API」**没有机器可读的边界**：`from amiyabot import *` 会导入 `__init__.py` 命名空间里所有非下划线名字，包括 `jieba`、`typing`、`asyncio` 等第三方/标准库模块（`amiyabot/__init__.py:1-3`）。这是真实的 API 卫生问题。

`[事实]` **没有 `py.typed`，也没有 `.pyi` 存根**：

```
$ find . -name "py.typed" -o -name "*.pyi" | grep -v .venv
（无输出）
```

`[推断]` 后果：即使调用方装了 mypy/pyright，本包也被视为 untyped，**所有来自 `amiyabot` 的类型推断在调用方被静默忽略**（除非用户 `ignore_missing_imports=False` 而报错）。这是「渐进式框架」在类型生态上的明显缺口。

`[事实]` 但**代码内部类型标注相当规范**：`factory/factoryTyping.py:10-32` 定义了整套 Callable 别名（`FunctionType`、`EventHandlerType`、`ExceptionHandlerType`、7 个生命周期钩子类型），并用 `dataclass` 建模（`GroupConfig:35`、`MessageHandlerItem:46`）。`[推断]` 类型标注是给内部/IDE 用的，未对外发布为可消费的类型信息。

`[建议]` 加 `py.typed` 是提升下游体验性价比最高的一步（见 [risks.md](risks.md) R-7）。**本次不改动。**

## 3. 主要类、函数与命令

### 3.1 顶层主类

| 名字 | 位置 | 说明 |
|---|---|---|
| `AmiyaBot` | `amiyabot/__init__.py:47` | 单账号入口；`__init__(appid, token, private=False, adapter=QQGuildBotInstance)`（`:48-54`） |
| `AmiyaBot.start(launch_browser=False)` | `:66` | 异步启动，含定时任务与可选浏览器 |
| `AmiyaBot.close()` | `:75` | 幂等关闭（`__closed` 保护，`:62`） |
| `MultipleAccounts` | `:105` | 多账号容器；`append`（`:143`）、`start`（`:128`）、`close`（`:162`）；支持 `in`/`[]`/`del`/迭代（`:115-126`） |

`[事实]` `AmiyaBot` 与 `MultipleAccounts` 都自动注册到 `SignalHandler.on_shutdown`（`:64`、`:113`），SIGINT 时触发关停。

### 3.2 注册装饰器（面向用户的主要 API）

`[事实]` 全部定义在 `BotHandlerFactory`（`factory/__init__.py:17`），因此 `AmiyaBot`、`MultipleAccounts`、`PluginInstance` 都有：

| 装饰器 | 位置 | 参数要点 |
|---|---|---|
| `@bot.on_message(...)` | `:73-117` | `group_id`, `keywords`, `verify`, `check_prefix`, `allow_direct`, `direct_only`, `level` |
| `@bot.on_event(events)` | `:119-143` | 默认 `'__all_event__'` 捕获全部事件 |
| `@bot.on_exception(exceptions)` | `:145-169` | 按异常类型注册，默认 `Exception` |
| `@bot.timed_task(each, ...)` | `:171-205` | 定时任务，`each` 秒 |
| `set_group_config` / `set_prefix_keywords` | `:214-219` | 非装饰器配置 |

`[事实]` 生命周期钩子注册器（`factory/factoryCore.py:91-117`，7 个）也是公共 API：`event_created`、`message_created`、`message_before_waiter_set`、`message_before_handle`、`message_before_send`、`message_after_send`、`message_after_handle`。

### 3.3 `Message` 与 `Chain`

| 名字 | 位置 | 公共成员 |
|---|---|---|
| `Message` | `builtin/message/__init__.py:47` | `send`（`:48`）、`recall`（`:57`）、`wait`（`:61`）、`wait_channel`（`:98`）、`copy`（`:151`） |
| `MessageStructure` 字段 | `builtin/message/structure.py:25-71` | `text`/`text_prefix`/`text_digits`/`text_unsigned`/`text_original`/`text_words`（`:44-49`）、`at_target`（`:51`）、`is_at`/`is_at_all`/`is_admin`/`is_direct`（`:53-56`）、`user_id`/`user_openid`（`:58-59`）、`channel_id`/`channel_openid`（`:61-62`）、`guild_id`/`src_guild_id`（`:64-65`）、`nickname`/`avatar`（`:67-68`）、`verify`（`:70`） |
| `Chain` | `builtin/messageChain/__init__.py:21` | 见下表链式方法 |
| `ChainBuilder` | `builtin/messageChain/element.py:12` | 4 个可覆写 classmethod 钩子：`get_image`（`:13`）、`get_voice`（`:17`）、`get_video`（`:21`）、`on_page_rendered`（`:25`） |
| `InlineKeyboard` | `builtin/messageChain/keyboard.py` | 按钮/行构建；上限各 5（`:64-65`、`:98-99`） |
| `CQCode` | `builtin/messageChain/element.py:222` | CQ 码元素 |

`[事实]` `Chain` 链式方法全貌（全 `return self`）：

| 方法 | 行 | 方法 | 行 |
|---|---|---|---|
| `.at()` | `:61` | `.voice()` | `:151` |
| `.at_all()` | `:71` | `.video()` | `:155` |
| `.tag()` | `:75` | `.html()` | `:159` |
| `.face()` | `:79` | `.markdown()` | `:181` |
| `.text()` | `:83` | `.markdown_template()` | `:202` |
| `.text_image()` | `:114` | `.embed()` | `:212` |
| `.image()` | `:134` | `.ark()` | `:216` |
| | | `.extend()` | `:220` |

`[事实]` 元素类型共 14 个 dataclass（`element.py`）：`At:30`、`AtAll:35`、`Tag:39`、`Face:44`、`Text:49`、`Image:54`、`Voice:68`、`Video:82`、`Html:95`、`Embed:156`、`Ark:174`、`Markdown:188`、`Extend:212`、`CQCode:222`。

### 3.4 适配器契约

`[事实]` `BotAdapterProtocol`（`adapters/__init__.py:19`）——**注意它并非真正的 ABC**：

```python
class BotAdapterProtocol:          # :19  未继承 abc.ABC
    @abc.abstractmethod            # :72  装饰器因此不被强制
    async def close(self): ...
```

`[事实]` 5 个待实现方法：`close`（`:72`）、`start`（`:79`）、`send_chain_message`（`:88`）、`build_active_message_chain`（`:99`）、`recall_message`（`:114`）。基类提供 `set_alive`（`:43`）、`send_message`（`:46`）、`get_websocket_connection`（`:60`）、`api` property（`:68`）。

`[事实]` 二层契约 `BotInstanceAPIProtocol`（`adapters/apiProtocol.py:6`）：`get`（`:7`）、`post`（`:11`）、`request`（`:15`），`get_user_avatar` 有默认实现（`:19-20`）。

`[事实]` 未继承 `abc.ABC` 意味着**漏实现方法不会在实例化时报错**，而是运行到才 `NotImplementedError`。`[建议]` 见 [risks.md](risks.md) R-8。

### 3.5 适配器工厂函数（公共构造入口）

| 函数 | 位置 | 签名 |
|---|---|---|
| `mirai_api_http` | `adapters/mirai/__init__.py:19` | `(host, ws_port, http_port)` |
| `cq_http` | `adapters/cqhttp/__init__.py:7` | `(host, ws_port, http_port)` |
| `onebot11` | `adapters/onebot/v11/__init__.py:18` | `(host, ws_port, http_port)` |
| `onebot12` | `adapters/onebot/v12/__init__.py:18` | `(host, ws_port, http_port)` |
| `com_wechat` | `adapters/comwechat/__init__.py:11` | `(host, ws_port, http_port)` |
| `qq_guild_shards` | `adapters/tencent/qqGuild/__init__.py:19` | `(shard_index, shards, sandbox=False)` |
| `qq_group` | `adapters/tencent/qqGroup/__init__.py:104` | 别名 → `build_adapter(client_secret, ...)`（`:38-55`） |
| `qq_global` | `adapters/tencent/qqGlobal/__init__.py:35` | 继承同上 |
| `test_instance` | `adapters/test/__init__.py:14` | `(host='127.0.0.1', port=32001)` |

`[事实]` **KOOK 没有工厂函数**，直接用 `KOOKBotInstance(appid, token)`（`adapters/kook/__init__.py:17`）。`[推断]` 这是不一致的：8 个平台有闭包工厂、KOOK 用裸类、`qq_group`/`qq_global` 用类属性 `build_adapter`，三种风格并存。

`[事实]` 统一调用点是 `factory/__init__.py:33` `self.instance = adapter(appid, token)`，而参数注解是 `Optional[Type[BotAdapterProtocol]]`（`:22`）——**注解与实际类型不符**（实际传的是返回实例的闭包/类）。`[建议]`

### 3.6 CLI 命令

`[事实]` **没有 CLI**。无 `entry_points`（`setup.py:99-117`），无 `__main__.py`：

```
$ find amiyabot -name "__main__.py"
（无输出）
```

`[推断]` 项目是纯库。用户唯一入口是自己写脚本（`README.md:27-41`）。

`[事实]` 但**运行时读取命令行参数**：`ChainConfig.max_length = argv('text-max-length', int) or 100`（`messageChain/__init__.py:17`）、`page_pool_size = argv('browser-page-pool-size')`（`browserService/launchConfig.py:9,19`）、`debug = argv('debug')`（`:20`）——这些是 `amiyautils.argv` 读取的**宿主脚本**命令行参数。`[推断]` 属于隐式配置，文档中需说明。

## 4. 弃用与语义化版本策略

`[事实]` **已发生过一次弃用移除**：`amiyabot/adapters/tencent/__init__.py` 曾定义两个别名子类 `TencentBotInstance`（原 `:4`）与 `TencentSandboxBotInstance`（原 `:7`），并附有一段**被注释掉的 `print()` 弃用提示**（原 `:10-17`，自述 `"will be removed in future versions"`）。

`[事实]` **该弃用已执行完毕（本次移除）**：两个类定义与注释块均已删除，文件现仅剩 1 行 re-export：

```python
from .qqGuild import QQGuildBotInstance, QQGuildSandboxBotInstance
```

`[事实]` **影响与迁移路径**：

| 项 | 说明 |
|---|---|
| 受影响写法 | `from amiyabot.adapters.tencent import TencentBotInstance`（或 `TencentSandboxBotInstance`）→ **`ImportError`** |
| **不受影响** | `from amiyabot.adapters.tencent import QQGuildBotInstance`（因保留 re-export，仍可用） |
| 推荐迁移 | `from amiyabot.adapters.tencent.qqGuild import QQGuildBotInstance, QQGuildSandboxBotInstance` |
| 内部是否受影响 | **无**。仓库内部代码全部直接引用 `amiyabot.adapters.tencent.qqGuild`（`amiyabot/__init__.py:17`、`qqGroup/__init__.py:6`、`qqGlobal/__init__.py:2,3`） |
| 默认适配器 | 是 `QQGuildBotInstance`（`amiyabot/__init__.py:53`），**非**别名，故不影响零配置用户 |

`[事实]` 这次移除也印证了「无正式弃用机制」：提示从未真正生效（`print()` 被注释、静默失效），用户实际是**在移除时才感知**的。`[建议]` 后续若有弃用需求，宜改用 `warnings.warn(..., DeprecationWarning)`。

`[事实]` **没有语义化版本承诺**：

- 版本号由 PyPI 最新版自增产生（`setup.py:61-63`），**与改动性质无关**（patch/minor/major 不由 break change 决定）。
- `[事实]` 无 `CHANGELOG`：`ls CHANGELOG*` 无结果；仅靠 git log（中文/英文混合的 commit message）。
- `[事实]` 无 `CONTRIBUTING`。

`[推断]` 综合：`2.x` 期间的类型/接口变动无法从版本号预判。公开 API（如 `on_message` 的参数、`Chain` 的方法、`BotAdapterProtocol` 的抽象方法）**无兼容性契约**。

`[建议]` 见 [risks.md](risks.md) R-9。**本次不改动。**

## 5. Python 版本兼容性

| 项 | 值 | 证据 |
|---|---|---|
| `python_requires` | `>=3.10` | `setup.py:112` |
| PyPI 元数据 | `>=3.10` | PyPI JSON `info.requires_python` |
| CI 构建/lint | 仅 `3.10` | `pypi.yml:22`、`pylint.yml:10` |
| `classifiers` | **无** | `setup.py:99-117` 无 `classifiers=` |
| 本机解释器 | `3.13.3` | `python3 -c "import sys; print(sys.version)"` |

`[事实]` `requirements.txt:9` 含条件依赖 `audioop-lts~=0.2.1; python_version>='3.13'`，说明**作者有意支持 3.13**（`audioop` 在 3.13 被移除）。`[事实]` 但 `.github/workflows/pylint.yml:10` 矩阵只有 `3.10`。`[推断]` **3.11 / 3.12 / 3.13 从未在 CI 验证**，3.13 支持是「声明式」而非「验证式」。

`[事实]` 无 `classifiers` 导致 PyPI 页面缺少 Python 版本徽章，也没声明 license classifier。

`[建议]` 见 [risks.md](risks.md) R-10。

## 6. 公共 API 稳定性小结

`[推断]` 按「用户可见程度 × 变更风险」给一个实用判断：

| 稳定性 | 组件 | 理由 |
|---|---|---|
| 高（事实标准） | `AmiyaBot`、`MultipleAccounts`、`on_message`/`on_event`、`Message`、`Chain` | README 示范、生态插件依赖 |
| 中 | `PluginInstance`、`ChainBuilder`、`Event`/`EventList` | 插件开发需要，但签名较易变动 |
| 低（实现细节） | `amiyabot.builtin.*`、`amiyabot.factory.*`、`adapters/*/api.py` | 无 `__all__` 边界，改动随意 |
| 明确不稳定 | `amiyabot.network.*` | 文件头自述「兼容旧版插件」（`network/httpRequests.py:1`、`httpServer.py:1`） |

`[事实]` `amiyabot/network/` 三个文件中两个是纯转发 shim（`httpRequests.py` 2 行、`httpServer.py` 3 行），`__init__.py` 为 0 行空文件。`[事实]` 但内部仍在用：6 处适配器导入 `amiyabot.network.httpRequests`（如 `kook/api.py:5`、`mirai/api.py:8`、`qqGuild/api.py:6`、`onebot/v11/api.py:3`、`onebot/v12/api.py:3`）。

## 相关文档

- 项目身份与版本来源 → [overview.md](overview.md)
- 架构与调用链 → [architecture.md](architecture.md)
- 风险排序 → [risks.md](risks.md)
