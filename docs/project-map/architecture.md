# 架构（architecture）

> 证据约定：`[事实]` / `[推断]` / `[建议]` / `[不确定]`。所有结论附 `文件:行`。

## 1. 分层总览

`[事实]` 由导入关系可还原为五层，依赖方向自上而下单向：

```
用户脚本 (main.py, 仓库外)
   │  from amiyabot import AmiyaBot, Message, Chain
   ▼
① 顶层门面        amiyabot/__init__.py        AmiyaBot / MultipleAccounts
   │
   ├─────────────┬──────────────┬─────────────┐
   ▼             ▼              ▼             ▼
② factory/    ③ handler/     ④ builtin/    ⑤ adapters/
   注册表+插件   消息分发      数据结构+能力   平台适配
   │             │              │             │
   └─────────────┴──────────────┴─────────────┘
                                ▼
                         database/  network/
```

`[事实]` 注意 **①→④→⑤ 存在环**：`adapters/__init__.py:10-11` 导入 `builtin.message`/`builtin.messageChain`，而 `amiyabot/__init__.py:11-18` 又导入 adapters。`[推断]` 这使 `amiyabot` 内部没有真正独立的 adapter 层，任何子模块 import 都会拉起近乎整个包。

`[事实]` **`import amiyabot` 是重导入**：顶层 `__init__.py` 依次急切导入全部 8 个适配器（`:11-18`）、factory（`:21`）、handler（`:24`）、eventBus/timedTask/browserService（`:28-30`）、messageChain/message（`:33-42`）。`[建议]` 冷启动成本与依赖面都由此决定。

## 2. 核心入口

| 入口 | 位置 | 说明 |
|---|---|---|
| `AmiyaBot` | `amiyabot/__init__.py:47` | 单账号主入口，继承 `BotInstance` |
| `AmiyaBot.__init__` | `:48-64` | 默认 `adapter=QQGuildBotInstance`（`:53`）；无 appid 时 `random_code(10)` 兜底（`:55-56`） |
| `AmiyaBot.start` | `:66-73` | 启动定时任务 → 可选启动浏览器 → `run_timed_tasks()` → `instance.start(handler)` |
| `AmiyaBot.__message_handler` | `:80-89` | **总入口回调**，所有入站消息/事件都经此进入 `message_handler` |
| `MultipleAccounts` | `:105` | 多账号容器，`append`（`:143`）挂载、`start`（`:128`）并发启动并保活 |

`[事实]` 启动序列（`amiyabot/__init__.py:66-73`）：

```python
async def start(self, launch_browser=False):
    TasksControl.start()                    # :67  幂等启动 apscheduler
    if launch_browser:                      # :69
        await basic_browser_service.launch(...)  # :70
    self.run_timed_tasks()                  # :72  把注册的 Task 灌进调度器
    await self.instance.start(self.__message_handler)  # :73  交给适配器
```

`[事实]` 异常兜底在 `__message_handler` 内：用 `log.catch(ignore=[asyncio.TimeoutError, WaitEventCancel, WaitEventOutOfFocus], handler=...)`（`:84-88`），忽略三类「正常控制流异常」；`__exception_handler`（`:91-102`）按**精确异常类型**查 `exception_handlers`，未注册的子类回落到 `Exception`（`:95-96`）。

## 3. 主要模块与边界

| 模块 | 职责边界 | 关键定义 |
|---|---|---|
| `factory/factoryCore.py` | 纯注册表 + 生命周期钩子容器，**不含分发逻辑** | `FactoryCore:7`、`__container:9-30`、`get_with_plugins:38` |
| `factory/__init__.py` | 对外工厂：装饰器注册、插件装卸 | `BotHandlerFactory:17`、`BotInstance:225`、`PluginInstance:337` |
| `factory/implemented.py` | 关键字/前缀/私信校验的具体实现 | `MessageHandlerItemImpl:11`、`verify:44` |
| `handler/messageHandler.py` | **唯一分发中心**：事件 → 等待事件 → 功能选择 | `message_handler:14`、`find_wait_event:159` |
| `builtin/message/` | 入站数据结构 + 等待事件 | `Message:47`、`WaitEvent:9`、`WaitEventsBucket:99` |
| `builtin/messageChain/` | 出站回复 DSL | `Chain:21`、`ChainBuilder`(`element.py:12`) |
| `adapters/` | 平台协议实现，统一契约 | `BotAdapterProtocol:19` |
| `database/` | peewee ORM + 自动建表/迁移 | `table():63`、`connect_database:93` |
| `network/` | HTTP/WS/下载，多为兼容 shim | `download.py:53`、`httpRequests.py:2` |

`[事实]` **边界规则**：适配器不直接调用 handler；handler 不直接调用 `websockets`。二者只通过 `BotAdapterProtocol.start(handler)` 回调契约与 `Chain` 数据结构耦合（`adapters/__init__.py:80`、`:89`）。

## 4. 典型调用链（入站消息）

`[事实]` 完整链路，逐跳给证据：

```
① 适配器 WS 循环收包
   kook/__init__.py:61-111  /  onebot/v11/__init__.py:60-62 等
   └─ 解析为 Message（event.py→package）
② handler(...) 回调            adapters 把 self.__message_handler 存下
   └─ amiyabot/__init__.py:80  __message_handler
③ message_handler(bot, data)   handler/messageHandler.py:14
   ├─ :18-25  按 appid 建独立 Logger
   ├─ :28-34  非 Message（事件）→ event_handler，结束
   ├─ :46-53  生命周期 message_created（可改写/拦截 data）
   ├─ :56     find_wait_event(data)
   │            └─ handler/messageHandler.py:159  三键查找 + check_alive
   ├─ :59-65  waiter.force → 直接投递，结束
   ├─ :68     choice_handlers(data, bot.message_handlers, waiter)
   │            └─ :133-156  逐个 verify → 按 Verify.weight 降序取第一
   ├─ :72-101 MessageHandlerItem 命中
   │            ├─ :73  factory_name = message_handler_id_map[id(func)]
   │            ├─ :79  生命周期 message_before_handle（False 可拦截）
   │            ├─ :87  await handler.action(data)   ← 用户函数
   │            ├─ :92-95 str 自动包成 Chain
   │            └─ :95  await data.send(reply)
   └─ :103-108 WaitEvent 命中 → handler.set(data) 投递给等待者
④ data.send(chain)             builtin/message/__init__.py:48-55
   └─ bot.processing_context(reply)  factory/__init__.py:61-71
        ├─ process_message_before_send 链（可改写 chain）  :64-65
        └─ process_message_after_send 链                    :70-71
⑤ instance.send_chain_message(chain, is_sync=True)   adapters/__init__.py:89
   └─ 平台 REST 调用（如 tencent/qqGuild/api.py:37）
```

`[事实]` **出站主动消息**走另一条路：`BotAdapterProtocol.send_message`（`adapters/__init__.py:46-58`）先 `build_active_message_chain`（`:53`，补齐 user_id/channel_id，各适配器实现），再包在同一个 `processing_context` 里发送（`:55-56`）。**两条路都经过 `processing_context`**，所以 `message_before_send`/`after_send` 钩子对两者都生效。`[事实]`

## 5. 消息选择算法（核心机制）

`[事实]` `choice_handlers`（`handler/messageHandler.py:133-156`）是框架的调度核心：

1. 若有 waiter，把 `(Verify(True, waiter.level), waiter)` 放进候选（`:137`）。
2. 遍历全部已注册 handler，`await item.verify(data.copy())`——**注意每个 handler 拿到的是 copy**（`:140`）。
3. 按 `Verify.weight` **降序**排序，取第一（`:148-149`）。**无并列保护，先到者胜**。`[推断]` 由 `sorted` 稳定性 + 未做 tie-break 推出。
4. 把胜出 `Verify` 写回 `data.verify`，并执行 `on_selected()` 回调（`:152-154`）——前缀剥离正是借此生效（`factory/implemented.py:82`）。

`[事实]` `verify` 的判定顺序（`factory/implemented.py:44-113`）：私信准入（`:50-60`）→ 前缀 / @ 检查（`:63-91`）→ 自定义 `custom_verify`（`:94-111`）或关键字匹配（`:113`）。

`[事实]` 关键字类型分派用 `type(obj)` 查字典表（`implemented.py:13-17`）：`str`→`check_str`、`Equal`→`check_equal`、`re.Pattern`→`check_reg`；`list` 递归（`:26-30`）。`[事实]` 三者的实现在 `builtin/message/__init__.py:168-190`。

## 6. 等待事件（Waiter）机制

`[事实]` 这是框架最具特色的能力：让某个「功能」挂起，等用户下一条消息。

| 概念 | 位置 | 说明 |
|---|---|---|
| `WaitEvent` | `builtin/message/waitEvent.py:9` | 用户级等待，`type='user'`（`:19`） |
| `ChannelWaitEvent` | `:61` | 频道级等待，`data` 为列表队列（`:65`），`type='channel'`（`:66`） |
| `WaitEventsBucket` | `:99` | 单例桶，`wait_events_bucket`（`:168`） |
| `Message.wait()` | `builtin/message/__init__.py:61-96` | 注册 + 忙等 + 取结果 |
| `Message.wait_channel()` | `:98-149` | 频道级多消息聚合，`focus` 失配抛 `WaitEventOutOfFocus` |

`[事实]` **桶的 key 规则**（三处严格对应）：

| 场景 | key 格式 | 生产 | 消费 |
|---|---|---|---|
| 私信 | `{appid}_{guild_id}_{user_id}` | `message/__init__.py:70` | `messageHandler.py:164` |
| 频道用户 | `{appid}_{channel_id}_{user_id}` | `__init__.py:72` | `messageHandler.py:169` |
| 频道全体 | `{appid}_{channel_id}` | `__init__.py:110` | `messageHandler.py:174` |

`[事实]` 匹配优先级（`messageHandler.py:167-180`）：用户级优先，**频道级 `force=True` 时覆盖用户级**（`:179-180`）。`[事实]` `check_alive()` 抛 `WaitEventCancel` 时视为无 waiter（`:186-187`）。

`[事实]` `check_alive()`（`waitEvent.py:36-46`）做三重校验：不在桶中 → 抛 `WaitEventCancel`（`:37-38`）；`event_id` 与桶中现存事件不一致 → 抛 `WaitEventCancel(del_event=False)`（`:40-41`，即「已被新 waiter 顶替」）；`[事实]` **超时分支被注释掉**（`:43-44`），所以超时只返回 `False` 不抛异常——`[推断]` 这是有意为之：超时应表现为「正常返回 None」，而取消才是异常。

`[事实]` `level` 只影响权重排序（`messageHandler.py:137`），`force` 只影响频道覆盖（`:179`）——两者语义不同，易混淆。`[建议]` 见 [risks.md](risks.md)。

## 7. 生命周期钩子（7 个）

`[事实]` 钩子容器在 `factory/factoryCore.py:18-25`，注册方法 `:91-117`，触发点全在 `handler/messageHandler.py`：

| 钩子 | 触发点 | 能力 |
|---|---|---|
| `event_created` | `messageHandler.py:30-31` | 改写事件 |
| `message_created` | `:46-53` | 改写消息；返回 `False` 丢弃 |
| `message_before_waiter_set` | `:61-63` / `:105-107` | 改写消息（两处） |
| `message_before_handle` | `:79-83` | 返回 `False` 阻止功能执行 |
| `message_before_send` | `factory/__init__.py:64-65` | 改写出站 Chain |
| `message_after_send` | `factory/__init__.py:70-71` | 仅观察 |
| `message_after_handle` | `messageHandler.py:98-99` | 仅观察 |

`[事实]` 这些钩子标注为 `# todo 生命周期 - xxx`，说明是**已知未完成设计**（`factory/__init__.py:63,69`；`messageHandler.py:29,45,60,77,97,104`）。

## 8. 插件系统

`[事实]` 插件即 `PluginInstance`（`factory/__init__.py:337`），本身就是 `BotHandlerFactory` 子类，因此**拥有与主 bot 完全相同的注册能力**（`on_message`/`on_event`/`timed_task`）。

`[事实]` 聚合靠 `get_with_plugins()`（`factory/factoryCore.py:38-61`）：`self.__container[attr] + Σ plugins[attr]`。dict 类型做合并，且 `:58-59` 对 list 值做 `list(set(...))` 去重——`[建议]` 这依赖元素可哈希。

`[事实]` 插件加载三种形态（`factory/__init__.py:237-259`）：目录（Python Package）、`.py` 文件、zip 包（`zipimport` 或解压）；统一以 `getattr(module, 'bot')` 取实例（`:261`）。`install_plugin`（`:270`）断言 plugin_id 唯一（`:286`）；`reload_plugin`（`:321`）深拷贝 path 后卸载重装。

`[事实]` `MultipleAccounts` 通过 `combine_factory`（`:333-334`）把主工厂挂到 `plugins['__factory__']`，实现多账号共享注册表。

`[推断]` `load_plugin` 用 `import_module` 在**同一进程**内执行插件代码，无沙箱、无签名校验——这是设计使然（插件是可信代码），但对「安装任意插件」场景属于固有风险。

## 9. 数据存储与外部依赖

`[事实]` 存储层是 **peewee**，双后端：

| 后端 | 构造 | 证据 |
|---|---|---|
| SQLite（默认） | `SqliteDatabase(database, pragmas={'timeout': 30})` | `database/__init__.py:107` |
| MySQL | `ReconnectMySQLDatabase`（`ReconnectMixin`，自动重连） | `:28`、`:104` |

`[事实]` `connect_database(database, is_mysql=False, config=None)`（`:93`）：MySQL 分支会**先 `CREATE DATABASE IF NOT EXISTS` 再连接**（`:98-104`）；非 MySQL 分支 `create_dir(database, is_file=True)` 建目录（`:106`）。

`[事实]` `@table` 装饰器（`:63-90`）实现**自动 schema 迁移**：`create_table()` 后读 `select * ... limit 1` 的 `description` 拿实际列，与模型字段做**双向差集**，多退少补——缺列 `add_column`（`:80-81`），多列 `drop_column`（`:84-85`）。

`[建议]` `drop_column` 是**破坏性**的：模型里删/改一个字段名，启动时自动 DROP 该列并**丢数据**。这是本项目最危险的设计之一，见 [risks.md](risks.md) R-5。

`[事实]` 外部网络依赖：各平台 API（KOOK `kook/api.py:13`、腾讯 `qqGuild/api.py:34`、`qqGroup/api.py:22,49`）、头像 CDN（`mirai/api.py:43,46`）、PyPI（构建期 `setup.py:18`）。`[推断]` 全部硬编码，无配置化代理入口。

## 10. 异步 / 定时 / 后台任务

`[事实]` 三类后台执行：

| 类型 | 机制 | 位置 |
|---|---|---|
| 定时任务 | apscheduler `AsyncIOScheduler`，单例 `scheduler` | `builtin/lib/timedTask/scheduler.py:9,28` |
| WS 保活 | `while self.keep_run: ... await asyncio.sleep(10)` | 各适配器（详见下） |
| 心跳 | 平台心跳协程 | `kook/__init__.py:113-131`、`qqGuild/__init__.py:181-193` |

`[事实]` 定时任务注册链：`@bot.timed_task(each=...)`（`factory/__init__.py:171-205`）→ `Task(func, each, tag=factory_name, sub_tag=...)`（`:191-200`）→ `run_timed_tasks()` 灌入调度器（`:210-212`）→ `TasksControl.add_timed_task`（`timedTask/__init__.py:27-45`）。`[事实]` job id 为 `f'{tag}.{sub_tag}'`，`sub_tag` 自动带 `key{len}` 序号（`factory/__init__.py:196`）。

`[事实]` 调度器配置 `coalesce=False`、`max_instances=1`（`scheduler.py:13-14`），且在关停时接 `SignalHandler.on_shutdown`（`timedTask/__init__.py:24`）。

`[事实]` **重连无界**：`kook/__init__.py:46-48`、`mirai/__init__.py:55-57`、`onebot/v11/__init__.py:60-62`、`onebot/v12/__init__.py:60-62`、`comwechat/__init__.py:23-25` 均为无限 10 秒重试，**无指数退避、无次数上限**。`[事实]` 仅 QQ 频道有上限：`qqGuild/__init__.py:141` `while self.keep_run and self.model.reconnect_limit > 0`，且 `:73-77` 在网关获取失败时用 `asyncio.create_task(self.start(handler))` **递归自调用**（无上限）。

`[建议]` 见 [risks.md](risks.md) R-6。

## 11. 架构层面的主要判断

`[推断]` 综合证据，三条结构性结论：

1. **分发是线性扫描**。`choice_handlers` 对**每个**入站消息遍历全部 handler 并对每个执行 `data.copy()`（`:139-142`）。`Message.copy()` 是 `deepcopy`（`builtin/message/__init__.py:152-165`）。`[推断]` 复杂度 O(handler 数) 次深拷贝/消息，插件多时是主要开销热点。`[不确定]` 未做基准测试。
2. **`processing_context` 是唯一的出站瓶颈**，所有发送都过它，因此它既是钩子的正确挂载点，也是潜在的串行点（`factory/__init__.py:61-71`）。
3. **适配器层缺少真正共享基类**。`[事实]` 存在 8 份独立 `build_message_send` 与 8 份 `package_*_message`；复用靠继承（`cqhttp`→`onebot11`、`comwechat`→`onebot12`、`qqGroup`→`qqGuild`）而非抽象。

## 相关文档

- 各适配器细节 → [modules/adapters.md](modules/adapters.md)
- 消息与 Chain → [modules/message-and-waiter.md](modules/message-and-waiter.md)
- 工厂与插件 → [modules/factory-and-plugins.md](modules/factory-and-plugins.md)
- 风险 → [risks.md](risks.md)
